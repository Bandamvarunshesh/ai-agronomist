import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { useAuth } from "../../auth/auth-store";
import { FarmIntelligenceNav } from "../../components/farms/FarmIntelligenceNav";
import { InlineAlert } from "../../components/ui/Feedback";
import { getFarm, type Farm } from "../../lib/api/farms";
import { getFarmWeather, type FarmWeather } from "../../lib/api/intelligence";

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function renderAdviceGroup(title: string, items: string[]) {
  return (
    <article className="surface-card" key={title}>
      <h3 className="section-title">{title}</h3>
      {items.length ? (
        <ul className="result-list">
          {items.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      ) : (
        <p className="list-body">No advice returned for this category.</p>
      )}
    </article>
  );
}

export function FarmWeatherPage() {
  const { farmId = "" } = useParams();
  const { state } = useAuth();
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [error, setError] = useState<string | null>(null);
  const [farm, setFarm] = useState<Farm | null>(null);
  const [weather, setWeather] = useState<FarmWeather | null>(null);
  const [refreshTick, setRefreshTick] = useState(0);

  useEffect(() => {
    if (state.status !== "authenticated" || !state.token || !farmId) {
      return;
    }

    let cancelled = false;

    const loadPage = async () => {
      setStatus("loading");
      setError(null);

      try {
        const [farmResponse, weatherResponse] = await Promise.all([
          getFarm(state.token!, farmId),
          getFarmWeather(state.token!, farmId),
        ]);
        if (cancelled) {
          return;
        }
        setFarm(farmResponse);
        setWeather(weatherResponse);
        setStatus("ready");
      } catch (loadError) {
        if (cancelled) {
          return;
        }
        setError(
          loadError instanceof Error
            ? loadError.message
            : "Unable to load farm weather right now.",
        );
        setStatus("error");
      }
    };

    void loadPage();

    return () => {
      cancelled = true;
    };
  }, [farmId, refreshTick, state.status, state.token]);

  return (
    <section className="page-stack">
      <article className="surface-card page-header">
        <div>
          <div className="eyebrow">Weather intelligence</div>
          <h2 className="surface-title">
            {farm ? `${farm.farm_name} weather` : "Farm weather"}
          </h2>
          <p className="surface-copy">
            Current conditions, seven-day forecast, and farm-specific weather advice.
          </p>
        </div>
        <div className="button-row">
          <Link className="button button-ghost button-link" to={`/app/farms/${farmId}`}>
            Back to farm
          </Link>
          <button
            className="button button-secondary"
            onClick={() => setRefreshTick((current) => current + 1)}
          >
            {status === "loading" ? "Refreshing..." : "Refresh"}
          </button>
        </div>
      </article>

      <FarmIntelligenceNav farmId={farmId} />

      {error ? (
        <InlineAlert title="Weather unavailable" message={error} />
      ) : null}

      {status === "ready" && weather ? (
        <>
          <div className="metric-grid">
            <article className="metric-card">
              <div className="metric-label">Condition</div>
              <div className="metric-value diagnosis-metric">{weather.current.condition}</div>
            </article>
            <article className="metric-card">
              <div className="metric-label">Temperature</div>
              <div className="metric-value">
                {weather.current.temperature_c ?? "--"} C
              </div>
            </article>
            <article className="metric-card">
              <div className="metric-label">Humidity</div>
              <div className="metric-value">
                {weather.current.relative_humidity_percent ?? "--"}%
              </div>
            </article>
            <article className="metric-card">
              <div className="metric-label">Wind</div>
              <div className="metric-value">
                {weather.current.wind_speed_kmh ?? "--"} km/h
              </div>
            </article>
          </div>

          <div className="dashboard-grid">
            <article className="surface-card">
              <h3 className="section-title">Location</h3>
              <div className="detail-grid">
                <div>
                  <div className="detail-label">Resolved place</div>
                  <p className="detail-value">{weather.resolved_location.name}</p>
                </div>
                <div>
                  <div className="detail-label">Timezone</div>
                  <p className="detail-value">{weather.resolved_location.timezone}</p>
                </div>
                <div>
                  <div className="detail-label">Coordinates</div>
                  <p className="detail-value">
                    {weather.resolved_location.latitude}, {weather.resolved_location.longitude}
                  </p>
                </div>
                <div>
                  <div className="detail-label">Fetched</div>
                  <p className="detail-value">{formatDate(weather.fetched_at)}</p>
                </div>
              </div>
            </article>

            <article className="surface-card">
              <h3 className="section-title">7-day forecast</h3>
              <div className="list-stack">
                {weather.forecast.map((day) => (
                  <div className="list-item list-item-block" key={day.date}>
                    <div className="panel-header">
                      <div className="list-title">{day.date}</div>
                      <div className="pill">{day.condition}</div>
                    </div>
                    <div className="list-meta">
                      {day.temperature_min_c ?? "--"} C to {day.temperature_max_c ?? "--"} C
                    </div>
                    <div className="list-body">
                      Rain {day.precipitation_sum_mm ?? "--"} mm | Probability{" "}
                      {day.precipitation_probability_max_percent ?? "--"}% | Wind{" "}
                      {day.wind_speed_max_kmh ?? "--"} km/h
                    </div>
                  </div>
                ))}
              </div>
            </article>
          </div>

          <div className="dashboard-grid">
            {renderAdviceGroup("Irrigation", weather.advice.irrigation)}
            {renderAdviceGroup("Rainfall", weather.advice.rainfall)}
            {renderAdviceGroup("Spraying", weather.advice.spraying)}
            {renderAdviceGroup("Heat", weather.advice.heat)}
            {renderAdviceGroup("Wind", weather.advice.wind)}
            {renderAdviceGroup("Humidity", weather.advice.humidity)}
          </div>
        </>
      ) : status === "loading" ? (
        <article className="surface-card">
          <div className="eyebrow">Loading</div>
          <h3 className="surface-title">Fetching weather intelligence...</h3>
          <p className="surface-copy">Pulling current weather and forecast from the backend.</p>
        </article>
      ) : null}
    </section>
  );
}
