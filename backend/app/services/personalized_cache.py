from threading import Lock
import time
from typing import Any, Optional


class PersonalizedRecommendationCache:
    """Thread-safe, process-local user taste profile and explanation cache with generation tracking."""

    def __init__(self, ttl_seconds: float = 3600.0, max_capacity: int = 500) -> None:
        self.ttl_seconds = ttl_seconds
        self.max_capacity = max_capacity
        self._lock = Lock()
        self._user_versions: dict[str, int] = {}
        # (user_id, shop_id) -> (location_independent_explanation, timestamp)
        self._explanation_cache: dict[tuple[str, str], tuple[str, float]] = {}
        # user_id -> (taste_profile_dict, timestamp)
        self._profile_cache: dict[str, tuple[dict[str, Any], float]] = {}

    def get_explanation(self, user_id: str, shop_id: str) -> Optional[str]:
        """Retrieve unexpired location-independent explanation for (user_id, shop_id)."""
        with self._lock:
            entry = self._explanation_cache.get((user_id, shop_id))
            if not entry:
                return None
            explanation, cached_at = entry
            if time.time() - cached_at > self.ttl_seconds:
                self._explanation_cache.pop((user_id, shop_id), None)
                return None
            return explanation

    def set_explanation(self, user_id: str, shop_id: str, explanation: str) -> None:
        """Store location-independent explanation in cache."""
        with self._lock:
            if len(self._explanation_cache) >= self.max_capacity and (user_id, shop_id) not in self._explanation_cache:
                oldest_key = min(self._explanation_cache, key=lambda k: self._explanation_cache[k][1])
                self._explanation_cache.pop(oldest_key, None)
            self._explanation_cache[(user_id, shop_id)] = (explanation, time.time())

    def get_profile(self, user_id: str) -> Optional[dict[str, Any]]:
        """Retrieve unexpired taste profile for user_id."""
        with self._lock:
            entry = self._profile_cache.get(user_id)
            if not entry:
                return None
            profile, cached_at = entry
            if time.time() - cached_at > self.ttl_seconds:
                self._profile_cache.pop(user_id, None)
                return None
            return profile

    def set_profile(self, user_id: str, profile: dict[str, Any]) -> None:
        """Store taste profile for user_id."""
        with self._lock:
            if len(self._profile_cache) >= self.max_capacity and user_id not in self._profile_cache:
                oldest_key = min(self._profile_cache, key=lambda k: self._profile_cache[k][1])
                self._profile_cache.pop(oldest_key, None)
            self._profile_cache[user_id] = (profile, time.time())

    def invalidate_user(self, user_id: str) -> None:
        """Invalidate all cached profiles and explanations for a user within this process."""
        with self._lock:
            self._user_versions[user_id] = self._user_versions.get(user_id, 0) + 1
            self._profile_cache.pop(user_id, None)
            keys_to_remove = [k for k in self._explanation_cache if k[0] == user_id]
            for k in keys_to_remove:
                self._explanation_cache.pop(k, None)

    def clear(self) -> None:
        """Clear all caches (used during unit test setUp/tearDown)."""
        with self._lock:
            self._user_versions.clear()
            self._profile_cache.clear()
            self._explanation_cache.clear()


_global_personalized_cache = PersonalizedRecommendationCache()


def get_personalized_cache() -> PersonalizedRecommendationCache:
    """Dependency / provider for the shared in-memory personalized recommendation cache."""
    return _global_personalized_cache
