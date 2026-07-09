import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { useAuth } from "../../auth/auth-store";
import { FarmIntelligenceNav } from "../../components/farms/FarmIntelligenceNav";
import { InlineAlert } from "../../components/ui/Feedback";
import { useToast } from "../../components/ui/ToastProvider";
import { getFarm, type Farm } from "../../lib/api/farms";
import {
  generateFarmRecommendation,
  listFarmRecommendations,
  type FarmRecommendation,
} from "../../lib/api/intelligence";

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function FarmRecommendationsPage() {
  const { farmId = "" } = useParams();
  const { state } = useAuth();
  const { pushToast } = useToast();
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [error, setError] = useState<string | null>(null);
  const [farm, setFarm] = useState<Farm | null>(null);
  const [recommendations, setRecommendations] = useState<FarmRecommendation[]>([]);
  const [refreshTick, setRefreshTick] = useState(0);
  const [generating, setGenerating] = useState(false);

  useEffect(() => {
    if (state.status !== "authenticated" || !state.token || !farmId) {
      return;
    }
    let cancelled = false;

    const loadPage = async () => {
      setStatus("loading");
      setError(null);

      try {
        const [farmResponse, recommendationsResponse] = await Promise.all([
          getFarm(state.token!, farmId),
          listFarmRecommendations(state.token!, farmId, 20),
        ]);
        if (cancelled) {
          return;
        }
        setFarm(farmResponse);
        setRecommendations(recommendationsResponse);
        setStatus("ready");
      } catch (loadError) {
        if (cancelled) {
          return;
        }
        setError(
          loadError instanceof Error
            ? loadError.message
            : "Unable to load recommendations right now.",
        );
        setStatus("error");
      }
    };

    void loadPage();
    return () => {
      cancelled = true;
    };
  }, [farmId, refreshTick, state.status, state.token]);

  const handleGenerate = async () => {
    if (!state.token) {
      return;
    }
    setGenerating(true);
    setError(null);

    try {
      const recommendation = await generateFarmRecommendation(state.token, farmId);
      setRecommendations((current) => [recommendation, ...current]);
      pushToast({
        title: "Recommendation generated",
        message: "A fresh AI recommendation is ready.",
        tone: "success",
      });
    } catch (generateError) {
      const detail =
        generateError instanceof Error
          ? generateError.message
          : "Unable to generate recommendations right now.";
      setError(detail);
      pushToast({
        title: "Generation failed",
        message: detail,
        tone: "error",
      });
    } finally {
      setGenerating(false);
    }
  };

  return (
    <section className="page-stack">
      <article className="surface-card page-header">
        <div>
          <div className="eyebrow">Recommendations</div>
          <h2 className="surface-title">
            {farm ? `${farm.farm_name} recommendations` : "Farm recommendations"}
          </h2>
          <p className="surface-copy">
            Generated farm health summaries, prioritized recommendations, and action plans.
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
          <button
            className="button button-primary"
            disabled={generating || status !== "ready"}
            onClick={() => void handleGenerate()}
          >
            {generating ? "Generating..." : "Generate recommendation"}
          </button>
        </div>
      </article>

      <FarmIntelligenceNav farmId={farmId} />

      {error ? <InlineAlert title="Recommendations unavailable" message={error} /> : null}

      {status === "ready" && recommendations.length ? (
        <div className="list-stack">
          {recommendations.map((recommendation) => (
            <article className="surface-card" key={recommendation.id}>
              <div className="panel-header">
                <div>
                  <h3 className="section-title">
                    Generated {formatDate(recommendation.generated_at)}
                  </h3>
                  <p className="surface-copy">{recommendation.weekly_summary}</p>
                </div>
                <div className="list-stack compact-stack">
                  <div className="pill">Health {recommendation.farm_health_score.toFixed(1)}</div>
                  <div className="pill pill-strong">{recommendation.risk_level}</div>
                </div>
              </div>

              <div className="dashboard-grid">
                <article className="metric-card">
                  <div className="metric-label">Confidence</div>
                  <div className="metric-value">
                    {Math.round(recommendation.confidence_score * 100)}%
                  </div>
                </article>
                <article className="metric-card dashboard-span-two">
                  <div className="metric-label">Daily action plan</div>
                  <div className="list-stack compact-stack">
                    {recommendation.daily_action_plan.map((plan) => (
                      <div key={`${recommendation.id}-${plan.day}`}>
                        <div className="list-title">{plan.day}</div>
                        <div className="list-body">{plan.actions.join(" | ")}</div>
                        {plan.explanation ? (
                          <div className="list-meta">{plan.explanation}</div>
                        ) : null}
                      </div>
                    ))}
                  </div>
                </article>
              </div>

              <div className="list-stack">
                {recommendation.prioritized_recommendations.map((item) => (
                  <div className="list-item list-item-block" key={`${recommendation.id}-${item.priority}-${item.title}`}>
                    <div className="panel-header">
                      <div>
                        <div className="list-title">
                          {item.priority}. {item.title}
                        </div>
                        <div className="list-meta">
                          {item.category} | {item.risk_level} |{" "}
                          {item.action_window || "No time window provided"}
                        </div>
                      </div>
                    </div>
                    <div className="list-body">{item.recommendation}</div>
                    <div className="list-meta">{item.explanation}</div>
                  </div>
                ))}
              </div>
            </article>
          ))}
        </div>
      ) : status === "ready" ? (
        <article className="surface-card">
          <div className="eyebrow">No recommendations yet</div>
          <h3 className="surface-title">Generate the first recommendation.</h3>
          <p className="surface-copy">
            This page will fill in once the backend generates a recommendation for the farm.
          </p>
        </article>
      ) : (
        <article className="surface-card">
          <div className="eyebrow">Loading</div>
          <h3 className="surface-title">Fetching farm recommendations...</h3>
          <p className="surface-copy">Reading existing recommendation history from the backend.</p>
        </article>
      )}
    </section>
  );
}
