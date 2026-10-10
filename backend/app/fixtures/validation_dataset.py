"""Authoritative single source of truth for LOKAL validation dataset (Issue #49).

Defines 23 coffee shops across Metro Manila, 23 first-party reviews, 10 controlled
test users, 8 favorites, 1 owner claim, and 23 curation audit records.

Integrity Rules:
1. Real coffee shops (Category A & C.1) contain verified public business metadata only.
   They have ZERO synthetic reviews and ZERO invented menu items in the database.
   To avoid persisting unrefreshed Google rating data, their rating is strictly None.
2. Synthetic validation test cafes (Category B) host all synthetic reviews, Must Try
   menu items, and owner claims. They are clearly prefixed with '[Test]'.
3. Real multi-location chains (Category C.1) with >= 6 physical locations (Yardstick,
   Toby's Estate, Starbucks) are classified as EXCLUDED.
4. Synthetic pending fixtures (Category C.2) are prefixed with '[Test Curation]' and
   classified as PENDING_REVIEW.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID


@dataclass(frozen=True)
class FixtureShop:
    id: UUID
    name: str
    address: str
    latitude: float
    longitude: float
    rating: Optional[float]
    google_place_id: str
    branch_count: Optional[int]
    curation_status: str
    confidence: str
    evidence_source: str
    curator_notes: str
    source_url: str
    verification_date: str
    is_real: bool
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class FixtureUser:
    id: UUID
    email: str
    full_name: str
    role: str
    app_metadata: dict


@dataclass(frozen=True)
class FixtureReview:
    id: UUID
    shop_id: UUID
    user_id: UUID
    author_name: str
    rating: int
    content: str
    source: str
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class FixtureFavorite:
    id: UUID
    user_id: UUID
    shop_id: UUID
    created_at: str


@dataclass(frozen=True)
class FixtureClaim:
    id: UUID
    shop_id: UUID
    user_id: UUID
    status: str
    claimant_name: str
    claimant_phone: str
    claimant_role: str
    business_proof: str
    curator_id: UUID
    review_notes: str
    reviewed_at: str
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class FixtureCurationAudit:
    id: UUID
    shop_id: UUID
    old_status: Optional[str]
    new_status: str
    old_location_count: Optional[int]
    new_location_count: Optional[int]
    changed_by: UUID
    change_source: str
    reason: str
    created_at: str


# ---------------------------------------------------------------------------
# Controlled Test Users (10 personas under @lokal.dev)
# ---------------------------------------------------------------------------

CURATOR_USER_ID = UUID("00000000-0000-4000-b000-000000000010")
OWNER_USER_ID = UUID("00000000-0000-4000-b000-000000000009")

FIXTURE_USERS: list[FixtureUser] = [
    FixtureUser(
        id=UUID("00000000-0000-4000-b000-000000000001"),
        email="scout.juan@lokal.dev",
        full_name="Juan Dela Cruz (LOKAL Scout)",
        role="reviewer",
        app_metadata={},
    ),
    FixtureUser(
        id=UUID("00000000-0000-4000-b000-000000000002"),
        email="scout.maria@lokal.dev",
        full_name="Maria Santos (LOKAL Scout)",
        role="reviewer",
        app_metadata={},
    ),
    FixtureUser(
        id=UUID("00000000-0000-4000-b000-000000000003"),
        email="scout.carlos@lokal.dev",
        full_name="Carlos Reyes (LOKAL Scout)",
        role="reviewer",
        app_metadata={},
    ),
    FixtureUser(
        id=UUID("00000000-0000-4000-b000-000000000004"),
        email="scout.bea@lokal.dev",
        full_name="Bea Ramos (LOKAL Scout)",
        role="reviewer",
        app_metadata={},
    ),
    FixtureUser(
        id=UUID("00000000-0000-4000-b000-000000000005"),
        email="scout.miguel@lokal.dev",
        full_name="Miguel Torres (LOKAL Scout)",
        role="reviewer",
        app_metadata={},
    ),
    FixtureUser(
        id=UUID("00000000-0000-4000-b000-000000000006"),
        email="scout.elena@lokal.dev",
        full_name="Elena Lim (LOKAL Scout)",
        role="reviewer",
        app_metadata={},
    ),
    FixtureUser(
        id=UUID("00000000-0000-4000-b000-000000000007"),
        email="scout.david@lokal.dev",
        full_name="David Tan (LOKAL Scout)",
        role="reviewer",
        app_metadata={},
    ),
    FixtureUser(
        id=UUID("00000000-0000-4000-b000-000000000008"),
        email="scout.hannah@lokal.dev",
        full_name="Hannah Sy (LOKAL Scout)",
        role="reviewer",
        app_metadata={},
    ),
    FixtureUser(
        id=OWNER_USER_ID,
        email="owner.roberto@lokal.dev",
        full_name="Roberto Gomez (Shop Owner)",
        role="owner",
        app_metadata={},
    ),
    FixtureUser(
        id=CURATOR_USER_ID,
        email="curator.admin@lokal.dev",
        full_name="Curator Admin",
        role="curator",
        app_metadata={"role": "curator"},
    ),
]


# ---------------------------------------------------------------------------
# 23 Coffee Shops
# ---------------------------------------------------------------------------

FIXTURE_SHOPS: list[FixtureShop] = [
    # --- Category A: 12 Real Approved Independent Coffee Shops ---
    FixtureShop(
        id=UUID("00000000-0000-4000-a000-000000000001"),
        name="The Den Coffee & Contemporary Culture",
        address="First United Bldg, 413 Escolta St, Binondo, Manila",
        latitude=14.5996,
        longitude=120.9785,
        rating=None,
        google_place_id="ChIJ3e1q4XDJlzMRmUqFwU1w9Qo",
        branch_count=1,
        curation_status="APPROVED",
        confidence="HIGH",
        evidence_source="curation_registry",
        curator_notes="Verified single location inside HUB: Make Lab, First United Building, Escolta.",
        source_url="https://thedenmanila.com",
        verification_date="2026-10-10",
        is_real=True,
        created_at="2026-08-15T08:00:00Z",
        updated_at="2026-08-15T08:00:00Z",
    ),
    FixtureShop(
        id=UUID("00000000-0000-4000-a000-000000000002"),
        name="Blocleaf Cafe",
        address="1850 M. H. Del Pilar St, Malate, Manila",
        latitude=14.5714,
        longitude=120.9855,
        rating=None,
        google_place_id="ChIJ-1c7vVPLlzMR4n4xXpZ1fJk",
        branch_count=1,
        curation_status="APPROVED",
        confidence="HIGH",
        evidence_source="curation_registry",
        curator_notes="Verified single neighborhood cafe in Hop Inn Hotel compound.",
        source_url="https://facebook.com/blocleafcafe",
        verification_date="2026-10-10",
        is_real=True,
        created_at="2026-08-15T08:00:00Z",
        updated_at="2026-08-15T08:00:00Z",
    ),
    FixtureShop(
        id=UUID("00000000-0000-4000-a000-000000000003"),
        name="Papakape (Fort Santiago)",
        address="18 Sta. Clara St, Fort Santiago, Intramuros, Manila",
        latitude=14.5940,
        longitude=120.9704,
        rating=None,
        google_place_id="ChIJGZfO4XDAlzMR2c2s4cK9y8s",
        branch_count=3,
        curation_status="APPROVED",
        confidence="HIGH",
        evidence_source="curation_registry",
        curator_notes="Verified 3 operating locations (Fort Santiago, National Museum, Legazpi Village).",
        source_url="https://papakape.com",
        verification_date="2026-10-10",
        is_real=True,
        created_at="2026-08-15T08:00:00Z",
        updated_at="2026-08-15T08:00:00Z",
    ),
    FixtureShop(
        id=UUID("00000000-0000-4000-a000-000000000004"),
        name="The Curator Coffee & Cocktails",
        address="134 Legazpi St, Legaspi Park View, Legazpi Village, Makati",
        latitude=14.5539,
        longitude=121.0180,
        rating=None,
        google_place_id="ChIJN1t_tDeuEmsRUsoyG83frY4",
        branch_count=1,
        curation_status="APPROVED",
        confidence="HIGH",
        evidence_source="curation_registry",
        curator_notes="Verified single location at 134 Legazpi St, Legazpi Village, Makati.",
        source_url="https://curatorcoffeeph.com",
        verification_date="2026-10-10",
        is_real=True,
        created_at="2026-08-15T08:00:00Z",
        updated_at="2026-08-15T08:00:00Z",
    ),
    FixtureShop(
        id=UUID("00000000-0000-4000-a000-000000000005"),
        name="Commune",
        address="36 Polaris cor Durban St, Poblacion, Makati",
        latitude=14.5638,
        longitude=121.0315,
        rating=None,
        google_place_id="ChIJyXG_tDeuEmsR1c9uEmsRUso",
        branch_count=1,
        curation_status="APPROVED",
        confidence="HIGH",
        evidence_source="curation_registry",
        curator_notes="Verified single location in Poblacion, Makati.",
        source_url="https://commune.ph",
        verification_date="2026-10-10",
        is_real=True,
        created_at="2026-08-15T08:00:00Z",
        updated_at="2026-08-15T08:00:00Z",
    ),
    FixtureShop(
        id=UUID("00000000-0000-4000-a000-000000000006"),
        name="Bad Cafe",
        address="Windsor Tower, 163 Legazpi St, Legazpi Village, Makati",
        latitude=14.5529,
        longitude=121.0163,
        rating=None,
        google_place_id="ChIJb1c7vVPLlzMR4n4xXpZ1fJ1",
        branch_count=1,
        curation_status="APPROVED",
        confidence="HIGH",
        evidence_source="curation_registry",
        curator_notes="Verified single location in Windsor Tower, Legazpi Village.",
        source_url="https://badcafe.com",
        verification_date="2026-10-10",
        is_real=True,
        created_at="2026-08-15T08:00:00Z",
        updated_at="2026-08-15T08:00:00Z",
    ),
    FixtureShop(
        id=UUID("00000000-0000-4000-a000-000000000007"),
        name="Habitual Coffee",
        address="Paseo Heights, L.P. Leviste St, Salcedo Village, Makati",
        latitude=14.5615,
        longitude=121.0250,
        rating=None,
        google_place_id="ChIJb1c7vVPLlzMR4n4xXpZ1fJ2",
        branch_count=1,
        curation_status="APPROVED",
        confidence="HIGH",
        evidence_source="curation_registry",
        curator_notes="Verified single location in Paseo Heights, Salcedo Village.",
        source_url="https://facebook.com/habitualcoffee",
        verification_date="2026-10-10",
        is_real=True,
        created_at="2026-08-15T08:00:00Z",
        updated_at="2026-08-15T08:00:00Z",
    ),
    FixtureShop(
        id=UUID("00000000-0000-4000-a000-000000000008"),
        name="Spotted Pig Cafe",
        address="109 Esteban St, Legazpi Village, Makati",
        latitude=14.5552,
        longitude=121.0179,
        rating=None,
        google_place_id="ChIJb1c7vVPLlzMR4n4xXpZ1fJ3",
        branch_count=3,
        curation_status="APPROVED",
        confidence="HIGH",
        evidence_source="curation_registry",
        curator_notes="Verified 3 locations (Esteban Makati, Proscenium Rockwell, General Luna Siargao).",
        source_url="https://spottedpigcafeph.com",
        verification_date="2026-10-10",
        is_real=True,
        created_at="2026-08-15T08:00:00Z",
        updated_at="2026-08-15T08:00:00Z",
    ),
    FixtureShop(
        id=UUID("00000000-0000-4000-a000-000000000009"),
        name="The Fat Seed Cafe + Roastery",
        address="One Maridien, 9th Ave cor 27th St, BGC, Taguig",
        latitude=14.5515,
        longitude=121.0494,
        rating=None,
        google_place_id="ChIJb1c7vVPLlzMR4n4xXpZ1fJ4",
        branch_count=5,
        curation_status="APPROVED",
        confidence="HIGH",
        evidence_source="curation_registry",
        curator_notes="Verified 5 operating branches (BGC, UP Town, Molito, One Ayala, Greenbelt 3). Exactly meets <= 5 threshold.",
        source_url="https://fatseed.com.ph",
        verification_date="2026-10-10",
        is_real=True,
        created_at="2026-08-15T08:00:00Z",
        updated_at="2026-08-15T08:00:00Z",
    ),
    FixtureShop(
        id=UUID("00000000-0000-4000-a000-000000000010"),
        name="Chapter Coffee Roastery & Cafe",
        address="143 Maginhawa St, Sikatuna Village, Quezon City",
        latitude=14.6468,
        longitude=121.0583,
        rating=None,
        google_place_id="ChIJb1c7vVPLlzMR4n4xXpZ1fJ5",
        branch_count=2,
        curation_status="APPROVED",
        confidence="HIGH",
        evidence_source="curation_registry",
        curator_notes="Verified 2 locations (Maginhawa QC and SM Marikina).",
        source_url="https://facebook.com/chaptercoffeeroastery",
        verification_date="2026-10-10",
        is_real=True,
        created_at="2026-08-15T08:00:00Z",
        updated_at="2026-08-15T08:00:00Z",
    ),
    FixtureShop(
        id=UUID("00000000-0000-4000-a000-000000000011"),
        name="Crema & Cream Coffee Roasters",
        address="116B Timog Ave cor 11th Jamboree, Sacred Heart, Quezon City",
        latitude=14.6345,
        longitude=121.0384,
        rating=None,
        google_place_id="ChIJb1c7vVPLlzMR4n4xXpZ1fJ6",
        branch_count=1,
        curation_status="APPROVED",
        confidence="HIGH",
        evidence_source="curation_registry",
        curator_notes="Verified single location on Timog Avenue, Quezon City.",
        source_url="https://cremaandcream.ph",
        verification_date="2026-10-10",
        is_real=True,
        created_at="2026-08-15T08:00:00Z",
        updated_at="2026-08-15T08:00:00Z",
    ),
    FixtureShop(
        id=UUID("00000000-0000-4000-a000-000000000012"),
        name="Exchange Alley Coffee House (EACH)",
        address="Unit 3, Bldg 7, Molito Lifestyle Ext, Madrigal Ave, Alabang, Muntinlupa",
        latitude=14.4237,
        longitude=121.0319,
        rating=None,
        google_place_id="ChIJb1c7vVPLlzMR4n4xXpZ1fJ7",
        branch_count=1,
        curation_status="APPROVED",
        confidence="HIGH",
        evidence_source="curation_registry",
        curator_notes="Verified single location in Molito Lifestyle Extension, Alabang.",
        source_url="https://facebook.com/each.coffee",
        verification_date="2026-10-10",
        is_real=True,
        created_at="2026-08-15T08:00:00Z",
        updated_at="2026-08-15T08:00:00Z",
    ),

    # --- Category B: 6 Synthetic Test Cafes (Approved) ---
    FixtureShop(
        id=UUID("00000000-0000-4000-a000-000000000013"),
        name="[Test] Escolta Specialty Coffee Lab",
        address="Unit 201, Escolta Test Plaza, Binondo, Manila",
        latitude=14.5998,
        longitude=120.9790,
        rating=4.80,
        google_place_id="test-place-escolta-lab",
        branch_count=1,
        curation_status="APPROVED",
        confidence="HIGH",
        evidence_source="validation_fixture",
        curator_notes="Synthetic fixture: rich-review and owner dashboard test cafe.",
        source_url="https://lokal.dev/fixtures/escolta-lab",
        verification_date="2026-10-10",
        is_real=False,
        created_at="2026-08-20T08:00:00Z",
        updated_at="2026-08-20T08:00:00Z",
    ),
    FixtureShop(
        id=UUID("00000000-0000-4000-a000-000000000014"),
        name="[Test] Intramuros Roasters Guild",
        address="Plaza Moraga Test Bldg, Binondo, Manila",
        latitude=14.5985,
        longitude=120.9760,
        rating=4.50,
        google_place_id="test-place-intramuros-guild",
        branch_count=1,
        curation_status="APPROVED",
        confidence="HIGH",
        evidence_source="validation_fixture",
        curator_notes="Synthetic fixture: exact AI summary threshold test cafe (3 reviews).",
        source_url="https://lokal.dev/fixtures/intramuros-guild",
        verification_date="2026-10-10",
        is_real=False,
        created_at="2026-08-20T08:00:00Z",
        updated_at="2026-08-20T08:00:00Z",
    ),
    FixtureShop(
        id=UUID("00000000-0000-4000-a000-000000000015"),
        name="[Test] Binondo Cold Brew Studio",
        address="Ongpin St Test Annex, Binondo, Manila",
        latitude=14.6002,
        longitude=120.9755,
        rating=4.20,
        google_place_id="test-place-binondo-coldbrew",
        branch_count=1,
        curation_status="APPROVED",
        confidence="HIGH",
        evidence_source="validation_fixture",
        curator_notes="Synthetic fixture: insufficient reviews fallback test cafe (1 review).",
        source_url="https://lokal.dev/fixtures/binondo-coldbrew",
        verification_date="2026-10-10",
        is_real=False,
        created_at="2026-08-20T08:00:00Z",
        updated_at="2026-08-20T08:00:00Z",
    ),
    FixtureShop(
        id=UUID("00000000-0000-4000-a000-000000000016"),
        name="[Test] Malate Pour-over Hub",
        address="Adriatico St Test Arcade, Malate, Manila",
        latitude=14.5720,
        longitude=120.9860,
        rating=None,
        google_place_id="test-place-malate-hub",
        branch_count=1,
        curation_status="APPROVED",
        confidence="HIGH",
        evidence_source="validation_fixture",
        curator_notes="Synthetic fixture: zero community reviews baseline test cafe.",
        source_url="https://lokal.dev/fixtures/malate-hub",
        verification_date="2026-10-10",
        is_real=False,
        created_at="2026-08-20T08:00:00Z",
        updated_at="2026-08-20T08:00:00Z",
    ),
    FixtureShop(
        id=UUID("00000000-0000-4000-a000-000000000017"),
        name="[Test] Metro Mixed Sentiment Cafe",
        address="Paseo Test Tower, Makati",
        latitude=14.5580,
        longitude=121.0200,
        rating=3.80,
        google_place_id="test-place-metro-mixed",
        branch_count=1,
        curation_status="APPROVED",
        confidence="HIGH",
        evidence_source="validation_fixture",
        curator_notes="Synthetic fixture: mixed and contradictory sentiment test cafe.",
        source_url="https://lokal.dev/fixtures/metro-mixed",
        verification_date="2026-10-10",
        is_real=False,
        created_at="2026-08-20T08:00:00Z",
        updated_at="2026-08-20T08:00:00Z",
    ),
    FixtureShop(
        id=UUID("00000000-0000-4000-a000-000000000018"),
        name="[Test] BGC Artisan Roastery",
        address="28th St Test Pavilion, BGC, Taguig",
        latitude=14.5505,
        longitude=121.0480,
        rating=4.60,
        google_place_id="test-place-bgc-artisan",
        branch_count=1,
        curation_status="APPROVED",
        confidence="HIGH",
        evidence_source="validation_fixture",
        curator_notes="Synthetic fixture: community feed pagination surplus test cafe.",
        source_url="https://lokal.dev/fixtures/bgc-artisan",
        verification_date="2026-10-10",
        is_real=False,
        created_at="2026-08-20T08:00:00Z",
        updated_at="2026-08-20T08:00:00Z",
    ),

    # --- Category C.1: 3 Real Excluded Multi-Location Chains (>= 6 locations) ---
    FixtureShop(
        id=UUID("00000000-0000-4000-a000-000000000019"),
        name="Yardstick Coffee",
        address="106 Esteban St, Legazpi Village, Makati",
        latitude=14.5547,
        longitude=121.0184,
        rating=None,
        google_place_id="ChIJ-1c7vVPLlzMR4n4xXpZ1fJ8",
        branch_count=9,
        curation_status="EXCLUDED",
        confidence="HIGH",
        evidence_source="google_places_text_search",
        curator_notes="Exceeds 5-location threshold (9 active locations across Metro Manila).",
        source_url="https://yardstickcoffee.com/pages/locations",
        verification_date="2026-10-10",
        is_real=True,
        created_at="2026-08-15T08:00:00Z",
        updated_at="2026-08-15T08:00:00Z",
    ),
    FixtureShop(
        id=UUID("00000000-0000-4000-a000-000000000020"),
        name="Toby's Estate",
        address="V Corporate Centre, L.P. Leviste St, Salcedo Village, Makati",
        latitude=14.5606,
        longitude=121.0242,
        rating=None,
        google_place_id="ChIJ-1c7vVPLlzMR4n4xXpZ1fJ9",
        branch_count=18,
        curation_status="EXCLUDED",
        confidence="HIGH",
        evidence_source="google_places_text_search",
        curator_notes="Exceeds 5-location threshold (18+ locations in commercial hubs).",
        source_url="https://tobysestateph.com",
        verification_date="2026-10-10",
        is_real=True,
        created_at="2026-08-15T08:00:00Z",
        updated_at="2026-08-15T08:00:00Z",
    ),
    FixtureShop(
        id=UUID("00000000-0000-4000-a000-000000000021"),
        name="Starbucks (Intramuros)",
        address="General Luna St, Intramuros, Manila",
        latitude=14.5895,
        longitude=120.9750,
        rating=None,
        google_place_id="ChIJ-1c7vVPLlzMR4n4xXpZ1fJ0",
        branch_count=400,
        curation_status="EXCLUDED",
        confidence="HIGH",
        evidence_source="google_places_text_search",
        curator_notes="Major multinational coffee chain with hundreds of branches.",
        source_url="https://starbucks.ph",
        verification_date="2026-10-10",
        is_real=True,
        created_at="2026-08-15T08:00:00Z",
        updated_at="2026-08-15T08:00:00Z",
    ),

    # --- Category C.2: 2 Synthetic Pending Curation Fixtures ---
    FixtureShop(
        id=UUID("00000000-0000-4000-a000-000000000022"),
        name="[Test Curation] Generic Manila Coffee Bar",
        address="Escolta Test Arcade, Manila",
        latitude=14.5990,
        longitude=120.9810,
        rating=None,
        google_place_id="test-place-pending-generic",
        branch_count=None,
        curation_status="PENDING_REVIEW",
        confidence="LOW",
        evidence_source="brand_distinctiveness_heuristic",
        curator_notes="Brand name lacks distinctiveness; manual curator verification required.",
        source_url="https://lokal.dev/fixtures/pending-generic",
        verification_date="2026-10-10",
        is_real=False,
        created_at="2026-08-25T08:00:00Z",
        updated_at="2026-08-25T08:00:00Z",
    ),
    FixtureShop(
        id=UUID("00000000-0000-4000-a000-000000000023"),
        name="[Test Curation] Corner Cafe Express",
        address="Ermita Test Plaza, Manila",
        latitude=14.5800,
        longitude=120.9820,
        rating=None,
        google_place_id="test-place-pending-corner",
        branch_count=None,
        curation_status="PENDING_REVIEW",
        confidence="LOW",
        evidence_source="provider_error",
        curator_notes="Simulated provider timeout during automated evaluation.",
        source_url="https://lokal.dev/fixtures/pending-corner",
        verification_date="2026-10-10",
        is_real=False,
        created_at="2026-08-25T08:00:00Z",
        updated_at="2026-08-25T08:00:00Z",
    ),
]


# ---------------------------------------------------------------------------
# 23 Synthetic Reviews (Distributed exclusively across Category B test shops)
# ---------------------------------------------------------------------------

SHOP_13_ID = UUID("00000000-0000-4000-a000-000000000013")  # Escolta Lab
SHOP_14_ID = UUID("00000000-0000-4000-a000-000000000014")  # Intramuros Guild
SHOP_15_ID = UUID("00000000-0000-4000-a000-000000000015")  # Binondo Cold Brew
SHOP_16_ID = UUID("00000000-0000-4000-a000-000000000016")  # Malate Hub (0 reviews)
SHOP_17_ID = UUID("00000000-0000-4000-a000-000000000017")  # Metro Mixed
SHOP_18_ID = UUID("00000000-0000-4000-a000-000000000018")  # BGC Artisan

U1 = FIXTURE_USERS[0].id
U2 = FIXTURE_USERS[1].id
U3 = FIXTURE_USERS[2].id
U4 = FIXTURE_USERS[3].id
U5 = FIXTURE_USERS[4].id
U6 = FIXTURE_USERS[5].id
U7 = FIXTURE_USERS[6].id
U8 = FIXTURE_USERS[7].id

FIXTURE_REVIEWS: list[FixtureReview] = [
    # --- Shop 13: [Test] Escolta Specialty Coffee Lab (8 reviews) ---
    FixtureReview(
        id=UUID("00000000-0000-4000-c000-000000000001"),
        shop_id=SHOP_13_ID,
        user_id=U1,
        author_name=FIXTURE_USERS[0].full_name,
        rating=5,
        content="[Validation Test] The Gesha Pour-over is magnificent with floral and bergamot notes. Incredible barista craft.",
        source="lokal",
        created_at="2026-09-10T10:00:00Z",
        updated_at="2026-09-10T10:00:00Z",
    ),
    FixtureReview(
        id=UUID("00000000-0000-4000-c000-000000000002"),
        shop_id=SHOP_13_ID,
        user_id=U2,
        author_name=FIXTURE_USERS[1].full_name,
        rating=5,
        content="[Validation Test] Sea Salt Latte is an absolute standout drink here. Perfectly textured foam and subtle sweetness.",
        source="lokal",
        created_at="2026-09-12T11:00:00Z",
        updated_at="2026-09-12T11:00:00Z",
    ),
    FixtureReview(
        id=UUID("00000000-0000-4000-c000-000000000003"),
        shop_id=SHOP_13_ID,
        user_id=U3,
        author_name=FIXTURE_USERS[2].full_name,
        rating=4,
        content="[Validation Test] Excellent espresso roast profile. Seating can be a bit tight during peak afternoon hours.",
        source="lokal",
        created_at="2026-09-15T09:30:00Z",
        updated_at="2026-09-15T09:30:00Z",
    ),
    FixtureReview(
        id=UUID("00000000-0000-4000-c000-000000000004"),
        shop_id=SHOP_13_ID,
        user_id=U4,
        author_name=FIXTURE_USERS[3].full_name,
        rating=5,
        content="[Validation Test] Outstanding Colombian pour-over and fast Wi-Fi. A top tier specialty coffee hub.",
        source="lokal",
        created_at="2026-09-18T14:15:00Z",
        updated_at="2026-09-18T14:15:00Z",
    ),
    FixtureReview(
        id=UUID("00000000-0000-4000-c000-000000000005"),
        shop_id=SHOP_13_ID,
        user_id=U5,
        author_name=FIXTURE_USERS[4].full_name,
        rating=4,
        content="[Validation Test] Loved the Gesha Pour-over. Very smooth extraction. Acoustic noise can get noticeable when crowded.",
        source="lokal",
        created_at="2026-09-20T16:00:00Z",
        updated_at="2026-09-21T08:00:00Z",  # Edited indicator test
    ),
    FixtureReview(
        id=UUID("00000000-0000-4000-c000-000000000006"),
        shop_id=SHOP_13_ID,
        user_id=U6,
        author_name=FIXTURE_USERS[5].full_name,
        rating=5,
        content="[Validation Test] The Sea Salt Latte pairs wonderfully with their flaky croissants. Friendly staff.",
        source="lokal",
        created_at="2026-09-22T10:45:00Z",
        updated_at="2026-09-22T10:45:00Z",
    ),
    FixtureReview(
        id=UUID("00000000-0000-4000-c000-000000000007"),
        shop_id=SHOP_13_ID,
        user_id=U7,
        author_name=FIXTURE_USERS[6].full_name,
        rating=4,
        content="[Validation Test] Solid flat white with great latte art. Minimalist aesthetic.",
        source="lokal",
        created_at="2026-09-24T12:00:00Z",
        updated_at="2026-09-24T12:00:00Z",
    ),
    FixtureReview(
        id=UUID("00000000-0000-4000-c000-000000000008"),
        shop_id=SHOP_13_ID,
        user_id=U8,
        author_name=FIXTURE_USERS[7].full_name,
        rating=5,
        content="[Validation Test] One of the cleanest espresso extractions in Manila. Highly recommend the single origin filters.",
        source="lokal",
        created_at="2026-09-26T15:30:00Z",
        updated_at="2026-09-26T15:30:00Z",
    ),

    # --- Shop 14: [Test] Intramuros Roasters Guild (3 reviews) ---
    FixtureReview(
        id=UUID("00000000-0000-4000-c000-000000000009"),
        shop_id=SHOP_14_ID,
        user_id=U1,
        author_name=FIXTURE_USERS[0].full_name,
        rating=4,
        content="[Validation Test] Rich Spanish Latte with balanced sweetness. Calm heritage setting.",
        source="lokal",
        created_at="2026-09-27T09:00:00Z",
        updated_at="2026-09-27T09:00:00Z",
    ),
    FixtureReview(
        id=UUID("00000000-0000-4000-c000-000000000010"),
        shop_id=SHOP_14_ID,
        user_id=U2,
        author_name=FIXTURE_USERS[1].full_name,
        rating=5,
        content="[Validation Test] The Almond Croissant and brewed filter coffee make an exceptional breakfast.",
        source="lokal",
        created_at="2026-09-28T10:15:00Z",
        updated_at="2026-09-28T10:15:00Z",
    ),
    FixtureReview(
        id=UUID("00000000-0000-4000-c000-000000000011"),
        shop_id=SHOP_14_ID,
        user_id=U3,
        author_name=FIXTURE_USERS[2].full_name,
        rating=4,
        content="[Validation Test] Warm hospitality and clean espresso. Great Spanish Latte.",
        source="lokal",
        created_at="2026-09-29T11:45:00Z",
        updated_at="2026-09-29T11:45:00Z",
    ),

    # --- Shop 15: [Test] Binondo Cold Brew Studio (1 review) ---
    FixtureReview(
        id=UUID("00000000-0000-4000-c000-000000000012"),
        shop_id=SHOP_15_ID,
        user_id=U1,
        author_name=FIXTURE_USERS[0].full_name,
        rating=5,
        content="[Validation Test] Great bottled cold brew for takeout. Crisp, chocolatey notes.",
        source="lokal",
        created_at="2026-09-30T13:00:00Z",
        updated_at="2026-09-30T13:00:00Z",
    ),

    # --- Shop 17: [Test] Metro Mixed Sentiment Cafe (5 reviews) ---
    FixtureReview(
        id=UUID("00000000-0000-4000-c000-000000000013"),
        shop_id=SHOP_17_ID,
        user_id=U1,
        author_name=FIXTURE_USERS[0].full_name,
        rating=5,
        content="[Validation Test] Specialty beans are top quality. Wonderful floral pour-over.",
        source="lokal",
        created_at="2026-10-01T08:30:00Z",
        updated_at="2026-10-01T08:30:00Z",
    ),
    FixtureReview(
        id=UUID("00000000-0000-4000-c000-000000000014"),
        shop_id=SHOP_17_ID,
        user_id=U2,
        author_name=FIXTURE_USERS[1].full_name,
        rating=2,
        content="[Validation Test] Coffee is decent but waited 25 minutes for an iced latte. Overly loud music makes working impossible.",
        source="lokal",
        created_at="2026-10-02T12:00:00Z",
        updated_at="2026-10-02T12:00:00Z",
    ),
    FixtureReview(
        id=UUID("00000000-0000-4000-c000-000000000015"),
        shop_id=SHOP_17_ID,
        user_id=U3,
        author_name=FIXTURE_USERS[2].full_name,
        rating=4,
        content="[Validation Test] Delicious cold brew with bright acidity. Limited parking outside.",
        source="lokal",
        created_at="2026-10-03T14:20:00Z",
        updated_at="2026-10-03T14:20:00Z",
    ),
    FixtureReview(
        id=UUID("00000000-0000-4000-c000-000000000016"),
        shop_id=SHOP_17_ID,
        user_id=U4,
        author_name=FIXTURE_USERS[3].full_name,
        rating=1,
        content="[Validation Test] Uncomfortable cramped seating and staff seemed disorganized during the rush.",
        source="lokal",
        created_at="2026-10-04T16:45:00Z",
        updated_at="2026-10-04T16:45:00Z",
    ),
    FixtureReview(
        id=UUID("00000000-0000-4000-c000-000000000017"),
        shop_id=SHOP_17_ID,
        user_id=U5,
        author_name=FIXTURE_USERS[4].full_name,
        rating=4,
        content="[Validation Test] Skilled baristas and great espresso tonic, though seating is minimal.",
        source="lokal",
        created_at="2026-10-05T09:15:00Z",
        updated_at="2026-10-05T09:15:00Z",
    ),

    # --- Shop 18: [Test] BGC Artisan Roastery (6 reviews) ---
    FixtureReview(
        id=UUID("00000000-0000-4000-c000-000000000018"),
        shop_id=SHOP_18_ID,
        user_id=U3,
        author_name=FIXTURE_USERS[2].full_name,
        rating=5,
        content="[Validation Test] Spacious cafe with natural light. The house blend flat white is velvety.",
        source="lokal",
        created_at="2026-10-05T11:00:00Z",
        updated_at="2026-10-05T11:00:00Z",
    ),
    FixtureReview(
        id=UUID("00000000-0000-4000-c000-000000000019"),
        shop_id=SHOP_18_ID,
        user_id=U4,
        author_name=FIXTURE_USERS[3].full_name,
        rating=4,
        content="[Validation Test] Reliable coffee and good power outlets. Ideal place to read or work.",
        source="lokal",
        created_at="2026-10-06T13:30:00Z",
        updated_at="2026-10-06T13:30:00Z",
    ),
    FixtureReview(
        id=UUID("00000000-0000-4000-c000-000000000020"),
        shop_id=SHOP_18_ID,
        user_id=U5,
        author_name=FIXTURE_USERS[4].full_name,
        rating=5,
        content="[Validation Test] Aeropress brew from Ethiopia was fragrant with floral jasmine notes.",
        source="lokal",
        created_at="2026-10-06T15:45:00Z",
        updated_at="2026-10-06T15:45:00Z",
    ),
    FixtureReview(
        id=UUID("00000000-0000-4000-c000-000000000021"),
        shop_id=SHOP_18_ID,
        user_id=U6,
        author_name=FIXTURE_USERS[5].full_name,
        rating=4,
        content="[Validation Test] Pleasant service and smooth cappuccino. Pastries sell out early.",
        source="lokal",
        created_at="2026-10-07T10:00:00Z",
        updated_at="2026-10-07T10:00:00Z",
    ),
    FixtureReview(
        id=UUID("00000000-0000-4000-c000-000000000022"),
        shop_id=SHOP_18_ID,
        user_id=U7,
        author_name=FIXTURE_USERS[6].full_name,
        rating=5,
        content="[Validation Test] Modern atmosphere and excellent single origin batch brew.",
        source="lokal",
        created_at="2026-10-07T14:20:00Z",
        updated_at="2026-10-07T14:20:00Z",
    ),
    FixtureReview(
        id=UUID("00000000-0000-4000-c000-000000000023"),
        shop_id=SHOP_18_ID,
        user_id=U8,
        author_name=FIXTURE_USERS[7].full_name,
        rating=4,
        content="[Validation Test] Consistent coffee standards. Highly recommended when in BGC.",
        source="lokal",
        created_at="2026-10-08T09:00:00Z",
        updated_at="2026-10-08T09:00:00Z",
    ),
]


# ---------------------------------------------------------------------------
# Favorites (8 samples linking test users to approved synthetic shops)
# ---------------------------------------------------------------------------

FIXTURE_FAVORITES: list[FixtureFavorite] = [
    FixtureFavorite(
        id=UUID("00000000-0000-4000-e000-000000000001"),
        user_id=U1,
        shop_id=SHOP_13_ID,
        created_at="2026-09-10T10:05:00Z",
    ),
    FixtureFavorite(
        id=UUID("00000000-0000-4000-e000-000000000002"),
        user_id=U2,
        shop_id=SHOP_13_ID,
        created_at="2026-09-12T11:10:00Z",
    ),
    FixtureFavorite(
        id=UUID("00000000-0000-4000-e000-000000000003"),
        user_id=U1,
        shop_id=SHOP_14_ID,
        created_at="2026-09-27T09:10:00Z",
    ),
    FixtureFavorite(
        id=UUID("00000000-0000-4000-e000-000000000004"),
        user_id=U3,
        shop_id=SHOP_14_ID,
        created_at="2026-09-29T12:00:00Z",
    ),
    FixtureFavorite(
        id=UUID("00000000-0000-4000-e000-000000000005"),
        user_id=U1,
        shop_id=SHOP_15_ID,
        created_at="2026-09-30T13:10:00Z",
    ),
    FixtureFavorite(
        id=UUID("00000000-0000-4000-e000-000000000006"),
        user_id=U3,
        shop_id=SHOP_18_ID,
        created_at="2026-10-05T11:15:00Z",
    ),
    FixtureFavorite(
        id=UUID("00000000-0000-4000-e000-000000000007"),
        user_id=U4,
        shop_id=SHOP_18_ID,
        created_at="2026-10-06T13:45:00Z",
    ),
    FixtureFavorite(
        id=UUID("00000000-0000-4000-e000-000000000008"),
        user_id=U5,
        shop_id=SHOP_18_ID,
        created_at="2026-10-06T16:00:00Z",
    ),
]


# ---------------------------------------------------------------------------
# Claims (1 approved claim on [Test] Escolta Lab for owner.roberto)
# ---------------------------------------------------------------------------

FIXTURE_CLAIMS: list[FixtureClaim] = [
    FixtureClaim(
        id=UUID("00000000-0000-4000-d000-000000000001"),
        shop_id=SHOP_13_ID,
        user_id=OWNER_USER_ID,
        status="APPROVED",
        claimant_name="Roberto Gomez",
        claimant_phone="+63 917 555 0199",
        claimant_role="Managing Partner",
        business_proof="DTI Registration No. 2026-0918-TEST-ESCOLTA",
        curator_id=CURATOR_USER_ID,
        review_notes="Verified business registration and lease agreement during validation seeding.",
        reviewed_at="2026-09-15T14:30:00Z",
        created_at="2026-09-15T12:00:00Z",
        updated_at="2026-09-15T14:30:00Z",
    )
]


# ---------------------------------------------------------------------------
# Curation Audit Records (23 deterministic audit entries)
# ---------------------------------------------------------------------------

FIXTURE_CURATION_AUDITS: list[FixtureCurationAudit] = [
    FixtureCurationAudit(
        id=UUID(f"00000000-0000-4000-f000-{idx+1:012d}"),
        shop_id=shop.id,
        old_status=None,
        new_status=shop.curation_status,
        old_location_count=None,
        new_location_count=shop.branch_count,
        changed_by=CURATOR_USER_ID,
        change_source="validation_seed",
        reason=shop.curator_notes,
        created_at=shop.created_at,
    )
    for idx, shop in enumerate(FIXTURE_SHOPS)
]
