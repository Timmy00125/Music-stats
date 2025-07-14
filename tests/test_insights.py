"""
Tests for app.insights module.
"""

import pytest
from app.insights import InsightsGenerator
from app.models import ListeningHistory, User, AudioFeatures, TopArtist, TopTrack
from sqlalchemy.orm import Session
from datetime import datetime, timedelta


@pytest.fixture
def test_user(db_session: Session) -> User:
    """Create a test user for insights testing."""
    user = User(
        user_id="test_user_123",
        spotify_user_id="spotify_test_123",
        spotify_display_name="Test User",
        email="test@example.com",
        access_token="test_token",
        refresh_token="test_refresh",
        token_expires_at=datetime.now() + timedelta(hours=1),
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def insights_generator(db_session: Session, test_user: User) -> InsightsGenerator:
    """Create an InsightsGenerator instance with test user."""
    return InsightsGenerator(db=db_session, user_id=test_user.user_id)


@pytest.fixture
def sample_listening_data(db_session: Session, test_user: User):
    """Add sample listening history data for testing."""
    listening_records = [
        ListeningHistory(
            user_id=test_user.user_id,
            track_id="track_1",
            track_name="Test Track 1",
            artist_id="artist_1",
            artist_name="Test Artist 1",
            played_at=datetime.now() - timedelta(days=1),
            duration_ms=180000,
        ),
        ListeningHistory(
            user_id=test_user.user_id,
            track_id="track_2",
            track_name="Test Track 2",
            artist_id="artist_2",
            artist_name="Test Artist 2",
            played_at=datetime.now() - timedelta(days=2),
            duration_ms=210000,
        ),
    ]

    audio_features = [
        AudioFeatures(
            track_id="track_1",
            danceability=0.7,
            energy=0.8,
            valence=0.6,
            tempo=120.0,
            acousticness=0.2,
            instrumentalness=0.1,
            liveness=0.3,
            speechiness=0.1,
        ),
        AudioFeatures(
            track_id="track_2",
            danceability=0.5,
            energy=0.6,
            valence=0.4,
            tempo=100.0,
            acousticness=0.4,
            instrumentalness=0.2,
            liveness=0.2,
            speechiness=0.05,
        ),
    ]

    for record in listening_records:
        db_session.add(record)
    for feature in audio_features:
        db_session.add(feature)

    db_session.commit()


def test_get_basic_insights_empty(insights_generator: InsightsGenerator):
    """Test get_basic_insights returns correct structure when no data."""
    result = insights_generator.get_basic_insights()
    assert isinstance(result, dict)
    assert "total_tracks_listened" in result
    assert "top_artists" in result
    assert "top_tracks" in result
    assert result["total_tracks_listened"] == 0
    assert len(result["top_artists"]) == 0
    assert len(result["top_tracks"]) == 0


def test_get_detailed_insights_empty(insights_generator: InsightsGenerator):
    """Test get_detailed_insights returns correct structure when no data."""
    result = insights_generator.get_detailed_insights()
    assert isinstance(result, dict)
    assert "total_tracks_listened" in result
    assert "top_tracks" in result
    assert "genre_distribution" in result
    assert "listening_trends_by_month" in result
    assert result["total_tracks_listened"] == 0


def test_get_basic_insights_with_data(
    insights_generator: InsightsGenerator, sample_listening_data
):
    """Test get_basic_insights with sample data."""
    result = insights_generator.get_basic_insights()
    assert isinstance(result, dict)
    assert result["total_tracks_listened"] == 2
    assert "top_artists" in result
    assert "top_tracks" in result
    assert "listening_time_stats" in result
    assert "audio_features_averages" in result


def test_total_tracks_listened(
    insights_generator: InsightsGenerator, sample_listening_data
):
    """Test _get_total_tracks_listened method."""
    total = insights_generator._get_total_tracks_listened()
    assert total == 2


def test_audio_features_averages(
    insights_generator: InsightsGenerator, sample_listening_data
):
    """Test _get_audio_features_averages method."""
    averages = insights_generator._get_audio_features_averages()
    assert isinstance(averages, dict)
    if averages:  # Only check if there are features
        assert "danceability" in averages
        assert "energy" in averages
        assert isinstance(averages["danceability"], float)


def test_get_detailed_insights_with_data(
    insights_generator: InsightsGenerator, sample_listening_data
):
    """Test get_detailed_insights with sample data."""
    result = insights_generator.get_detailed_insights()
    assert isinstance(result, dict)
    assert result["total_tracks_listened"] == 2
    assert "genre_distribution" in result
    assert "listening_trends_by_month" in result
    assert "popular_vs_obscure" in result
    assert "mood_analysis" in result
