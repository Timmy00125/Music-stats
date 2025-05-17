import base64
import requests
import secrets
from datetime import datetime, timedelta, timezone  # Import timezone
from fastapi import (
    Depends,
    HTTPException,
    status,
    APIRouter,
    Request,
    Response,
)  # Import Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from urllib.parse import urlencode
from jose import JWTError, jwt  # Import JWT handling
from pydantic import BaseModel
from typing import Any  # Import Any for precise type hinting

from app.database import get_db
from app.models import User
from app.config import settings

router = APIRouter()

# --- Constants ---
SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API_BASE_URL = "https://api.spotify.com/v1"
SPOTIFY_SCOPES = [
    "user-read-private",
    "user-read-email",
    "user-read-recently-played",
    "user-top-read",
]
# Cookie name for storing the state parameter during OAuth flow
OAUTH_STATE_COOKIE = "spotify_oauth_state"
# Cookie name for storing the JWT access token
ACCESS_TOKEN_COOKIE = "spotify_stats_access_token"


# --- Helper Models ---
class TokenData(BaseModel):
    """Pydantic model for JWT payload"""

    user_id: str | None = None


# --- JWT Utilities ---
def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None):
    """Creates a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        # Default expiry if not provided (e.g., 15 minutes)
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


# --- Spotify API Interaction (existing functions slightly adapted) ---


def get_spotify_tokens(code: str):
    """Exchange the authorization code for access and refresh tokens"""
    auth_string = f"{settings.SPOTIFY_CLIENT_ID}:{settings.SPOTIFY_CLIENT_SECRET}"
    auth_bytes = auth_string.encode("utf-8")
    auth_base64 = base64.b64encode(auth_bytes).decode("utf-8")

    headers = {
        "Authorization": f"Basic {auth_base64}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": settings.SPOTIFY_REDIRECT_URI,
    }

    response = requests.post(SPOTIFY_TOKEN_URL, headers=headers, data=data)
    response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
    return response.json()


def refresh_spotify_token(refresh_token: str):
    """Refresh the Spotify access token using the refresh token"""
    auth_string = f"{settings.SPOTIFY_CLIENT_ID}:{settings.SPOTIFY_CLIENT_SECRET}"
    auth_bytes = auth_string.encode("utf-8")
    auth_base64 = base64.b64encode(auth_bytes).decode("utf-8")

    headers = {
        "Authorization": f"Basic {auth_base64}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {"grant_type": "refresh_token", "refresh_token": refresh_token}

    response = requests.post(SPOTIFY_TOKEN_URL, headers=headers, data=data)
    response.raise_for_status()  # Raise HTTPError for bad responses
    return response.json()


def get_spotify_user_info(access_token: str):
    """Get the user's Spotify profile information"""
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(f"{SPOTIFY_API_BASE_URL}/me", headers=headers)
    response.raise_for_status()  # Raise HTTPError for bad responses
    return response.json()


# --- Authentication Dependency ---


async def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """
    Dependency to get the current user based on the JWT stored in the cookie.
    Handles token validation, expiration, and Spotify token refresh if needed.
    """
    token = request.cookies.get(ACCESS_TOKEN_COOKIE)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated (Missing Token Cookie)",
            headers={"WWW-Authenticate": "Bearer"},
        )

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # Decode the JWT
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        # Fix for: Type "Any | None" is not assignable to declared type "str"
        _jwt_sub = payload.get("sub")  # "sub" is the standard claim for subject
        if not isinstance(_jwt_sub, str):  # Ensures _jwt_sub is a string, handles None
            raise credentials_exception
        user_id: str = _jwt_sub  # Now _jwt_sub is confirmed to be str.
        token_data_model = TokenData(user_id=user_id)  # Renamed to avoid clash later
    except JWTError:
        raise credentials_exception

    # Find user in database using the internal user_id from the JWT
    user = db.query(User).filter(User.user_id == token_data_model.user_id).first()
    if user is None:
        raise credentials_exception

    # --- Spotify Token Refresh Logic (Optional but recommended here) ---
    # Check if the stored Spotify token is expired or close to expiring
    # Add a buffer (e.g., 5 minutes) to refresh before actual expiry
    # Make naive datetime timezone-aware by replacing it with a timezone-aware one
    token_expires_at_utc = user.token_expires_at.replace(tzinfo=timezone.utc)
    if token_expires_at_utc < datetime.now(timezone.utc) + timedelta(minutes=5):
        try:
            print(f"Refreshing Spotify token for user {user.user_id}")  # Add logging
            # Fix for: Argument of type "Column[str]" cannot be assigned to parameter "refresh_token"
            refreshed_token_payload = refresh_spotify_token(str(user.refresh_token))

            # Update user with new Spotify tokens
            user.access_token = refreshed_token_payload.get("access_token")
            # Ensure expires_in is handled correctly, default to 1 hour if missing
            expires_in = refreshed_token_payload.get("expires_in", 3600)
            # Store naive datetime to match the model's DateTime column definition
            expiry_time = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
            # Fix for: "datetime" is not assignable to "Column[datetime]"
            setattr(user, "token_expires_at", expiry_time.replace(tzinfo=None))

            # Spotify might issue a new refresh token
            if "refresh_token" in refreshed_token_payload:
                user.refresh_token = refreshed_token_payload["refresh_token"]

            db.commit()
            db.refresh(user)
            print(
                f"Spotify token refreshed successfully for user {user.user_id}"
            )  # Add logging
        except requests.exceptions.RequestException as e:
            # If refresh fails, the user might need to re-authenticate
            db.rollback()
            print(
                f"Spotify token refresh failed for user {user.user_id}: {e}"
            )  # Add logging
            # Depending on the error, you might let the request proceed
            # or force re-authentication by raising an error.
            # For now, let's raise an error to indicate the issue.
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Failed to refresh Spotify token: {str(e)}. Please login again.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except Exception as e:  # Catch other potential errors during refresh
            db.rollback()
            print(
                f"Unexpected error during Spotify token refresh for user {user.user_id}: {e}"
            )  # Add logging
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An error occurred during token refresh.",
            )

    return user


