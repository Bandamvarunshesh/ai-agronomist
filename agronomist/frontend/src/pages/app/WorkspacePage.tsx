import { useEffect, useState } from "react";

import { useAuth } from "../../auth/auth-store";
import { InlineAlert } from "../../components/ui/Feedback";
import {
  getCachedFarmWeather,
  listFarmRecommendations,
  listFarmTimeline,
  listFarms,
  listNotifications,
  type Farm,
  type FarmRecommendation,
  type FarmWeather,
  type Notification,
  type TimelineEvent,
} from "../../lib/api/dashboard";
import { ApiError } from "../../lib/api/client";

type DashboardData = {
  farms: Farm[];
  notifications: Notification[];
  recommendations: Array<FarmRecommendation & { farm: Farm }>;
  weatherSummaries: Array<FarmWeather & { farm: Farm }>;
  timeline: Array<TimelineEvent & { farm: Farm | null }>;
};

type SectionLoadingState = {
  farms: boolean;
  notifications: boolean;
  recommendations: boolean;
  weather: boolean;
  timeline: boolean;
};

type SectionErrorState = Record<keyof SectionLoadingState, string | null>;

const relativeDateFormatter = new Intl.RelativeTimeFormat(undefined, {
  numeric: "auto",
});

function createEmptyDashboard(farms: Farm[]): DashboardData {
  return {
    farms,
    notifications: [],
    recommendations: [],
    weatherSummaries: [],
    timeline: [],
  };
}

function createSectionLoadingState(value: boolean): SectionLoadingState {
  return {
    farms: value,
    notifications: value,
    recommendations: value,
    weather: value,
    timeline: value,
  };
}

function createSectionErrorState(): SectionErrorState {
  return {
    farms: null,
    notifications: null,
    recommendations: null,
    weather: null,
    timeline: null,
  };
}

