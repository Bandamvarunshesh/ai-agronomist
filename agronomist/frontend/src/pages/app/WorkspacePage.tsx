import { useEffect, useState } from "react";

import { useAuth } from "../../auth/auth-store";
import { InlineAlert } from "../../components/ui/Feedback";
import {
  getFarmWeather,
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
  partialErrors: string[];
};

const relativeDateFormatter = new Intl.RelativeTimeFormat(undefined, {
  numeric: "auto",
});

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
    return `${section}: ${error.message}`;
  }
  return `${section}: unable to load data`;
}

export function WorkspacePage() {
  const { state } = useAuth();
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [error, setError] = useState<string | null>(null);
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [refreshTick, setRefreshTick] = useState(0);

  useEffect(() => {
    if (state.status !== "authenticated" || !state.token) {
      return;
    }

    let cancelled = false;

    const loadDashboard = async () => {
      setStatus("loading");
      setError(null);

      try {
        const farms = await listFarms(state.token!);
        const limitedFarms = farms.slice(0, 6);

        const notificationsPromise = Promise.allSettled([
          listNotifications(state.token!, 6),
        ]);
        const recommendationsPromise = Promise.allSettled(
          limitedFarms.map(async (farm) => {
            const recommendations = await listFarmRecommendations(
              state.token!,
              farm.id,
              1,
            );
            return recommendations[0]
              ? ({ ...recommendations[0], farm } as FarmRecommendation & { farm: Farm })
              : null;
          }),
        );
        const weatherPromise = Promise.allSettled(
          limitedFarms.slice(0, 4).map(async (farm) => ({
            ...(await getFarmWeather(state.token!, farm.id)),
            farm,
          })),
        );
        const timelinePromise = Promise.allSettled(
          limitedFarms.map(async (farm) => {
            const timelineEntries = await listFarmTimeline(state.token!, farm.id, 4);
            return timelineEntries.map((entry) => ({ ...entry, farm }));
          }),
        );

        const [notificationResults, recommendationResults, weatherResults, timelineResults] =
          await Promise.all([
            notificationsPromise,
            recommendationsPromise,
            weatherPromise,
            timelinePromise,
          ]);

        const partialErrors: string[] = [];
        const notifications =
          notificationResults[0]?.status === "fulfilled"
            ? notificationResults[0].value
            : [];
        if (notificationResults[0]?.status === "rejected") {
          partialErrors.push(
            summarizePartialError("Notifications", notificationResults[0].reason),
          );
        }

        const recommendations = recommendationResults
          .flatMap((result) => {
            if (result.status === "fulfilled") {
              return result.value ? [result.value] : [];
            }
            partialErrors.push(
              summarizePartialError("Recommendations", result.reason),
            );
            return [];
          })
          .sort(
            (left, right) =>
              new Date(right.generated_at).getTime() -
              new Date(left.generated_at).getTime(),
          );

        const weatherSummaries = weatherResults.flatMap((result) => {
          if (result.status === "fulfilled") {
            return [result.value];
          }
          partialErrors.push(summarizePartialError("Weather", result.reason));
          return [];
        });

        const timeline = timelineResults
          .flatMap((result) => {
            if (result.status === "fulfilled") {
              return result.value;
            }
            partialErrors.push(summarizePartialError("Timeline", result.reason));
            return [];
          })
          .sort(
            (left, right) =>
              new Date(right.created_at).getTime() -
              new Date(left.created_at).getTime(),
          )
          .slice(0, 6);

        if (cancelled) {
          return;
        }

        setDashboard({
          farms,
          notifications,
          recommendations,
          weatherSummaries,
          timeline,
          partialErrors,
        });
        setStatus("ready");
      } catch (loadError) {
        if (cancelled) {
          return;
        }

        if (loadError instanceof ApiError && loadError.status === 403) {
          setError(
            "Dashboard data is only available for farmer accounts because the farm-backed APIs require farmer access.",
          );
        } else {
          setError(
            loadError instanceof Error
              ? loadError.message
              : "Unable to load the dashboard right now.",
          );
        }
        setStatus("error");
      }
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
            {status === "loading" ? "Refreshing..." : "Refresh dashboard"}
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

      {status === "ready" && dashboard?.partialErrors.length ? (
        <InlineAlert
          tone="warning"
          title="Some sections are incomplete"
          message={dashboard.partialErrors.join(" | ")}
        />
      ) : null}

      <section className="metric-grid">
        <article className="metric-card">
          <div className="metric-label">Farms</div>
          <div className="metric-value">
            {status === "ready" ? dashboard?.farms.length ?? 0 : "--"}
          </div>
        </article>
        <article className="metric-card">
          <div className="metric-label">Crops tracked</div>
          <div className="metric-value">{status === "ready" ? uniqueCrops : "--"}</div>
        </article>
        <article className="metric-card">
          <div className="metric-label">Land area</div>
          <div className="metric-value">
            {status === "ready" ? `${formatAcreage(String(totalAcreage))} ac` : "--"}
          </div>
        </article>
        <article className="metric-card">
          <div className="metric-label">Unread notifications</div>
          <div className="metric-value">
            {status === "ready" ? unreadNotifications : "--"}
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
          {status === "loading" ? (
            <p className="surface-copy">Loading farms...</p>
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
          {status === "loading" ? (
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
          {status === "loading" ? (
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
          {status === "loading" ? (
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
          {status === "loading" ? (
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
          ) : (
            <p className="surface-copy">No recent timeline activity yet.</p>
          )}
        </article>
      </section>
    </section>
  );
}
