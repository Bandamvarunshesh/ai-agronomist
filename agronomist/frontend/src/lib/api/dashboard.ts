import { apiRequest } from "./client";
import { listFarms as listFarmsRequest, type Farm } from "./farms";

export type { Farm } from "./farms";

export type RecommendationItem = {
  priority: number;
  category: string;
  title: string;
  recommendation: string;
  explanation: string;
  risk_level: string;
  action_window: string | null;
};

export type DailyActionPlanItem = {
  day: string;
  actions: string[];
  explanation: string | null;
};

export type FarmRecommendation = {
  id: string;
  farm_id: string;
  user_id: string | null;
  farm_health_score: number;
  risk_level: string;
  prioritized_recommendations: RecommendationItem[];
  daily_action_plan: DailyActionPlanItem[];
  weekly_summary: string;
  confidence_score: number;
  generated_at: string;
  created_at: string;
  updated_at: string;
};

export type FarmWeather = {
  farm_id: string;
  farm_name: string;
  crop: string;
  resolved_location: {
    name: string;
    latitude: number;
    longitude: number;
    timezone: string;
    country: string | null;
    admin1: string | null;
    admin2: string | null;
  };
  current: {
    time: string;
    temperature_c: number | null;
    apparent_temperature_c: number | null;
    relative_humidity_percent: number | null;
    precipitation_mm: number | null;
    rain_mm: number | null;
    weather_code: number | null;
    condition: string;
    cloud_cover_percent: number | null;
    wind_speed_kmh: number | null;
    wind_direction_degrees: number | null;
    wind_gusts_kmh: number | null;
  };
  forecast: Array<{
    date: string;
    weather_code: number | null;
    condition: string;
    temperature_max_c: number | null;
    temperature_min_c: number | null;
    apparent_temperature_max_c: number | null;
    apparent_temperature_min_c: number | null;
    precipitation_sum_mm: number | null;
    precipitation_probability_max_percent: number | null;
    relative_humidity_mean_percent: number | null;
    wind_speed_max_kmh: number | null;
    wind_gusts_max_kmh: number | null;
  }>;
  advice: {
    irrigation: string[];
    rainfall: string[];
    spraying: string[];
    heat: string[];
    wind: string[];
    humidity: string[];
  };
  source: string;
  fetched_at: string;
  is_stale?: boolean;
  unavailable?: string | null;
  cache_status?: string;
};

export type Notification = {
  id: string;
  user_id: string;
  farm_id: string | null;
  diagnosis_id: string | null;
  notification_type: string;
  title: string;
  body: string;
  priority: string;
  channel: string;
  is_read: boolean;
  read_at: string | null;
  scheduled_for: string | null;
  sent_at: string | null;
  payload: Record<string, unknown>;
  source: string;
  dedupe_key: string | null;
  deep_link: string | null;
  push_title: string | null;
  push_body: string | null;
  push_data: Record<string, unknown>;
  delivery_status: string;
  delivery_error: string | null;
  created_at: string;
  updated_at: string;
};

export type TimelineEvent = {
  id: string;
  farm_id: string;
  user_id: string | null;
  event_type: string;
  title: string;
  description: string | null;
  event_date: string;
  source: string;
  payload: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

const FARMS_CACHE_TTL_MS = 60 * 1000;
const NOTIFICATIONS_CACHE_TTL_MS = 30 * 1000;
const RECOMMENDATIONS_CACHE_TTL_MS = 60 * 1000;
const WEATHER_CACHE_TTL_MS = 15 * 60 * 1000;
const TIMELINE_CACHE_TTL_MS = 60 * 1000;
const WEATHER_REQUEST_TIMEOUT_MS = 8000;

type CacheEntry<T> = {
  expiresAt: number;
  value: T;
};

const responseCache = new Map<string, CacheEntry<unknown>>();
const inflightRequests = new Map<string, Promise<unknown>>();

function readCache<T>(key: string): T | null {
  const cached = responseCache.get(key);
  if (!cached) {
    return null;
  }

  if (cached.expiresAt <= Date.now()) {
    responseCache.delete(key);
    return null;
  }

  return cached.value as T;
}

function writeCache<T>(key: string, value: T, ttlMs: number): T {
  responseCache.set(key, {
    expiresAt: Date.now() + ttlMs,
    value,
  });
  return value;
}

async function cachedRequest<T>(
  key: string,
  ttlMs: number,
  load: () => Promise<T>,
): Promise<T> {
  const cached = readCache<T>(key);
  if (cached !== null) {
    return cached;
  }

  const inflight = inflightRequests.get(key);
  if (inflight) {
    return inflight as Promise<T>;
  }

  const request = load()
    .then((value) => writeCache(key, value, ttlMs))
    .finally(() => {
      inflightRequests.delete(key);
    });

  inflightRequests.set(key, request);
  return request;
}

export async function listFarms(
  authToken: string,
  options: { skip?: number; limit?: number } = {},
) {
  const skip = options.skip ?? 0;
  const limit = options.limit ?? 100;
  return cachedRequest(
    `farms:${authToken}:${skip}:${limit}`,
    FARMS_CACHE_TTL_MS,
    () => listFarmsRequest(authToken, { skip, limit }),
  );
}

export async function listFarmRecommendations(
  authToken: string,
  farmId: string,
  limit = 1,
) {
  return cachedRequest(
    `recommendations:${authToken}:${farmId}:${limit}`,
    RECOMMENDATIONS_CACHE_TTL_MS,
    () =>
      apiRequest<FarmRecommendation[]>(
        `/farms/${farmId}/recommendations?limit=${limit}&skip=0`,
        {
          method: "GET",
          authToken,
        },
      ),
  );
}

export async function getFarmWeather(authToken: string, farmId: string) {
  return apiRequest<FarmWeather>(`/farms/${farmId}/weather`, {
    method: "GET",
    authToken,
    timeoutMs: WEATHER_REQUEST_TIMEOUT_MS,
  });
}

export async function getCachedFarmWeather(authToken: string, farmId: string) {
  return cachedRequest(
    `weather:${authToken}:${farmId}`,
    WEATHER_CACHE_TTL_MS,
    async () => {
      let lastError: unknown;
      for (let attempt = 0; attempt < 2; attempt += 1) {
        try {
          return await getFarmWeather(authToken, farmId);
        } catch (error) {
          lastError = error;
        }
      }

      throw lastError instanceof Error
        ? lastError
        : new Error("Unable to load weather right now.");
    },
  );
}

export async function listNotifications(authToken: string, limit = 6) {
  return cachedRequest(
    `notifications:${authToken}:${limit}`,
    NOTIFICATIONS_CACHE_TTL_MS,
    () =>
      apiRequest<Notification[]>(
        `/notifications?limit=${limit}&skip=0&unread_only=false`,
        {
          method: "GET",
          authToken,
        },
      ),
  );
}

export async function listFarmTimeline(
  authToken: string,
  farmId: string,
  limit = 4,
) {
  return cachedRequest(
    `timeline:${authToken}:${farmId}:${limit}`,
    TIMELINE_CACHE_TTL_MS,
    () =>
      apiRequest<TimelineEvent[]>(
        `/farms/${farmId}/timeline?limit=${limit}&skip=0`,
        {
          method: "GET",
          authToken,
        },
      ),
  );
}
