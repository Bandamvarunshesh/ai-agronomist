import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { useAuth } from "../../auth/auth-store";
import { InlineAlert } from "../../components/ui/Feedback";
import { useToast } from "../../components/ui/ToastProvider";
import { ApiError } from "../../lib/api/client";
import { deleteFarm, getFarm, type Farm } from "../../lib/api/farms";
import { FarmIntelligenceNav } from "../../components/farms/FarmIntelligenceNav";

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function FarmDetailPage() {
  const { farmId = "" } = useParams();
  const { state } = useAuth();
  const { pushToast } = useToast();
  const navigate = useNavigate();
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [error, setError] = useState<string | null>(null);
  const [farm, setFarm] = useState<Farm | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [refreshTick, setRefreshTick] = useState(0);

  useEffect(() => {
    if (state.status !== "authenticated" || !state.token || !farmId) {
      return;
    }

    let cancelled = false;

    const loadFarm = async () => {
      setStatus("loading");
      setError(null);

      try {
        const response = await getFarm(state.token!, farmId);
        if (cancelled) {
          return;
        }

        setFarm(response);
        setStatus("ready");
      } catch (loadError) {
        if (cancelled) {
          return;
        }

        if (loadError instanceof ApiError && loadError.status === 404) {
          setError("This farm could not be found.");
        } else {
          setError(
            loadError instanceof Error
              ? loadError.message
              : "Unable to load the farm right now.",
          );
        }
        setStatus("error");
      }
    };

    void loadFarm();

    return () => {
      cancelled = true;
    };
  }, [farmId, refreshTick, state.status, state.token]);

  const handleDelete = async () => {
    if (!state.token || !farm) {
      return;
    }

    const confirmed = window.confirm(
      `Delete ${farm.farm_name}? This removes the farm record from the backend.`,
    );
    if (!confirmed) {
      return;
    }

    setDeleting(true);
    setError(null);

    try {
      await deleteFarm(state.token, farm.id);
      pushToast({
        title: "Farm deleted",
        message: `${farm.farm_name} was removed successfully.`,
        tone: "success",
      });
      navigate("/app/farms", { replace: true });
    } catch (deleteError) {
      const detail =
        deleteError instanceof Error
          ? deleteError.message
          : "Unable to delete the farm right now.";
      setError(detail);
      pushToast({
        title: "Delete failed",
        message: detail,
        tone: "error",
      });
    } finally {
      setDeleting(false);
    }
  };

  return (
    <section className="page-stack">
      <article className="surface-card page-header">
        <div>
          <div className="eyebrow">Farm detail</div>
          <h2 className="surface-title">
            {status === "ready" && farm ? farm.farm_name : "Farm profile"}
          </h2>
          <p className="surface-copy">
            Review the stored profile, then update or remove it when field reality
            changes.
          </p>
        </div>
        <div className="button-row">
          <Link className="button button-ghost button-link" to="/app/farms">
            Back to farms
          </Link>
          <Link
            className="button button-secondary button-link"
            to={`/app/chat?farmId=${farmId}`}
          >
            Farming chat
          </Link>
          <Link
            className="button button-secondary button-link"
            to={`/app/farms/${farmId}/diagnosis`}
          >
            Diagnose crop image
          </Link>
          <button
            className="button button-secondary"
            onClick={() => setRefreshTick((current) => current + 1)}
          >
            {status === "loading" ? "Refreshing..." : "Refresh"}
          </button>
          {farm ? (
            <Link
              className="button button-primary button-link"
              to={`/app/farms/${farm.id}/edit`}
            >
              Edit farm
            </Link>
          ) : null}
        </div>
      </article>

      {error ? (
        <InlineAlert
          title="Farm unavailable"
          message={error}
        />
      ) : null}

      {farm ? <FarmIntelligenceNav farmId={farm.id} /> : null}

      {status === "loading" ? (
        <article className="surface-card">
          <div className="eyebrow">Loading</div>
          <h3 className="surface-title">Fetching farm profile...</h3>
          <p className="surface-copy">Pulling the latest farm record from the backend.</p>
        </article>
      ) : null}

      {status === "ready" && farm ? (
        <>
          <article className="surface-card">
            <div className="panel-header">
              <div>
                <h3 className="section-title">Farm intelligence</h3>
                <p className="surface-copy">
                  Jump into weather, stage, recommendations, timeline, diagnosis, chat, and escalation tools for this farm.
                </p>
              </div>
            </div>
            <div className="action-grid">
              <Link className="button button-ghost button-link" to={`/app/farms/${farm.id}/weather`}>
                Weather
              </Link>
              <Link className="button button-ghost button-link" to={`/app/farms/${farm.id}/stage-advisory`}>
                Crop stage
              </Link>
              <Link className="button button-ghost button-link" to={`/app/farms/${farm.id}/recommendations`}>
                Recommendations
              </Link>
              <Link className="button button-ghost button-link" to={`/app/farms/${farm.id}/timeline`}>
                Timeline
              </Link>
              <Link className="button button-ghost button-link" to={`/app/farms/${farm.id}/diagnosis`}>
                Diagnosis
              </Link>
              <Link className="button button-ghost button-link" to={`/app/chat?farmId=${farm.id}`}>
                AI chat
              </Link>
              <Link className="button button-ghost button-link" to={`/app/escalations?farmId=${farm.id}`}>
                Escalation
              </Link>
            </div>
          </article>

          <article className="surface-card">
            <div className="detail-grid">
              <div>
                <div className="detail-label">Primary crop</div>
                <p className="detail-value">{farm.crop}</p>
              </div>
              <div>
                <div className="detail-label">Land size</div>
                <p className="detail-value">{farm.land_size_acres} acres</p>
              </div>
              <div>
                <div className="detail-label">Location</div>
                <p className="detail-value">{farm.location}</p>
              </div>
              <div>
                <div className="detail-label">Village</div>
                <p className="detail-value">{farm.village}</p>
              </div>
              <div>
                <div className="detail-label">District</div>
                <p className="detail-value">{farm.district}</p>
              </div>
              <div>
                <div className="detail-label">State</div>
                <p className="detail-value">{farm.state}</p>
              </div>
              <div>
                <div className="detail-label">Soil type</div>
                <p className="detail-value">{farm.soil_type || "Not specified"}</p>
              </div>
              <div>
                <div className="detail-label">Irrigation type</div>
                <p className="detail-value">
                  {farm.irrigation_type || "Not specified"}
                </p>
              </div>
              <div>
                <div className="detail-label">Sowing date</div>
                <p className="detail-value">{farm.sowing_date || "Not specified"}</p>
              </div>
              <div>
                <div className="detail-label">Created</div>
                <p className="detail-value">{formatDate(farm.created_at)}</p>
              </div>
              <div>
                <div className="detail-label">Last updated</div>
                <p className="detail-value">{formatDate(farm.updated_at)}</p>
              </div>
              <div>
                <div className="detail-label">Farm ID</div>
                <p className="detail-value">{farm.id}</p>
              </div>
            </div>
          </article>

          <article className="surface-card">
            <div className="panel-header">
              <div>
                <h3 className="section-title">Danger zone</h3>
                <p className="surface-copy">
                  Delete the farm only when you are sure it should be removed from the
                  system.
                </p>
              </div>
              <button
                className="button button-danger"
                disabled={deleting}
                onClick={handleDelete}
                type="button"
              >
                {deleting ? "Deleting..." : "Delete farm"}
              </button>
            </div>
          </article>
        </>
      ) : null}
    </section>
  );
}