function formatRelativeTime(value: string) {
  const target = new Date(value).getTime();
  const deltaMinutes = Math.round((target - Date.now()) / 60000);

  if (Math.abs(deltaMinutes) < 60) {
    return relativeDateFormatter.format(deltaMinutes, "minute");
  }

  const deltaHours = Math.round(deltaMinutes / 60);
  if (Math.abs(deltaHours) < 24) {
    return relativeDateFormatter.format(deltaHours, "hour");
  }

  const deltaDays = Math.round(deltaHours / 24);
  return relativeDateFormatter.format(deltaDays, "day");
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function formatAcreage(value: string) {
  const numericValue = Number(value);
  if (Number.isNaN(numericValue)) {
    return value;
  }
  return new Intl.NumberFormat(undefined, {
    maximumFractionDigits: 2,
  }).format(numericValue);
}

function summarizePartialError(section: string, error: unknown) {
  if (error instanceof Error) {
    if (section === "Weather") {
      return "Weather temporarily unavailable.";
    }
    return error.message;
  }
  return `${section} is temporarily unavailable.`;
}

export function WorkspacePage() {
  const { state } = useAuth();
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [error, setError] = useState<string | null>(null);
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [sectionLoading, setSectionLoading] = useState<SectionLoadingState>(() =>
    createSectionLoadingState(false),
  );
  const [sectionErrors, setSectionErrors] = useState<SectionErrorState>(() =>
    createSectionErrorState(),
  );
  const [refreshTick, setRefreshTick] = useState(0);

  useEffect(() => {
    if (state.status !== "authenticated" || !state.token) {
      return;
    }

    let cancelled = false;

    const loadDashboard = async () => {
      setStatus("ready");
      setError(null);
      setDashboard((current) => current || createEmptyDashboard([]));
      setSectionErrors(createSectionErrorState());
      setSectionLoading({
        farms: true,
        notifications: true,
        recommendations: false,
        weather: false,
        timeline: false,
      });

      const updateDashboard = (updater: (current: DashboardData) => DashboardData) => {
        if (cancelled) {
          return;
        }
        setDashboard((current) => updater(current || createEmptyDashboard([])));
      };

      const setSectionError = (
        section: keyof SectionErrorState,
        message: string | null,
      ) => {
        if (cancelled) {
          return;
        }
        setSectionErrors((current) => ({ ...current, [section]: message }));
      };

      const finishSection = (section: keyof SectionLoadingState) => {
        if (cancelled) {
          return;
        }
        setSectionLoading((current) => ({ ...current, [section]: false }));
      };

      const loadNotificationsSection = async () => {
        try {
          const [notificationResult] = await Promise.allSettled([
            listNotifications(state.token!, 6),
          ]);

          if (notificationResult.status === "fulfilled") {
            updateDashboard((current) => ({
              ...current,
              notifications: notificationResult.value,
            }));
            setSectionError("notifications", null);
          } else {
            setSectionError(
              "notifications",
              summarizePartialError("Notifications", notificationResult.reason),
            );
          }
        } finally {
          finishSection("notifications");
        }
      };

      const loadRecommendationsSection = async (limitedFarms: Farm[]) => {
        setSectionLoading((current) => ({ ...current, recommendations: true }));
        try {
          const recommendationResults = await Promise.allSettled(
            limitedFarms.map(async (farm) => {
              const recommendations = await listFarmRecommendations(
                state.token!,
                farm.id,
                1,
              );
              return recommendations[0]
                ? ({ ...recommendations[0], farm } as FarmRecommendation & {
                    farm: Farm;
                  })
                : null;
            }),
          );

          const errors: string[] = [];
          const recommendations = recommendationResults
            .flatMap((result) => {
              if (result.status === "fulfilled") {
                return result.value ? [result.value] : [];
              }
              errors.push(summarizePartialError("Recommendations", result.reason));
              return [];
            })
            .sort(
              (left, right) =>
                new Date(right.generated_at).getTime() -
                new Date(left.generated_at).getTime(),
            );

          updateDashboard((current) => ({
            ...current,
            recommendations,
          }));
          setSectionError("recommendations", errors[0] || null);
        } finally {
          finishSection("recommendations");
        }
      };

      const loadWeatherSection = async (limitedFarms: Farm[]) => {
        setSectionLoading((current) => ({ ...current, weather: true }));
        try {
          const weatherResults = await Promise.allSettled(
            limitedFarms.slice(0, 4).map(async (farm) => ({
              ...(await getCachedFarmWeather(state.token!, farm.id)),
              farm,
            })),
          );

          const errors: string[] = [];
          const weatherSummaries = weatherResults.flatMap((result) => {
            if (result.status === "fulfilled") {
              return [result.value];
            }
            errors.push(summarizePartialError("Weather", result.reason));
            return [];
          });

          updateDashboard((current) => ({
            ...current,
            weatherSummaries,
          }));
          setSectionError("weather", errors[0] || null);
        } finally {
          finishSection("weather");
        }
      };

      const loadTimelineSection = async (limitedFarms: Farm[]) => {
        setSectionLoading((current) => ({ ...current, timeline: true }));
        try {
          const timelineResults = await Promise.allSettled(
            limitedFarms.map(async (farm) => {
              const timelineEntries = await listFarmTimeline(state.token!, farm.id, 4);
              return timelineEntries.map((entry) => ({ ...entry, farm }));
            }),
          );

          const errors: string[] = [];
          const timeline = timelineResults
            .flatMap((result) => {
              if (result.status === "fulfilled") {
                return result.value;
              }
              errors.push(summarizePartialError("Timeline", result.reason));
              return [];
            })
            .sort(
              (left, right) =>
                new Date(right.created_at).getTime() -
                new Date(left.created_at).getTime(),
            )
            .slice(0, 6);

          updateDashboard((current) => ({
            ...current,
            timeline,
          }));
          setSectionError("timeline", errors[0] || null);
        } finally {
          finishSection("timeline");
        }
      };

      const loadFarmsSection = async () => {
        try {
          const [farmResult] = await Promise.allSettled([listFarms(state.token!)]);

          if (farmResult.status !== "fulfilled") {
            if (farmResult.reason instanceof ApiError && farmResult.reason.status === 403) {
              setError(
                "Dashboard data is only available for farmer accounts because the farm-backed APIs require farmer access.",
              );
              setStatus("error");
            }
            setSectionError("farms", summarizePartialError("Farms", farmResult.reason));
            return;
          }

          const farms = farmResult.value;
          const limitedFarms = farms.slice(0, 6);
          updateDashboard((current) => ({
            ...current,
            farms,
          }));
          setSectionError("farms", null);

          if (limitedFarms.length) {
            void Promise.allSettled([
              loadRecommendationsSection(limitedFarms),
              loadWeatherSection(limitedFarms),
              loadTimelineSection(limitedFarms),
            ]);
          }
        } finally {
          finishSection("farms");
        }
      };

      void Promise.allSettled([loadFarmsSection(), loadNotificationsSection()]);
    };

    void loadDashboard();

    return () => {
      cancelled = true;
    };
  }, [refreshTick, state.status, state.token]);

  const handleRefresh = () => {
    setRefreshTick((current) => current + 1);
  };

  const totalAcreage =
    dashboard?.farms.reduce(
      (sum, farm) => sum + (Number(farm.land_size_acres) || 0),
      0,
    ) ?? 0;
  const uniqueCrops = new Set(dashboard?.farms.map((farm) => farm.crop) ?? []).size;
  const unreadNotifications =
    dashboard?.notifications.filter((notification) => !notification.is_read).length ?? 0;
  const isDashboardBusy =
    sectionLoading.farms ||
    sectionLoading.notifications ||
    sectionLoading.recommendations ||
    sectionLoading.weather ||
    sectionLoading.timeline;

  return (
    <section className="dashboard-stack">
      <article className="surface-card dashboard-hero">
        <div className="dashboard-hero-copy">
          <div className="eyebrow">Dashboard</div>
          <h2 className="surface-title">Farm operations snapshot</h2>
          <p className="surface-copy">
            Live summaries are stitched together from farms, recommendations,
            weather, notifications, and timeline activity using the existing backend.
          </p>
        </div>
        <div className="button-row">
          <button className="button button-secondary" onClick={handleRefresh}>
            {isDashboardBusy ? "Refreshing..." : "Refresh dashboard"}
          </button>
        </div>
      </article>

      {status === "error" ? (
        <InlineAlert
          title="Dashboard unavailable"
          message={error || "Unable to load the dashboard right now."}
          action={
            <button className="button button-primary" onClick={handleRefresh}>
              Try again
            </button>
          }
        />
      ) : null}

      <section className="metric-grid">
        <article className="metric-card">
          <div className="metric-label">Farms</div>
          <div className="metric-value">
            {sectionLoading.farms && !dashboard?.farms.length
              ? "--"
              : dashboard?.farms.length ?? 0}
          </div>
        </article>
        <article className="metric-card">
          <div className="metric-label">Crops tracked</div>
          <div className="metric-value">
            {sectionLoading.farms && !dashboard?.farms.length ? "--" : uniqueCrops}
          </div>
        </article>
        <article className="metric-card">
          <div className="metric-label">Land area</div>
          <div className="metric-value">
            {sectionLoading.farms && !dashboard?.farms.length
              ? "--"
              : `${formatAcreage(String(totalAcreage))} ac`}
          </div>
        </article>
        <article className="metric-card">
          <div className="metric-label">Unread notifications</div>
          <div className="metric-value">
            {!sectionLoading.notifications
              ? unreadNotifications
              : "--"}
          </div>
        </article>
      </section>

      {status === "ready" && dashboard && !dashboard.farms.length ? (
        <article className="surface-card">
          <div className="eyebrow">No farms yet</div>
          <h2 className="surface-title">The dashboard comes alive once farms exist.</h2>
          <p className="surface-copy">
            Your backend connection is working, but there are no farms to summarize yet.
          </p>
        </article>
      ) : null}

      <section className="dashboard-grid">
        <article className="surface-card">
          <div className="panel-header">
            <div>
              <div className="eyebrow">Farms</div>
              <h3 className="surface-title">Farm summary</h3>
            </div>
          </div>
          {sectionLoading.farms && !dashboard?.farms.length ? (
            <p className="surface-copy">Loading farms...</p>
          ) : sectionErrors.farms ? (
            <InlineAlert
              title="Farm summary unavailable"
              message={sectionErrors.farms}
              tone="warning"
            />
          ) : (
            <div className="list-stack">
              {dashboard?.farms.slice(0, 5).map((farm) => (
                <div className="list-item" key={farm.id}>
                  <div>
                    <div className="list-title">{farm.farm_name}</div>
                    <div className="list-meta">
                      {farm.crop} | {farm.district}, {farm.state}
                    </div>
                  </div>
                  <div className="pill">{formatAcreage(farm.land_size_acres)} ac</div>
                </div>
              ))}
            </div>
          )}
        </article>

        <article className="surface-card">
          <div className="panel-header">
            <div>
              <div className="eyebrow">AI</div>
              <h3 className="surface-title">Latest recommendations</h3>
            </div>
          </div>
          {sectionLoading.recommendations && !dashboard?.recommendations.length ? (
            <p className="surface-copy">Loading recommendations...</p>
          ) : dashboard?.recommendations.length ? (
            <div className="list-stack">
              {dashboard.recommendations.slice(0, 4).map((recommendation) => {
                const leadItem = recommendation.prioritized_recommendations[0];
                return (
                  <div className="list-item list-item-block" key={recommendation.id}>
                    <div className="list-title">
                      {recommendation.farm.farm_name} | {leadItem?.title || "Recommendation"}
                    </div>
                    <div className="list-meta">
                      Risk: {recommendation.risk_level} | Health score:{" "}
                      {recommendation.farm_health_score.toFixed(1)} |{" "}
                      {formatRelativeTime(recommendation.generated_at)}
                    </div>
                    {leadItem ? (
                      <p className="list-body">{leadItem.recommendation}</p>
                    ) : (
                      <p className="list-body">{recommendation.weekly_summary}</p>
                    )}
                  </div>
                );
              })}
            </div>
          ) : sectionErrors.recommendations ? (
            <InlineAlert
              title="Recommendations unavailable"
              message={sectionErrors.recommendations}
              tone="warning"
            />
          ) : (
            <p className="surface-copy">No recommendations generated yet.</p>
          )}
        </article>

        <article className="surface-card">
          <div className="panel-header">
            <div>
              <div className="eyebrow">Weather</div>
              <h3 className="surface-title">Weather summary</h3>
            </div>
          </div>
          {sectionLoading.weather && !dashboard?.weatherSummaries.length ? (
            <p className="surface-copy">Loading weather summaries...</p>
          ) : dashboard?.weatherSummaries.length ? (
            <div className="list-stack">
              {dashboard.weatherSummaries.map((weather) => (
                <div className="list-item list-item-block" key={weather.farm_id}>
                  <div className="list-title">{weather.farm_name}</div>
                  <div className="list-meta">
                    {weather.current.condition} |{" "}
                    {weather.current.temperature_c !== null
                      ? `${weather.current.temperature_c.toFixed(1)} C`
                      : "Temp unavailable"}
                    {weather.current.wind_speed_kmh !== null
                      ? ` | Wind ${weather.current.wind_speed_kmh.toFixed(1)} km/h`
                      : ""}
                    {` | Updated ${formatDate(weather.fetched_at)}`}
                    {weather.is_stale ? " | Cached" : ""}
                  </div>
                  <p className="list-body">
                    {weather.advice.irrigation[0] ||
                      weather.advice.rainfall[0] ||
                      weather.advice.heat[0] ||
                      "No weather advice available yet."}
                  </p>
                </div>
              ))}
            </div>
          ) : sectionErrors.weather ? (
            <InlineAlert
              title="Weather temporarily unavailable"
              message={sectionErrors.weather}
              tone="warning"
            />
          ) : (
            <p className="surface-copy">Weather summaries are not available yet.</p>
          )}
        </article>

        <article className="surface-card">
          <div className="panel-header">
            <div>
              <div className="eyebrow">Notifications</div>
              <h3 className="surface-title">Recent notifications</h3>
            </div>
          </div>
          {sectionLoading.notifications && !dashboard?.notifications.length ? (
            <p className="surface-copy">Loading notifications...</p>
          ) : dashboard?.notifications.length ? (
            <div className="list-stack">
              {dashboard.notifications.map((notification) => (
                <div className="list-item list-item-block" key={notification.id}>
                  <div className="list-row">
                    <div className="list-title">{notification.title}</div>
                    <div className={notification.is_read ? "pill" : "pill pill-strong"}>
                      {notification.is_read ? "Read" : "Unread"}
                    </div>
                  </div>
                  <div className="list-meta">
                    {notification.notification_type} | {formatDate(notification.created_at)}
                  </div>
                  <p className="list-body">{notification.body}</p>
                </div>
              ))}
            </div>
          ) : sectionErrors.notifications ? (
            <InlineAlert
              title="Notifications unavailable"
              message={sectionErrors.notifications}
              tone="warning"
            />
          ) : (
            <p className="surface-copy">No notifications yet.</p>
          )}
        </article>

        <article className="surface-card dashboard-span-two">
          <div className="panel-header">
            <div>
              <div className="eyebrow">Timeline</div>
              <h3 className="surface-title">Recent activity</h3>
            </div>
          </div>
          {sectionLoading.timeline && !dashboard?.timeline.length ? (
            <p className="surface-copy">Loading timeline activity...</p>
          ) : dashboard?.timeline.length ? (
            <div className="timeline-list">
              {dashboard.timeline.map((event) => (
                <div className="timeline-item" key={event.id}>
                  <div className="timeline-date">{formatDate(event.created_at)}</div>
                  <div className="timeline-content">
                    <div className="list-title">
                      {event.title}
                      {event.farm ? ` | ${event.farm.farm_name}` : ""}
                    </div>
                    <div className="list-meta">
                      {event.event_type} | {event.source}
                    </div>
                    {event.description ? (
                      <p className="list-body">{event.description}</p>
                    ) : null}
                  </div>
                </div>
              ))}
            </div>
          ) : sectionErrors.timeline ? (
            <InlineAlert
              title="Timeline unavailable"
              message={sectionErrors.timeline}
              tone="warning"
            />
          ) : (
            <p className="surface-copy">No recent timeline activity yet.</p>
          )}
        </article>
      </section>
    </section>
  );
}
