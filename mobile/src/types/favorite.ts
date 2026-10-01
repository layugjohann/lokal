export interface FavoriteStatusResponse {
  shop_id: string;
  is_favorite: boolean;
  favorited_at: string | null;
}

export interface FavoriteShop {
  id: string;
  name: string;
  address: string | null;
  latitude: number;
  longitude: number;
  rating: number | null;
  google_place_id?: string | null;
  favorited_at: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  distance_meters?: number | null;
}

