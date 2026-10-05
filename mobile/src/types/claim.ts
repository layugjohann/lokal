import { Shop } from './shop.ts';
import { UnifiedReview } from './review.ts';

export type ShopClaimStatus = 'PENDING' | 'APPROVED' | 'REJECTED' | 'REVOKED';

/**
 * User-facing representation of a coffee shop ownership claim.
 * Internal user_id, claimant phone, and business proof are excluded for privacy.
 */
export interface ShopClaim {
  id: string;
  shop_id: string;
  status: ShopClaimStatus;
  claimant_name: string;
  claimant_role: string;
  rejection_reason?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ClaimSubmissionPayload {
  claimant_name: string;
  claimant_phone?: string;
  claimant_role: string;
  business_proof?: string;
}

export interface OwnerShopUpdatePayload {
  name?: string;
  address?: string;
}

export interface OwnerDashboardData {
  shop: Shop;
  claim: ShopClaim;
  lokal_rating?: number | null;
  lokal_reviews_count: number;
  rating?: number | null;
  recent_reviews: UnifiedReview[];
}
