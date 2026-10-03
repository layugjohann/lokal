import { useState, useEffect, useCallback, useRef } from 'react';
import type { LocationCoordinates } from '../types/location.ts';
import type {
  PersonalizedSearchParams,
  PersonalizedRecommendationsResponse,
  RecommendationStatus,
  RecommendedShopItem,
} from '../types/recommendation.ts';
import { fetchPersonalizedRecommendations } from '../services/recommendationService.ts';

export interface PersonalizedRecommendationsState {
  status: RecommendationStatus | 'idle';
  recommendations: RecommendedShopItem[];
  totalCandidatesEvaluated: number;
  isLoading: boolean;
  errorMessage: string | null;
  userMessage: string | null;
}

export type PersonalizedRecommendationsListener = (
  state: PersonalizedRecommendationsState
) => void;

/**
 * Encapsulates personalized recommendation discovery lifecycle, monotonic request sequencing,
 * user principal binding, and stale-response discarding.
 */
export class PersonalizedRecommendationsController {
  private requestId = 0;
  private activeUserId: string | null = null;
  private state: PersonalizedRecommendationsState;
  private listeners = new Set<PersonalizedRecommendationsListener>();
  private fetchFn: (
    params: PersonalizedSearchParams,
    authToken: string
  ) => Promise<PersonalizedRecommendationsResponse>;

  constructor(
    fetchFn: (
      params: PersonalizedSearchParams,
      authToken: string
    ) => Promise<PersonalizedRecommendationsResponse> = fetchPersonalizedRecommendations
  ) {
    this.fetchFn = fetchFn;
    this.state = {
      status: 'idle',
      recommendations: [],
      totalCandidatesEvaluated: 0,
      isLoading: false,
      errorMessage: null,
      userMessage: null,
    };
  }

  /**
   * Returns the current immutable snapshot of personalized recommendations state.
   */
  getState(): PersonalizedRecommendationsState {
    return this.state;
  }

  /**
   * Subscribes a listener to state updates and returns an unsubscribe cleanup function.
   */
  subscribe(listener: PersonalizedRecommendationsListener): () => void {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  }

  private setState(nextState: PersonalizedRecommendationsState): void {
    this.state = nextState;
    this.listeners.forEach((listener) => listener(nextState));
  }

  /**
   * Invalidates any active in-flight requests by bumping the monotonic request ID.
   */
  cancel(): void {
    this.requestId += 1;
  }

  /**
   * Loads personalized recommendations for the given parameters and authenticated user.
   * If unauthenticated, clears recommendations and resets to idle.
   */
  async load(
    params: PersonalizedSearchParams,
    authToken?: string | null,
    userId?: string | null
  ): Promise<void> {
    if (!authToken || !authToken.trim() || !userId) {
      this.requestId += 1;
      this.activeUserId = null;
      this.setState({
        status: 'idle',
        recommendations: [],
        totalCandidatesEvaluated: 0,
        isLoading: false,
        errorMessage: null,
        userMessage: null,
      });
      return;
    }

    // If switching user principal, immediately clear state to prevent cross-account display
    if (this.activeUserId !== userId) {
      this.activeUserId = userId;
      this.state = {
        status: 'idle',
        recommendations: [],
        totalCandidatesEvaluated: 0,
        isLoading: true,
        errorMessage: null,
        userMessage: null,
      };
    }

    const currentId = ++this.requestId;
    const currentBoundUserId = userId;

    this.setState({
      ...this.state,
      isLoading: true,
      errorMessage: null,
    });

    try {
      const data = await this.fetchFn(params, authToken);

      if (
        currentId !== this.requestId ||
        this.activeUserId !== currentBoundUserId
      ) {
        return;
      }

      this.setState({
        status: data.status,
        recommendations: data.recommendations,
        totalCandidatesEvaluated: data.total_candidates_evaluated,
        userMessage: data.message ?? null,
        isLoading: false,
        errorMessage: null,
      });
    } catch (err) {
      if (
        currentId !== this.requestId ||
        this.activeUserId !== currentBoundUserId
      ) {
        return;
      }

      const message =
        err instanceof Error
          ? err.message
          : 'Unable to load personalized recommendations.';

      this.setState({
        ...this.state,
        isLoading: false,
        errorMessage: message,
      });
    }
  }
}

export interface UsePersonalizedRecommendationsResult {
  status: RecommendationStatus | 'idle';
  recommendations: RecommendedShopItem[];
  totalCandidatesEvaluated: number;
  isLoading: boolean;
  errorMessage: string | null;
  userMessage: string | null;
  refetch: () => Promise<void>;
}

export function usePersonalizedRecommendations(
  location: LocationCoordinates | null,
  authToken?: string | null,
  userId?: string | null
): UsePersonalizedRecommendationsResult {
  const controllerRef = useRef<PersonalizedRecommendationsController | null>(null);
  if (!controllerRef.current) {
    controllerRef.current = new PersonalizedRecommendationsController();
  }
  const controller = controllerRef.current;

  const [state, setState] = useState<PersonalizedRecommendationsState>(() =>
    controller.getState()
  );

  useEffect(() => {
    const unsubscribe = controller.subscribe((nextState) => {
      setState(nextState);
    });
    return () => {
      unsubscribe();
    };
  }, [controller]);

  useEffect(() => {
    return () => {
      controller.cancel();
    };
  }, [controller]);

  const fetchRecommendations = useCallback(async () => {
    await controller.load(
      {
        latitude: location?.latitude ?? null,
        longitude: location?.longitude ?? null,
      },
      authToken,
      userId
    );
  }, [controller, location?.latitude, location?.longitude, authToken, userId]);

  useEffect(() => {
    fetchRecommendations();
  }, [fetchRecommendations]);

  return {
    status: state.status,
    recommendations: state.recommendations,
    totalCandidatesEvaluated: state.totalCandidatesEvaluated,
    isLoading: state.isLoading,
    errorMessage: state.errorMessage,
    userMessage: state.userMessage,
    refetch: fetchRecommendations,
  };
}
