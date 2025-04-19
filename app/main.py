import logging
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import Dict, Any

from app.database import get_db, engine, Base
from app.models import User
from app.config import settings
from app.auth import router as auth_router, get_current_user
from app.spotify_api import SpotifyAPI
from app.insights import InsightsGenerator

# Create all tables in the database
Base.metadata.create_all(bind=engine)

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
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, set this to your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include router for authentication
app.include_router(auth_router, prefix=f"{settings.API_V1_STR}/auth", tags=["authentication"])


# Define API endpoints
@app.get("/")
def read_root():
    """
    Root endpoint to verify API is running
    """
    return {"message": "Welcome to Spotify Insights API", "status": "online"}


@app.get(f"{settings.API_V1_STR}/user/profile")
def get_user_profile(db: Session = Depends(get_db), token: str = None):
    """
    Get the user's profile information
    """
    user = get_current_user(db, token)
    spotify = SpotifyAPI(user, db)
    return spotify.get_user_profile()


@app.post(f"{settings.API_V1_STR}/data/sync")
def sync_user_data(background_tasks: BackgroundTasks, db: Session = Depends(get_db), token: str = None):
    """
    Trigger synchronization of user data from Spotify
    """
    user = get_current_user(db, token)
    spotify = SpotifyAPI(user, db)

    # Start data sync in the background
    background_tasks.add_task(spotify.fetch_and_store_recently_played)
    background_tasks.add_task(spotify.fetch_and_store_top_items)

    return {"status": "success", "message": "Data synchronization started in the background"}


@app.get(f"{settings.API_V1_STR}/insights/basic")
def get_basic_insights(db: Session = Depends(get_db), token: str = None):
    """
    Get basic insights about the user's listening history
    """
    user = get_current_user(db, token)
    insights = InsightsGenerator(db, user.user_id)
    return insights.get_basic_insights()


@app.get(f"{settings.API_V1_STR}/insights/detailed")
def get_detailed_insights(db: Session = Depends(get_db), token: str = None):
    """
    Get detailed insights about the user's listening history
    """
    user = get_current_user(db, token)
    insights = InsightsGenerator(db, user.user_id)
    return insights.get_detailed_insights()


@app.get(f"{settings.API_V1_STR}/admin/status")
def get_api_status():
    """
    Get the status of the API
    """
    return {
        "status": "online",
        "api_version": "1.0.0",
        "api_name": settings.APP_NAME
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)