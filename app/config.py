import os
from pydantic_settings import BaseSettings
from pydantic import PostgresDsn, Field, AnyHttpUrl


class Settings(BaseSettings):
    """Application settings configuration."""

    # PostgreSQL database connection
    DATABASE_URL: PostgresDsn

    # Spotify API credentials
    SPOTIFY_CLIENT_ID: str
    SPOTIFY_CLIENT_SECRET: str
    SPOTIFY_REDIRECT_URI: str  # This is the backend callback URL

    # Frontend URL for redirection after successful login
    # Example: "http://localhost:3000/auth/callback" or your production frontend URL

    # API settings
    APP_NAME: str = "Music Stats"
    API_V1_STR: str = "/api/v1"
    FRONTEND_CALLBACK_URL: AnyHttpUrl = Field(..., env="FRONTEND_CALLBACK_URL")

    # JWT Settings
    # Generate a strong secret key, e.g., using: openssl rand -hex 32
    JWT_SECRET_KEY: str = Field(..., env="JWT_SECRET_KEY")
    JWT_ALGORITHM: str = "HS256"
    # Set an appropriate access token expiry time (e.g., 30 minutes, 1 day)
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day

    class Config:
        env_file = ".env"
        case_sensitive = True
        # Example .env file:
        # DATABASE_URL=postgresql+psycopg2://user:password@host:port/dbname
        # SPOTIFY_CLIENT_ID=your_spotify_client_id
        # SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
        # SPOTIFY_REDIRECT_URI=http://localhost:8000/api/v1/auth/callback # Your backend callback
        # FRONTEND_CALLBACK_URL=http://localhost:3000/dashboard # Where to send user after login
        # JWT_SECRET_KEY=a_very_strong_random_secret_key_here


settings = Settings()
