import { apiRequest } from "./client";

export type ReverseGeocodeResult = {
  latitude: number;
  longitude: number;
  formatted_address: string | null;
  locality: string | null;
  district: string | null;
  state: string | null;
  country: string | null;
  postal_code: string | null;
  provider: string;
  cache_hit: boolean;
};

export async function reverseGeocode(
  authToken: string,
  latitude: number,
  longitude: number,
) {
  const params = new URLSearchParams({
    latitude: latitude.toFixed(6),
    longitude: longitude.toFixed(6),
  });

  return apiRequest<ReverseGeocodeResult>(`/geocoding/reverse?${params.toString()}`, {
    method: "GET",
    authToken,
    timeoutMs: 12000,
  });
}
