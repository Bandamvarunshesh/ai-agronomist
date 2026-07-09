import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { useAuth } from "../../auth/auth-store";
import { FarmIntelligenceNav } from "../../components/farms/FarmIntelligenceNav";
import { InlineAlert } from "../../components/ui/Feedback";
import { getFarm, type Farm } from "../../lib/api/farms";
import { listFarmTimeline, type TimelineEvent } from "../../lib/api/intelligence";

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function FarmTimelinePage() {
  const { farmId = "" } = useParams();
  const { state } = useAuth();
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [error, setError] = useState<string | null>(null);
  const [farm, setFarm] = useState<Farm | null>(null);
  const [events, setEvents] = useState<TimelineEvent[]>([]);
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
        const [farmResponse, eventsResponse] = await Promise.all([
          getFarm(state.token!, farmId),
          listFarmTimeline(state.token!, farmId, 25),
        ]);
        if (cancelled) {
          return;
        }
        setFarm(farmResponse);
        setEvents(eventsResponse);
        setStatus("ready");
      } catch (loadError) {
        if (cancelled) {
          return;
        }
        setError(
          loadError instanceof Error
            ? loadError.message
            : "Unable to load farm timeline right now.",
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
          <div className="eyebrow">Timeline</div>
          <h2 className="surface-title">
            {farm ? `${farm.farm_name} timeline` : "Farm timeline"}
          </h2>
          <p className="surface-copy">
            Reverse chronological farm activity from uploads, diagnoses, weather checks, stage advisories, and chat sessions.
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

      {error ? <InlineAlert title="Timeline unavailable" message={error} /> : null}

      {status === "ready" && events.length ? (
        <article className="surface-card">
          <div className="timeline-list">
            {events.map((event) => (
              <div className="timeline-item" key={event.id}>
                <div className="timeline-date">{formatDate(event.created_at)}</div>
                <div className="timeline-content">
                  <div className="list-title">{event.title}</div>
                  <div className="list-meta">
                    {event.event_type} | {event.source} | {event.event_date}
                  </div>
                  {event.description ? (
                    <div className="list-body">{event.description}</div>
                  ) : null}
                  {Object.keys(event.payload || {}).length ? (
                    <details className="details-block">
                      <summary>Payload</summary>
                      <pre className="json-block">
                        {JSON.stringify(event.payload, null, 2)}
                      </pre>
                    </details>
                  ) : null}
                </div>
              </div>
            ))}
          </div>
        </article>
      ) : status === "ready" ? (
        <article className="surface-card">
          <div className="eyebrow">No events yet</div>
          <h3 className="surface-title">The timeline is still empty.</h3>
          <p className="surface-copy">Farm activity will appear here as it happens.</p>
        </article>
      ) : (
        <article className="surface-card">
          <div className="eyebrow">Loading</div>
          <h3 className="surface-title">Fetching farm timeline...</h3>
          <p className="surface-copy">Pulling recent intelligence events from the backend.</p>
        </article>
      )}
    </section>
  );
}