# --- Authentication Routes ---
@router.get("/login", summary="Initiate Spotify Login")
def login(response: Response):
    """
    Generates the Spotify authorization URL and redirects the user.
    Sets a temporary state cookie for CSRF protection.
    """
    state = secrets.token_urlsafe(16)
    params = {
        "client_id": settings.SPOTIFY_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": settings.SPOTIFY_REDIRECT_URI,  # Backend callback
        "scope": " ".join(SPOTIFY_SCOPES),
        "state": state,
        "show_dialog": "true",  # Force user to confirm authorization each time
    }
    auth_url = f"{SPOTIFY_AUTH_URL}?{urlencode(params)}"

    # Set the state in a short-lived, secure cookie
    response = RedirectResponse(url=auth_url)
    response.set_cookie(
        key=OAUTH_STATE_COOKIE,
        value=state,
        max_age=600,  # Expires in 10 minutes
        httponly=True,  # Prevent JS access
        samesite="lax",  # CSRF protection
        secure=False,  # Only send over HTTPS in production, Change to True in production
        path="/api/v1/auth",  # Scope cookie to auth path
    )
    return response


@router.get("/callback", summary="Handle Spotify Callback")
def callback(
    request: Request,
    response: Response,
    code: str,
    state: str,
    db: Session = Depends(get_db),
):
    """
    Handles the callback from Spotify after user authorization.
    Validates state, exchanges code for tokens, creates/updates user,
    sets a JWT cookie, and redirects to the frontend.
    """
    # 1. Validate State (CSRF Protection)
    stored_state = request.cookies.get(OAUTH_STATE_COOKIE)
    if not stored_state or stored_state != state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="State mismatch error. Potential CSRF attack.",
        )

    try:
        # 2. Exchange code for tokens
        token_data = get_spotify_tokens(code)
        access_token = token_data["access_token"]
        refresh_token = token_data["refresh_token"]
        # Ensure expires_in is handled correctly, default to 1 hour if missing
        expires_in = token_data.get("expires_in", 3600)
        # Create timezone-aware datetime for expiry calculation then convert to naive for storage
        expires_at_aware = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        expires_at = expires_at_aware.replace(tzinfo=None)

        # 3. Get user info from Spotify
        user_info = get_spotify_user_info(access_token)
        spotify_user_id = user_info["id"]

        # 4. Check if user exists, create or update
        user = db.query(User).filter(User.spotify_user_id == spotify_user_id).first()

        if user:
            # Update existing user's Spotify tokens and info
            user.access_token = access_token
            user.refresh_token = (
                refresh_token  # Always update refresh token if provided
            )
            user.token_expires_at = expires_at  # type: ignore[assignment]
            user.spotify_display_name = user_info.get("display_name")
            user.email = user_info.get("email")
            # user.updated_at will be handled by the DB onupdate trigger
        else:
            # Create new user record
            user = User(
                # user_id is generated by default
                spotify_user_id=spotify_user_id,
                spotify_display_name=user_info.get("display_name"),
                email=user_info.get("email"),
                access_token=access_token,
                refresh_token=refresh_token,
                token_expires_at=expires_at,  # type: ignore[arg-type]
                # created_at and updated_at have defaults
            )
            db.add(user)

        db.commit()
        db.refresh(user)

        # 5. Create JWT containing our internal user_id
        jwt_payload = {"sub": user.user_id}  # Use 'sub' (subject) standard claim
        jwt_expires = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        jwt_token = create_access_token(data=jwt_payload, expires_delta=jwt_expires)

        # 6. Prepare redirect response to frontend
        # Redirect to the configured frontend URL
        redirect_url = str(settings.FRONTEND_CALLBACK_URL)
        response = RedirectResponse(url=redirect_url)

        # 7. Set the JWT as a secure, HTTP-only cookie
        response.set_cookie(
            key=ACCESS_TOKEN_COOKIE,
            value=jwt_token,
            max_age=int(jwt_expires.total_seconds()),  # Set cookie expiry to match JWT
            httponly=True,  # Crucial: Makes cookie inaccessible to JavaScript
            samesite="lax",  # Good balance of security and usability
            secure=False,  # Crucial: Only transmit over HTTPS, Change to True in production
            path="/",  # Make cookie available to all paths on the domain
        )

        # 8. Clear the state cookie as it's no longer needed
        response.delete_cookie(OAUTH_STATE_COOKIE, path="/api/v1/auth")

        return response

    except requests.exceptions.RequestException as e:
        # Handle errors during communication with Spotify
        print(f"Spotify API request failed: {e}")  # Log the error
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to communicate with Spotify: {str(e)}",
        )
    except Exception as e:
        # Handle unexpected errors (DB issues, etc.)
        db.rollback()  # Rollback DB changes on error
        print(f"Error during Spotify callback processing: {e}")  # Log the error
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An internal error occurred during authentication callback: {str(e)}",
        )


@router.post("/logout", summary="Log out user")
async def logout(response: Response):
    """
    Logs the user out by deleting the access token cookie.
    """
    response.delete_cookie(
        ACCESS_TOKEN_COOKIE,
        path="/",
        secure=False,  # Change secure=True in production
        httponly=True,
        samesite="lax",
    )
    return {"message": "Successfully logged out"}
