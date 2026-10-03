import asyncio
import json
import logging
import re
from typing import Any, Optional, Protocol, runtime_checkable
from uuid import UUID
from fastapi import HTTPException, status
import httpx
from pydantic import ValidationError
from supabase import Client

from ..core.config import settings
from ..schemas.auth import UserResponse
from ..schemas.recommendation import (
    CandidateEvidencePack,
    PersonalizedRecommendationsResponse,
    RecommendationStatus,
    RecommendedShopItem,
    StructuredAIExplanation,
)
from ..schemas.shop import NearbyShopResponse
from .personalized_cache import PersonalizedRecommendationCache, get_personalized_cache
from .reviews.base import ExternalProviderError
from .reviews.recommendations import build_gemini_generation_config

logger = logging.getLogger(__name__)

GEMINI_API_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"

CANDIDATE_OVERFETCH_LIMIT = 30
CANDIDATE_EVALUATION_LIMIT = 10
MAX_RECOMMENDATIONS_RETURNED = 5
EXPLANATION_BATCH_TIMEOUT = 7.0

PROXIMITY_FORBIDDEN_TERMS = {
    "nearby",
    "close",
    "closest",
    "meter",
    "meters",
    "km",
    "kilometer",
    "kilometers",
    "away",
    "walking",
    "walk",
    "distance",
    "neighborhood",
    "around the corner",
}

COFFEE_FEATURE_ONTOLOGY: dict[str, dict[str, Any]] = {
    # Brew & Beverage Styles
    "pour_over": {
        "label": "pour-over coffee",
        "keywords": ["pour over", "pour-over", "pourover", "manual brew", "filter coffee", "drip"],
    },
    "espresso": {
        "label": "espresso & milk drinks",
        "keywords": ["espresso", "cortado", "macchiato", "flat white", "americano"],
    },
    "cold_brew": {
        "label": "cold brew",
        "keywords": ["cold brew", "coldbrew", "nitro", "iced coffee"],
    },
    "specialty_lattes": {
        "label": "specialty lattes",
        "keywords": ["spanish latte", "caramel latte", "vanilla latte", "oat latte", "sea salt latte"],
    },
    "matcha": {
        "label": "matcha & tea",
        "keywords": ["matcha", "matcha latte", "hojicha", "green tea"],
    },
    # Beans & Craft
    "specialty_beans": {
        "label": "specialty roast beans",
        "keywords": ["specialty", "single origin", "roastery", "in-house roast", "beans", "ethiopian", "colombian"],
    },
    # Ambiance & Work
    "quiet_study": {
        "label": "quiet work-friendly space",
        "keywords": ["quiet", "work", "laptop", "study", "wifi", "sockets", "outlets", "peaceful"],
    },
    "cozy_aesthetic": {
        "label": "cozy aesthetic ambiance",
        "keywords": ["cozy", "aesthetic", "minimalist", "warm", "vibes", "ambiance", "atmosphere"],
    },
    "spacious": {
        "label": "spacious outdoor seating",
        "keywords": ["spacious", "outdoor", "al fresco", "airy", "plenty of seating", "patio"],
    },
    # Bakery & Food
    "pastries": {
        "label": "fresh pastries",
        "keywords": ["croissant", "pastry", "pastries", "baked goods", "croissants", "sourdough", "bread"],
    },
    "breakfast_food": {
        "label": "breakfast & brunch",
        "keywords": ["breakfast", "brunch", "sandwiches", "bagel", "toast", "waffles"],
    },
}


def extract_features_from_text(text: Optional[str]) -> set[str]:
    """Scan text for keywords in the coffee feature ontology."""
    if not text or not text.strip():
        return set()

    norm = text.lower()
    matched = set()

    for feat_key, meta in COFFEE_FEATURE_ONTOLOGY.items():
        for kw in meta["keywords"]:
            pattern = r"\b" + re.escape(kw) + r"\b"
            if re.search(pattern, norm):
                matched.add(feat_key)
                break

    return matched


