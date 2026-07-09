import { apiRequest } from "./client";
import {
  getFarmWeather,
  listFarmRecommendations,
  listFarmTimeline,
  listNotifications,
  type FarmRecommendation,
  type FarmWeather,
  type Notification,
  type TimelineEvent,
} from "./dashboard";

export {
  getFarmWeather,
  listFarmRecommendations,
  listFarmTimeline,
  listNotifications,
  type FarmRecommendation,
  type FarmWeather,
  type Notification,
  type TimelineEvent,
};

export type StageWindow = {
  name: string;
  stage_order: number | null;
  start_day: number | null;
  end_day: number | null;
};

export type StageDiagnosisContext = {
  id: string;
  disease_name: string;
  severity: string;
  confidence_score: number;
  escalate_to_human: boolean;
  created_at: string;
};

export type StageWeatherContext = {
  source: string;
  summary: string;
  unavailable_reason: string | null;
};

export type StageAdvisory = {
  farm_id: string;
  farm_name: string;
  crop: string;
  days_since_sowing: number | null;
  current_stage: StageWindow;
  next_stage: StageWindow | null;
  important_actions: string[];
  risks: string[];
  ai_recommendations: string[];
  latest_diagnosis: StageDiagnosisContext | null;
  weather_context: StageWeatherContext;
  generated_at: string;
};

export type NotificationPreference = {
  id: string;
  user_id: string;
  notifications_enabled: boolean;
  in_app_enabled: boolean;
  push_enabled: boolean;
  email_enabled: boolean;
  sms_enabled: boolean;
  enabled_types: Record<string, boolean>;
  quiet_hours_enabled: boolean;
  quiet_hours_start: string | null;
  quiet_hours_end: string | null;
  timezone: string;
  push_token: string | null;
  push_platform: string | null;
  push_provider: string | null;
  device_metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type NotificationPreferenceUpdateInput = Partial<
  Pick<
    NotificationPreference,
    | "notifications_enabled"
    | "in_app_enabled"
    | "push_enabled"
    | "email_enabled"
    | "sms_enabled"
    | "enabled_types"
    | "quiet_hours_enabled"
    | "quiet_hours_start"
    | "quiet_hours_end"
    | "timezone"
    | "push_token"
    | "push_platform"
    | "push_provider"
  >
>;

export type KnowledgeCitation = {
  document_id: string;
  version_id: string;
  chunk_id: string;
  title: string;
  source_uri: string | null;
  citation_label: string;
};

export type KnowledgeSearchResult = {
  chunk_id: string;
  document_id: string;
  version_id: string;
  title: string;
  content: string;
  score: number;
  semantic_score: number;
  lexical_score: number;
  citation: KnowledgeCitation;
};

export type KnowledgeSearchResponse = {
  query: string;
  results: KnowledgeSearchResult[];
  citations: KnowledgeCitation[];
  cache_hit: boolean;
};

export type EscalationContact = {
  id: string;
  user_id: string | null;
  farm_id: string | null;
  name: string;
  contact_type: string;
  role: string | null;
  organization: string | null;
  district: string | null;
  state: string | null;
  phone_number: string | null;
  email: string | null;
  preferred_channel: string;
  is_active: boolean;
  contact_priority: number;
  is_fallback: boolean;
  notes: string | null;
  service_area: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type EscalationContactLookup = {
  farm_id: string;
  farm_name: string;
  district: string;
  state: string;
  requested_contact_type: string | null;
  routing_level: string;
  fallback_used: boolean;
  contact: EscalationContact;
};

export type Escalation = {
  id: string;
  farm_id: string;
  user_id: string | null;
  diagnosis_id: string | null;
  chat_session_id: string | null;
  contact_id: string | null;
  escalation_type: string;
  contact_type_requested: string | null;
  status: string;
  priority: string;
  subject: string;
  description: string | null;
  resolution_notes: string | null;
  routing_status: string;
  routing_reason: string | null;
  fallback_used: boolean;
  contact_snapshot: Record<string, unknown>;
  escalated_at: string;
  resolved_at: string | null;
  escalation_metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  contact: EscalationContact | null;
};

export type EscalationCreateInput = {
  farm_id: string;
  diagnosis_id?: string | null;
  chat_session_id?: string | null;
  escalation_type?: string | null;
  contact_type_requested?: string | null;
  priority: string;
  subject: string;
  description?: string | null;
};

export async function getStageAdvisory(authToken: string, farmId: string) {
  return apiRequest<StageAdvisory>(`/farms/${farmId}/stage-advisory`, {
    method: "GET",
    authToken,
  });
}

export async function generateFarmRecommendation(authToken: string, farmId: string) {
  return apiRequest<FarmRecommendation>(`/farms/${farmId}/recommendations/generate`, {
    method: "POST",
    authToken,
  });
}

export async function markNotificationRead(
  authToken: string,
  notificationId: string,
) {
  return apiRequest<Notification>(`/notifications/${notificationId}/read`, {
    method: "PATCH",
    authToken,
  });
}

export async function getNotificationPreferences(authToken: string) {
  return apiRequest<NotificationPreference>("/notification-preferences", {
    method: "GET",
    authToken,
  });
}

export async function updateNotificationPreferences(
  authToken: string,
  payload: NotificationPreferenceUpdateInput,
) {
  return apiRequest<NotificationPreference>("/notification-preferences", {
    method: "PUT",
    authToken,
    body: payload,
  });
}

export async function searchKnowledge(
  authToken: string,
  payload: {
    query: string;
    limit?: number;
    language?: string | null;
    content_type?: string | null;
    use_hybrid?: boolean;
  },
) {
  return apiRequest<KnowledgeSearchResponse>("/knowledge/search", {
    method: "POST",
    authToken,
    body: payload,
  });
}

export async function lookupFarmEscalationContact(
  authToken: string,
  farmId: string,
  contactType?: string | null,
) {
  const params = new URLSearchParams();
  if (contactType) {
    params.set("contact_type", contactType);
  }

  const suffix = params.toString() ? `?${params.toString()}` : "";
  return apiRequest<EscalationContactLookup>(
    `/farms/${farmId}/escalation-contact${suffix}`,
    {
      method: "GET",
      authToken,
    },
  );
}

export async function listEscalations(
  authToken: string,
  options: { skip?: number; limit?: number } = {},
) {
  const params = new URLSearchParams({
    skip: String(options.skip ?? 0),
    limit: String(options.limit ?? 100),
  });

  return apiRequest<Escalation[]>(`/escalations?${params.toString()}`, {
    method: "GET",
    authToken,
  });
}

export async function createEscalation(
  authToken: string,
  payload: EscalationCreateInput,
) {
  return apiRequest<Escalation>("/escalations", {
    method: "POST",
    authToken,
    body: payload,
  });
}
