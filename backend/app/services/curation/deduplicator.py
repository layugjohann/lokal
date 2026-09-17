import re
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class CandidatePlace:
    """Raw candidate place item from external provider."""
    place_id: str
    display_name: str
    formatted_address: Optional[str] = None


@dataclass(frozen=True)
class QualifyingLocation:
    """A distinct physical location verified through deduplication."""
    place_id: str
    display_name: str
    normalized_address_key: str
    region_key: str


class LocationDeduplicator:
    """Deduplicates candidate places by Provider Place ID and physical street address.

    Prevents multiple Place IDs at the same physical establishment from inflating location counts.
    """

    @classmethod
    def normalize_address(cls, address: Optional[str]) -> tuple[str, str]:
        """Normalize address to produce a street-level deduplication key and a regional key.

        Returns:
            (normalized_address_key, region_key)
        """
        if not address or not address.strip():
            return "", ""

        raw = address.lower().strip()

        # Remove suite, unit, floor, room, building qualifiers
        cleaned = re.sub(
            r"\b(?:unit|suite|ste|floor|fl|rm|room|level|bldg|building|#)\s*[\w\-]+",
            "",
            raw,
            flags=re.IGNORECASE,
        )

        # Remove postal codes and common country names for cleaner street matching
        cleaned = re.sub(r"\b\d{4,6}\b", "", cleaned)
        cleaned = re.sub(r"\b(philippines|ph|usa|us)\b", "", cleaned)

        # Clean punctuation and extra whitespace
        cleaned = re.sub(r"[,.\-_/]+", " ", cleaned)
        cleaned = " ".join(cleaned.split())

        # Extract broad region / locality (e.g. Makati, Quezon City, Manila, Cebu)
        parts = [p.strip() for p in raw.split(",") if p.strip()]
        region_key = parts[-2].strip() if len(parts) >= 2 else (parts[0] if parts else "")

        return cleaned, region_key

    @classmethod
    def deduplicate(cls, candidates: list[CandidatePlace]) -> list[QualifyingLocation]:
        """Deduplicate candidate places by Place ID and physical address.

        Returns a list of distinct qualifying physical locations.
        """
        seen_place_ids: set[str] = set()
        seen_address_keys: set[str] = set()
        qualifying: list[QualifyingLocation] = []

        for candidate in candidates:
            if not candidate.place_id or candidate.place_id in seen_place_ids:
                continue

            seen_place_ids.add(candidate.place_id)

            norm_addr, region = cls.normalize_address(candidate.formatted_address)

            # If address is substantial, ensure no duplicate physical location at same address
            if norm_addr and len(norm_addr) > 5:
                if norm_addr in seen_address_keys:
                    # Same physical address already counted under another Place ID
                    continue
                seen_address_keys.add(norm_addr)

            qualifying.append(
                QualifyingLocation(
                    place_id=candidate.place_id,
                    display_name=candidate.display_name,
                    normalized_address_key=norm_addr,
                    region_key=region,
                )
            )

        return qualifying
