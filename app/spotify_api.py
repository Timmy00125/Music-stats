import requests
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
from sqlalchemy.orm import Session

from app.models import User, ListeningHistory, TopArtist, TopTrack, AudioFeatures
from app.auth import refresh_spotify_token

logger = logging.getLogger(__name__)


class SpotifyAPI:
    """
    Class to interact with the Spotify Web API
    """

    BASE_URL = "https://api.spotify.com/v1"

    def __init__(self, user: User, db: Session):
        self.user = user
        self.db = db
        self.access_token = user.access_token
        self.headers = {"Authorization": f"Bearer {self.access_token}"}

    def _check_token(self):
        """
        Check if the access token is expired and refresh if needed
        """
        current_time = datetime.now()
        token_expires = getattr(self.user, "token_expires_at", None)
        if token_expires is None or current_time >= token_expires:
            token_data = refresh_spotify_token(str(self.user.refresh_token))

            # Update user with new tokens
            setattr(self.user, "access_token", token_data.get("access_token"))
            setattr(self.user, "token_expires_at", current_time + timedelta(
                seconds=token_data.get("expires_in", 3600)
            ))

            # If a new refresh token is provided, update it
            if "refresh_token" in token_data:
                setattr(self.user, "refresh_token", token_data["refresh_token"])

            self.db.commit()
            self.db.refresh(self.user)

            # Update the access token and headers
            self.access_token = self.user.access_token
            self.headers = {"Authorization": f"Bearer {self.access_token}"}

    def _make_request(
        self, endpoint: str, method: str = "GET", params: Dict[str, Any] | None = None, data: Dict[str, Any] | None = None
    ) -> Dict[str, Any]:
        """
        Make a request to the Spotify API with automatic token refresh
        """
        self._check_token()

        url = f"{self.BASE_URL}{endpoint}"
        response = None
        
        # Default to empty dict if params or data is None
        params = params or {}
        data = data or {}

        try:
            if method == "GET":
                response = requests.get(url, headers=self.headers, params=params)
            elif method == "POST":
                response = requests.post(url, headers=self.headers, json=data)
            elif method == "PUT":
                response = requests.put(url, headers=self.headers, json=data)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP Error: {e}")
            response = e.response
            if response and response.status_code == 401:
                # Token might be invalid, force refresh
                setattr(self.user, "token_expires_at", None)  # Force token refresh
                self._check_token()
                return self._make_request(endpoint, method, params, data)
            raise
        except Exception as e:
            logger.error(f"Error making request to Spotify API: {e}")
            raise

    def get_user_profile(self) -> Dict[str, Any]:
        """
        Get the user's Spotify profile
        """
        return self._make_request("/me")

    def get_recently_played(
        self, limit: int = 50, after: int | None = None, before: int | None = None
    ) -> Dict[str, Any]:
        """
        Get the user's recently played tracks
        """
        params: Dict[str, Any] = {"limit": limit}
        if after is not None:
            params["after"] = after
        if before is not None:
            params["before"] = before

        return self._make_request("/me/player/recently-played", params=params)

    def get_top_artists(
        self, time_range: str = "medium_term", limit: int = 50, offset: int = 0
    ) -> Dict[str, Any]:
        """
        Get the user's top artists
        time_range: 'short_term' (4 weeks), 'medium_term' (6 months), or 'long_term' (years)
        """
        params: Dict[str, Any] = {"time_range": time_range, "limit": limit, "offset": offset}

        return self._make_request("/me/top/artists", params=params)

    def get_top_tracks(
        self, time_range: str = "medium_term", limit: int = 50, offset: int = 0
    ) -> Dict[str, Any]:
        """
        Get the user's top tracks
        time_range: 'short_term' (4 weeks), 'medium_term' (6 months), or 'long_term' (years)
        """
        params: Dict[str, Any] = {"time_range": time_range, "limit": limit, "offset": offset}

        return self._make_request("/me/top/tracks", params=params)

    def get_audio_features(self, track_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Get audio features for multiple tracks
        """
        if not track_ids:
            return []

        # Spotify API limits to 100 IDs per request
        if len(track_ids) > 100:
            results: List[Dict[str, Any]] = []
            for i in range(0, len(track_ids), 100):
                batch = track_ids[i : i + 100]
                results.extend(self.get_audio_features(batch))
            return results

        params = {"ids": ",".join(track_ids)}
        response = self._make_request("/audio-features", params=params)
        return response.get("audio_features", [])

    def fetch_and_store_recently_played(self) -> Dict[str, str]:
        """
        Fetch and store the user's recently played tracks
        """
        try:
            # Get the most recent timestamp in the database
            latest_played = (
                self.db.query(ListeningHistory)
                .filter(ListeningHistory.user_id == self.user.user_id)
                .order_by(ListeningHistory.played_at.desc())
                .first()
            )

            # If we have data, use 'after' parameter to get only new plays
            after_param = None
            if latest_played is not None:
                played_at = getattr(latest_played, "played_at", None)
                if played_at is not None:
                    # Convert datetime to timestamp in milliseconds
                    after_param = int(played_at.timestamp() * 1000)

            # Get recently played tracks from Spotify
            data = self.get_recently_played(after=after_param)
            items = data.get("items", [])

            # If we didn't get any new tracks, return
            if not items:
                return {"status": "success", "message": "No new tracks to fetch"}

            # Process and store each track
            new_tracks: List[ListeningHistory] = [] # Add type hint
            track_ids: List[str] = [] # Add type hint
            for item in items:
                # Extract necessary data
                track = item.get("track", {})
                track_id = track.get("id")

                # Skip tracks without IDs
                if not track_id:
                    continue

                # Check if we already have this play
                played_at = datetime.fromisoformat(
                    item.get("played_at").replace("Z", "+00:00")
                )
                existing = (
                    self.db.query(ListeningHistory)
                    .filter(
                        ListeningHistory.user_id == self.user.user_id,
                        ListeningHistory.track_id == track_id,
                        ListeningHistory.played_at == played_at,
                    )
                    .first()
                )

                if existing:
                    continue

                # Create a new ListeningHistory record
                artist = track.get("artists", [{}])[0]  # Get the first artist
                album = track.get("album", {})

                new_track = ListeningHistory(
                    user_id=self.user.user_id,
                    track_id=track_id,
                    track_name=track.get("name", ""),
                    artist_id=artist.get("id", ""),
                    artist_name=artist.get("name", ""),
                    album_id=album.get("id", ""),
                    album_name=album.get("name", ""),
                    played_at=played_at,
                    duration_ms=track.get("duration_ms", 0),
                )

                new_tracks.append(new_track)
                track_ids.append(track_id)

            # Bulk insert new listening history records
            if new_tracks:
                self.db.bulk_save_objects(new_tracks)
                self.db.commit()

            # Fetch and store audio features for new tracks
            self._store_audio_features(track_ids)

            return {
                "status": "success",
                "message": f"Fetched and stored {len(new_tracks)} new tracks",
            }

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error fetching recently played: {e}")
            return {"status": "error", "message": str(e)}

    def fetch_and_store_top_items(self) -> Dict[str, str]:
        """
        Fetch and store the user's top artists and tracks
        """
        try:
            time_ranges = ["short_term", "medium_term", "long_term"]

            for time_range in time_ranges:
                # Fetch top artists
                artists_data = self.get_top_artists(time_range=time_range)
                artists = artists_data.get("items", [])

                # Clear existing top artists for this user and time range
                self.db.query(TopArtist).filter(
                    TopArtist.user_id == self.user.user_id, TopArtist.term == time_range
                ).delete()

                # Store new top artists
                for rank, artist in enumerate(artists, 1):
                    top_artist = TopArtist(
                        user_id=self.user.user_id,
                        artist_id=artist.get("id", ""),
                        artist_name=artist.get("name", ""),
                        term=time_range,
                        rank=rank,
                        genres=",".join(artist.get("genres", [])),
                        popularity=artist.get("popularity", 0),
                    )
                    self.db.add(top_artist)

                # Fetch top tracks
                tracks_data = self.get_top_tracks(time_range=time_range)
                tracks = tracks_data.get("items", [])

                # Clear existing top tracks for this user and time range
                self.db.query(TopTrack).filter(
                    TopTrack.user_id == self.user.user_id, TopTrack.term == time_range
                ).delete()

                # Track IDs for audio features
                track_ids: List[str] = [] # Add type hint

                # Store new top tracks
                for rank, track in enumerate(tracks, 1):
                    artist = track.get("artists", [{}])[0]  # Get the first artist
                    album = track.get("album", {})

                    top_track = TopTrack(
                        user_id=self.user.user_id,
                        track_id=track.get("id", ""),
                        track_name=track.get("name", ""),
                        artist_id=artist.get("id", ""),
                        artist_name=artist.get("name", ""),
                        album_id=album.get("id", ""),
                        album_name=album.get("name", ""),
                        term=time_range,
                        rank=rank,
                        popularity=track.get("popularity", 0),
                    )
                    self.db.add(top_track)
                    track_ids.append(track.get("id"))

                # Fetch and store audio features for top tracks
                self._store_audio_features(track_ids)

            self.db.commit()

            return {
                "status": "success",
                "message": "Fetched and stored top artists and tracks",
            }

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error fetching top items: {e}")
            return {"status": "error", "message": str(e)}

    def _store_audio_features(self, track_ids: List[str]):
        """
        Fetch and store audio features for tracks
        """
        if not track_ids:
            return

        # Remove duplicates
        track_ids = list(set(track_ids))

        # Check which track_ids already have audio features
        existing_track_ids = [
            r[0]
            for r in self.db.query(AudioFeatures.track_id)
            .filter(AudioFeatures.track_id.in_(track_ids))
            .all()
        ]

        # Filter out track_ids that already have audio features
        new_track_ids = [tid for tid in track_ids if tid not in existing_track_ids]

        if not new_track_ids:
            return

        # Fetch audio features for new tracks
        audio_features = self.get_audio_features(new_track_ids)

        # Store audio features
        for feature in audio_features:
            if not feature or not feature.get("id"):
                continue

            audio_feature = AudioFeatures(
                track_id=feature.get("id"),
                danceability=feature.get("danceability", 0),
                energy=feature.get("energy", 0),
                key=feature.get("key", 0),
                loudness=feature.get("loudness", 0),
                mode=feature.get("mode", 0),
                speechiness=feature.get("speechiness", 0),
                acousticness=feature.get("acousticness", 0),
                instrumentalness=feature.get("instrumentalness", 0),
                liveness=feature.get("liveness", 0),
                valence=feature.get("valence", 0),
                tempo=feature.get("tempo", 0),
                duration_ms=feature.get("duration_ms", 0),
                time_signature=feature.get("time_signature", 4),
            )
            self.db.add(audio_feature)

        self.db.commit()
