"""
Tests for app.models module.
"""

from datetime import datetime, timedelta
from app.models import User, ListeningHistory, AudioFeatures, TopArtist, TopTrack
from sqlalchemy.orm import Session


def test_user_creation(db_session: Session):
    """Test User model creation and basic properties."""
    user = User(
        spotify_user_id="spotify_123",
        spotify_display_name="Test User",
        email="test@example.com",
        access_token="test_token",
        refresh_token="test_refresh",
        token_expires_at=datetime.now() + timedelta(hours=1),
    )
    db_session.add(user)
    db_session.commit()

    assert user.id is not None
    assert user.user_id is not None  # Should be auto-generated UUID
    assert user.spotify_user_id == "spotify_123"  # type: ignore
    assert user.spotify_display_name == "Test User"  # type: ignore
    assert user.email == "test@example.com"  # type: ignore
    assert user.created_at is not None
    assert user.updated_at is not None


def test_listening_history_creation(db_session: Session):
    """Test ListeningHistory model creation."""
    user = User(
        spotify_user_id="spotify_123", access_token="token", refresh_token="refresh"
    )
    db_session.add(user)
    db_session.commit()

    listening_record = ListeningHistory(
        user_id=user.user_id,
        track_id="track_123",
        track_name="Test Track",
        artist_id="artist_123",
        artist_name="Test Artist",
        played_at=datetime.now(),
        duration_ms=180000,
    )
    db_session.add(listening_record)
    db_session.commit()

    assert listening_record.id is not None
    assert listening_record.user_id == user.user_id  # type: ignore
    assert listening_record.track_id == "track_123"  # type: ignore
    assert listening_record.track_name == "Test Track"  # type: ignore
    assert listening_record.artist_id == "artist_123"  # type: ignore
    assert listening_record.artist_name == "Test Artist"  # type: ignore
    assert listening_record.duration_ms == 180000  # type: ignore


def test_audio_features_creation(db_session: Session):
    """Test AudioFeatures model creation."""
    audio_features = AudioFeatures(
        track_id="track_123",
        danceability=0.7,
        energy=0.8,
        valence=0.6,
        tempo=120.0,
        acousticness=0.2,
        instrumentalness=0.1,
        liveness=0.3,
        speechiness=0.1,
    )
    db_session.add(audio_features)
    db_session.commit()

    assert audio_features.id is not None
    assert audio_features.track_id == "track_123"  # type: ignore
    assert audio_features.danceability == 0.7  # type: ignore
    assert audio_features.energy == 0.8  # type: ignore
    assert audio_features.valence == 0.6  # type: ignore
    assert audio_features.tempo == 120.0  # type: ignore


def test_top_artist_creation(db_session: Session):
    """Test TopArtist model creation."""
    user = User(
        spotify_user_id="spotify_123", access_token="token", refresh_token="refresh"
    )
    db_session.add(user)
    db_session.commit()

    top_artist = TopArtist(
        user_id=user.user_id,
        artist_id="artist_123",
        artist_name="Test Artist",
        term="medium_term",
        rank=1,
        genres='["pop", "rock"]',  # Store as JSON string, not list
    )
    db_session.add(top_artist)
    db_session.commit()

    assert top_artist.id is not None
    assert top_artist.user_id == user.user_id  # type: ignore
    assert top_artist.artist_id == "artist_123"  # type: ignore
    assert top_artist.artist_name == "Test Artist"  # type: ignore
    assert top_artist.term == "medium_term"  # type: ignore
    assert top_artist.rank == 1  # type: ignore
    assert top_artist.genres == '["pop", "rock"]'  # type: ignore


def test_top_track_creation(db_session: Session):
    """Test TopTrack model creation."""
    user = User(
        spotify_user_id="spotify_123", access_token="token", refresh_token="refresh"
    )
    db_session.add(user)
    db_session.commit()

    top_track = TopTrack(
        user_id=user.user_id,
        track_id="track_123",
        track_name="Test Track",
        artist_id="artist_123",
        artist_name="Test Artist",
        term="medium_term",
        rank=1,
        popularity=80,
    )
    db_session.add(top_track)
    db_session.commit()

    assert top_track.id is not None
    assert top_track.user_id == user.user_id  # type: ignore
    assert top_track.track_id == "track_123"  # type: ignore
    assert top_track.track_name == "Test Track"  # type: ignore
    assert top_track.artist_id == "artist_123"  # type: ignore
    assert top_track.artist_name == "Test Artist"  # type: ignore
    assert top_track.term == "medium_term"  # type: ignore
    assert top_track.rank == 1  # type: ignore
    assert top_track.popularity == 80  # type: ignore


def test_user_relationships(db_session: Session):
    """Test User model relationships with other models."""
    user = User(
        spotify_user_id="spotify_123", access_token="token", refresh_token="refresh"
    )
    db_session.add(user)
    db_session.commit()

    # Add related records
    listening_record = ListeningHistory(
        user_id=user.user_id,
        track_id="track_123",
        track_name="Test Track",
        artist_id="artist_123",
        artist_name="Test Artist",
        played_at=datetime.now(),
        duration_ms=180000,
    )

    top_artist = TopArtist(
        user_id=user.user_id,
        artist_id="artist_123",
        artist_name="Test Artist",
        term="medium_term",
        rank=1,
    )

    top_track = TopTrack(
        user_id=user.user_id,
        track_id="track_123",
        track_name="Test Track",
        artist_id="artist_123",
        artist_name="Test Artist",
        term="medium_term",
        rank=1,
    )

    db_session.add_all([listening_record, top_artist, top_track])
    db_session.commit()

    # Test relationships
    assert len(user.listening_history) == 1
    assert len(user.top_artists) == 1
    assert len(user.top_tracks) == 1
    assert user.listening_history[0].track_name == "Test Track"  # type: ignore
    assert user.top_artists[0].artist_name == "Test Artist"  # type: ignore
    assert user.top_tracks[0].track_name == "Test Track"  # type: ignore
