"""
Tests for app.spotify_api module.
"""

from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import pytest
from app.spotify_api import SpotifyAPI
from app.models import User
from sqlalchemy.orm import Session


@pytest.fixture
def test_user_with_tokens(db_session: Session) -> User:
    """Create a test user with Spotify tokens."""
    user = User(
        user_id="test_user_123",
        spotify_user_id="spotify_test_123",
        spotify_display_name="Test User",
        email="test@example.com",
        access_token="test_access_token",
        refresh_token="test_refresh_token",
        token_expires_at=datetime.now() + timedelta(hours=1),
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def spotify_api(db_session: Session, test_user_with_tokens: User) -> SpotifyAPI:
    """Create a SpotifyAPI instance with test user."""
    return SpotifyAPI(user=test_user_with_tokens, db=db_session)


@patch("app.spotify_api.requests.get")
def test_get_user_profile_success(mock_get: MagicMock, spotify_api: SpotifyAPI):
    """Test successful user profile retrieval."""
    mock_response = Mock()
    mock_response.json.return_value = {
        "id": "spotify_user_123",
        "display_name": "Test User",
        "email": "test@example.com",
        "followers": {"total": 100},
    }
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    profile = spotify_api.get_user_profile()
    assert profile["id"] == "spotify_user_123"
    assert profile["display_name"] == "Test User"
    assert profile["email"] == "test@example.com"


@patch("app.spotify_api.requests.get")
def test_make_request_get_method(mock_get: MagicMock, spotify_api: SpotifyAPI):
    """Test _make_request with GET method."""
    mock_response = Mock()
    mock_response.json.return_value = {"test": "data"}
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    result = spotify_api._make_request("/test")  # type: ignore
    assert result == {"test": "data"}
    mock_get.assert_called_once()


def test_spotify_api_initialization(
    spotify_api: SpotifyAPI, test_user_with_tokens: User
):
    """Test SpotifyAPI initialization."""
    assert spotify_api.user == test_user_with_tokens
    assert spotify_api.access_token == "test_access_token"  # type: ignore
    assert "Bearer test_access_token" in spotify_api.headers["Authorization"]


def test_check_token_not_expired(spotify_api: SpotifyAPI):
    """Test _check_token when token is still valid."""
    # Token is set to expire in 1 hour, so it should be valid
    original_token = spotify_api.access_token
    spotify_api._check_token()  # type: ignore
    assert spotify_api.access_token == original_token  # type: ignore


@patch("app.spotify_api.requests.get")
def test_make_request_http_error(mock_get: MagicMock, spotify_api: SpotifyAPI):
    """Test _make_request handling HTTP errors."""
    import requests

    mock_response = Mock()
    mock_response.status_code = 404
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
        response=mock_response
    )
    mock_get.return_value = mock_response

    with pytest.raises(requests.exceptions.HTTPError):
        spotify_api._make_request("/nonexistent")  # type: ignore