@runtime_checkable
class ExplanationGenerator(Protocol):
    """Protocol for generating location-independent recommendation explanations."""

    async def generate_explanation(
        self,
        evidence: CandidateEvidencePack,
    ) -> Optional[str]:
        ...


class GeminiExplanationGenerator:
    """Location-independent explanation generator using Google Gemini API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 6.0,
    ) -> None:
        """Initialize generator with API key, model target, and per-call timeout."""
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model = model or settings.GEMINI_MODEL or "gemini-2.5-flash"
        self.timeout = timeout

    async def generate_explanation(
        self,
        evidence: CandidateEvidencePack,
    ) -> Optional[str]:
        """Synthesize a location-independent explanation strictly from the evidence pack."""
        if not self.api_key:
            return None

        system_instruction = (
            "You are LOKAL's coffee shop recommendation explanation writer.\n"
            "Instructions:\n"
            "1. Write 1 concise, factual sentence explaining why this shop was recommended based on its verified matched coffee trait or community rating.\n"
            "2. Never mention distance, location, proximity, walking, kilometers, or meters.\n"
            "3. Never invent claims or attributes not present in the provided evidence.\n"
            "4. Output valid JSON strictly conforming to the requested schema.\n"
        )

        user_content = (
            f"Evidence Pack:\n"
            f"Shop Name: {evidence.shop_name}\n"
            f"Matched Feature: {evidence.matched_feature_label or 'None'}\n"
            f"Community Rating: {evidence.lokal_community_rating or 'None'}\n"
            "Please provide a location-independent 1-sentence explanation."
        )

        response_schema = {
            "type": "object",
            "properties": {
                "matched_feature": {
                    "type": "string",
                    "description": "The exact matched feature label from the evidence pack",
                },
                "explanation": {
                    "type": "string",
                    "description": "1 concise sentence explaining the recommendation",
                },
            },
            "required": ["explanation"],
        }

        generation_config = build_gemini_generation_config(self.model, response_schema)

        body = {
            "system_instruction": {"parts": [{"text": system_instruction}]},
            "contents": [{"role": "user", "parts": [{"text": user_content}]}],
            "generationConfig": generation_config,
        }

        url = f"{GEMINI_API_BASE_URL}/{self.model}:generateContent"
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, headers=headers, json=body)

            if response.status_code != 200:
                logger.warning(f"Gemini API returned status {response.status_code} for explanation.")
                return None

            data = response.json()
            candidates = data.get("candidates", [])
            if not candidates or not isinstance(candidates[0], dict):
                return None

            content_parts = candidates[0].get("content", {}).get("parts", [])
            if not content_parts or not isinstance(content_parts[0], dict):
                return None

            raw_text = content_parts[0].get("text", "")
            parsed = StructuredAIExplanation.model_validate_json(raw_text)

            # Grounding Validation: Reject any proximity mention
            norm_exp = parsed.explanation.lower()
            for term in PROXIMITY_FORBIDDEN_TERMS:
                pattern = r"\b" + re.escape(term) + r"\b"
                if re.search(pattern, norm_exp):
                    logger.warning(f"Gemini explanation rejected: contained proximity term '{term}'")
                    return None

            # Grounding Validation: If matched_feature returned, verify exact match
            if parsed.matched_feature and evidence.matched_feature_label:
                if parsed.matched_feature.strip().lower() != evidence.matched_feature_label.strip().lower():
                    logger.warning("Gemini explanation rejected: matched_feature did not match evidence label")
                    return None

            return parsed.explanation.strip()

        except Exception as exc:
            logger.warning(f"Gemini explanation synthesis failed: {exc}")
            return None


class PersonalizedRecommendationService:
    """Service layer managing candidate generation, deterministic personalization scoring,

    and location-independent grounded explanation synthesis.
    """

    def __init__(
        self,
        explanation_generator: Optional[ExplanationGenerator] = None,
        cache: Optional[PersonalizedRecommendationCache] = None,
        batch_timeout: float = EXPLANATION_BATCH_TIMEOUT,
    ) -> None:
        """Initialize service with explanation generator, cache, and concurrent batch timeout."""
        self.generator = explanation_generator or GeminiExplanationGenerator()
        self.cache = cache or get_personalized_cache()
        self.batch_timeout = batch_timeout

    def build_user_taste_profile(
        self,
        user_id: str,
        user_reviews: list[dict[str, Any]],
        user_favorites: list[dict[str, Any]],
        supabase: Client,
        generation: Optional[int] = None,
    ) -> tuple[dict[str, float], set[str], Optional[float]]:
        """Construct user taste profile (P_user, N_user, user_avg_rating) from user signals.

        Returns:
            Tuple of (p_user_weights, n_user_avoidance, user_avg_rating).
        """
        # Cached profile check
        cached_profile = self.cache.get_profile(user_id)
        if cached_profile:
            return (
                cached_profile.get("p_user", {}),
                set(cached_profile.get("n_user", [])),
                cached_profile.get("user_avg_rating"),
            )

        # 1. User average rating: arithmetic mean across user's first-party LOKAL reviews
        user_avg_rating: Optional[float] = None
        if user_reviews:
            user_avg_rating = round(
                sum(float(r["rating"]) for r in user_reviews) / len(user_reviews), 2
            )

        p_user_weights: dict[str, float] = {}
        n_user_avoidance: set[str] = set()

        # 2. Extract features from user's own reviews
        for rev in user_reviews:
            rating = float(rev.get("rating", 0))
            content = rev.get("content") or ""
            feats = extract_features_from_text(content)

            if rating >= 4.0:
                for f in feats:
                    p_user_weights[f] = p_user_weights.get(f, 0.0) + 2.0
            elif rating <= 2.0:
                n_user_avoidance.update(feats)

        # 3. Extract features from user's favorited shops' positive reviews
        fav_shop_ids = [str(fav["shop_id"]) for fav in user_favorites if fav.get("shop_id")]
        if fav_shop_ids:
            try:
                fav_revs_res = (
                    supabase.table("reviews")
                    .select("shop_id, content, rating")
                    .in_("shop_id", fav_shop_ids)
                    .eq("source", "lokal")
                    .gte("rating", 4)
                    .execute()
                )
                for fr in fav_revs_res.data or []:
                    content = fr.get("content") or ""
                    feats = extract_features_from_text(content)
                    for f in feats:
                        p_user_weights[f] = p_user_weights.get(f, 0.0) + 1.0
            except Exception as exc:
                logger.warning(f"Failed to fetch favorited shops reviews for user {user_id}: {exc}")

        # 4. Normalize p_user_weights to [0.0, 1.0]
        if p_user_weights:
            max_w = max(p_user_weights.values())
            normalized_p = {f: w / max_w for f, w in p_user_weights.items()}
        else:
            normalized_p = {}

        # Cache profile with generation fencing
        profile_dict = {
            "p_user": normalized_p,
            "n_user": list(n_user_avoidance),
            "user_avg_rating": user_avg_rating,
        }
        self.cache.set_profile(user_id, profile_dict, generation=generation)

        return normalized_p, n_user_avoidance, user_avg_rating

    def _generate_fallback_explanation(
        self,
        matched_label: Optional[str],
        lokal_rating: Optional[float],
        provider_rating: Optional[float],
    ) -> str:
        """Deterministic location-independent fallback template."""
        if matched_label:
            return f"Recommended for its praised {matched_label}, matching your saved coffee preferences."
        if lokal_rating is not None:
            return f"Recommended for strong community ratings (☕ {lokal_rating:.1f}★), matching your coffee standards."
        rating_str = f"{provider_rating:.1f}" if provider_rating is not None else "4.5"
        return f"Recommended for high customer ratings (★ {rating_str}), matching your coffee standards."

    async def get_personalized_recommendations(
        self,
        user: UserResponse,
        supabase: Client,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        radius: float = 5000.0,
        limit: int = 5,
    ) -> PersonalizedRecommendationsResponse:
        """Retrieve personalized recommendations for the authenticated user."""
        clamped_limit = max(1, min(limit, MAX_RECOMMENDATIONS_RETURNED))
        str_user_id = str(user.id)

        # 0. Capture user mutation generation upfront for generation fencing
        user_generation = self.cache.get_user_generation(str_user_id)

        # 1. Fetch caller's first-party reviews
        try:
            reviews_res = (
                supabase.table("reviews")
                .select("id, shop_id, rating, content")
                .eq("user_id", str_user_id)
                .eq("source", "lokal")
                .execute()
            )
            user_reviews = reviews_res.data or []
        except Exception as exc:
            logger.error(f"Database error querying reviews for user {user.id}: {exc}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="A database error occurred while retrieving user reviews.",
            ) from exc

        # 2. Fetch caller's favorites
        try:
            favs_res = (
                supabase.table("favorites")
                .select("id, shop_id")
                .eq("user_id", str_user_id)
                .execute()
            )
            user_favorites = favs_res.data or []
        except Exception as exc:
            logger.error(f"Database error querying favorites for user {user.id}: {exc}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="A database error occurred while retrieving user favorites.",
            ) from exc

        # 3. Extract user taste profile (with generation fencing)
        p_user, n_user, user_avg_rating = self.build_user_taste_profile(
            str_user_id, user_reviews, user_favorites, supabase, generation=user_generation
        )

        # 4. Evaluate Insufficient-Data Gate
        # Personalization sufficiency is defined strictly by the presence of usable positive preference features
        if not p_user:
            return PersonalizedRecommendationsResponse(
                status=RecommendationStatus.INSUFFICIENT_DATA,
                message="Save coffee shops to your favorites or leave positive reviews to unlock personalized recommendations.",
                recommendations=[],
                total_candidates_evaluated=0,
            )

        # 5. Over-fetch candidates (CANDIDATE_OVERFETCH_LIMIT = 30)
        has_location = latitude is not None and longitude is not None
        raw_candidates: list[dict[str, Any]] = []

        if has_location:
            try:
                rpc_res = supabase.rpc(
                    "get_nearby_shops",
                    {
                        "user_lat": latitude,
                        "user_lng": longitude,
                        "radius_meters": radius,
                        "result_limit": CANDIDATE_OVERFETCH_LIMIT,
                        "result_offset": 0,
                        "search_query": None,
                        "min_rating": None,
                        "sort_by": "distance",
                        "min_lokal_rating": None,
                    },
                ).execute()
                raw_candidates = rpc_res.data or []
            except Exception as exc:
                logger.error(f"Database error executing nearby search RPC: {exc}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="A database error occurred while fetching candidate coffee shops.",
                ) from exc
        else:
            try:
                # No-location path: enforce APPROVED curation filter BEFORE candidate limit (30)
                # Order by rating DESC with nulls last, then deterministic tie-breaker by shop id
                shops_res = (
                    supabase.table("shops")
                    .select(
                        "id, name, address, latitude, longitude, rating, google_place_id, created_at, updated_at, shop_curation!inner(status)"
                    )
                    .eq("shop_curation.status", "APPROVED")
                    .order("rating", desc=True, nullsfirst=False)
                    .order("id")
                    .limit(CANDIDATE_OVERFETCH_LIMIT)
                    .execute()
                )
                shops_data = shops_res.data or []
                approved_ids = [str(s["id"]) for s in shops_data if s.get("id")]

                rating_acc: dict[str, list[float]] = {}
                # Prevent executing review query if zero approved candidate IDs exist
                if approved_ids:
                    revs_res = (
                        supabase.table("reviews")
                        .select("shop_id, rating")
                        .in_("shop_id", approved_ids)
                        .eq("source", "lokal")
                        .execute()
                    )
                    for r in revs_res.data or []:
                        sid = str(r["shop_id"])
                        rating_acc.setdefault(sid, []).append(float(r["rating"]))

                for s in shops_data:
                    sid = str(s["id"])
                    ratings = rating_acc.get(sid, [])
                    l_count = len(ratings)
                    l_avg = round(sum(ratings) / l_count, 2) if l_count > 0 else None
                    clean_shop = {k: v for k, v in s.items() if k != "shop_curation"}
                    raw_candidates.append({
                        **clean_shop,
                        "distance_meters": None,
                        "lokal_rating": l_avg,
                        "lokal_reviews_count": l_count,
                    })
            except Exception as exc:
                logger.error(f"Database error executing approved shops query: {exc}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="A database error occurred while fetching candidate coffee shops.",
                ) from exc

        # 6. Exclusion Filtering
        # Exclude shops user has already favorited OR reviewed
        user_excluded_shop_ids = {str(fav["shop_id"]) for fav in user_favorites if fav.get("shop_id")}
        user_excluded_shop_ids.update({str(rev["shop_id"]) for rev in user_reviews if rev.get("shop_id")})

        surviving_candidates = [
            c for c in raw_candidates if str(c.get("id")) not in user_excluded_shop_ids
        ]

        if not surviving_candidates:
            return PersonalizedRecommendationsResponse(
                status=RecommendationStatus.EMPTY,
                message="No new coffee shops to recommend nearby. Try expanding your search area.",
                recommendations=[],
                total_candidates_evaluated=0,
            )

        # 7. Candidate Feature Extraction & Deterministic Scoring (Bounded to top 10)
        evaluation_candidates = surviving_candidates[:CANDIDATE_EVALUATION_LIMIT]
        eval_shop_ids = [str(c["id"]) for c in evaluation_candidates if c.get("id")]

        candidate_features_map: dict[str, dict[str, float]] = {}
        if eval_shop_ids:
            try:
                cand_revs_res = (
                    supabase.table("reviews")
                    .select("shop_id, content, rating")
                    .in_("shop_id", eval_shop_ids)
                    .eq("source", "lokal")
                    .gte("rating", 4)
                    .execute()
                )
                for cr in cand_revs_res.data or []:
                    sid = str(cr["shop_id"])
                    content = cr.get("content") or ""
                    feats = extract_features_from_text(content)
                    if sid not in candidate_features_map:
                        candidate_features_map[sid] = {}
                    for f in feats:
                        candidate_features_map[sid][f] = min(
                            1.0, candidate_features_map[sid].get(f, 0.0) + 0.5
                        )
            except Exception as exc:
                logger.warning(f"Failed to fetch candidate reviews: {exc}")

        # Compute deterministic scores
        scored_candidates: list[tuple[float, dict[str, Any], Optional[str]]] = []
        w_taste = 0.60 if has_location else 0.70
        w_quality = 0.25 if has_location else 0.30
        w_proximity = 0.15 if has_location else 0.0

        for cand in evaluation_candidates:
            sid = str(cand["id"])
            c_feats = candidate_features_map.get(sid, {})

            # Taste score
            if any(f in n_user for f in c_feats):
                s_taste = 0.0
                best_feature = None
            else:
                overlap = sum(p_user[f] * c_feats.get(f, 0.0) for f in p_user if f in c_feats)
                sum_p = sum(p_user.values())
                s_taste = overlap / sum_p if sum_p > 0 else 0.0

                # Baseline for unreviewed candidates if ratings match user favorites standard
                if s_taste == 0.0 and not c_feats and cand.get("rating") is not None:
                    s_taste = 0.15

                # Find single best matched feature label
                matching_features = [f for f in p_user if f in c_feats]
                if matching_features:
                    best_feat = max(matching_features, key=lambda f: p_user[f] * c_feats[f])
                    best_feature = COFFEE_FEATURE_ONTOLOGY[best_feat]["label"]
                else:
                    best_feature = None

            # Quality score
            lokal_rating = cand.get("lokal_rating")
            provider_rating = cand.get("rating")
            count = cand.get("lokal_reviews_count", 0)
            base_rating = float(lokal_rating) if lokal_rating is not None else (float(provider_rating) if provider_rating is not None else 3.5)
            s_quality = 0.6 * (base_rating / 5.0) + 0.4 * min(1.0, count / 10.0)

            # Proximity score
            dist = cand.get("distance_meters")
            if dist is not None and radius > 0:
                s_proximity = max(0.0, 1.0 - (float(dist) / radius))
            else:
                s_proximity = 0.0

            relevance_score = (w_taste * s_taste) + (w_quality * s_quality) + (w_proximity * s_proximity)
            scored_candidates.append((relevance_score, cand, best_feature))

        # Deterministic sorting: RelevanceScore DESC, distance_meters ASC, lokal_reviews_count DESC, id ASC
        scored_candidates.sort(
            key=lambda item: (
                -item[0],
                item[1].get("distance_meters") if item[1].get("distance_meters") is not None else 99999999.0,
                -item[1].get("lokal_reviews_count", 0),
                str(item[1].get("id")),
            )
        )

        selected_candidates = scored_candidates[:clamped_limit]

        # 8. Location-Independent Grounded Explanation Generation (Concurrent with Bounded Batch Timeout)
        async def _resolve_candidate_explanation(
            cand_tuple: tuple[float, dict[str, Any], Optional[str]],
        ) -> str:
            _, cand, matched_label = cand_tuple
            sid = str(cand["id"])

            # Check explanation cache
            cached_exp = self.cache.get_explanation(str_user_id, sid)
            if cached_exp:
                return cached_exp

            evidence = CandidateEvidencePack(
                shop_id=sid,
                shop_name=cand["name"],
                matched_feature_label=matched_label,
                lokal_community_rating=cand.get("lokal_rating"),
            )

            # Attempt Gemini explanation
            try:
                ai_exp = await self.generator.generate_explanation(evidence)
                if ai_exp:
                    self.cache.set_explanation(
                        str_user_id, sid, ai_exp, generation=user_generation
                    )
                    return ai_exp
            except Exception as exc:
                logger.warning(
                    f"Gemini explanation generator raised an unexpected error for shop {sid}: {exc}"
                )

            # Deterministic fallback
            fallback = self._generate_fallback_explanation(
                matched_label, cand.get("lokal_rating"), cand.get("rating")
            )
            self.cache.set_explanation(
                str_user_id, sid, fallback, generation=user_generation
            )
            return fallback

        tasks = [
            asyncio.create_task(_resolve_candidate_explanation(cand_tuple))
            for cand_tuple in selected_candidates
        ]

        if tasks:
            done, pending = await asyncio.wait(tasks, timeout=self.batch_timeout)
            for p_task in pending:
                p_task.cancel()
        else:
            done, pending = set(), set()

        recommendations: list[RecommendedShopItem] = []
        for i, (_score, cand, matched_label) in enumerate(selected_candidates):
            task = tasks[i]
            if task in done and not task.cancelled() and task.exception() is None:
                explanation = task.result()
            else:
                if task in done and task.exception() is not None:
                    logger.warning(
                        f"Explanation task for shop {cand.get('id')} failed with exception: {task.exception()}"
                    )
                fallback = self._generate_fallback_explanation(
                    matched_label, cand.get("lokal_rating"), cand.get("rating")
                )
                self.cache.set_explanation(
                    str_user_id, str(cand["id"]), fallback, generation=user_generation
                )
                explanation = fallback

            shop_response = NearbyShopResponse(
                id=cand["id"],
                name=cand["name"],
                address=cand.get("address"),
                latitude=cand["latitude"],
                longitude=cand["longitude"],
                rating=cand.get("rating"),
                google_place_id=cand.get("google_place_id"),
                created_at=cand.get("created_at"),
                updated_at=cand.get("updated_at"),
                distance_meters=cand.get("distance_meters"),
                lokal_rating=cand.get("lokal_rating"),
                lokal_reviews_count=cand.get("lokal_reviews_count", 0),
            )
            recommendations.append(
                RecommendedShopItem(
                    shop=shop_response,
                    explanation=explanation,
                )
            )

        return PersonalizedRecommendationsResponse(
            status=RecommendationStatus.PERSONALIZED,
            message="Recommendations tailored to your coffee preferences.",
            recommendations=recommendations,
            total_candidates_evaluated=len(surviving_candidates),
        )


_global_personalized_service = PersonalizedRecommendationService()


def get_personalized_recommendation_service() -> PersonalizedRecommendationService:
    """Dependency / provider for PersonalizedRecommendationService."""
    return _global_personalized_service
