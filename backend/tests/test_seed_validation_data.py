"""Unit tests for validation dataset management script and safety contract (Issue #49)."""

import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, call, patch
from uuid import UUID

from backend.app.fixtures.validation_dataset import (
    CURATOR_USER_ID,
    OWNER_USER_ID,
    FIXTURE_CLAIMS,
    FIXTURE_CURATION_AUDITS,
    FIXTURE_FAVORITES,
    FIXTURE_REVIEWS,
    FIXTURE_SHOPS,
    FIXTURE_USERS,
)
from backend.scripts.seed_validation_data import (
    FixturePayloadConflictError,
    IdentityCollisionError,
    SecurityError,
    clean_dataset,
    export_sql,
    fetch_all_auth_users,
    main,
    seed_database_records,
    seed_users,
    verify_dataset,
)


class MockAuthUser:
    """Mock user returned by Supabase Auth GoTrue API."""

    def __init__(self, uid: str, email: str, full_name: str = "Test User"):
        self.id = uid
        self.email = email
        self.user_metadata = {"full_name": full_name}


def make_matching_db_datasets():
    """Generate exact expected database records for all fixtures."""
    shops_data = [{
        "id": str(s.id), "name": s.name, "address": s.address, "latitude": s.latitude, "longitude": s.longitude,
        "rating": s.rating, "google_place_id": s.google_place_id, "created_at": s.created_at, "updated_at": s.updated_at
    } for s in FIXTURE_SHOPS]

    curation_data = [{
        "shop_id": str(s.id), "status": s.curation_status, "location_count": s.branch_count, "evidence_source": s.evidence_source,
        "confidence": s.confidence, "is_manual_override": False, "curator_id": str(CURATOR_USER_ID), "curator_notes": s.curator_notes,
        "evaluated_at": s.created_at, "created_at": s.created_at, "updated_at": s.updated_at
    } for s in FIXTURE_SHOPS]

    audits_data = [{
        "id": str(a.id), "shop_id": str(a.shop_id), "old_status": a.old_status, "new_status": a.new_status,
        "old_location_count": a.old_location_count, "new_location_count": a.new_location_count,
        "changed_by": str(a.changed_by), "change_source": a.change_source, "reason": a.reason, "created_at": a.created_at
    } for a in FIXTURE_CURATION_AUDITS]

    reviews_data = [{
        "id": str(r.id), "shop_id": str(r.shop_id), "user_id": str(r.user_id), "author_name": r.author_name,
        "rating": r.rating, "content": r.content, "source": r.source, "created_at": r.created_at, "updated_at": r.updated_at
    } for r in FIXTURE_REVIEWS]

    favorites_data = [{
        "id": str(f.id), "user_id": str(f.user_id), "shop_id": str(f.shop_id), "created_at": f.created_at
    } for f in FIXTURE_FAVORITES]

    claims_data = [{
        "id": str(c.id), "shop_id": str(c.shop_id), "user_id": str(c.user_id), "status": c.status,
        "claimant_name": c.claimant_name, "claimant_phone": c.claimant_phone, "claimant_role": c.claimant_role,
        "business_proof": c.business_proof, "curator_id": str(c.curator_id), "review_notes": c.review_notes,
        "reviewed_at": c.reviewed_at, "created_at": c.created_at, "updated_at": c.updated_at
    } for c in FIXTURE_CLAIMS]

    auth_users_data = [MockAuthUser(str(u.id), u.email, u.full_name) for u in FIXTURE_USERS]

    return shops_data, curation_data, audits_data, reviews_data, favorites_data, claims_data, auth_users_data


