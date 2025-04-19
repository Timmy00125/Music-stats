import os

from pydantic_settings import BaseSettings
from pydantic import PostgresDsn

class Settings(BaseSettings):
    """Application settings configuration."""
    # PostgreSQL database connection
    DATABASE_URL: PostgresDsn

    # Spotify API credentials
    SPOTIFY_CLIENT_ID: str
    SPOTIFY_CLIENT_SECRET: str
    SPOTIFY_REDIRECT_URI: str

    # API settings
    APP_NAME: str = "Music Stats"
    API_V1_STR: str = "/api/v1"

    # JWT Secret for token
    SECRET_KEY: str

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()