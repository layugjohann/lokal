export type ReviewSource = 'google' | 'lokal';

export interface ReviewAuthor {
  display_name: string;
  avatar_url?: string | null;
  profile_url?: string | null;
}

export interface UnifiedReview {
  id: string;
  source: ReviewSource;
  rating: number;
  text?: string | null;
  original_text?: string | null;
  language?: string | null;
  author: ReviewAuthor;
  published_at?: string | null;
  updated_at?: string | null;
  is_edited?: boolean;
  relative_time?: string | null;
  report_url?: string | null;
}

export interface ReviewCreateInput {
  rating: number;
  content?: string | null;
}

export interface ReviewUpdateInput {
  rating?: number | null;
  content?: string | null;
}

export interface ProviderAttribution {
  provider: ReviewSource;
  display_name: string;
  source_url?: string | null;
  required_notice: string;
}

export interface ShopReviewsResponse {
  shop_id: string;
  average_rating?: number | null;
  total_reviews_count?: number | null;
  lokal_average_rating?: number | null;
  lokal_reviews_count?: number;
  reviews: UnifiedReview[];
  attributions: ProviderAttribution[];
  has_more: boolean;
}

export interface MessageResponse {
  message: string;
}

export type SummaryStatus = 'available' | 'insufficient_reviews';

export interface ShopReviewSummaryResponse {
  shop_id: string;
  status: SummaryStatus;
  summary?: string | null;
  positive_themes: string[];
  negative_themes: string[];
  review_count_analyzed: number;
}

export type RecommendationStatus = 'available' | 'insufficient_reviews';

export interface RecommendationItem {
  item_name: string;
  reason: string;
}

export interface ShopRecommendationsResponse {
  shop_id: string;
  status: RecommendationStatus;
  items: RecommendationItem[];
  review_count_analyzed: number;
}

