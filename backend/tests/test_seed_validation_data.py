"""Unit tests for validation dataset management script and safety contract (Issue #49)."""

import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, call, patch
from uuid import UUID

from backend.app.fixtures.validation_dataset import (
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

        # Page 1: unrelated users
        page_1 = [MockAuthUser(f"00000000-0000-0000-0000-{i:012d}", f"user{i}@lokal.dev") for i in range(1, 51)]
        # Page 2: account with scout.juan's UUID but DIFFERENT email
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

        # Return all 10 fixture users as already existing with matching IDs and emails
        existing = [MockAuthUser(str(u.id), u.email, u.full_name) for u in FIXTURE_USERS]
        mock_supabase.auth.admin.list_users.return_value = existing

        with patch("backend.scripts.seed_validation_data.settings.TEST_USER_PASSWORD", "test-pass-123"):
            seed_users(mock_supabase)

        # Zero user creation or update calls
        mock_supabase.auth.admin.create_user.assert_not_called()
        mock_supabase.auth.admin.update_user_by_id.assert_not_called()

    def test_verify_dataset_returns_true_on_complete_dataset(self) -> None:
        """Verify verify_dataset returns True when all fixture entities are present."""
        mock_supabase = MagicMock()

        # Mock table().select().in_().execute() returning data of exact fixture lengths
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value = mock_table
        mock_table.in_.return_value = mock_table

        def mock_execute():
            res = MagicMock()
            res.data = [{"id": "dummy"}] * 23  # matches 23 shops/audits
            return res

        mock_table.execute.side_effect = [
            MagicMock(data=[{"id": str(s.id)} for s in FIXTURE_SHOPS]),
            MagicMock(data=[{"shop_id": str(s.id)} for s in FIXTURE_SHOPS]),
            MagicMock(data=[{"id": str(a.id)} for a in FIXTURE_CURATION_AUDITS]),
            MagicMock(data=[{"id": str(r.id)} for r in FIXTURE_REVIEWS]),
            MagicMock(data=[{"id": str(f.id)} for f in FIXTURE_FAVORITES]),
            MagicMock(data=[{"id": "dummy"}]),  # 1 claim
        ]

        result = verify_dataset(mock_supabase)
        self.assertTrue(result)

    def test_verify_dataset_returns_false_on_incomplete_dataset(self) -> None:
        """Verify verify_dataset returns False when any entity table count is deficient."""
        mock_supabase = MagicMock()
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value = mock_table
        mock_table.in_.return_value = mock_table

        # Return empty data for shops
        mock_table.execute.side_effect = [
            MagicMock(data=[]),  # 0 shops
            MagicMock(data=[]),
            MagicMock(data=[]),
            MagicMock(data=[]),
            MagicMock(data=[]),
            MagicMock(data=[]),
        ]

        result = verify_dataset(mock_supabase)
        self.assertFalse(result)

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
        # Return existing record with differing name
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
        """Verify identical database records trigger zero inserts and zero updates."""
        mock_supabase = MagicMock()
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table

        # Mock all entities as returning matching records
        def mock_select_execute():
            # Return matching shop record
            target_shop = FIXTURE_SHOPS[0]
            return MagicMock(data=[{
                "id": str(target_shop.id),
                "name": target_shop.name,
                "address": target_shop.address,
                "latitude": target_shop.latitude,
                "longitude": target_shop.longitude,
                "rating": target_shop.rating,
                "google_place_id": target_shop.google_place_id,
                "created_at": target_shop.created_at,
                "updated_at": target_shop.updated_at,
            }])

        mock_table.execute.side_effect = mock_select_execute

        # Test single shop loop iteration
        shop = FIXTURE_SHOPS[0]
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
        # Zero inserts or updates called
        mock_table.insert.assert_not_called()
        mock_table.update.assert_not_called()

    def test_export_sql_excludes_auth_dependencies_and_conflict_clauses(self) -> None:
        """Verify exported SQL excludes auth-dependent tables and contains zero ON CONFLICT clauses."""
        with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".sql") as tmp:
            tmp_path = tmp.name

        try:
            export_sql(tmp_path)
            with open(tmp_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Must contain non-Auth tables
            self.assertIn("INSERT INTO shops", content)
            self.assertIn("INSERT INTO shop_curation", content)
            self.assertIn("INSERT INTO shop_curation_audit", content)

            # Must exclude Auth-dependent tables
            self.assertNotIn("INSERT INTO reviews", content)
            self.assertNotIn("INSERT INTO favorites", content)
            self.assertNotIn("INSERT INTO shop_claims", content)

            # Must NOT contain silent conflict handling
            self.assertNotIn("ON CONFLICT DO UPDATE", content)
            self.assertNotIn("ON CONFLICT DO NOTHING", content)

            # Must include explanatory header
            self.assertIn("Auth-dependent entities", content)
            self.assertIn("python -m backend.scripts.seed_validation_data seed", content)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)


if __name__ == "__main__":
    unittest.main()
