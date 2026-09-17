import re
from dataclasses import dataclass
from typing import Optional


GENERIC_COFFEE_TOKENS = {
    "coffee",
    "cafe",
    "café",
    "shop",
    "the",
    "espresso",
    "bar",
    "brew",
    "brews",
    "brewing",
    "roaster",
    "roasters",
    "roastery",
    "house",
    "corner",
    "daily",
    "hub",
    "spot",
    "tea",
    "bakery",
    "kitchen",
    "lounge",
    "co",
    "co.",
    "company",
    "stand",
    "kiosk",
    "stop",
    "point",
    "station",
}

BRANCH_DELIMITERS_REGEX = re.compile(
    r"\s+(?:-|–|—|\||@|\/)\s+|\s*\([^)]*\)|\s*\[[^\]]*\]",
    re.IGNORECASE,
)

TRAILING_BRANCH_REGEX = re.compile(
    r",\s*(?:[A-Za-z0-9\s]+(?:City|Mall|Plaza|Village|Branch|BGC|Makati|Manila|Pasig|Taguig|Quezon City)?)$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class BrandExtractionResult:
    """Result of normalizing a raw shop name and evaluating distinctiveness."""
    raw_name: str
    normalized_brand: str
    is_distinctive: bool
    distinctive_tokens: list[str]


class BrandNormalizer:
    """Extracts base brand name from raw shop names and checks distinctiveness."""

    @classmethod
    def extract_brand(cls, raw_name: str) -> BrandExtractionResult:
        """Extract the core brand name from a raw shop name.

        Strips branch markers, parenthetical annotations, and location suffixes.
        Evaluates whether the extracted brand name is distinctive or overly generic.
        """
        if not raw_name or not raw_name.strip():
            return BrandExtractionResult(
                raw_name=raw_name,
                normalized_brand="",
                is_distinctive=False,
                distinctive_tokens=[],
            )

        cleaned = raw_name.strip()

        # Split on primary branch delimiters (e.g. "Yardstick Coffee - Legazpi" -> "Yardstick Coffee")
        parts = BRANCH_DELIMITERS_REGEX.split(cleaned)
        brand_candidate = parts[0].strip() if parts else cleaned

        # Strip trailing location after comma (e.g. "Toby's Estate, Makati" -> "Toby's Estate")
        brand_candidate = TRAILING_BRANCH_REGEX.sub("", brand_candidate).strip()

        # Clean trailing punctuation
        brand_candidate = re.sub(r"[\s\-_,.]+$", "", brand_candidate).strip()
        if not brand_candidate:
            brand_candidate = cleaned

        # Tokenize and evaluate distinctiveness
        tokens = [
            t.lower()
            for t in re.findall(r"[A-Za-z0-9]+", brand_candidate)
            if len(t) > 0
        ]

        distinctive_tokens = [
            t for t in tokens if t not in GENERIC_COFFEE_TOKENS and len(t) > 2
        ]

        # A brand is distinctive if it contains at least one non-generic, substantive token
        is_distinctive = len(distinctive_tokens) > 0 and len(brand_candidate) >= 3

        return BrandExtractionResult(
            raw_name=raw_name,
            normalized_brand=brand_candidate,
            is_distinctive=is_distinctive,
            distinctive_tokens=distinctive_tokens,
        )

    @classmethod
    def is_candidate_match(cls, candidate_display_name: str, brand_name: str) -> bool:
        """Evaluate if a candidate place's display name matches the normalized brand name.

        Uses token set containment and boundary checking.
        """
        if not candidate_display_name or not brand_name:
            return False

        norm_candidate = candidate_display_name.lower().strip()
        norm_brand = brand_name.lower().strip()

        if norm_candidate == norm_brand:
            return True

        # Extract tokens
        brand_tokens = [
            t.lower()
            for t in re.findall(r"[A-Za-z0-9]+", norm_brand)
            if len(t) > 0
        ]
        candidate_tokens = set(
            t.lower()
            for t in re.findall(r"[A-Za-z0-9]+", norm_candidate)
            if len(t) > 0
        )

        if not brand_tokens:
            return False

        # Reject proximity references like "near Yardstick" or "beside Yardstick"
        if re.search(r"\b(?:near|beside|opposite|across\s+from)\s+" + re.escape(norm_brand), norm_candidate):
            return False

        for token in brand_tokens:
            if re.search(r"\b(?:near|beside|opposite|across\s+from)\s+" + re.escape(token), norm_candidate):
                return False

        # Extract brand distinctive tokens (non-generic)
        distinctive_brand_tokens = [
            t for t in brand_tokens if t not in GENERIC_COFFEE_TOKENS and len(t) > 2
        ]

        if distinctive_brand_tokens:
            # Candidate must contain all distinctive tokens of the brand
            if not set(distinctive_brand_tokens).issubset(candidate_tokens):
                return False
            return True

        # Fallback for brands without distinctive tokens
        brand_token_set = set(brand_tokens)
        return brand_token_set.issubset(candidate_tokens)
