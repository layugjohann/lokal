from threading import Lock
import time
from typing import Any, Optional

EXPLANATION_CACHE_TTL = 3600.0
TASTE_PROFILE_CACHE_TTL = 1800.0


class PersonalizedRecommendationCache:
    """Thread-safe, process-local user taste profile and explanation cache with generation fencing."""

    def __init__(
        self,
        explanation_ttl_seconds: float = EXPLANATION_CACHE_TTL,
        profile_ttl_seconds: float = TASTE_PROFILE_CACHE_TTL,
        max_capacity: int = 500,
    ) -> None:
        """Initialize recommendation cache with distinct TTLs and bounded capacity."""
        self.explanation_ttl_seconds = explanation_ttl_seconds
        self.profile_ttl_seconds = profile_ttl_seconds
        self.max_capacity = max_capacity
        self._lock = Lock()
        self._user_versions: dict[str, int] = {}
        # (user_id, shop_id) -> (location_independent_explanation, timestamp)
        self._explanation_cache: dict[tuple[str, str], tuple[str, float]] = {}
        # user_id -> (taste_profile_dict, timestamp)
        self._profile_cache: dict[str, tuple[dict[str, Any], float]] = {}

    def get_user_generation(self, user_id: str) -> int:
        """Return the current mutation generation for a user."""
        with self._lock:
            return self._user_versions.get(user_id, 0)

    def get_explanation(self, user_id: str, shop_id: str) -> Optional[str]:
        """Retrieve unexpired location-independent explanation for (user_id, shop_id)."""
        with self._lock:
            entry = self._explanation_cache.get((user_id, shop_id))
            if not entry:
                return None
            explanation, cached_at = entry
            if time.time() - cached_at > self.explanation_ttl_seconds:
                self._explanation_cache.pop((user_id, shop_id), None)
                return None
            return explanation

    def set_explanation(
        self,
        user_id: str,
        shop_id: str,
        explanation: str,
        generation: Optional[int] = None,
    ) -> bool:
        """Store location-independent explanation in cache with generation fencing.

        Returns True if write succeeded, False if rejected due to stale generation.
        """
        with self._lock:
            if generation is not None and self._user_versions.get(user_id, 0) != generation:
                return False
            if (
                len(self._explanation_cache) >= self.max_capacity
                and (user_id, shop_id) not in self._explanation_cache
            ):
                oldest_key = min(
                    self._explanation_cache, key=lambda k: self._explanation_cache[k][1]
                )
                self._explanation_cache.pop(oldest_key, None)
            self._explanation_cache[(user_id, shop_id)] = (explanation, time.time())
            return True

    def get_profile(self, user_id: str) -> Optional[dict[str, Any]]:
        """Retrieve unexpired taste profile for user_id."""
        with self._lock:
            entry = self._profile_cache.get(user_id)
            if not entry:
                return None
            profile, cached_at = entry
            if time.time() - cached_at > self.profile_ttl_seconds:
                self._profile_cache.pop(user_id, None)
                return None
            return profile

    def set_profile(
        self,
        user_id: str,
        profile: dict[str, Any],
        generation: Optional[int] = None,
    ) -> bool:
        """Store taste profile for user_id with generation fencing.

        Returns True if write succeeded, False if rejected due to stale generation.
        """
        with self._lock:
            if generation is not None and self._user_versions.get(user_id, 0) != generation:
                return False
            if (
                len(self._profile_cache) >= self.max_capacity
                and user_id not in self._profile_cache
            ):
                oldest_key = min(
                    self._profile_cache, key=lambda k: self._profile_cache[k][1]
                )
                self._profile_cache.pop(oldest_key, None)
            self._profile_cache[user_id] = (profile, time.time())
            return True

    def invalidate_user(self, user_id: str) -> None:
        """Invalidate all cached profiles and explanations for a user and advance mutation generation."""
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
