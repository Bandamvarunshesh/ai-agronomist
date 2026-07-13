import { apiRequest } from "./client";

export type UserProfile = {
  id: string;
  email: string | null;
  phone_number: string | null;
  full_name: string | null;
  profile_picture_url: string | null;
  preferred_language: string;
  role: string;
  is_active: boolean;
  default_state: string | null;
  default_district: string | null;
  default_farm_id: string | null;
  account_settings: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type UserProfileUpdate = {
  full_name?: string | null;
  phone_number?: string | null;
  preferred_language?: string | null;
  profile_picture_url?: string | null;
  default_state?: string | null;
  default_district?: string | null;
  default_farm_id?: string | null;
};

export type AccountSettings = {
  preferred_language: string;
  units: "metric" | "imperial";
  timezone: string;
  date_format: "dd-mm-yyyy" | "mm-dd-yyyy" | "yyyy-mm-dd";
  theme: "light" | "dark" | "system";
  default_state: string | null;
  default_district: string | null;
  default_farm_id: string | null;
  default_location: string;
  default_location_latitude: number | null;
  default_location_longitude: number | null;
  location_source: string;
  location_permission_status: string;
  weather_alerts: boolean;
  irrigation_reminders: boolean;
  fertilizer_reminders: boolean;
  disease_alerts: boolean;
  crop_stage_reminders: boolean;
  high_risk_alerts: boolean;
  daily_summary: boolean;
  weekly_summary: boolean;
  push_enabled: boolean;
  push_token: string | null;
  push_platform: string | null;
  push_provider: string | null;
  response_language: string;
  explanation_detail: "concise" | "standard" | "detailed";
  organic_treatment_preference: boolean;
  chemical_treatment_preference: boolean;
  show_sources_by_default: boolean;
  allow_farm_context_in_chat: boolean;
  location_usage_consent: boolean;
  ai_data_usage_explanation: string;
  delete_account_requested: boolean;
  export_account_data_requested: boolean;
};

export type AccountSettingsUpdate = Partial<AccountSettings>;

export async function getProfile(authToken: string) {
  return apiRequest<UserProfile>("/users/me/profile", {
    method: "GET",
    authToken,
  });
}

export async function updateProfile(
  authToken: string,
  payload: UserProfileUpdate,
) {
  return apiRequest<UserProfile>("/users/me/profile", {
    method: "PUT",
    authToken,
    body: payload,
  });
}

export async function getAccountSettings(authToken: string) {
  return apiRequest<AccountSettings>("/users/me/settings", {
    method: "GET",
    authToken,
  });
}

export async function updateAccountSettings(
  authToken: string,
  payload: AccountSettingsUpdate,
) {
  return apiRequest<AccountSettings>("/users/me/settings", {
    method: "PUT",
    authToken,
    body: payload,
  });
}

export async function changePassword(
  authToken: string,
  payload: { current_password: string; new_password: string },
) {
  return apiRequest<{ changed: boolean }>("/users/me/password", {
    method: "POST",
    authToken,
    body: payload,
  });
}