class TestSeedValidationDataScript(unittest.TestCase):
    """Test suite verifying CLI seeding, verification, cleanup, and SQL export behaviors."""

    def test_fetch_all_auth_users_pagination(self) -> None:
        """Verify fetch_all_auth_users iterates until page length is less than page_size."""
        mock_supabase = MagicMock()

        # Page 1: 50 users (full page)
        page_1 = [MockAuthUser(f"00000000-0000-0000-0000-{i:012d}", f"user{i}@lokal.dev") for i in range(1, 51)]
        # Page 2: 12 users (< 50, terminal page)
        page_2 = [MockAuthUser(f"00000000-0000-0000-0000-{i:012d}", f"user{i}@lokal.dev") for i in range(51, 63)]

        mock_supabase.auth.admin.list_users.side_effect = [page_1, page_2]

        users = fetch_all_auth_users(mock_supabase, page_size=50)

        self.assertEqual(len(users), 62)
        self.assertEqual(mock_supabase.auth.admin.list_users.call_count, 2)
        mock_supabase.auth.admin.list_users.assert_has_calls([
            call(page=1, per_page=50),
            call(page=2, per_page=50),
        ])

    def test_seed_users_multi_page_collision_detection(self) -> None:
        """Verify collision detection triggers when conflicting account exists on a later page."""
        mock_supabase = MagicMock()

        page_1 = [MockAuthUser(f"00000000-0000-0000-0000-{i:012d}", f"user{i}@lokal.dev") for i in range(1, 51)]
        target_fix = FIXTURE_USERS[0]
        page_2 = [MockAuthUser(str(target_fix.id), "imposter@lokal.dev")]

        mock_supabase.auth.admin.list_users.side_effect = [page_1, page_2]

        with patch("backend.scripts.seed_validation_data.settings.TEST_USER_PASSWORD", "test-pass-123"):
            with self.assertRaises(IdentityCollisionError) as ctx:
                seed_users(mock_supabase)
            self.assertIn("already exists with email 'imposter@lokal.dev'", str(ctx.exception))

    def test_seed_users_preserves_existing_matching_accounts(self) -> None:
        """Verify existing accounts with matching UUID and email are untouched without password reset."""
        mock_supabase = MagicMock()

        existing = [MockAuthUser(str(u.id), u.email, u.full_name) for u in FIXTURE_USERS]
        mock_supabase.auth.admin.list_users.return_value = existing

        with patch("backend.scripts.seed_validation_data.settings.TEST_USER_PASSWORD", "test-pass-123"):
            seed_users(mock_supabase)

        mock_supabase.auth.admin.create_user.assert_not_called()
        mock_supabase.auth.admin.update_user_by_id.assert_not_called()

    def test_verify_dataset_returns_true_on_complete_and_matching_dataset(self) -> None:
        """Verify verify_dataset returns True when all fixture entities and auth identities match perfectly."""
        mock_supabase = MagicMock()

        shops_d, cur_d, aud_d, rev_d, fav_d, clm_d, auth_d = make_matching_db_datasets()
        mock_supabase.auth.admin.list_users.return_value = auth_d

        def table_side_effect(table_name: str):
            mock_t = MagicMock()
            mock_t.select.return_value = mock_t
            if table_name == "shops":
                mock_t.in_.return_value.execute.return_value = MagicMock(data=shops_d)
            elif table_name == "shop_curation":
                mock_t.in_.return_value.execute.return_value = MagicMock(data=cur_d)
            elif table_name == "shop_curation_audit":
                mock_t.in_.return_value.execute.return_value = MagicMock(data=aud_d)
            elif table_name == "reviews":
                mock_t.in_.return_value.execute.return_value = MagicMock(data=rev_d)
            elif table_name == "favorites":
                mock_t.in_.return_value.execute.return_value = MagicMock(data=fav_d)
            elif table_name == "shop_claims":
                mock_t.in_.return_value.execute.return_value = MagicMock(data=clm_d)
            return mock_t

        mock_supabase.table.side_effect = table_side_effect

        result = verify_dataset(mock_supabase)
        self.assertTrue(result)

    def test_verify_dataset_detects_changed_fixture_field_with_matching_row_count(self) -> None:
        """Verify verify_dataset fails when row counts match but an entity field value is mismatched."""
        mock_supabase = MagicMock()

        shops_d, cur_d, aud_d, rev_d, fav_d, clm_d, auth_d = make_matching_db_datasets()
        # Corrupt one shop's name in the returned database record
        shops_d[0]["name"] = "Corrupted Shop Name"
        mock_supabase.auth.admin.list_users.return_value = auth_d

        def table_side_effect(table_name: str):
            mock_t = MagicMock()
            mock_t.select.return_value = mock_t
            if table_name == "shops":
                mock_t.in_.return_value.execute.return_value = MagicMock(data=shops_d)
            elif table_name == "shop_curation":
                mock_t.in_.return_value.execute.return_value = MagicMock(data=cur_d)
            elif table_name == "shop_curation_audit":
                mock_t.in_.return_value.execute.return_value = MagicMock(data=aud_d)
            elif table_name == "reviews":
                mock_t.in_.return_value.execute.return_value = MagicMock(data=rev_d)
            elif table_name == "favorites":
                mock_t.in_.return_value.execute.return_value = MagicMock(data=fav_d)
            elif table_name == "shop_claims":
                mock_t.in_.return_value.execute.return_value = MagicMock(data=clm_d)
            return mock_t

        mock_supabase.table.side_effect = table_side_effect

        result = verify_dataset(mock_supabase)
        self.assertFalse(result)

    def test_verify_dataset_fails_on_missing_or_conflicting_auth_identity(self) -> None:
        """Verify verify_dataset fails when an Auth test account is missing or has a conflicting email."""
        mock_supabase = MagicMock()

        shops_d, cur_d, aud_d, rev_d, fav_d, clm_d, auth_d = make_matching_db_datasets()

        def table_side_effect(table_name: str):
            mock_t = MagicMock()
            mock_t.select.return_value = mock_t
            mock_t.in_.return_value.execute.return_value = MagicMock(
                data=shops_d if table_name == "shops" else
                     cur_d if table_name == "shop_curation" else
                     aud_d if table_name == "shop_curation_audit" else
                     rev_d if table_name == "reviews" else
                     fav_d if table_name == "favorites" else clm_d
            )
            return mock_t

        mock_supabase.table.side_effect = table_side_effect

        # Case 1: Missing user
        mock_supabase.auth.admin.list_users.return_value = auth_d[1:]  # omit first user
        self.assertFalse(verify_dataset(mock_supabase))

        # Case 2: Conflicting email on matching UUID
        conflicting_auth_d = [MockAuthUser(auth_d[0].id, "intruder@lokal.dev")] + auth_d[1:]
        mock_supabase.auth.admin.list_users.return_value = conflicting_auth_d
        self.assertFalse(verify_dataset(mock_supabase))

    def test_verify_dataset_returns_false_on_missing_database_record(self) -> None:
        """Verify verify_dataset returns False when any entity table count is deficient."""
        mock_supabase = MagicMock()
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value = mock_table
        mock_table.in_.return_value.execute.return_value = MagicMock(data=[])
        mock_supabase.auth.admin.list_users.return_value = []

        result = verify_dataset(mock_supabase)
        self.assertFalse(result)

    def test_clean_dataset_aborts_on_auth_collision_before_any_deletion(self) -> None:
        """Verify clean_dataset validates Auth identities first and aborts before any table delete."""
        mock_supabase = MagicMock()

        # Auth collision: user with expected UUID has different email
        target_fix = FIXTURE_USERS[0]
        colliding_users = [MockAuthUser(str(target_fix.id), "mismatch@lokal.dev")]
        mock_supabase.auth.admin.list_users.return_value = colliding_users

        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.in_.return_value.execute.return_value = MagicMock(data=[{"id": "dummy"}])

        with self.assertRaises(IdentityCollisionError) as ctx:
            clean_dataset(mock_supabase, "localhost", dry_run=False)

        self.assertIn("Safety abort:", str(ctx.exception))
        self.assertIn("mismatch@lokal.dev", str(ctx.exception))

        # Confirm ZERO deletions were performed
        mock_table.delete.assert_not_called()
        mock_supabase.auth.admin.delete_user.assert_not_called()

    def test_clean_dataset_aborts_on_email_to_uuid_collision_before_any_deletion(self) -> None:
        """Verify clean_dataset aborts if expected email belongs to a different UUID."""
        mock_supabase = MagicMock()

        target_fix = FIXTURE_USERS[0]
        different_uid = "00000000-9999-9999-9999-000000000099"
        colliding_users = [MockAuthUser(different_uid, target_fix.email)]
        mock_supabase.auth.admin.list_users.return_value = colliding_users

        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table

        with self.assertRaises(IdentityCollisionError) as ctx:
            clean_dataset(mock_supabase, "localhost", dry_run=False)

        self.assertIn("Safety abort:", str(ctx.exception))
        mock_table.delete.assert_not_called()
        mock_supabase.auth.admin.delete_user.assert_not_called()

    def test_main_verify_command_exits_nonzero_when_incomplete(self) -> None:
        """Verify CLI exits non-zero (sys.exit(1)) when verify command detects incomplete dataset."""
        with patch("sys.argv", ["seed_validation_data", "verify"]), \
             patch("backend.scripts.seed_validation_data.validate_environment_and_target_host", return_value="127.0.0.1"), \
             patch("backend.scripts.seed_validation_data.get_service_role_supabase_client"), \
             patch("backend.scripts.seed_validation_data.verify_dataset", return_value=False):
            with self.assertRaises(SystemExit) as ctx:
                main()
            self.assertEqual(ctx.exception.code, 1)

    def test_main_seed_command_exits_nonzero_when_post_seed_verify_fails(self) -> None:
        """Verify CLI exits non-zero if verification after seed fails."""
        with patch("sys.argv", ["seed_validation_data", "seed"]), \
             patch("backend.scripts.seed_validation_data.validate_environment_and_target_host", return_value="127.0.0.1"), \
             patch("backend.scripts.seed_validation_data.get_service_role_supabase_client"), \
             patch("backend.scripts.seed_validation_data.seed_users"), \
             patch("backend.scripts.seed_validation_data.seed_database_records"), \
             patch("backend.scripts.seed_validation_data.verify_dataset", return_value=False):
            with self.assertRaises(SystemExit) as ctx:
                main()
            self.assertEqual(ctx.exception.code, 1)

    def test_conflicting_shop_payload_raises_conflict_without_update(self) -> None:
        """Verify seed_database_records raises conflict on mismatched existing record and performs zero updates."""
        mock_supabase = MagicMock()
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table

        target_shop = FIXTURE_SHOPS[0]
        mismatched_db_record = {
            "id": str(target_shop.id),
            "name": "Different Name Coffee",
            "address": target_shop.address,
            "latitude": target_shop.latitude,
            "longitude": target_shop.longitude,
            "rating": target_shop.rating,
            "google_place_id": target_shop.google_place_id,
            "created_at": target_shop.created_at,
            "updated_at": target_shop.updated_at,
        }
        mock_table.execute.return_value = MagicMock(data=[mismatched_db_record])

        with self.assertRaises(FixturePayloadConflictError) as ctx:
            seed_database_records(mock_supabase)

        self.assertIn(f"Shop {target_shop.id} conflict:", str(ctx.exception))
        self.assertIn("name:", str(ctx.exception))
        mock_table.insert.assert_not_called()
        mock_table.update.assert_not_called()

    def test_identical_shop_payload_remains_untouched(self) -> None:
        """Verify that when database records identically match fixtures, seed_database_records performs zero writes."""
        mock_supabase = MagicMock()

        shops_d, cur_d, aud_d, rev_d, fav_d, clm_d, _ = make_matching_db_datasets()
        shops_map = {row["id"]: row for row in shops_d}
        cur_map = {row["shop_id"]: row for row in cur_d}
        aud_map = {row["id"]: row for row in aud_d}
        rev_map = {row["id"]: row for row in rev_d}
        fav_map = {row["id"]: row for row in fav_d}
        clm_map = {row["id"]: row for row in clm_d}

        table_mocks = {}
        for table_name in ["shops", "shop_curation", "shop_curation_audit", "reviews", "favorites", "shop_claims"]:
            mock_t = MagicMock()
            mock_t.select.return_value = mock_t

            def make_eq(tname):
                def mock_eq(field: str, val: str):
                    query_m = MagicMock()
                    if tname == "shops":
                        row = shops_map.get(val)
                    elif tname == "shop_curation":
                        row = cur_map.get(val)
                    elif tname == "shop_curation_audit":
                        row = aud_map.get(val)
                    elif tname == "reviews":
                        row = rev_map.get(val)
                    elif tname == "favorites":
                        row = fav_map.get(val)
                    elif tname == "shop_claims":
                        row = clm_map.get(val)
                    else:
                        row = None
                    query_m.execute.return_value = MagicMock(data=[row] if row else [])
                    return query_m
                return mock_eq

            mock_t.eq.side_effect = make_eq(table_name)
            table_mocks[table_name] = mock_t

        mock_supabase.table.side_effect = lambda tname: table_mocks[tname]

        # Invoke seed_database_records to exercise full idempotency traversal
        seed_database_records(mock_supabase)

        # Assert zero insert and zero update operations across all 6 tables
        for tname, m in table_mocks.items():
            m.insert.assert_not_called()
            m.update.assert_not_called()

    def test_export_sql_excludes_auth_dependencies_and_conflict_clauses(self) -> None:
        """Verify exported SQL excludes auth-dependent tables and contains zero ON CONFLICT clauses."""
        with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".sql") as tmp:
            tmp_path = tmp.name

        try:
            export_sql(tmp_path)
            with open(tmp_path, "r", encoding="utf-8") as f:
                content = f.read()

            self.assertIn("INSERT INTO shops", content)
            self.assertIn("INSERT INTO shop_curation", content)
            self.assertIn("INSERT INTO shop_curation_audit", content)

            self.assertNotIn("INSERT INTO reviews", content)
            self.assertNotIn("INSERT INTO favorites", content)
            self.assertNotIn("INSERT INTO shop_claims", content)

            self.assertNotIn("ON CONFLICT DO UPDATE", content)
            self.assertNotIn("ON CONFLICT DO NOTHING", content)

            self.assertIn("Auth-dependent entities", content)
            self.assertIn("python -m backend.scripts.seed_validation_data seed", content)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)


if __name__ == "__main__":
    unittest.main()
