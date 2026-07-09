import { apiRequest } from "./client";

export type Farm = {
  id: string;
  user_id: string;
  farm_name: string;
  crop: string;
  location: string;
  village: string;
  district: string;
  state: string;
  soil_type: string | null;
  land_size_acres: string;
  irrigation_type: string | null;
  sowing_date: string | null;
  created_at: string;
  updated_at: string;
};

export type FarmCreateInput = {
  farm_name: string;
  crop: string;
  location: string;
  village: string;
  district: string;
  state: string;
  soil_type: string | null;
  land_size_acres: string;
  irrigation_type: string | null;
  sowing_date: string | null;
};

export type FarmUpdateInput = Partial<FarmCreateInput>;

export async function listFarms(
  authToken: string,
  options: { skip?: number; limit?: number } = {},
) {
  const params = new URLSearchParams({
    skip: String(options.skip ?? 0),
    limit: String(options.limit ?? 100),
  });

  return apiRequest<Farm[]>(`/farms?${params.toString()}`, {
    method: "GET",
    authToken,
  });
}

export async function getFarm(authToken: string, farmId: string) {
  return apiRequest<Farm>(`/farms/${farmId}`, {
    method: "GET",
    authToken,
  });
}

export async function createFarm(authToken: string, payload: FarmCreateInput) {
  return apiRequest<Farm>("/farms", {
    method: "POST",
    authToken,
    body: payload,
  });
}

export async function updateFarm(
  authToken: string,
  farmId: string,
  payload: FarmUpdateInput,
) {
  return apiRequest<Farm>(`/farms/${farmId}`, {
    method: "PUT",
    authToken,
    body: payload,
  });
}

export async function deleteFarm(authToken: string, farmId: string) {
  return apiRequest<void>(`/farms/${farmId}`, {
    method: "DELETE",
    authToken,
  });
}
