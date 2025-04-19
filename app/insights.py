from sqlalchemy.orm import Session
from sqlalchemy import func, desc, distinct
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import json

from app.models import User, ListeningHistory, TopArtist, TopTrack, AudioFeatures


class InsightsGenerator:
    """
    Class to generate insights from user's Spotify data
    """

    def __init__(self, db: Session, user_id: str):
        self.db = db
        self.user_id = user_id

    def get_basic_insights(self) -> Dict[str, Any]:
        """
        Generate basic insights about user's listening history
        """
        insights = {
            "total_tracks_listened": self._get_total_tracks_listened(),
            "top_artists": self._get_top_artists(),
            "top_tracks": self._get_top_tracks(),
            "listening_time_stats": self._get_listening_time_stats(),
            "listening_by_time_of_day": self._get_listening_by_time_of_day(),
            "recent_favorites": self._get_recent_favorites(),
            "audio_features_averages": self._get_audio_features_averages()
        }

        return insights

    def _get_total_tracks_listened(self) -> int:
        """
        Get the total number of tracks listened to
        """
        return self.db.query(ListeningHistory) \
            .filter(ListeningHistory.user_id == self.user_id) \
            .count()

    def _get_top_artists(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get the top 5 most listened artists overall
        """
        results = self.db.query(
            ListeningHistory.artist_id,
            ListeningHistory.artist_name,
            func.count(ListeningHistory.id).label("listen_count")
        ).filter(
            ListeningHistory.user_id == self.user_id
        ).group_by(
            ListeningHistory.artist_id,
            ListeningHistory.artist_name
        ).order_by(
            desc("listen_count")
        ).limit(limit).all()

        return [
            {
                "artist_id": r.artist_id,
                "artist_name": r.artist_name,
                "listen_count": r.listen_count
            }
            for r in results
        ]

    def _get_top_tracks(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get the top 5 most listened tracks overall
        """
        results = self.db.query(
            ListeningHistory.track_id,
            ListeningHistory.track_name,
            ListeningHistory.artist_name,
            func.count(ListeningHistory.id).label("listen_count")
        ).filter(
            ListeningHistory.user_id == self.user_id
        ).group_by(
            ListeningHistory.track_id,
            ListeningHistory.track_name,
            ListeningHistory.artist_name
        ).order_by(
            desc("listen_count")
        ).limit(limit).all()

        return [
            {
                "track_id": r.track_id,
                "track_name": r.track_name,
                "artist_name": r.artist_name,
                "listen_count": r.listen_count
            }
            for r in results
        ]

    def _get_listening_time_stats(self) -> Dict[str, Any]:
        """
        Get stats about listening time (total, average per day, etc.)
        """
        # Get total duration in ms
        total_duration = self.db.query(
            func.sum(ListeningHistory.duration_ms)
        ).filter(
            ListeningHistory.user_id == self.user_id
        ).scalar() or 0

        # Convert to hours
        total_hours = total_duration / (1000 * 60 * 60)

        # Get earliest and latest listen
        earliest = self.db.query(
            func.min(ListeningHistory.played_at)
        ).filter(
            ListeningHistory.user_id == self.user_id
        ).scalar()

        latest = self.db.query(
            func.max(ListeningHistory.played_at)
        ).filter(
            ListeningHistory.user_id == self.user_id
        ).scalar()

        # Calculate days of data
        days_of_data = 1  # Default to 1 to avoid division by zero
        if earliest and latest:
            delta = latest - earliest
            days_of_data = max(1, delta.days)

        # Average per day
        avg_hours_per_day = total_hours / days_of_data

        return {
            "total_listening_hours": round(total_hours, 2),
            "average_hours_per_day": round(avg_hours_per_day, 2),
            "days_of_data": days_of_data,
            "earliest_listen": earliest.isoformat() if earliest else None,
            "latest_listen": latest.isoformat() if latest else None
        }

    def _get_listening_by_time_of_day(self) -> Dict[str, int]:
        """
        Get listening patterns by time of day
        """
        # Define time ranges
        time_ranges = {
            "morning": (6, 12),  # 6 AM - 12 PM
            "afternoon": (12, 18),  # 12 PM - 6 PM
            "evening": (18, 24),  # 6 PM - 12 AM
            "night": (0, 6)  # 12 AM - 6 AM
        }

        # Initialize results
        results = {period: 0 for period in time_ranges.keys()}

        # Query all played times
        played_times = self.db.query(
            ListeningHistory.played_at
        ).filter(
            ListeningHistory.user_id == self.user_id
        ).all()

        # Count plays in each time range
        for pt in played_times:
            hour = pt.played_at.hour
            for period, (start, end) in time_ranges.items():
                if start <= hour < end:
                    results[period] += 1
                    break

        return results

    def _get_recent_favorites(self, days: int = 30, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get the most listened tracks in the last 30 days
        """
        cutoff_date = datetime.now() - timedelta(days=days)

        results = self.db.query(
            ListeningHistory.track_id,
            ListeningHistory.track_name,
            ListeningHistory.artist_name,
            func.count(ListeningHistory.id).label("listen_count")
        ).filter(
            ListeningHistory.user_id == self.user_id,
            ListeningHistory.played_at >= cutoff_date
        ).group_by(
            ListeningHistory.track_id,
            ListeningHistory.track_name,
            ListeningHistory.artist_name
        ).order_by(
            desc("listen_count")
        ).limit(limit).all()

        return [
            {
                "track_id": r.track_id,
                "track_name": r.track_name,
                "artist_name": r.artist_name,
                "listen_count": r.listen_count
            }
            for r in results
        ]

    def _get_audio_features_averages(self) -> Dict[str, float]:
        """
        Get average audio features for user's listening history
        """
        # Get all track IDs from user's listening history
        track_ids = [
            r[0] for r in self.db.query(distinct(ListeningHistory.track_id))
            .filter(ListeningHistory.user_id == self.user_id)
            .all()
        ]

        if not track_ids:
            return {}

        # Calculate averages for each audio feature
        feature_fields = [
            "danceability", "energy", "speechiness",
            "acousticness", "instrumentalness", "liveness",
            "valence"
        ]

        results = {}
        for field in feature_fields:
            avg_value = self.db.query(
                func.avg(getattr(AudioFeatures, field))
            ).filter(
                AudioFeatures.track_id.in_(track_ids)
            ).scalar() or 0

            results[field] = round(avg_value, 3)

        return results

    def get_detailed_insights(self) -> Dict[str, Any]:
        """
        Generate more detailed insights about user's listening habits
        """
        basic_insights = self.get_basic_insights()

        # Add more detailed insights
        detailed_insights = {
            **basic_insights,
            "genre_distribution": self._get_genre_distribution(),
            "listening_trends_by_month": self._get_listening_trends_by_month(),
            "popular_vs_obscure": self._get_popular_vs_obscure_ratio(),
            "mood_analysis": self._analyze_mood_based_on_features()
        }

        return detailed_insights

    def _get_genre_distribution(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get the distribution of genres based on top artists
        """
        top_artists = self.db.query(TopArtist).filter(
            TopArtist.user_id == self.user_id,
            TopArtist.term == "medium_term"  # Use medium term for better representation
        ).all()

        # Count genres
        genre_counts = {}
        for artist in top_artists:
            genres = artist.genres.split(",") if artist.genres else []
            for genre in genres:
                if genre:
                    genre_counts[genre] = genre_counts.get(genre, 0) + (50 - artist.rank + 1)  # Weight by rank

        # Sort and limit
        sorted_genres = sorted(genre_counts.items(), key=lambda x: x[1], reverse=True)[:limit]

        return [{"genre": genre, "score": score} for genre, score in sorted_genres]

    def _get_listening_trends_by_month(self, months: int = 6) -> Dict[str, int]:
        """
        Get listening trends by month for the last 6 months
        """
        result = {}
        now = datetime.now()

        # Generate month labels and query for each month
        for i in range(months - 1, -1, -1):
            month_start = (now.replace(day=1) - timedelta(days=now.day - 1) - timedelta(days=30 * i)).replace(hour=0,
                                                                                                              minute=0,
                                                                                                              second=0,
                                                                                                              microsecond=0)
            if i > 0:
                month_end = (now.replace(day=1) - timedelta(days=now.day - 1) - timedelta(days=30 * (i - 1))).replace(
                    hour=0, minute=0, second=0, microsecond=0)
            else:
                month_end = now

            month_label = month_start.strftime("%Y-%m")

            count = self.db.query(ListeningHistory).filter(
                ListeningHistory.user_id == self.user_id,
                ListeningHistory.played_at >= month_start,
                ListeningHistory.played_at < month_end
            ).count()

            result[month_label] = count

        return result

    def _get_popular_vs_obscure_ratio(self) -> Dict[str, Any]:
        """
        Analyze the ratio of popular vs obscure music in the user's listening
        Based on Spotify's popularity score (0-100)
        """
        # Get average popularity from top tracks
        avg_popularity = self.db.query(
            func.avg(TopTrack.popularity)
        ).filter(
            TopTrack.user_id == self.user_id,
            TopTrack.term.in_(["short_term", "medium_term"])
        ).scalar() or 50  # Default to 50 if no data

        # Count tracks in different popularity brackets
        brackets = {
            "mainstream": (80, 100),  # Very popular
            "popular": (60, 80),  # Popular
            "mixed": (40, 60),  # Moderate popularity
            "niche": (20, 40),  # Less popular
            "obscure": (0, 20)  # Very obscure
        }

        counts = {}
        for label, (min_pop, max_pop) in brackets.items():
            count = self.db.query(TopTrack).filter(
                TopTrack.user_id == self.user_id,
                TopTrack.popularity >= min_pop,
                TopTrack.popularity < max_pop,
                TopTrack.term.in_(["short_term", "medium_term"])
            ).count()
            counts[label] = count

        return {
            "average_popularity": round(avg_popularity, 1),
            "popularity_distribution": counts
        }

    def _analyze_mood_based_on_features(self) -> Dict[str, Any]:
        """
        Analyze the overall mood of the user's music based on audio features
        """
        # Get all track IDs from user's listening history
        track_ids = [
            r[0] for r in self.db.query(distinct(ListeningHistory.track_id))
            .filter(ListeningHistory.user_id == self.user_id)
            .all()
        ]

        if not track_ids:
            return {}

        # Get average values for mood-related features
        avg_valence = self.db.query(
            func.avg(AudioFeatures.valence)
        ).filter(
            AudioFeatures.track_id.in_(track_ids)
        ).scalar() or 0.5

        avg_energy = self.db.query(
            func.avg(AudioFeatures.energy)
        ).filter(
            AudioFeatures.track_id.in_(track_ids)
        ).scalar() or 0.5

        avg_danceability = self.db.query(
            func.avg(AudioFeatures.danceability)
        ).filter(
            AudioFeatures.track_id.in_(track_ids)
        ).scalar() or 0.5

        # Determine mood quadrant
        # High valence + high energy = Exuberant
        # High valence + low energy = Relaxed
        # Low valence + high energy = Tense/Angry
        # Low valence + low energy = Sad/Depressed

        moods = {
            "Exuberant": avg_valence > 0.5 and avg_energy > 0.5,
            "Relaxed": avg_valence > 0.5 and avg_energy <= 0.5,
            "Tense": avg_valence <= 0.5 and avg_energy > 0.5,
            "Melancholy": avg_valence <= 0.5 and avg_energy <= 0.5
        }

        primary_mood = max(moods.items(), key=lambda x: x[1])[0]

        # Calculate some additional mood indicators
        mood_indicators = {
            "happiness": avg_valence,
            "energy": avg_energy,
            "danceability": avg_danceability,
            "calmness": 1 - avg_energy
        }

        return {
            "primary_mood": primary_mood,
            "mood_indicators": {k: round(v, 3) for k, v in mood_indicators.items()},
            "mood_quadrant_values": {
                "valence": round(avg_valence, 3),
                "energy": round(avg_energy, 3)
            }
        }