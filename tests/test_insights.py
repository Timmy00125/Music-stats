"""
Tests for app.insights module.
"""

import pytest
from app.insights import InsightsGenerator
from app.models import ListeningHistory
from sqlalchemy.orm import Session
from typing import Any, Dict


class DummySpotifyAPI:
    """Mock Spotify API for testing."""

    def get_audio_features(self, track_ids):
        return [{"id": tid, "danceability": 0.5, "energy": 0.7} for tid in track_ids]


@pytest.fixture
def insights_generator(db_session: Session) -> InsightsGenerator:
    return InsightsGenerator(db=db_session, spotify_api=DummySpotifyAPI())


def test_get_detailed_insights_empty(insights_generator: InsightsGenerator):
    """Test get_detailed_insights returns empty structure when no data."""
    result = insights_generator.get_detailed_insights()
    assert isinstance(result, dict)
    assert not result.get("top_tracks")


# Add more tests for edge cases and populated data
