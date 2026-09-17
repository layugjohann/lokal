import logging
from dataclasses import dataclass
from typing import Optional

from ...schemas.curation import CurationConfidence, ShopEligibilityStatus
from .brand_normalizer import BrandNormalizer
from .deduplicator import CandidatePlace, LocationDeduplicator, QualifyingLocation
from .evidence_provider import BaseEvidenceProvider, ExternalProviderError, ProviderSearchResult

logger = logging.getLogger(__name__)

DISTANT_MAJOR_REGIONS = {
    "metro manila", "manila", "makati", "taguig", "quezon city", "pasig",
    "cebu", "mandaue", "davao", "baguio", "iloilo", "bacolod", "cagayan de oro",
    "pampanga", "angeles",
}


@dataclass(frozen=True)
class ClassificationDecision:
    """The result of an automated eligibility classification run."""
    status: ShopEligibilityStatus
    confidence: CurationConfidence
    location_count: Optional[int]
    evidence_source: str
    reason: str
    qualifying_locations: list[QualifyingLocation]
    is_short_circuit: bool = False


class EligibilityClassifier:
    """Asymmetric, fail-closed business location classifier.

    Enforces:
    - >= 6 qualifying distinct locations -> EXCLUDED (existential proof, short-circuits)
    - 1–5 qualifying locations with complete evidence -> APPROVED
    - Insufficient, ambiguous, or incomplete evidence -> PENDING_REVIEW
    """

    def __init__(self, provider: BaseEvidenceProvider) -> None:
        self.provider = provider

    async def classify(
        self, shop_name: str, shop_place_id: Optional[str] = None
    ) -> ClassificationDecision:
        """Classify a shop's eligibility based on brand name and external evidence."""
        # 1. Brand extraction & distinctiveness check
        brand_result = BrandNormalizer.extract_brand(shop_name)

        if not brand_result.is_distinctive:
            logger.info(
                f"Shop '{shop_name}' brand '{brand_result.normalized_brand}' has low distinctiveness."
            )
            return ClassificationDecision(
                status=ShopEligibilityStatus.PENDING_REVIEW,
                confidence=CurationConfidence.LOW,
                location_count=None,
                evidence_source="brand_distinctiveness_heuristic",
                reason="Brand name is generic or lacks distinctiveness; manual verification required.",
                qualifying_locations=[],
                is_short_circuit=False,
            )

        # 2. Collect evidence from external provider
        query = f"{brand_result.normalized_brand} coffee"
        try:
            search_result: ProviderSearchResult = await self.provider.search_locations(query)
        except ExternalProviderError as exc:
            logger.warning(f"External evidence provider error classifying '{shop_name}': {exc}")
            return ClassificationDecision(
                status=ShopEligibilityStatus.PENDING_REVIEW,
                confidence=CurationConfidence.LOW,
                location_count=None,
                evidence_source="provider_error",
                reason=f"Evidence provider unavailable: {str(exc)}",
                qualifying_locations=[],
                is_short_circuit=False,
            )

        # 3. Filter by brand token matching heuristic
        matching_candidates: list[CandidatePlace] = [
            place
            for place in search_result.places
            if BrandNormalizer.is_candidate_match(place.display_name, brand_result.normalized_brand)
        ]

        # 4. Deduplicate candidates by Place ID and physical address
        qualifying_locations = LocationDeduplicator.deduplicate(matching_candidates)
        qualifying_count = len(qualifying_locations)

        # 5. Evidentiary Asymmetry Evaluation

        # Case A: >= 6 qualifying distinct locations -> EXCLUDED
        if qualifying_count >= 6:
            logger.info(
                f"Shop '{shop_name}' classified EXCLUDED ({qualifying_count} qualifying locations >= 6)."
            )
            return ClassificationDecision(
                status=ShopEligibilityStatus.EXCLUDED,
                confidence=CurationConfidence.HIGH,
                location_count=qualifying_count,
                evidence_source="google_places_text_search",
                reason=f"Found {qualifying_count} qualifying distinct physical locations (exceeds 5-location threshold).",
                qualifying_locations=qualifying_locations,
                is_short_circuit=True,
            )

        # Case B: 1–5 qualifying locations -> Check Completeness Criteria for APPROVED
        if 1 <= qualifying_count <= 5:
            # Completeness Criterion 1: Terminal search (no nextPageToken indicating missing places)
            if search_result.has_more:
                logger.info(
                    f"Shop '{shop_name}' has {qualifying_count} locations on page 1 but search is non-terminal."
                )
                return ClassificationDecision(
                    status=ShopEligibilityStatus.PENDING_REVIEW,
                    confidence=CurationConfidence.MEDIUM,
                    location_count=qualifying_count,
                    evidence_source="google_places_text_search",
                    reason=f"Found {qualifying_count} locations, but provider returned a continuation token indicating incomplete results.",
                    qualifying_locations=qualifying_locations,
                    is_short_circuit=False,
                )

            # Completeness Criterion 2: Geographic clustering sanity (no multi-region sprawl)
            if self._has_regional_sprawl(qualifying_locations):
                logger.info(
                    f"Shop '{shop_name}' locations exhibit multi-region sprawl: {qualifying_locations}"
                )
                return ClassificationDecision(
                    status=ShopEligibilityStatus.PENDING_REVIEW,
                    confidence=CurationConfidence.MEDIUM,
                    location_count=qualifying_count,
                    evidence_source="google_places_text_search",
                    reason="Qualifying locations span multiple distant metropolitan regions; incomplete chain inventory suspected.",
                    qualifying_locations=qualifying_locations,
                    is_short_circuit=False,
                )

            # All completeness criteria satisfied
            logger.info(
                f"Shop '{shop_name}' classified APPROVED ({qualifying_count} locations verified with complete evidence)."
            )
            return ClassificationDecision(
                status=ShopEligibilityStatus.APPROVED,
                confidence=CurationConfidence.HIGH,
                location_count=qualifying_count,
                evidence_source="google_places_text_search",
                reason=f"Established {qualifying_count} qualifying distinct physical location(s) with terminal search evidence.",
                qualifying_locations=qualifying_locations,
                is_short_circuit=False,
            )

        # Case C: 0 qualifying locations -> PENDING_REVIEW
        return ClassificationDecision(
            status=ShopEligibilityStatus.PENDING_REVIEW,
            confidence=CurationConfidence.LOW,
            location_count=0,
            evidence_source="google_places_text_search",
            reason="No qualifying provider locations identified for normalized brand name.",
            qualifying_locations=[],
            is_short_circuit=False,
        )

    @classmethod
    def _has_regional_sprawl(cls, locations: list[QualifyingLocation]) -> bool:
        """Detect if locations span across multiple distant metropolitan regions.

        If a brand has only 2-4 locations but they are scattered in different distant major cities
        (e.g. Manila and Cebu and Davao), it strongly indicates a widespread chain whose
        intermediate branches were omitted by ranking filters.
        """
        if len(locations) < 2:
            return False

        detected_major_regions: set[str] = set()
        for loc in locations:
            region_lower = loc.region_key.lower()
            for major in DISTANT_MAJOR_REGIONS:
                if major in region_lower:
                    detected_major_regions.add(major)
                    break

        # If locations span 3 or more distinct major distant regions, suspect regional sprawl
        # Or if 2 locations are in completely different island groups (e.g. Manila vs Cebu/Davao)
        island_groups = set()
        for r in detected_major_regions:
            if r in {"metro manila", "manila", "makati", "taguig", "quezon city", "pasig", "pampanga", "angeles", "baguio"}:
                island_groups.add("luzon")
            elif r in {"cebu", "mandaue", "iloilo", "bacolod"}:
                island_groups.add("visayas")
            elif r in {"davao", "cagayan de oro"}:
                island_groups.add("mindanao")

        return len(island_groups) >= 2
