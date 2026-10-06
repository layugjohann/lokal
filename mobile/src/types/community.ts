export interface CommunityFeedItem {
  id: string;
  shop_id: string;
  shop_name: string;
  shop_address: string | null;
  author_name: string;
  rating: number;
  content: string | null;
  created_at: string;
  updated_at: string | null;
  is_edited: boolean;
}

export interface CommunityFeedResponse {
  items: CommunityFeedItem[];
  limit: number;
  offset: number;
  has_more: boolean;
}
