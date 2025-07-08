# Frontend API Documentation

This document describes the available API endpoints for the Music-stats project. It is intended for frontend developers to understand how to interact with the backend, what data to send, and what responses to expect.

---

## Authentication

### 1. `GET /api/v1/auth/login`

**Description:** Initiates the Spotify OAuth login flow. Redirects the user to Spotify's login page.

- **Request:** No parameters.
- **Response:** Redirects to Spotify login.

### 2. `GET /api/v1/auth/callback`

**Description:** Handles the callback from Spotify after user authentication. Exchanges code for tokens and sets authentication cookies.

- **Request:**
  - Query params: `code`, `state` (provided by Spotify)
- **Response:** Redirects to frontend callback URL with authentication status.

### 3. `POST /api/v1/auth/logout`

**Description:** Logs out the user by clearing authentication cookies.

- **Request:** No parameters.
- **Response:** 204 No Content

---

## User Profile

### 4. `GET /api/v1/user/profile`

**Description:** Returns the logged-in user's profile information.

- **Request:**
  - Requires authentication (JWT cookie)
- **Response:**

```json
{
  "user_id": "string",
  "spotify_user_id": "string",
  "spotify_display_name": "string",
  "email": "string",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

---

## Data Sync

### 5. `POST /api/v1/data/sync`

**Description:** Syncs the user's latest Spotify data (recently played, top tracks/artists, audio features) into the backend database.

- **Request:**
  - Requires authentication
- **Response:**

```json
{
  "recently_played": "success|error",
  "top_items": "success|error"
}
```

---

## Insights

### 6. `GET /api/v1/insights/basic`

**Description:** Returns basic listening insights for the user.

- **Request:**
  - Requires authentication
- **Response:**

```json
{
  "total_tracks_listened": 1234,
  "top_artists": [
    {"artist_id": "string", "artist_name": "string", "listen_count": 42}
  ],
  "top_tracks": [
    {"track_id": "string", "track_name": "string", "artist_name": "string", "listen_count": 17}
  ],
  "listening_time_stats": {
    "total_minutes": 12345,
    "average_per_day": 67.8
  },
  "listening_by_time_of_day": {
    "morning": 123,
    "afternoon": 456,
    "evening": 789,
    "night": 101
  },
  "recent_favorites": [
    {"track_id": "string", "track_name": "string", "artist_name": "string", "listen_count": 5}
  ],
  "audio_features_averages": {
    "danceability": 0.5,
    "energy": 0.7,
    "valence": 0.6,
    ...
  }
}
```

### 7. `GET /api/v1/insights/detailed`

**Description:** Returns detailed listening insights for the user.

- **Request:**
  - Requires authentication
- **Response:**

```json
{
  "genre_distribution": [
    { "genre": "pop", "count": 123 },
    { "genre": "rock", "count": 45 }
  ],
  "listening_trends_by_month": {
    "2025-01": 123,
    "2025-02": 234
  },
  "popular_vs_obscure_ratio": {
    "popular": 0.7,
    "obscure": 0.3
  },
  "mood_analysis": {
    "happy": 0.6,
    "sad": 0.2,
    "energetic": 0.2
  }
}
```

---

## General Notes

- All endpoints under `/api/v1/` require authentication unless otherwise specified.
- Authentication is handled via JWT tokens stored in cookies.
- Date/time fields are in ISO 8601 format (e.g., `2025-07-08T12:34:56Z`).
- For endpoints returning lists, expect empty arrays if no data is available.
- Error responses follow standard FastAPI error format:

```json
{
  "detail": "Error message here."
}
```

---

## Example Usage Flow

1. User clicks "Login with Spotify" → Frontend redirects to `/api/v1/auth/login`.
2. After Spotify login, backend handles `/api/v1/auth/callback` and redirects to frontend.
3. Frontend can now call `/api/v1/user/profile`, `/api/v1/data/sync`, and insights endpoints using the authenticated session.

---

For any additional details or changes in the API, please consult the backend team or check the backend codebase.
