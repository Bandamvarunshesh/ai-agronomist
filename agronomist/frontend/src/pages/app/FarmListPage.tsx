import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { useAuth } from "../../auth/auth-store";
import { InlineAlert } from "../../components/ui/Feedback";
import { listFarms, type Farm } from "../../lib/api/farms";

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

export function FarmListPage() {
  const { state } = useAuth();
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [error, setError] = useState<string | null>(null);
  const [farms, setFarms] = useState<Farm[]>([]);
  const [refreshTick, setRefreshTick] = useState(0);

  useEffect(() => {
    if (state.status !== "authenticated" || !state.token) {
      return;
    }

    let cancelled = false;

    const loadFarms = async () => {
      setStatus("loading");
      setError(null);

      try {
        const response = await listFarms(state.token!);
        if (cancelled) {
          return;
        }

        setFarms(
          [...response].sort(
            (left, right) =>
              new Date(right.updated_at).getTime() -
              new Date(left.updated_at).getTime(),
          ),
        );
        setStatus("ready");
      } catch (loadError) {
        if (cancelled) {
          return;
        }

        setError(
          loadError instanceof Error
            ? loadError.message
            : "Unable to load farms right now.",
        );
        setStatus("error");
      }
    };

    void loadFarms();

    return () => {
      cancelled = true;
    };
  }, [refreshTick, state.status, state.token]);

  return (
    <section className="page-stack">
      <article className="surface-card page-header">
        <div>
          <div className="eyebrow">Farm management</div>
          <h2 className="surface-title">Farm records</h2>
          <p className="surface-copy">
            Manage the core profiles that power recommendations, weather, timeline,
            and the rest of the platform.
          </p>
        </div>
        <div className="button-row">
          <button
            className="button button-secondary"
            onClick={() => setRefreshTick((current) => current + 1)}
          >
            {status === "loading" ? "Refreshing..." : "Refresh"}
          </button>
          <Link className="button button-primary button-link" to="/app/farms/new">
            Add farm
          </Link>
        </div>
      </article>

      {status === "error" ? (
        <InlineAlert
          title="Unable to load farms"
          message={error || "The farm list is not available right now."}
          action={
            <button
              className="button button-primary"
              onClick={() => setRefreshTick((current) => current + 1)}
            >
              Try again
            </button>
          }
        />
      ) : null}

      {status === "ready" && !farms.length ? (
        <article className="surface-card">
          <div className="eyebrow">No farms yet</div>
          <h2 className="surface-title">Create your first farm profile.</h2>
          <p className="surface-copy">
            Once a farm exists, the rest of the intelligence features have something
            real to work with.
          </p>
          <div className="button-row">
            <Link className="button button-primary button-link" to="/app/farms/new">
              Create farm
            </Link>
          </div>
        </article>
      ) : null}

      <div className="farm-grid">
        {status === "loading"
          ? Array.from({ length: 4 }).map((_, index) => (
              <article className="surface-card" key={index}>
                <div className="eyebrow">Loading</div>
                <h3 className="surface-title">Fetching farm profile...</h3>
                <p className="surface-copy">
                  Pulling current farm records from the backend.
                </p>
              </article>
            ))
          : farms.map((farm) => (
              <article className="surface-card farm-card" key={farm.id}>
                <div className="panel-header">
                  <div>
                    <div className="list-title">{farm.farm_name}</div>
                    <div className="list-meta">
                      {farm.crop} | {farm.village}, {farm.district}, {farm.state}
                    </div>
                  </div>
                  <div className="pill">{formatAcreage(farm.land_size_acres)} ac</div>
                </div>

                <div className="farm-card-grid">
                  <div>
                    <div className="meta-label">Location</div>
                    <div className="detail-value">{farm.location}</div>
                  </div>
                  <div>
                    <div className="meta-label">Irrigation</div>
                    <div className="detail-value">
                      {farm.irrigation_type || "Not specified"}
                    </div>
                  </div>
                  <div>
                    <div className="meta-label">Soil</div>
                    <div className="detail-value">
                      {farm.soil_type || "Not specified"}
                    </div>
                  </div>
                  <div>
                    <div className="meta-label">Updated</div>
                    <div className="detail-value">{formatDate(farm.updated_at)}</div>
                  </div>
                </div>

                <div className="button-row">
                  <Link
                    className="button button-ghost button-link"
                    to={`/app/farms/${farm.id}/edit`}
                  >
                    Edit
                  </Link>
                  <Link
                    className="button button-primary button-link"
                    to={`/app/farms/${farm.id}`}
                  >
                    View details
                  </Link>
                </div>
              </article>
            ))}
      </div>
    </section>
  );
}
