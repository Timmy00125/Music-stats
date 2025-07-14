"""
Tests for app.auth module.
"""

from datetime import datetime, timedelta
from unittest.mock import patch, Mock
import pytest
from app.auth import (
    create_access_token,
    get_spotify_tokens,
    refresh_spotify_token,
    get_spotify_user_info,
)


def test_create_access_token():
    """Test JWT token generation returns a string."""
    data = {"sub": "test_user", "exp": datetime.utcnow() + timedelta(minutes=15)}
    token = create_access_token(data)
    assert isinstance(token, str)
    assert len(token) > 0


def test_create_access_token_with_expires_delta():
    """Test JWT token generation with custom expiration."""
    data = {"sub": "test_user"}
    expires_delta = timedelta(hours=1)
    token = create_access_token(data, expires_delta)
    assert isinstance(token, str)
    assert len(token) > 0


@patch("app.auth.requests.post")
def test_get_spotify_tokens_success(mock_post):
    """Test successful Spotify token exchange."""
    mock_response = Mock()
    mock_response.json.return_value = {
        "access_token": "test_access_token",
        "refresh_token": "test_refresh_token",
        "expires_in": 3600,
    }
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    result = get_spotify_tokens("test_code")
    assert result["access_token"] == "test_access_token"
    assert result["refresh_token"] == "test_refresh_token"
    assert result["expires_in"] == 3600


@patch("app.auth.requests.post")
def test_refresh_spotify_token_success(mock_post):
    """Test successful Spotify token refresh."""
    mock_response = Mock()
    mock_response.json.return_value = {
        "access_token": "new_access_token",
        "expires_in": 3600,
    }
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    result = refresh_spotify_token("test_refresh_token")
    assert result["access_token"] == "new_access_token"
    assert result["expires_in"] == 3600


@patch("app.auth.requests.get")
def test_get_spotify_user_info_success(mock_get):
    """Test successful Spotify user info retrieval."""
    mock_response = Mock()
    mock_response.json.return_value = {
        "id": "spotify_user_123",
        "display_name": "Test User",
        "email": "test@example.com",
    }
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    result = get_spotify_user_info("test_access_token")
    assert result["id"] == "spotify_user_123"
    assert result["display_name"] == "Test User"
    assert result["email"] == "test@example.com"


@patch("app.auth.requests.post")
def test_get_spotify_tokens_failure(mock_post):
    """Test Spotify token exchange failure."""
    mock_response = Mock()
    mock_response.raise_for_status.side_effect = Exception("HTTP Error")
    mock_post.return_value = mock_response

    with pytest.raises(Exception):
        get_spotify_tokens("invalid_code")
