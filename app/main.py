import logging
from fastapi import (
    FastAPI,
    Depends,
    HTTPException,
    BackgroundTasks,
    Request,
    status,
)  # Import Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import Dict, Any

from app.database import get_db, engine, Base
from app.models import User  # Keep User import if needed elsewhere
from app.config import settings

# Import the specific function, not the whole router if using Depends
from app.auth import router as auth_router, get_current_user
from app.spotify_api import SpotifyAPI
from app.insights import InsightsGenerator

# Create all tables in the database (consider using Alembic for migrations in production)
# Base.metadata.create_all(bind=engine) # Comment out if using migrations

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="API for Spotify Listening History Insights",
    version="1.0.0",
    # Add root_path if running behind a proxy like Nginx or Traefik
    # root_path="/api/v1" # Example if proxy strips /api/v1
)

# Add CORS middleware
# Make sure allow_origins is configured correctly for your frontend URL
# For production, use the specific frontend origin(s) instead of "*"
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        str(settings.FRONTEND_CALLBACK_URL).rstrip("/"),
        # "localhost:3000",  # Example frontend URL
        # "http://localhost:3000",  # Example frontend URL
    ],  # Allow frontend origin
    # allow_origins=["*"] # Use for development if needed, but restrict in prod
    allow_credentials=True,  # Important for cookies
    allow_methods=["*"],  # Or restrict to specific methods like ["GET", "POST"]
    allow_headers=["*"],  # Or restrict specific headers if needed
)

# Include router for authentication
app.include_router(
    auth_router, prefix=f"{settings.API_V1_STR}/auth", tags=["authentication"]
)


# --- API Endpoints ---


@app.get("/")
def read_root():
    """Root endpoint to verify API is running"""
    return {"message": f"Welcome to {settings.APP_NAME} API", "status": "online"}


# Use the User model from get_current_user dependency
@app.get(f"{settings.API_V1_STR}/user/profile", summary="Get logged-in user's profile")
async def get_user_profile(
    current_user: User = Depends(get_current_user),  # Use the dependency
    db: Session = Depends(get_db),
):
    """
    Get the authenticated user's Spotify profile information.
    Authentication is handled via JWT cookie.
    """
    # The get_current_user dependency already fetches the user and handles refresh
    # We just need the access token from the user object to call Spotify
    spotify = SpotifyAPI(current_user, db)  # Pass the validated user object
    # Consider wrapping Spotify API calls in try-except blocks here as well
    try:
        return spotify.get_user_profile()
    except HTTPException as e:
        # Re-raise HTTPExceptions from SpotifyAPI if needed
        raise e
    except Exception as e:
        logger.error(
            f"Failed to get Spotify profile for user {current_user.user_id}: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not fetch profile from Spotify.",
        )


@app.post(f"{settings.API_V1_STR}/data/sync", summary="Sync user data from Spotify")
async def sync_user_data(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),  # Use the dependency
    db: Session = Depends(get_db),
):
    """
    Trigger background synchronization of the authenticated user's data from Spotify.
    """
    logger.info(f"Initiating data sync for user: {current_user.user_id}")
    spotify = SpotifyAPI(current_user, db)

    # Add tasks to run in the background
    background_tasks.add_task(spotify.fetch_and_store_recently_played)
    background_tasks.add_task(spotify.fetch_and_store_top_items)
    # Potentially add audio features sync task here too if needed
    # background_tasks.add_task(spotify.fetch_and_store_audio_features_for_history)

    return {
        "status": "success",
        "message": "Data synchronization started in the background",
    }


@app.get(
    f"{settings.API_V1_STR}/insights/basic", summary="Get basic listening insights"
)
async def get_basic_insights(
    current_user: User = Depends(get_current_user),  # Use the dependency
    db: Session = Depends(get_db),
):
    """
    Get basic insights about the authenticated user's listening history.
    """
    logger.info(f"Fetching basic insights for user: {current_user.user_id}")
    insights = InsightsGenerator(
        db, current_user.user_id
    )  # Use user_id from validated user
    # Consider adding try-except block for insight generation
    try:
        return insights.get_basic_insights()
    except Exception as e:
        logger.error(
            f"Failed to generate basic insights for user {current_user.user_id}: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not generate insights.",
        )


@app.get(
    f"{settings.API_V1_STR}/insights/detailed",
    summary="Get detailed listening insights",
)
async def get_detailed_insights(
    current_user: User = Depends(get_current_user),  # Use the dependency
    db: Session = Depends(get_db),
):
    """
    Get detailed insights about the authenticated user's listening history.
    """
    logger.info(f"Fetching detailed insights for user: {current_user.user_id}")
    insights = InsightsGenerator(db, current_user.user_id)
    # Consider adding try-except block for insight generation
    try:
        return insights.get_detailed_insights()
    except Exception as e:
        logger.error(
            f"Failed to generate detailed insights for user {current_user.user_id}: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not generate insights.",
        )


@app.get(f"{settings.API_V1_STR}/admin/status", summary="Get API status")
async def get_api_status():
    """Get the status of the API (unauthenticated endpoint)"""
    return {"status": "online", "api_version": "1.0.0", "api_name": settings.APP_NAME}


# --- Optional: Add Exception Handlers for better error responses ---
from fastapi.responses import JSONResponse


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    # You can customize the error response format here
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=getattr(exc, "headers", None),
    )


# Add more specific handlers if needed

# --- Run Command (for local development) ---
if __name__ == "__main__":
    import uvicorn

    # Use reload=True only for development
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
