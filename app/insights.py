from datetime import datetime, timedelta
from typing import Any, Dict, List, Tuple

from sqlalchemy import desc, distinct, func
from sqlalchemy.orm import Session

from app.models import AudioFeatures, ListeningHistory, TopArtist, TopTrack


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
        insights: Dict[str, Any] = {
            "total_tracks_listened": self._get_total_tracks_listened(),
            "top_artists": self._get_top_artists(),
            "top_tracks": self._get_top_tracks(),
            "listening_time_stats": self._get_listening_time_stats(),
            "listening_by_time_of_day": self._get_listening_by_time_of_day(),
            "recent_favorites": self._get_recent_favorites(),
            "audio_features_averages": self._get_audio_features_averages(),
        }

        return insights

    def _get_total_tracks_listened(self) -> int:
        """
        Get the total number of tracks listened to
        """
        return (
            self.db.query(ListeningHistory)
            .filter(ListeningHistory.user_id == self.user_id)
            .count()
        )

    def _get_top_artists(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get the top 5 most listened artists overall
        """
        results = (
            self.db.query(
                ListeningHistory.artist_id,
                ListeningHistory.artist_name,
                func.count(ListeningHistory.id).label("listen_count"),
            )
            .filter(ListeningHistory.user_id == self.user_id)
            .group_by(ListeningHistory.artist_id, ListeningHistory.artist_name)
            .order_by(desc("listen_count"))
            .limit(limit)
            .all()
        )

        return [
            {
                "artist_id": r.artist_id,
                "artist_name": r.artist_name,
                "listen_count": r.listen_count,
            }
            for r in results
        ]

    def _get_top_tracks(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get the top 5 most listened tracks overall
        """
        results = (
            self.db.query(
                ListeningHistory.track_id,
                ListeningHistory.track_name,
                ListeningHistory.artist_name,
                func.count(ListeningHistory.id).label("listen_count"),
            )
            .filter(ListeningHistory.user_id == self.user_id)
            .group_by(
                ListeningHistory.track_id,
                ListeningHistory.track_name,
                ListeningHistory.artist_name,
            )
            .order_by(desc("listen_count"))
            .limit(limit)
            .all()
        )

        return [
            {
                "track_id": r.track_id,
                "track_name": r.track_name,
                "artist_name": r.artist_name,
                "listen_count": r.listen_count,
            }
            for r in results
        ]

    def _get_listening_time_stats(self) -> Dict[str, Any]:
        """
        Get stats about listening time (total, average per day, etc.)
        """
        # Get total duration in ms
        total_duration = (
            self.db.query(func.sum(ListeningHistory.duration_ms))
            .filter(ListeningHistory.user_id == self.user_id)
            .scalar()
            or 0
        )

        # Convert to hours
        total_hours = total_duration / (1000 * 60 * 60)

        # Get earliest and latest listen
        earliest = (
            self.db.query(func.min(ListeningHistory.played_at))
            .filter(ListeningHistory.user_id == self.user_id)
            .scalar()
        )

        latest = (
            self.db.query(func.max(ListeningHistory.played_at))
            .filter(ListeningHistory.user_id == self.user_id)
            .scalar()
        )

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
            "latest_listen": latest.isoformat() if latest else None,
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
            "night": (0, 6),  # 12 AM - 6 AM
        }

        # Initialize results
        results: Dict[str, int] = {period: 0 for period in time_ranges.keys()}

        # Query all played times
        played_time_tuples = (
            self.db.query(ListeningHistory.played_at)
            .filter(ListeningHistory.user_id == self.user_id)
            .all()
        )

        # Count plays in each time range
        for pt_tuple in played_time_tuples:
            played_at_time = pt_tuple[
                0
            ]  # Querying a single column returns a list of tuples
            if isinstance(played_at_time, datetime):
                hour = played_at_time.hour
                for period, (start, end) in time_ranges.items():
                    if start <= hour < end:
                        results[period] += 1
                        break
            # else: Consider logging or handling if played_at_time is not a datetime object

        return results

    def _get_recent_favorites(
        self, days: int = 30, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get the most listened tracks in the last 30 days
        """
        cutoff_date = datetime.now() - timedelta(days=days)

        results = (
            self.db.query(
                ListeningHistory.track_id,
                ListeningHistory.track_name,
                ListeningHistory.artist_name,
                func.count(ListeningHistory.id).label("listen_count"),
            )
            .filter(
                ListeningHistory.user_id == self.user_id,
                ListeningHistory.played_at >= cutoff_date,
            )
            .group_by(
                ListeningHistory.track_id,
                ListeningHistory.track_name,
                ListeningHistory.artist_name,
            )
            .order_by(desc("listen_count"))
            .limit(limit)
            .all()
        )

        return [
            {
                "track_id": r.track_id,
                "track_name": r.track_name,
                "artist_name": r.artist_name,
                "listen_count": r.listen_count,
            }
            for r in results
        ]

    def _get_audio_features_averages(self) -> Dict[str, float]:
        """
        Get average audio features for user's listening history
        """
        # Get all track IDs from user's listening history
        track_ids_tuples = (
            self.db.query(distinct(ListeningHistory.track_id))
            .filter(ListeningHistory.user_id == self.user_id)
            .all()
        )
        track_ids: List[str] = [r[0] for r in track_ids_tuples]

        if not track_ids:
            return {}

        # Calculate averages for each audio feature
        feature_fields = [
            "danceability",
            "energy",
            "speechiness",
            "acousticness",
            "instrumentalness",
            "liveness",
            "valence",
        ]

        avg_results: Dict[str, float] = {}
        for field in feature_fields:
            avg_value_query_result = (
                self.db.query(func.avg(getattr(AudioFeatures, field)))
                .filter(AudioFeatures.track_id.in_(track_ids))
                .scalar()
            )
            avg_value = (
                avg_value_query_result if avg_value_query_result is not None else 0.0
            )

            avg_results[field] = round(avg_value, 3)

        return avg_results

    def get_detailed_insights(self) -> Dict[str, Any]:
        """
        Generate more detailed insights about user's listening habits
        """
        basic_insights = self.get_basic_insights()

        # Add more detailed insights
        detailed_insights: Dict[str, Any] = {
            **basic_insights,
            "genre_distribution": self._get_genre_distribution(),
            "listening_trends_by_month": self._get_listening_trends_by_month(),
            "popular_vs_obscure": self._get_popular_vs_obscure_ratio(),
            "mood_analysis": self._analyze_mood_based_on_features(),
        }

        return detailed_insights

    def _get_genre_distribution(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get the distribution of genres based on top artists
        """
        top_artists_results = (
            self.db.query(TopArtist)
            .filter(
                TopArtist.user_id == self.user_id,
                TopArtist.term
                == "medium_term",  # Use medium term for better representation
            )
            .all()
        )

        genre_counts: Dict[str, int] = {}
        for artist in top_artists_results:
            genre_string: str = getattr(artist, "genres", "") or ""
            artist_rank: int = getattr(
                artist, "rank", 0
            )  # Default to 0 if rank is not found

            genres_list: List[str] = genre_string.split(",") if genre_string else []
            for genre_item_raw in genres_list:
                genre_item = genre_item_raw.strip()
                if genre_item:
                    score_weight: int = 50 - artist_rank + 1
                    genre_counts[genre_item] = (
                        genre_counts.get(genre_item, 0) + score_weight
                    )

        sorted_genres_tuples: List[Tuple[str, int]] = sorted(
            genre_counts.items(), key=lambda item: item[1], reverse=True
        )[:limit]

        return [{"genre": g, "score": s} for g, s in sorted_genres_tuples]

    def _get_listening_trends_by_month(self, months: int = 6) -> Dict[str, int]:
        """
        Get listening trends by month for the last N months
        """
        result: Dict[str, int] = {}
        now = datetime.now()

        for i in range(months - 1, -1, -1):
            current_month_zero_indexed = now.month - 1

            # Calculate total months from year 0 up to current month, then subtract i
            total_months_from_epoch_current = now.year * 12 + current_month_zero_indexed
            total_months_from_epoch_target = total_months_from_epoch_current - i

            target_year = total_months_from_epoch_target // 12
            target_month_one_indexed = (total_months_from_epoch_target % 12) + 1

            month_start_dt = datetime(
                target_year, target_month_one_indexed, 1, 0, 0, 0, 0
            )

            if target_month_one_indexed == 12:
                next_month_start_dt = datetime(target_year + 1, 1, 1, 0, 0, 0, 0)
            else:
                next_month_start_dt = datetime(
                    target_year, target_month_one_indexed + 1, 1, 0, 0, 0, 0
                )

            # Determine month_end_dt
            # If this iteration is for the current calendar month (i.e., i=0 and calculated year/month match now's year/month)
            # then the end date is 'now'. Otherwise, it's the start of the next month.
            if (
                i == 0
                and target_year == now.year
                and target_month_one_indexed == now.month
            ):
                month_end_dt = now
            else:
                month_end_dt = next_month_start_dt

            month_label = month_start_dt.strftime("%Y-%m")

            count = (
                self.db.query(ListeningHistory)
                .filter(
                    ListeningHistory.user_id == self.user_id,
                    ListeningHistory.played_at >= month_start_dt,
                    ListeningHistory.played_at < month_end_dt,
                )
                .count()
            )
            result[month_label] = count
        return result

    def _get_popular_vs_obscure_ratio(self) -> Dict[str, Any]:
        """
        Analyze the ratio of popular vs obscure music in the user's listening
        Based on Spotify's popularity score (0-100)
        """
        # Get average popularity from top tracks
        avg_popularity_query_result = (
            self.db.query(func.avg(TopTrack.popularity))
            .filter(
                TopTrack.user_id == self.user_id,
                TopTrack.term.in_(["short_term", "medium_term"]),
            )
            .scalar()
        )
        avg_popularity = (
            avg_popularity_query_result
            if avg_popularity_query_result is not None
            else 50.0
        )

        brackets = {
            "mainstream": (80, 101),  # Very popular (inclusive of 100)
            "popular": (60, 80),  # Popular
            "mixed": (40, 60),  # Moderate popularity
            "niche": (20, 40),  # Less popular
            "obscure": (0, 20),  # Very obscure
        }

        counts: Dict[str, int] = {}
        for label, (min_pop, max_pop) in brackets.items():
            count = (
                self.db.query(TopTrack)
                .filter(
                    TopTrack.user_id == self.user_id,
                    TopTrack.popularity >= min_pop,
                    TopTrack.popularity < max_pop,  # max_pop is exclusive
                    TopTrack.term.in_(["short_term", "medium_term"]),
                )
                .count()
            )
            counts[label] = count

        return {
            "average_popularity": round(avg_popularity, 1),
            "popularity_distribution": counts,
        }

    def _analyze_mood_based_on_features(self) -> Dict[str, Any]:
        """
        Analyze the overall mood of the user's music based on audio features
        """
        track_ids_tuples = (
            self.db.query(distinct(ListeningHistory.track_id))
            .filter(ListeningHistory.user_id == self.user_id)
            .all()
        )
        track_ids: List[str] = [r[0] for r in track_ids_tuples]

        if not track_ids:
            # Return a default structure if no track_ids to avoid errors downstream
            return {
                "primary_mood": "Unknown",
                "mood_indicators": {
                    "happiness": 0.0,
                    "energy": 0.0,
                    "danceability": 0.0,
                    "calmness": 0.0,
                },
                "mood_quadrant_values": {"valence": 0.0, "energy": 0.0},
            }

        # Get average values for mood-related features
        avg_valence_qr = (
            self.db.query(func.avg(AudioFeatures.valence))  # type: ignore
            .filter(AudioFeatures.track_id.in_(track_ids))
            .scalar()
        )
        avg_valence = avg_valence_qr if avg_valence_qr is not None else 0.5

        avg_energy_qr = (
            self.db.query(func.avg(AudioFeatures.energy))  # type: ignore
            .filter(AudioFeatures.track_id.in_(track_ids))
            .scalar()
        )
        avg_energy = avg_energy_qr if avg_energy_qr is not None else 0.5

        avg_danceability_qr = (
            self.db.query(func.avg(AudioFeatures.danceability))  # type: ignore
            .filter(AudioFeatures.track_id.in_(track_ids))
            .scalar()
        )
        avg_danceability = (
            avg_danceability_qr if avg_danceability_qr is not None else 0.5
        )

        # Determine mood quadrant
        mood_map: Dict[str, bool] = {
            "Exuberant": avg_valence > 0.5 and avg_energy > 0.5,
            "Relaxed": avg_valence > 0.5 and avg_energy <= 0.5,
            "Tense": avg_valence <= 0.5 and avg_energy > 0.5,
            "Melancholy": avg_valence <= 0.5 and avg_energy <= 0.5,
        }

        # Find the primary mood; default if none are true (should not happen with these conditions)
        primary_mood = "Unknown"
        for mood, is_active in mood_map.items():
            if is_active:
                primary_mood = mood
                break

        # Fallback if no mood is explicitly true (e.g. if valence or energy is exactly 0.5 in some edge cases)
        # This logic ensures one mood is always primary.
        if primary_mood == "Unknown":
            if avg_valence > 0.5:
                primary_mood = "Exuberant" if avg_energy > 0.5 else "Relaxed"
            else:
                primary_mood = "Tense" if avg_energy > 0.5 else "Melancholy"

        mood_indicators: Dict[str, float] = {
            "happiness": avg_valence,
            "energy": avg_energy,
            "danceability": avg_danceability,
            "calmness": 1 - avg_energy,
        }

        return {
            "primary_mood": primary_mood,
            "mood_indicators": {k: round(v, 3) for k, v in mood_indicators.items()},
            "mood_quadrant_values": {
                "valence": round(avg_valence, 3),
                "energy": round(avg_energy, 3),
            },
        }
