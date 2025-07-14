"""
Tests for app.spotify_api module.
"""

import pytest
from app.spotify_api import SpotifyAPI
from unittest.mock import patch


def test_get_user_profile(monkeypatch):
    """Test get_user_profile returns expected data structure."""

    class DummyResponse:
        def json(self):
            return {"id": "user123", "display_name": "Test User"}

    monkeypatch.setattr("requests.get", lambda *a, **kw: DummyResponse())
    api = SpotifyAPI(token="dummy")
    profile = api.get_user_profile()
    assert profile["id"] == "user123"
    assert profile["display_name"] == "Test User"


# Add more tests for error handling, API failures, etc.
