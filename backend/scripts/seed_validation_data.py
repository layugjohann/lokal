"""CLI utility for managing LOKAL validation dataset (Issue #49).

Usage:
    python -m backend.scripts.seed_validation_data seed
    python -m backend.scripts.seed_validation_data verify
    python -m backend.scripts.seed_validation_data clean --dry-run
    python -m backend.scripts.seed_validation_data clean
    python -m backend.scripts.seed_validation_data export-sql --output supabase/seed.sql
"""

import argparse
from datetime import datetime, timezone
import logging
import os
import sys
from typing import Any, Optional
from urllib.parse import urlparse
from uuid import UUID

from dotenv import load_dotenv

load_dotenv()

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import settings
from app.core.supabase import get_service_role_supabase_client
from app.fixtures.validation_dataset import (
    CURATOR_USER_ID,
    OWNER_USER_ID,
    FIXTURE_CLAIMS,
    FIXTURE_CURATION_AUDITS,
    FIXTURE_FAVORITES,
    FIXTURE_REVIEWS,
    FIXTURE_SHOPS,
    FIXTURE_USERS,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

ALLOWED_TARGET_HOSTS = {
    "thustdjwwtkhlhbnuvin.supabase.co",  # Verified Remote Development Project
    "127.0.0.1",                         # Local Docker Postgres
    "localhost",                         # Local Docker Postgres
}


class SecurityError(Exception):
    """Raised when an environment or target host safety invariant is violated."""


class FixturePayloadConflictError(Exception):
    """Raised when an existing database record differs unexpectedly from fixture definition."""


class IdentityCollisionError(Exception):
    """Raised when an existing authentication account does not match expected fixture identity."""


def validate_environment_and_target_host() -> str:
    """Validate that the target Supabase host and environment are strictly allowed.

    Returns:
        The validated target hostname.

    Raises:
        SecurityError: If host or environment is not in the fail-closed allowlist.
    """
    if not settings.SUPABASE_URL:
        raise SecurityError("SUPABASE_URL is not configured.")

    parsed = urlparse(settings.SUPABASE_URL)
    hostname = (parsed.hostname or "").lower()

    if hostname not in ALLOWED_TARGET_HOSTS:
        raise SecurityError(
            f"Target host '{hostname}' is not in the development allowlist {ALLOWED_TARGET_HOSTS}. "
            "Refusing to execute."
        )

    if settings.ENVIRONMENT.lower() != "development":
        raise SecurityError(
            f"ENVIRONMENT is set to '{settings.ENVIRONMENT}'. "
            "Operations are strictly restricted to 'development'."
        )

    return hostname


def normalize_val(val: Any) -> Any:
    """Normalize database and fixture values for comparison."""
    if val is None:
        return None
    if isinstance(val, bool):
        return val
    if isinstance(val, UUID):
        return str(val)
    if isinstance(val, (int, float)):
        return round(float(val), 4)
    if isinstance(val, datetime):
        dt_utc = val.astimezone(timezone.utc)
        return dt_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
    if isinstance(val, str):
        clean = val.strip()
        try:
            iso_str = clean.replace("Z", "+00:00")
            dt = datetime.fromisoformat(iso_str)
            dt_utc = dt.astimezone(timezone.utc)
            return dt_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
        except (ValueError, TypeError):
            pass
        return clean
    return val


def compare_fields(existing: dict[str, Any], expected: dict[str, Any], field_names: list[str]) -> list[str]:
    """Compare fields and return list of differences."""
    diffs = []
    for f in field_names:
        v1 = normalize_val(existing.get(f))
        v2 = normalize_val(expected.get(f))
        if v1 != v2:
            diffs.append(f"{f}: db='{v1}' vs expected='{v2}'")
    return diffs


def fetch_all_auth_users(supabase: Any, page_size: int = 50) -> list[Any]:
    """Fetch all auth users from Supabase GoTrue admin API across all pages.

    Stops when the returned page contains fewer users than the requested page size.
    """
    all_users: list[Any] = []
    page = 1
    while True:
        res = supabase.auth.admin.list_users(page=page, per_page=page_size)
        page_users = getattr(res, "users", res) or []
        all_users.extend(page_users)
        if len(page_users) < page_size:
            break
        page += 1
    return all_users


# ---------------------------------------------------------------------------
# Seeding Logic
# ---------------------------------------------------------------------------

def seed_users(supabase: Any) -> None:
    """Idempotently provision test accounts via GoTrue Admin API without resetting passwords."""
    password = settings.TEST_USER_PASSWORD or os.getenv("TEST_USER_PASSWORD", "")
    if not password:
        raise SecurityError(
            "TEST_USER_PASSWORD must be configured in environment (.env) to provision test accounts."
        )

    logger.info("Verifying controlled test authentication accounts across all pages...")
    existing_users = fetch_all_auth_users(supabase)

    by_id = {str(u.id): u for u in existing_users}
    by_email = {u.email.lower(): u for u in existing_users if u.email}

    for u_fix in FIXTURE_USERS:
        uid_str = str(u_fix.id)
        email_str = u_fix.email.lower()

        existing_by_id = by_id.get(uid_str)
        existing_by_email = by_email.get(email_str)

        # Check for UUID collision with different email
        if existing_by_id and existing_by_id.email.lower() != email_str:
            raise IdentityCollisionError(
                f"Collision: User ID {uid_str} already exists with email '{existing_by_id.email}', "
                f"expected '{email_str}'."
            )

        # Check for Email collision with different UUID
        if existing_by_email and str(existing_by_email.id) != uid_str:
            raise IdentityCollisionError(
                f"Collision: Email '{email_str}' already exists with User ID {existing_by_email.id}, "
                f"expected '{uid_str}'."
            )

        if existing_by_id and existing_by_email:
            # Account exists and identity matches; preserve credentials without resetting password
            logger.info(f"User {email_str} ({uid_str}) already exists with matching identity. Untouched.")
            continue

        # Account does not exist; create it
        logger.info(f"Creating test account {email_str} ({uid_str})...")
        supabase.auth.admin.create_user({
            "id": uid_str,
            "email": email_str,
            "password": password,
            "email_confirm": True,
            "user_metadata": {"full_name": u_fix.full_name},
            "app_metadata": u_fix.app_metadata,
        })


def seed_database_records(supabase: Any) -> None:
    """Idempotently seed database records using read-before-write payload comparison."""
    logger.info("Seeding coffee shops...")
    for shop in FIXTURE_SHOPS:
        res = supabase.table("shops").select("*").eq("id", str(shop.id)).execute()
        expected = {
            "id": str(shop.id),
            "name": shop.name,
            "address": shop.address,
            "latitude": shop.latitude,
            "longitude": shop.longitude,
            "rating": shop.rating,
            "google_place_id": shop.google_place_id,
            "created_at": shop.created_at,
            "updated_at": shop.updated_at,
        }
        if res.data:
            diffs = compare_fields(res.data[0], expected, list(expected.keys()))
            if diffs:
                raise FixturePayloadConflictError(f"Shop {shop.id} conflict: {', '.join(diffs)}")
        else:
            supabase.table("shops").insert(expected).execute()

    logger.info("Seeding shop curation records...")
    for shop in FIXTURE_SHOPS:
        res = supabase.table("shop_curation").select("*").eq("shop_id", str(shop.id)).execute()
        expected = {
            "shop_id": str(shop.id),
            "status": shop.curation_status,
            "location_count": shop.branch_count,
            "evidence_source": shop.evidence_source,
            "confidence": shop.confidence,
            "is_manual_override": False,
            "curator_id": str(CURATOR_USER_ID),
            "curator_notes": shop.curator_notes,
            "evaluated_at": shop.created_at,
            "created_at": shop.created_at,
            "updated_at": shop.updated_at,
        }
        if res.data:
            diffs = compare_fields(res.data[0], expected, list(expected.keys()))
            if diffs:
                raise FixturePayloadConflictError(f"Shop curation {shop.id} conflict: {', '.join(diffs)}")
        else:
            supabase.table("shop_curation").insert(expected).execute()

    logger.info("Seeding shop curation audit logs...")
    for audit in FIXTURE_CURATION_AUDITS:
        res = supabase.table("shop_curation_audit").select("*").eq("id", str(audit.id)).execute()
        expected = {
            "id": str(audit.id),
            "shop_id": str(audit.shop_id),
            "old_status": audit.old_status,
            "new_status": audit.new_status,
            "old_location_count": audit.old_location_count,
            "new_location_count": audit.new_location_count,
            "changed_by": str(audit.changed_by),
            "change_source": audit.change_source,
            "reason": audit.reason,
            "created_at": audit.created_at,
        }
        if res.data:
            diffs = compare_fields(res.data[0], expected, list(expected.keys()))
            if diffs:
                raise FixturePayloadConflictError(f"Curation audit {audit.id} conflict: {', '.join(diffs)}")
        else:
            supabase.table("shop_curation_audit").insert(expected).execute()

    logger.info("Seeding synthetic reviews...")
    for rev in FIXTURE_REVIEWS:
        res = supabase.table("reviews").select("*").eq("id", str(rev.id)).execute()
        expected = {
            "id": str(rev.id),
            "shop_id": str(rev.shop_id),
            "user_id": str(rev.user_id),
            "author_name": rev.author_name,
            "rating": rev.rating,
            "content": rev.content,
            "source": rev.source,
            "created_at": rev.created_at,
            "updated_at": rev.updated_at,
        }
        if res.data:
            diffs = compare_fields(res.data[0], expected, list(expected.keys()))
            if diffs:
                raise FixturePayloadConflictError(f"Review {rev.id} conflict: {', '.join(diffs)}")
        else:
            supabase.table("reviews").insert(expected).execute()

    logger.info("Seeding favorites...")
    for fav in FIXTURE_FAVORITES:
        res = supabase.table("favorites").select("*").eq("id", str(fav.id)).execute()
        expected = {
            "id": str(fav.id),
            "user_id": str(fav.user_id),
            "shop_id": str(fav.shop_id),
            "created_at": fav.created_at,
        }
        if res.data:
            diffs = compare_fields(res.data[0], expected, list(expected.keys()))
            if diffs:
                raise FixturePayloadConflictError(f"Favorite {fav.id} conflict: {', '.join(diffs)}")
        else:
            supabase.table("favorites").insert(expected).execute()

    logger.info("Seeding claims...")
    for claim in FIXTURE_CLAIMS:
        res = supabase.table("shop_claims").select("*").eq("id", str(claim.id)).execute()
        expected = {
            "id": str(claim.id),
            "shop_id": str(claim.shop_id),
            "user_id": str(claim.user_id),
            "status": claim.status,
            "claimant_name": claim.claimant_name,
            "claimant_phone": claim.claimant_phone,
            "claimant_role": claim.claimant_role,
            "business_proof": claim.business_proof,
            "curator_id": str(claim.curator_id),
            "review_notes": claim.review_notes,
            "reviewed_at": claim.reviewed_at,
            "created_at": claim.created_at,
            "updated_at": claim.updated_at,
        }
        if res.data:
            diffs = compare_fields(res.data[0], expected, list(expected.keys()))
            if diffs:
                raise FixturePayloadConflictError(f"Claim {claim.id} conflict: {', '.join(diffs)}")
        else:
            supabase.table("shop_claims").insert(expected).execute()


# ---------------------------------------------------------------------------
# Verification Logic
# ---------------------------------------------------------------------------


def verify_dataset(supabase: Any) -> bool:
    """Verify that all fixture entities are present in the database.

    Returns:
        True if all records are verified, False otherwise.
    """
    logger.info("Verifying database entities against fixture definitions...")

    shop_ids = [str(s.id) for s in FIXTURE_SHOPS]
    rev_ids = [str(r.id) for r in FIXTURE_REVIEWS]
    fav_ids = [str(f.id) for f in FIXTURE_FAVORITES]
    claim_ids = [str(c.id) for c in FIXTURE_CLAIMS]
    audit_ids = [str(a.id) for a in FIXTURE_CURATION_AUDITS]

    shops_res = supabase.table("shops").select("id").in_("id", shop_ids).execute()
    curation_res = supabase.table("shop_curation").select("shop_id").in_("shop_id", shop_ids).execute()
    audits_res = supabase.table("shop_curation_audit").select("id").in_("id", audit_ids).execute()
    reviews_res = supabase.table("reviews").select("id").in_("id", rev_ids).execute()
    favorites_res = supabase.table("favorites").select("id").in_("id", fav_ids).execute()
    claims_res = supabase.table("shop_claims").select("id").in_("id", claim_ids).execute()

    print("\n================== VALIDATION DATASET INTEGRITY ==================")
    print(f"Shops:               {len(shops_res.data):2d} / {len(FIXTURE_SHOPS):2d}")
    print(f"Shop Curation:       {len(curation_res.data):2d} / {len(FIXTURE_SHOPS):2d}")
    print(f"Curation Audits:     {len(audits_res.data):2d} / {len(FIXTURE_CURATION_AUDITS):2d}")
    print(f"Reviews:             {len(reviews_res.data):2d} / {len(FIXTURE_REVIEWS):2d}")
    print(f"Favorites:           {len(favorites_res.data):2d} / {len(FIXTURE_FAVORITES):2d}")
    print(f"Claims:              {len(claims_res.data):2d} / {len(FIXTURE_CLAIMS):2d}")
    print("==================================================================")

    is_complete = (
        len(shops_res.data) == len(FIXTURE_SHOPS)
        and len(curation_res.data) == len(FIXTURE_SHOPS)
        and len(audits_res.data) == len(FIXTURE_CURATION_AUDITS)
        and len(reviews_res.data) == len(FIXTURE_REVIEWS)
        and len(favorites_res.data) == len(FIXTURE_FAVORITES)
        and len(claims_res.data) == len(FIXTURE_CLAIMS)
    )

    if is_complete:
        print("Status: ALL FIXTURE RECORDS VERIFIED SUCCESSFULLY.")
        return True
    else:
        print("Status: INCOMPLETE DATASET DETECTED.")
        return False


# ---------------------------------------------------------------------------
# Cleanup Logic
# ---------------------------------------------------------------------------

def inspect_fixture_records(supabase: Any) -> dict[str, list[str]]:
    """Inspect and return exact IDs of existing fixture-owned records."""
    shop_ids = [str(s.id) for s in FIXTURE_SHOPS]
    rev_ids = [str(r.id) for r in FIXTURE_REVIEWS]
    fav_ids = [str(f.id) for f in FIXTURE_FAVORITES]
    claim_ids = [str(c.id) for c in FIXTURE_CLAIMS]
    audit_ids = [str(a.id) for a in FIXTURE_CURATION_AUDITS]

    r_rev = supabase.table("reviews").select("id").in_("id", rev_ids).execute()
    r_fav = supabase.table("favorites").select("id").in_("id", fav_ids).execute()
    r_clm = supabase.table("shop_claims").select("id").in_("id", claim_ids).execute()
    r_aud = supabase.table("shop_curation_audit").select("id").in_("id", audit_ids).execute()
    r_cur = supabase.table("shop_curation").select("shop_id").in_("shop_id", shop_ids).execute()
    r_shp = supabase.table("shops").select("id").in_("id", shop_ids).execute()

    return {
        "reviews": [row["id"] for row in r_rev.data or []],
        "favorites": [row["id"] for row in r_fav.data or []],
        "shop_claims": [row["id"] for row in r_clm.data or []],
        "shop_curation_audit": [row["id"] for row in r_aud.data or []],
        "shop_curation": [row["shop_id"] for row in r_cur.data or []],
        "shops": [row["id"] for row in r_shp.data or []],
    }


def clean_dataset(supabase: Any, hostname: str, dry_run: bool = False) -> None:
    """Safely delete fixture-owned records using exact IDs and two-factor user checks."""
    found = inspect_fixture_records(supabase)

    print(f"\n================ DRY-RUN CLEANUP PREVIEW [Target: {hostname}] ================")
    print(f"Reviews to delete:              {len(found['reviews'])}")
    print(f"Favorites to delete:            {len(found['favorites'])}")
    print(f"Claims to delete:               {len(found['shop_claims'])}")
    print(f"Curation Audits to delete:      {len(found['shop_curation_audit'])}")
    print(f"Curation entries to delete:     {len(found['shop_curation'])}")
    print(f"Shops to delete:                {len(found['shops'])}")
    print("==============================================================================")

    if dry_run:
        logger.info("Dry-run preview complete. Zero records were modified.")
        return

    # Interactive confirmation protocol
    prompt = f"Type '{hostname}' to confirm deletion: "
    user_confirm = input(prompt).strip()
    if user_confirm != hostname:
        logger.warning("Confirmation input mismatch. Cleanup aborted.")
        return

    logger.info("Executing scoped deletions in reverse-dependency order...")

    if found["reviews"]:
        supabase.table("reviews").delete().in_("id", found["reviews"]).execute()
    if found["favorites"]:
        supabase.table("favorites").delete().in_("id", found["favorites"]).execute()
    if found["shop_claims"]:
        supabase.table("shop_claims").delete().in_("id", found["shop_claims"]).execute()
    if found["shop_curation_audit"]:
        supabase.table("shop_curation_audit").delete().in_("id", found["shop_curation_audit"]).execute()
    if found["shop_curation"]:
        supabase.table("shop_curation").delete().in_("shop_id", found["shop_curation"]).execute()
    if found["shops"]:
        supabase.table("shops").delete().in_("id", found["shops"]).execute()

    # Two-factor verification for user accounts across all pages
    logger.info("Cleaning up controlled test user accounts across all pages...")
    existing_users = fetch_all_auth_users(supabase)
    by_id = {str(u.id): u for u in existing_users}

    for u_fix in FIXTURE_USERS:
        u_obj = by_id.get(str(u_fix.id))
        if not u_obj:
            continue

        # Two-factor check: both UUID and email must match expected fixture persona
        if u_obj.email.lower() != u_fix.email.lower():
            raise IdentityCollisionError(
                f"Safety abort: Account {u_obj.id} has email '{u_obj.email}', "
                f"expected '{u_fix.email}'. Deletion halted."
            )

        logger.info(f"Deleting test user account {u_obj.email} ({u_obj.id})...")
        supabase.auth.admin.delete_user(str(u_obj.id))

    logger.info("Cleanup completed successfully.")


# ---------------------------------------------------------------------------
# SQL Export Logic
# ---------------------------------------------------------------------------

def export_sql(output_path: str) -> None:
    """Programmatically export raw SQL from the authoritative Python fixture module.

    Excludes Auth-dependent entities (reviews, favorites, claims) so the SQL
    safely executes in environments without synthetic auth.users records.
    Removes ON CONFLICT DO UPDATE / DO NOTHING so execution fails closed on unexpected existing data.
    """
    lines = [
        "-- Programmatically generated seed SQL for LOKAL validation dataset (Issue #49).",
        "-- Derived directly from backend/app/fixtures/validation_dataset.py",
        "--",
        "-- NOTE: This file seeds baseline coffee shops, curation eligibility records,",
        "-- and curation audit entries. Auth-dependent entities (synthetic reviews,",
        "-- user favorites, shop claims, and controlled user accounts) are strictly",
        "-- excluded because they require Supabase Auth GoTrue provisioning.",
        "--",
        "-- To provision the complete dataset including Auth accounts, reviews, favorites,",
        "-- and claims, run the Python management command:",
        "--     python -m backend.scripts.seed_validation_data seed",
        "",
        "BEGIN;",
        "",
    ]

    # Shops
    lines.append("-- 1. Shops")
    for s in FIXTURE_SHOPS:
        rating_sql = "NULL" if s.rating is None else f"{s.rating:.2f}"
        name_esc = s.name.replace("'", "''")
        addr_esc = s.address.replace("'", "''")
        lines.append(
            f"INSERT INTO shops (id, name, address, latitude, longitude, rating, google_place_id, created_at, updated_at) "
            f"VALUES ('{s.id}', '{name_esc}', '{addr_esc}', {s.latitude}, {s.longitude}, {rating_sql}, '{s.google_place_id}', '{s.created_at}', '{s.updated_at}');"
        )

    # Shop Curation
    lines.append("\n-- 2. Shop Curation")
    for s in FIXTURE_SHOPS:
        count_sql = "NULL" if s.branch_count is None else str(s.branch_count)
        notes_esc = s.curator_notes.replace("'", "''")
        lines.append(
            f"INSERT INTO shop_curation (shop_id, status, location_count, evidence_source, confidence, is_manual_override, curator_id, curator_notes, evaluated_at, created_at, updated_at) "
            f"VALUES ('{s.id}', '{s.curation_status}', {count_sql}, '{s.evidence_source}', '{s.confidence}', FALSE, '{CURATOR_USER_ID}', '{notes_esc}', '{s.created_at}', '{s.created_at}', '{s.updated_at}');"
        )

    # Curation Audit
    lines.append("\n-- 3. Shop Curation Audit")
    for a in FIXTURE_CURATION_AUDITS:
        count_sql = "NULL" if a.new_location_count is None else str(a.new_location_count)
        reason_esc = a.reason.replace("'", "''")
        lines.append(
            f"INSERT INTO shop_curation_audit (id, shop_id, new_status, new_location_count, changed_by, change_source, reason, created_at) "
            f"VALUES ('{a.id}', '{a.shop_id}', '{a.new_status}', {count_sql}, '{a.changed_by}', '{a.change_source}', '{reason_esc}', '{a.created_at}');"
        )

    lines.append("\nCOMMIT;\n")

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    logger.info(f"Exported SQL seed file successfully to {output_path}")


# ---------------------------------------------------------------------------
# Main CLI Entry Point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="LOKAL Validation Dataset Tool")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("seed", help="Idempotently seed validation dataset")
    subparsers.add_parser("verify", help="Verify validation dataset integrity")

    clean_parser = subparsers.add_parser("clean", help="Safely clean up validation dataset")
    clean_parser.add_argument("--dry-run", action="store_true", help="Preview records to be deleted without writing")

    export_parser = subparsers.add_parser("export-sql", help="Export dataset as raw SQL")
    export_parser.add_argument("--output", default="supabase/seed.sql", help="Output path for SQL seed file")

    args = parser.parse_args()

    if args.command == "export-sql":
        export_sql(args.output)
        return

    # Database-connected commands require safety validation and service role key
    target_host = validate_environment_and_target_host()
    supabase = get_service_role_supabase_client()

    if args.command == "seed":
        logger.info(f"Seeding validation dataset to target host: {target_host}...")
        seed_users(supabase)
        seed_database_records(supabase)
        logger.info("Validation dataset seeded successfully.")
        success = verify_dataset(supabase)
        if not success:
            logger.error("Verification failed after seeding: incomplete dataset detected.")
            sys.exit(1)
    elif args.command == "verify":
        success = verify_dataset(supabase)
        if not success:
            logger.error("Verification failed: incomplete dataset detected.")
            sys.exit(1)
    elif args.command == "clean":
        clean_dataset(supabase, target_host, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
