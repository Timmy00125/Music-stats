import uuid

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class User(Base):
    """
    User model storing Spotify authentication details
    """

    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    user_id = Column(String, unique=True, index=True, default=lambda: str(uuid.uuid4()))
    spotify_user_id = Column(String, unique=True, index=True)
    spotify_display_name = Column(String, nullable=True)
    email = Column(String, unique=True, index=True, nullable=True)
    access_token = Column(String)
    refresh_token = Column(String)
    token_expires_at = Column(DateTime)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(
        DateTime,
        default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    listening_history = relationship("ListeningHistory", back_populates="user")
    top_artists = relationship("TopArtist", back_populates="user")
    top_tracks = relationship("TopTrack", back_populates="user")


class ListeningHistory(Base):
    """
    Model for storing user's listening history
    """

    __tablename__ = "listening_history"

    id = Column(Integer, primary_key=True)
    user_id = Column(String, ForeignKey("users.user_id"))
    track_id = Column(String, index=True)
    track_name = Column(String)
    artist_id = Column(String, index=True)
    artist_name = Column(String)
    album_id = Column(String)
    album_name = Column(String)
    played_at = Column(DateTime, index=True)
    duration_ms = Column(Integer)
    timestamp = Column(DateTime, default=func.now())

    # Relationships
    user = relationship("User", back_populates="listening_history")


class TopArtist(Base):
    """
    Model for storing user's top artists
    """

    __tablename__ = "top_artists"

    id = Column(Integer, primary_key=True)
    user_id = Column(String, ForeignKey("users.user_id"))
    artist_id = Column(String, index=True)
    artist_name = Column(String)
    term = Column(String, index=True)  # short_term, medium_term, long_term
    rank = Column(Integer)
    genres = Column(String)  # Stored as JSON string
    popularity = Column(Integer)
    timestamp = Column(DateTime, default=func.now())

    # Relationships
    user = relationship("User", back_populates="top_artists")


class TopTrack(Base):
    """
    Model for storing user's top tracks
    """

    __tablename__ = "top_tracks"

    id = Column(Integer, primary_key=True)
    user_id = Column(String, ForeignKey("users.user_id"))
    track_id = Column(String, index=True)
    track_name = Column(String)
    artist_id = Column(String, index=True)
    artist_name = Column(String)
    album_id = Column(String)
    album_name = Column(String)
    term = Column(String, index=True)  # short_term, medium_term, long_term
    rank = Column(Integer)
    popularity = Column(Integer)
    timestamp = Column(DateTime, default=func.now())

    # Relationships
    user = relationship("User", back_populates="top_tracks")


class AudioFeatures(Base):
    """
    Model for storing audio features of tracks
    """

    __tablename__ = "audio_features"

    id = Column(Integer, primary_key=True)
    track_id = Column(String, unique=True, index=True)
    danceability = Column(Float)  # type: ignore
    energy = Column(Float)  # type: ignore
    key = Column(Integer)  # type: ignore
    loudness = Column(Float)  # type: ignore
    mode = Column(Integer)  # type: ignore
    speechiness = Column(Float)  # type: ignore
    acousticness = Column(Float)  # type: ignore
    instrumentalness = Column(Float)  # type: ignore
    liveness = Column(Float)  # type: ignore
    valence = Column(Float)  # type: ignore
    tempo = Column(Float)  # type: ignore
    duration_ms = Column(Integer)  # type: ignore
    time_signature = Column(Integer)  # type: ignore
    updated_at = Column(
        DateTime,
        default=func.now(),
        onupdate=func.now(),
    )
