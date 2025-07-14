"""
Tests for database interactions and edge cases.
"""

import pytest
from datetime import datetime, timedelta
from app.models import User, ListeningHistory, AudioFeatures
from app.insights import InsightsGenerator
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError


def test_database_integrity_constraints(db_session: Session):
    """Test database integrity constraints."""
    # Test unique constraint on spotify_user_id
    user1 = User(
        spotify_user_id="duplicate_id", access_token="token1", refresh_token="refresh1"
    )
    user2 = User(
        spotify_user_id="duplicate_id",  # Same ID should cause constraint violation
        access_token="token2",
        refresh_token="refresh2",
    )

    db_session.add(user1)
    db_session.commit()

    db_session.add(user2)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_insights_with_large_dataset(db_session: Session):
    """Test insights generation with a larger dataset."""
    user = User(
        spotify_user_id="large_dataset_user",
        access_token="token",
        refresh_token="refresh",
    )
    db_session.add(user)
    db_session.commit()

    # Create 100 listening records across different artists and tracks
    listening_records = []
    for i in range(100):
        record = ListeningHistory(
            user_id=user.user_id,  # type: ignore
            track_id=f"track_{i % 20}",  # 20 unique tracks
            track_name=f"Track {i % 20}",
            artist_id=f"artist_{i % 10}",  # 10 unique artists
            artist_name=f"Artist {i % 10}",
            played_at=datetime.now() - timedelta(days=i % 30),
            duration_ms=180000 + (i * 1000),  # Varying durations
        )
        listening_records.append(record)  # type: ignore

    db_session.add_all(listening_records)  # type: ignore
    db_session.commit()

    # Test insights generation
    insights_gen = InsightsGenerator(db=db_session, user_id=str(user.user_id))  # type: ignore
    insights = insights_gen.get_basic_insights()

    assert insights["total_tracks_listened"] == 100
    assert len(insights["top_artists"]) <= 5  # Should return top 5 or fewer
    assert len(insights["top_tracks"]) <= 5  # Should return top 5 or fewer


def test_insights_with_time_ranges(db_session: Session):
    """Test insights with data spanning different time periods."""
    user = User(
        spotify_user_id="time_range_user", access_token="token", refresh_token="refresh"
    )
    db_session.add(user)
    db_session.commit()

    # Create records from different time periods
    base_time = datetime.now()
    time_periods = [
        base_time - timedelta(days=1),  # Recent
        base_time - timedelta(days=30),  # Last month
        base_time - timedelta(days=90),  # 3 months ago
        base_time - timedelta(days=365),  # Last year
    ]

    for i, played_at in enumerate(time_periods):
        record = ListeningHistory(
            user_id=user.user_id,
            track_id=f"track_{i}",
            track_name=f"Track {i}",
            artist_id=f"artist_{i}",
            artist_name=f"Artist {i}",
            played_at=played_at,
            duration_ms=180000,
        )
        db_session.add(record)

    db_session.commit()

    insights_gen = InsightsGenerator(db=db_session, user_id=str(user.user_id))  # type: ignore
    insights = insights_gen.get_basic_insights()

    assert insights["total_tracks_listened"] == 4
    assert "recent_favorites" in insights
    assert "listening_by_time_of_day" in insights


def test_audio_features_edge_cases(db_session: Session):
    """Test audio features with edge case values."""
    # Test with extreme values
    audio_features = [
        AudioFeatures(
            track_id="extreme_low",
            danceability=0.0,
            energy=0.0,
            valence=0.0,
            tempo=50.0,
            acousticness=0.0,
            instrumentalness=0.0,
            liveness=0.0,
            speechiness=0.0,
        ),
        AudioFeatures(
            track_id="extreme_high",
            danceability=1.0,
            energy=1.0,
            valence=1.0,
            tempo=200.0,
            acousticness=1.0,
            instrumentalness=1.0,
            liveness=1.0,
            speechiness=1.0,
        ),
    ]

    for feature in audio_features:
        db_session.add(feature)

    db_session.commit()

    # Query and verify
    low_feature = (
        db_session.query(AudioFeatures).filter_by(track_id="extreme_low").first()
    )
    high_feature = (
        db_session.query(AudioFeatures).filter_by(track_id="extreme_high").first()
    )

    assert low_feature is not None and low_feature.danceability == 0.0  # type: ignore
    assert low_feature is not None and low_feature.tempo == 50.0  # type: ignore
    assert high_feature is not None and high_feature.danceability == 1.0  # type: ignore
    assert high_feature is not None and high_feature.tempo == 200.0  # type: ignore


def test_insights_empty_user(db_session: Session):
    """Test insights generation for user with no listening history."""
    user = User(
        spotify_user_id="empty_user", access_token="token", refresh_token="refresh"
    )
    db_session.add(user)
    db_session.commit()

    insights_gen = InsightsGenerator(db=db_session, user_id=str(user.user_id))  # type: ignore
    insights = insights_gen.get_basic_insights()

    # Should handle empty data gracefully
    assert insights["total_tracks_listened"] == 0
    assert insights["top_artists"] == []
    assert insights["top_tracks"] == []
    assert isinstance(insights["listening_time_stats"], dict)
    assert isinstance(insights["audio_features_averages"], dict)


def test_user_token_expiration_handling(db_session: Session):
    """Test user model with expired tokens."""
    # Create user with expired token
    expired_user = User(
        spotify_user_id="expired_user",
        access_token="expired_token",
        refresh_token="refresh_token",
        token_expires_at=datetime.now() - timedelta(hours=1),  # Already expired
    )
    db_session.add(expired_user)
    db_session.commit()

    # Create user with valid token
    valid_user = User(
        spotify_user_id="valid_user",
        access_token="valid_token",
        refresh_token="refresh_token",
        token_expires_at=datetime.now() + timedelta(hours=1),  # Still valid
    )
    db_session.add(valid_user)
    db_session.commit()

    # Verify token expiration status
    assert expired_user.token_expires_at < datetime.now()  # type: ignore
    assert valid_user.token_expires_at > datetime.now()  # type: ignore
