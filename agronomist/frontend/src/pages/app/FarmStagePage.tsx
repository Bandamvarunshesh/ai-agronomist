import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { useAuth } from "../../auth/auth-store";
import { FarmIntelligenceNav } from "../../components/farms/FarmIntelligenceNav";
import { InlineAlert } from "../../components/ui/Feedback";
import { getFarm, type Farm } from "../../lib/api/farms";
import { getStageAdvisory, type StageAdvisory } from "../../lib/api/intelligence";

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function renderBulletCard(title: string, items: string[]) {
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
        <p className="list-body">No items returned.</p>
      )}
    </article>
  );
}

export function FarmStagePage() {
  const { farmId = "" } = useParams();
  const { state } = useAuth();
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [error, setError] = useState<string | null>(null);
  const [farm, setFarm] = useState<Farm | null>(null);
  const [advisory, setAdvisory] = useState<StageAdvisory | null>(null);
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
        const [farmResponse, advisoryResponse] = await Promise.all([
          getFarm(state.token!, farmId),
          getStageAdvisory(state.token!, farmId),
        ]);
        if (cancelled) {
          return;
        }
        setFarm(farmResponse);
        setAdvisory(advisoryResponse);
        setStatus("ready");
      } catch (loadError) {
        if (cancelled) {
          return;
        }
        setError(
          loadError instanceof Error
            ? loadError.message
            : "Unable to load crop stage advisory right now.",
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
          <div className="eyebrow">Crop stage</div>
          <h2 className="surface-title">
            {farm ? `${farm.farm_name} stage advisory` : "Stage advisory"}
          </h2>
          <p className="surface-copy">
            Current crop stage, next stage, and actions based on sowing date, weather, and recent diagnosis.
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

      {error ? <InlineAlert title="Stage advisory unavailable" message={error} /> : null}

      {status === "ready" && advisory ? (
        <>
          <div className="metric-grid">
            <article className="metric-card">
              <div className="metric-label">Current stage</div>
              <div className="metric-value diagnosis-metric">{advisory.current_stage.name}</div>
            </article>
            <article className="metric-card">
              <div className="metric-label">Days since sowing</div>
              <div className="metric-value">{advisory.days_since_sowing ?? "--"}</div>
            </article>
            <article className="metric-card">
              <div className="metric-label">Next stage</div>
              <div className="metric-value diagnosis-metric">
                {advisory.next_stage?.name || "Not available"}
              </div>
            </article>
            <article className="metric-card">
              <div className="metric-label">Generated</div>
              <div className="metric-value diagnosis-metric">
                {formatDate(advisory.generated_at)}
              </div>
            </article>
          </div>

          <div className="dashboard-grid">
            <article className="surface-card">
              <h3 className="section-title">Stage context</h3>
              <div className="detail-grid">
                <div>
                  <div className="detail-label">Current stage window</div>
                  <p className="detail-value">
                    {advisory.current_stage.start_day ?? "--"} to{" "}
                    {advisory.current_stage.end_day ?? "--"} days
                  </p>
                </div>
                <div>
                  <div className="detail-label">Next stage window</div>
                  <p className="detail-value">
                    {advisory.next_stage
                      ? `${advisory.next_stage.start_day ?? "--"} to ${advisory.next_stage.end_day ?? "--"} days`
                      : "Not available"}
                  </p>
                </div>
                <div>
                  <div className="detail-label">Weather summary</div>
                  <p className="detail-value">{advisory.weather_context.summary}</p>
                </div>
                <div>
                  <div className="detail-label">Weather source</div>
                  <p className="detail-value">{advisory.weather_context.source}</p>
                </div>
              </div>
            </article>

            <article className="surface-card">
              <h3 className="section-title">Latest diagnosis</h3>
              {advisory.latest_diagnosis ? (
                <div className="detail-grid">
                  <div>
                    <div className="detail-label">Disease</div>
                    <p className="detail-value">{advisory.latest_diagnosis.disease_name}</p>
                  </div>
                  <div>
                    <div className="detail-label">Severity</div>
                    <p className="detail-value">{advisory.latest_diagnosis.severity}</p>
                  </div>
                  <div>
                    <div className="detail-label">Confidence</div>
                    <p className="detail-value">
                      {Math.round(advisory.latest_diagnosis.confidence_score * 100)}%
                    </p>
                  </div>
                  <div>
                    <div className="detail-label">Created</div>
                    <p className="detail-value">
                      {formatDate(advisory.latest_diagnosis.created_at)}
                    </p>
                  </div>
                </div>
              ) : (
                <p className="list-body">No recent diagnosis was included.</p>
              )}
            </article>
          </div>

          <div className="dashboard-grid">
            {renderBulletCard("Important actions", advisory.important_actions)}
            {renderBulletCard("Risks", advisory.risks)}
            {renderBulletCard("AI recommendations", advisory.ai_recommendations)}
          </div>
        </>
      ) : status === "loading" ? (
        <article className="surface-card">
          <div className="eyebrow">Loading</div>
          <h3 className="surface-title">Fetching crop stage advisory...</h3>
          <p className="surface-copy">Pulling stage intelligence from the backend.</p>
        </article>
      ) : null}
    </section>
  );
}
