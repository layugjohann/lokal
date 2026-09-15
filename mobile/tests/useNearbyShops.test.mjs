import test from 'node:test';
import assert from 'node:assert';

test('selection sync keeps updated shop if found in refreshed data', () => {
  const previousSelected = {
    id: 'shop-1',
    name: 'Old Name',
    address: 'Old Address',
    latitude: 14.5,
    longitude: 121.0,
    rating: 4.5,
    distance_meters: 500,
  };

  const refreshedData = [
    {
      id: 'shop-1',
      name: 'New Name',
      address: 'New Address',
      latitude: 14.5,
      longitude: 121.0,
      rating: 4.8,
      distance_meters: 300,
    },
    {
      id: 'shop-2',
      name: 'Other Shop',
      address: 'Other Address',
      latitude: 14.6,
      longitude: 121.1,
      rating: 4.0,
      distance_meters: 800,
    },
  ];

  const syncSelection = (prev, data) => {
    if (!prev) return null;
    const found = data.find((s) => s.id === prev.id);
    return found || null;
  };

  const updated = syncSelection(previousSelected, refreshedData);
  assert.strictEqual(updated?.name, 'New Name');
  assert.strictEqual(updated?.distance_meters, 300);
});

test('selection sync resets to null if shop is absent from refreshed data', () => {
  const previousSelected = {
    id: 'shop-old',
    name: 'Old Shop',
    address: 'Old Address',
    latitude: 14.5,
    longitude: 121.0,
    rating: 4.5,
    distance_meters: 500,
  };

  const refreshedData = [
    {
      id: 'shop-new',
      name: 'New Shop',
      address: 'New Address',
      latitude: 14.6,
      longitude: 121.1,
      rating: 4.0,
      distance_meters: 800,
    },
  ];

  const syncSelection = (prev, data) => {
    if (!prev) return null;
    const found = data.find((s) => s.id === prev.id);
    return found || null;
  };

  const updated = syncSelection(previousSelected, refreshedData);
  assert.strictEqual(updated, null);
});

test('monotonic request counter discards out-of-order stale responses', async () => {
  let requestIdCounter = 0;
  let appliedData = null;

  const simulateFetch = async (requestId, delayMs, result) => {
    await new Promise((resolve) => setTimeout(resolve, delayMs));
    if (requestId === requestIdCounter) {
      appliedData = result;
    }
  };

  // Launch request 1 (slow, 50ms)
  const req1 = ++requestIdCounter;
  const p1 = simulateFetch(req1, 50, ['req1_data']);

  // Launch request 2 (fast, 10ms)
  const req2 = ++requestIdCounter;
  const p2 = simulateFetch(req2, 10, ['req2_data']);

  await Promise.all([p1, p2]);

  // Request 2 was latest; req 1 finished late and was discarded
  assert.deepStrictEqual(appliedData, ['req2_data']);
});
