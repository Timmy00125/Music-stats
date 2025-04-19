import base64
import requests
import secrets
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status, APIRouter, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from urllib.parse import urlencode

from app.database import get_db
from app.models import User
from app.config import settings

router = APIRouter()

# Spotify authorization scopes
SPOTIFY_SCOPES = [
    "user-read-private",
    "user-read-email",
    "user-read-recently-played",
    "user-top-read"
]


def generate_spotify_oauth_url():
    """
    Generate the Spotify authorization URL for OAuth flow
    """
    state = secrets.token_urlsafe(16)
    params = {
        "client_id": settings.SPOTIFY_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": settings.SPOTIFY_REDIRECT_URI,
        "scope": " ".join(SPOTIFY_SCOPES),
        "state": state,
        "show_dialog": "true"
    }
    return f"https://accounts.spotify.com/authorize?{urlencode(params)}", state


def get_spotify_tokens(code: str):
    """
    Exchange the authorization code for access and refresh tokens
    """
    auth_string = f"{settings.SPOTIFY_CLIENT_ID}:{settings.SPOTIFY_CLIENT_SECRET}"
    auth_bytes = auth_string.encode("utf-8")
    auth_base64 = base64.b64encode(auth_bytes).decode("utf-8")

    headers = {
        "Authorization": f"Basic {auth_base64}",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": settings.SPOTIFY_REDIRECT_URI
    }

    response = requests.post(
        "https://accounts.spotify.com/api/token",
        headers=headers,
        data=data
    )

    if response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to get Spotify tokens"
        )

    return response.json()


def refresh_spotify_token(refresh_token: str):
    """
    Refresh the Spotify access token using the refresh token
    """
    auth_string = f"{settings.SPOTIFY_CLIENT_ID}:{settings.SPOTIFY_CLIENT_SECRET}"
    auth_bytes = auth_string.encode("utf-8")
    auth_base64 = base64.b64encode(auth_bytes).decode("utf-8")

    headers = {
        "Authorization": f"Basic {auth_base64}",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token
    }

    response = requests.post(
        "https://accounts.spotify.com/api/token",
        headers=headers,
        data=data
    )

    if response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to refresh Spotify token"
        )

    return response.json()


def get_spotify_user_info(access_token: str):
    """
    Get the user's Spotify profile information
    """
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get("https://api.spotify.com/v1/me", headers=headers)

    if response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to get user info from Spotify"
        )

    return response.json()


def get_current_user(db: Session = Depends(get_db), token: str = None):
    """
    Get the current user based on the provided token
    If the token is expired, it refreshes it
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )

    user = db.query(User).filter(User.access_token == token).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

    # Check if token is expired
    if user.token_expires_at < datetime.now():
        # Refresh token
        try:
            token_data = refresh_spotify_token(user.refresh_token)

            # Update user with new tokens
            user.access_token = token_data.get("access_token")
            user.token_expires_at = datetime.now() + timedelta(seconds=token_data.get("expires_in", 3600))

            # If a new refresh token is provided, update it
            if "refresh_token" in token_data:
                user.refresh_token = token_data["refresh_token"]

            db.commit()
            db.refresh(user)
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Token refresh failed: {str(e)}"
            )

    return user


# Routes
@router.get("/login")
def login():
    """
    Redirect the user to Spotify for authorization
    """
    auth_url, _ = generate_spotify_oauth_url()
    return RedirectResponse(url=auth_url)


@router.get("/callback")
def callback(code: str, state: str, db: Session = Depends(get_db)):
    """
    Handle the callback from Spotify after user authorization
    """
    # Exchange the authorization code for tokens
    token_data = get_spotify_tokens(code)

    # Get user info from Spotify
    user_info = get_spotify_user_info(token_data["access_token"])

    # Check if user already exists
    user = db.query(User).filter(User.spotify_user_id == user_info["id"]).first()

    if user:
        # Update existing user
        user.access_token = token_data["access_token"]
        user.refresh_token = token_data["refresh_token"]
        user.token_expires_at = datetime.now() + timedelta(seconds=token_data["expires_in"])
        user.spotify_display_name = user_info.get("display_name")
        user.email = user_info.get("email")
    else:
        # Create new user
        user = User(
            spotify_user_id=user_info["id"],
            spotify_display_name=user_info.get("display_name"),
            email=user_info.get("email"),
            access_token=token_data["access_token"],
            refresh_token=token_data["refresh_token"],
            token_expires_at=datetime.now() + timedelta(seconds=token_data["expires_in"])
        )
        db.add(user)

    db.commit()
    db.refresh(user)

    # Redirect to frontend with token
    # In a real application, you might want to use cookies or sessions instead of exposing the token in the URL
    return RedirectResponse(url=f"/success?token={user.access_token}")