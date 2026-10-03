import { Shop } from './shop';

export type RecommendationStatus = 'personalized' | 'insufficient_data' | 'empty';

export interface RecommendedShopItem {
  shop: Shop;
  explanation: string;
}

export interface PersonalizedRecommendationsResponse {
  status: RecommendationStatus;
  message?: string | null;
  recommendations: RecommendedShopItem[];
  total_candidates_evaluated: number;
}

export interface PersonalizedSearchParams {
  latitude?: number | null;
  longitude?: number | null;
  radius?: number;
  limit?: number;
}
