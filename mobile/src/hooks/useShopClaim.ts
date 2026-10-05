import { useState, useEffect, useCallback, useRef } from 'react';
import type { ShopClaim } from '../types/claim.ts';
import { fetchShopClaimStatus } from '../services/claimService.ts';

export interface ShopClaimState {
  claim: ShopClaim | null;
  isLoading: boolean;
  errorMessage: string | null;
}

export type ShopClaimListener = (state: ShopClaimState) => void;

/**
 * Pure state sequencer and request coordinator for coffee shop ownership claims.
 * Encapsulates monotonic request sequencing, stale-response protection, and
 * immediate cleanup on principal or shop transitions.
 */
export class ShopClaimController {
  private requestId = 0;
  private currentPrincipal: string | null = null;
  private currentShopId: string | null = null;
  private state: ShopClaimState;
  private listeners = new Set<ShopClaimListener>();
  private fetchFn: (shopId: string, token: string) => Promise<ShopClaim | null>;

  constructor(
    fetchFn: (shopId: string, token: string) => Promise<ShopClaim | null> = fetchShopClaimStatus,
    initialClaim: ShopClaim | null = null,
    initialPrincipal: string | null = null,
    initialShopId: string | null = null
  ) {
    this.fetchFn = fetchFn;
    this.currentPrincipal = initialPrincipal;
    this.currentShopId = initialShopId;
    this.state = {
      claim: initialClaim,
      isLoading: false,
      errorMessage: null,
    };
  }

  getState(): ShopClaimState {
    return this.state;
  }

  subscribe(listener: ShopClaimListener): () => void {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  }

  private setState(nextState: ShopClaimState): void {
    this.state = nextState;
    this.listeners.forEach((listener) => listener(nextState));
  }

  cancel(): void {
    this.requestId += 1;
  }

  setClaim(claim: ShopClaim | null): void {
    this.setState({
      ...this.state,
      claim,
      errorMessage: null,
    });
  }

  async load(
    shopId?: string | null,
    authToken?: string | null,
    principalId?: string | null
  ): Promise<void> {
    const trimmedToken = authToken?.trim() || null;
    const effectivePrincipal = principalId !== undefined ? principalId : trimmedToken;
    const effectiveShopId = shopId?.trim() || null;

    if (!trimmedToken || !effectivePrincipal || !effectiveShopId) {
      this.requestId += 1;
      this.currentPrincipal = null;
      this.currentShopId = null;
      this.setState({
        claim: null,
        isLoading: false,
        errorMessage: null,
      });
      return;
    }

    // Reset immediately on principal or shop switch
    if (this.currentPrincipal !== effectivePrincipal || this.currentShopId !== effectiveShopId) {
      this.currentPrincipal = effectivePrincipal;
      this.currentShopId = effectiveShopId;
      this.setState({
        claim: null,
        isLoading: true,
        errorMessage: null,
      });
    } else {
      this.setState({
        ...this.state,
        isLoading: true,
        errorMessage: null,
      });
    }

    const activeRequestId = ++this.requestId;

    try {
      const claim = await this.fetchFn(effectiveShopId, trimmedToken);

      if (activeRequestId === this.requestId) {
        this.setState({
          claim,
          isLoading: false,
          errorMessage: null,
        });
      }
    } catch (err: unknown) {
      if (activeRequestId === this.requestId) {
        const message = err instanceof Error ? err.message : 'Failed to retrieve claim status.';
        this.setState({
          claim: null,
          isLoading: false,
          errorMessage: message,
        });
      }
    }
  }
}

/**
 * React hook for consuming coffee shop ownership claim state for an active shop.
 */
export function useShopClaim(
  shopId?: string | null,
  authToken?: string | null,
  userId?: string | null
) {
  const controllerRef = useRef<ShopClaimController | null>(null);
  if (!controllerRef.current) {
    controllerRef.current = new ShopClaimController();
  }
  const controller = controllerRef.current;

  const [state, setState] = useState<ShopClaimState>(() => controller.getState());

  useEffect(() => {
    return controller.subscribe(setState);
  }, [controller]);

  useEffect(() => {
    controller.load(shopId, authToken, userId);
  }, [controller, shopId, authToken, userId]);

  const refetch = useCallback(() => {
    return controller.load(shopId, authToken, userId);
  }, [controller, shopId, authToken, userId]);

  const setClaim = useCallback(
    (claim: ShopClaim | null) => {
      controller.setClaim(claim);
    },
    [controller]
  );

  return {
    claim: state.claim,
    isLoading: state.isLoading,
    errorMessage: state.errorMessage,
    refetch,
    setClaim,
  };
}
