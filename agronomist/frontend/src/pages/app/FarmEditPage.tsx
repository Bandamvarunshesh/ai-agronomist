import { type FormEvent, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { useAuth } from "../../auth/auth-store";
import {
  FarmForm,
  farmFormValuesToPayload,
  farmToFormValues,
  type FarmFormValues,
} from "../../components/farms/FarmForm";
import { InlineAlert } from "../../components/ui/Feedback";
import { useToast } from "../../components/ui/ToastProvider";
import { ApiError } from "../../lib/api/client";
import { getFarm, updateFarm } from "../../lib/api/farms";

export function FarmEditPage() {
  const { farmId = "" } = useParams();
  const { state } = useAuth();
  const { pushToast } = useToast();
  const navigate = useNavigate();
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [values, setValues] = useState<FarmFormValues | null>(null);

  useEffect(() => {
    if (state.status !== "authenticated" || !state.token || !farmId) {
      return;
    }

    let cancelled = false;

    const loadFarm = async () => {
      setStatus("loading");
      setError(null);

      try {
        const farm = await getFarm(state.token!, farmId);
        if (cancelled) {
          return;
        }

        setValues(farmToFormValues(farm));
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
  }, [farmId, state.status, state.token]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!state.token || !values) {
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      const farm = await updateFarm(state.token, farmId, farmFormValuesToPayload(values));
      pushToast({
        title: "Farm updated",
        message: `${farm.farm_name} has been saved successfully.`,
        tone: "success",
      });
      navigate(`/app/farms/${farm.id}`, { replace: true });
    } catch (submitError) {
      const detail =
        submitError instanceof Error
          ? submitError.message
          : "Unable to update the farm right now.";
      setError(detail);
      pushToast({
        title: "Update failed",
        message: detail,
        tone: "error",
      });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <section className="page-stack">
      <article className="surface-card page-header">
        <div>
          <div className="eyebrow">Farm management</div>
          <h2 className="surface-title">Edit farm</h2>
          <p className="surface-copy">
            Keep the farm profile aligned with what is happening in the field so the
            rest of the platform stays useful.
          </p>
        </div>
        <div className="button-row">
          <Link className="button button-ghost button-link" to={`/app/farms/${farmId}`}>
            Back to detail
          </Link>
        </div>
      </article>

      <article className="surface-card">
        {error ? (
          <InlineAlert
            title="Unable to edit farm"
            message={error}
          />
        ) : null}

        {status === "loading" ? (
          <div className="form-stack">
            <div className="eyebrow">Loading</div>
            <h3 className="surface-title">Fetching editable farm data...</h3>
            <p className="surface-copy">
              Pulling the latest values from the backend before you make changes.
            </p>
          </div>
        ) : status === "ready" && values ? (
          <FarmForm
            authToken={state.token}
            cancelTo={`/app/farms/${farmId}`}
            onChange={(field, value) =>
              setValues((current) =>
                current ? { ...current, [field]: value } : current,
              )
            }
            onSubmit={handleSubmit}
            submitLabel="Save changes"
            submitting={submitting}
            values={values}
          />
        ) : null
        }
      </article>
    </section>
  );
}
