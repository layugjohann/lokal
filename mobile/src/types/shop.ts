export interface Shop {
  id: string;
  name: string;
  address: string | null;
  latitude: number;
  longitude: number;
  rating: number | null;
  google_place_id?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  distance_meters: number;
}

export interface NearbySearchParams {
  latitude: number;
  longitude: number;
  radius?: number;
  limit?: number;
  offset?: number;
  query?: string;
  minRating?: number;
  sortBy?: 'distance' | 'rating';
}

