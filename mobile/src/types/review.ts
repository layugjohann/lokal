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
  relative_time?: string | null;
  report_url?: string | null;
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
  reviews: UnifiedReview[];
  attributions: ProviderAttribution[];
  has_more: boolean;
}
