import test from 'node:test';
import assert from 'node:assert';
import {
  fetchShopClaimStatus,
  submitShopClaim,
  fetchMyClaims,
  fetchOwnerDashboard,
  updateOwnerShop,
} from '../src/services/claimService.ts';

test('fetchShopClaimStatus throws error when authToken is missing or whitespace', async () => {
  await assert.rejects(
    async () => {
      await fetchShopClaimStatus('shop-1', '');
    },
    {
      message: 'Authentication token is required to fetch claim status.',
    }
  );

  await assert.rejects(
    async () => {
      await fetchShopClaimStatus('shop-1', '   ');
    },
    {
      message: 'Authentication token is required to fetch claim status.',
    }
  );
});

test('fetchShopClaimStatus constructs GET request with auth headers and returns claim', async () => {
  const originalFetch = globalThis.fetch;
  let requestedUrl = '';
  let requestedHeaders = {};
  let requestedMethod = '';

  const mockClaim = {
    id: 'claim-123',
    shop_id: 'shop-abc',
    status: 'PENDING',
    claimant_name: 'Maria Santos',
    claimant_role: 'Owner',
    rejection_reason: null,
    created_at: '2026-10-06T00:00:00Z',
    updated_at: '2026-10-06T00:00:00Z',
  };

  globalThis.fetch = async (input, init) => {
    requestedUrl = input.toString();
    requestedMethod = init?.method || 'GET';
    requestedHeaders = init?.headers || {};
    return {
      ok: true,
      json: async () => mockClaim,
    };
  };

  try {
    const result = await fetchShopClaimStatus('shop-abc', 'valid-jwt-token');
    assert.deepStrictEqual(result, mockClaim);
    assert.ok(requestedUrl.includes('/api/v1/shops/shop-abc/claim'));
    assert.strictEqual(requestedMethod, 'GET');
    assert.strictEqual(requestedHeaders['Authorization'], 'Bearer valid-jwt-token');
    assert.strictEqual(requestedHeaders['Accept'], 'application/json');
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('fetchShopClaimStatus returns null when backend returns null or 200 with null body', async () => {
  const originalFetch = globalThis.fetch;

  globalThis.fetch = async () => ({
    ok: true,
    json: async () => null,
  });

  try {
    const result = await fetchShopClaimStatus('shop-unclaimed', 'valid-jwt-token');
    assert.strictEqual(result, null);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('fetchShopClaimStatus throws descriptive error when backend fails with detail', async () => {
  const originalFetch = globalThis.fetch;

  globalThis.fetch = async () => ({
    ok: false,
    status: 400,
    json: async () => ({ detail: 'Only approved coffee shops can have ownership claims.' }),
  });

  try {
    await assert.rejects(
      async () => {
        await fetchShopClaimStatus('shop-excluded', 'valid-jwt-token');
      },
      {
        message: 'Only approved coffee shops can have ownership claims.',
      }
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('submitShopClaim throws error when authToken is missing or whitespace', async () => {
  await assert.rejects(
    async () => {
      await submitShopClaim('shop-1', { claimant_name: 'Maria', claimant_role: 'Owner' }, '');
    },
    {
      message: 'Authentication token is required to submit a claim.',
    }
  );
});

test('submitShopClaim constructs POST request with JSON body and returns created claim', async () => {
  const originalFetch = globalThis.fetch;
  let requestedUrl = '';
  let requestedMethod = '';
  let requestedBody = '';

  const mockPayload = {
    claimant_name: 'Maria Santos',
    claimant_role: 'Owner',
    claimant_phone: '+639171234567',
    business_proof: 'Permit #12345',
  };

  const mockCreatedClaim = {
    id: 'claim-456',
    shop_id: 'shop-abc',
    status: 'PENDING',
    claimant_name: 'Maria Santos',
    claimant_role: 'Owner',
    rejection_reason: null,
    created_at: '2026-10-06T00:00:00Z',
    updated_at: '2026-10-06T00:00:00Z',
  };

  globalThis.fetch = async (input, init) => {
    requestedUrl = input.toString();
    requestedMethod = init?.method || '';
    requestedBody = init?.body || '';
    return {
      ok: true,
      status: 201,
      json: async () => mockCreatedClaim,
    };
  };

  try {
    const result = await submitShopClaim('shop-abc', mockPayload, 'valid-token');
    assert.deepStrictEqual(result, mockCreatedClaim);
    assert.strictEqual(requestedMethod, 'POST');
    assert.ok(requestedUrl.includes('/api/v1/shops/shop-abc/claim'));
    assert.deepStrictEqual(JSON.parse(requestedBody), mockPayload);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('submitShopClaim throws conflict error when shop already has approved claim', async () => {
  const originalFetch = globalThis.fetch;

  globalThis.fetch = async () => ({
    ok: false,
    status: 409,
    json: async () => ({ detail: 'This coffee shop already has an approved owner.' }),
  });

  try {
    await assert.rejects(
      async () => {
        await submitShopClaim(
          'shop-claimed',
          { claimant_name: 'Maria', claimant_role: 'Owner' },
          'valid-token'
        );
      },
      {
        message: 'This coffee shop already has an approved owner.',
      }
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('fetchMyClaims constructs GET request to /claims/mine and returns user claims', async () => {
  const originalFetch = globalThis.fetch;
  let requestedUrl = '';
  let requestedHeaders = {};

  const mockClaimsList = [
    {
      id: 'claim-1',
      shop_id: 'shop-1',
      status: 'APPROVED',
      claimant_name: 'Maria',
      claimant_role: 'Owner',
      rejection_reason: null,
      created_at: '2026-10-06T00:00:00Z',
      updated_at: '2026-10-06T00:00:00Z',
    },
  ];

  globalThis.fetch = async (input, init) => {
    requestedUrl = input.toString();
    requestedHeaders = init?.headers || {};
    return {
      ok: true,
      json: async () => mockClaimsList,
    };
  };

  try {
    const result = await fetchMyClaims('valid-token');
    assert.deepStrictEqual(result, mockClaimsList);
    assert.ok(requestedUrl.includes('/api/v1/claims/mine'));
    assert.strictEqual(requestedHeaders['Authorization'], 'Bearer valid-token');
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('fetchOwnerDashboard constructs GET request to /owner/shops/:id/dashboard and returns data', async () => {
  const originalFetch = globalThis.fetch;
  let requestedUrl = '';
  let requestedHeaders = {};

  const mockDashboardData = {
    shop: {
      id: 'shop-1',
      name: 'Owner Cafe',
      address: '456 Bean St',
      latitude: 14.5,
      longitude: 121.0,
      rating: 4.6,
    },
    claim: {
      id: 'claim-1',
      shop_id: 'shop-1',
      status: 'APPROVED',
      claimant_name: 'Maria',
      claimant_role: 'Owner',
      created_at: '2026-10-06T00:00:00Z',
      updated_at: '2026-10-06T00:00:00Z',
    },
    lokal_rating: 4.8,
    lokal_reviews_count: 5,
    rating: 4.6,
    recent_reviews: [],
  };

  globalThis.fetch = async (input, init) => {
    requestedUrl = input.toString();
    requestedHeaders = init?.headers || {};
    return {
      ok: true,
      json: async () => mockDashboardData,
    };
  };

  try {
    const result = await fetchOwnerDashboard('shop-1', 'valid-token');
    assert.deepStrictEqual(result, mockDashboardData);
    assert.ok(requestedUrl.includes('/api/v1/owner/shops/shop-1/dashboard'));
    assert.strictEqual(requestedHeaders['Authorization'], 'Bearer valid-token');
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('fetchOwnerDashboard throws 403 Forbidden when user is not approved owner', async () => {
  const originalFetch = globalThis.fetch;

  globalThis.fetch = async () => ({
    ok: false,
    status: 403,
    json: async () => ({
      detail: 'You are not the approved owner of this coffee shop, or the shop is not currently approved.',
    }),
  });

  try {
    await assert.rejects(
      async () => {
        await fetchOwnerDashboard('shop-unauthorized', 'valid-token');
      },
      {
        message: 'You are not the approved owner of this coffee shop, or the shop is not currently approved.',
      }
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('updateOwnerShop sends PATCH request with safe fields and returns updated shop', async () => {
  const originalFetch = globalThis.fetch;
  let requestedUrl = '';
  let requestedMethod = '';
  let requestedBody = '';

  const mockUpdatedShop = {
    id: 'shop-1',
    name: 'Updated Cafe Name',
    address: 'New Address 789',
    latitude: 14.5,
    longitude: 121.0,
    rating: 4.6,
  };

  globalThis.fetch = async (input, init) => {
    requestedUrl = input.toString();
    requestedMethod = init?.method || '';
    requestedBody = init?.body || '';
    return {
      ok: true,
      json: async () => mockUpdatedShop,
    };
  };

  try {
    const result = await updateOwnerShop(
      'shop-1',
      { name: 'Updated Cafe Name', address: 'New Address 789' },
      'valid-token'
    );
    assert.deepStrictEqual(result, mockUpdatedShop);
    assert.strictEqual(requestedMethod, 'PATCH');
    assert.ok(requestedUrl.includes('/api/v1/owner/shops/shop-1'));
    assert.deepStrictEqual(JSON.parse(requestedBody), {
      name: 'Updated Cafe Name',
      address: 'New Address 789',
    });
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('updateOwnerShop handles validation error detail array properly', async () => {
  const originalFetch = globalThis.fetch;

  globalThis.fetch = async () => ({
    ok: false,
    status: 422,
    json: async () => ({
      detail: [
        { msg: 'Extra inputs are not permitted' },
      ],
    }),
  });

  try {
    await assert.rejects(
      async () => {
        await updateOwnerShop('shop-1', { name: 'Attempted Hack' }, 'valid-token');
      },
      {
        message: 'Extra inputs are not permitted',
      }
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});
