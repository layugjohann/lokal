from abc import ABC, abstractmethod
from typing import Optional, Tuple
from ...schemas.review import ProviderAttribution, UnifiedReview


class ExternalProviderError(Exception):
    """Exception raised when an upstream review provider fails or returns an error."""
    pass


class BaseReviewProvider(ABC):
    """Abstract base class for external coffee shop review providers."""

    @abstractmethod
    async def fetch_reviews(
        self, external_id: str
    ) -> Tuple[list[UnifiedReview], Optional[ProviderAttribution], Optional[float], Optional[int]]:
        """Fetch and normalize reviews from the external provider.

        Args:
            external_id: Unique external identifier (e.g. Google Place ID).

        Returns:
            Tuple of:
                - list of normalized UnifiedReview objects
                - Optional ProviderAttribution
                - Optional average rating float
                - Optional total reviews count integer

        Raises:
            ExternalProviderError: If the upstream provider fails or cannot fulfill the request.
        """
        pass
