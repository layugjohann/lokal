import type {
  PersonalizedSearchParams,
  PersonalizedRecommendationsResponse,
} from '../types/recommendation.ts';
import { getApiBaseUrl } from './shopService.ts';

/**
 * Retrieves personalized coffee shop recommendations from the FastAPI backend.
 * Requires user authentication.
 */
export async function fetchPersonalizedRecommendations(
  params: PersonalizedSearchParams,
  authToken: string
): Promise<PersonalizedRecommendationsResponse> {
  if (!authToken || !authToken.trim()) {
    throw new Error('Authentication is required to view personalized recommendations.');
  }

  const baseUrl = getApiBaseUrl();
  const queryParams = new URLSearchParams();

  if (
    params.latitude !== undefined &&
    params.latitude !== null &&
    !isNaN(params.latitude) &&
    params.longitude !== undefined &&
    params.longitude !== null &&
    !isNaN(params.longitude)
  ) {
    queryParams.append('latitude', params.latitude.toString());
    queryParams.append('longitude', params.longitude.toString());
  }

  if (params.radius !== undefined && params.radius !== null && !isNaN(params.radius)) {
    queryParams.append('radius', params.radius.toString());
  }

  if (params.limit !== undefined && params.limit !== null && !isNaN(params.limit)) {
    queryParams.append('limit', params.limit.toString());
  }

  const queryString = queryParams.toString();
  const url = `${baseUrl}/api/v1/shops/recommendations/personalized${
    queryString ? `?${queryString}` : ''
  }`;

  const response = await fetch(url, {
    method: 'GET',
    headers: {
      Accept: 'application/json',
      Authorization: `Bearer ${authToken.trim()}`,
    },
  });

  if (!response.ok) {
    let errorDetail = 'Failed to fetch personalized recommendations.';
    try {
      const data = await response.json();
      if (data && typeof data.detail === 'string') {
        errorDetail = data.detail;
      }
    } catch {
      // Ignore JSON parse errors on non-json error responses
    }
    throw new Error(errorDetail);
  }

  return response.json();
}
