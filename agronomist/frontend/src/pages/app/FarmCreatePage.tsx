import { type FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { useAuth } from "../../auth/auth-store";
import {
  FarmForm,
  emptyFarmFormValues,
  farmFormValuesToPayload,
  type FarmFormValues,
} from "../../components/farms/FarmForm";
import { InlineAlert } from "../../components/ui/Feedback";
import { useToast } from "../../components/ui/ToastProvider";
import { createFarm } from "../../lib/api/farms";

export function FarmCreatePage() {
  const { state } = useAuth();
  const { pushToast } = useToast();
  const navigate = useNavigate();
  const [values, setValues] = useState<FarmFormValues>(emptyFarmFormValues);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!state.token) {
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      const farm = await createFarm(state.token, farmFormValuesToPayload(values));
      pushToast({
        title: "Farm created",
        message: `${farm.farm_name} is ready to use across the platform.`,
        tone: "success",
      });
      navigate(`/app/farms/${farm.id}`, { replace: true });
    } catch (submitError) {
      setError(
        submitError instanceof Error
          ? submitError.message
          : "Unable to create the farm right now.",
      );
      pushToast({
        title: "Farm creation failed",
        message:
          submitError instanceof Error
            ? submitError.message
            : "Unable to create the farm right now.",
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
          <h2 className="surface-title">Create farm</h2>
          <p className="surface-copy">
            Add the farm profile once, and the rest of the farming intelligence can
            use it as shared context.
          </p>
        </div>
        <div className="button-row">
          <Link className="button button-ghost button-link" to="/app/farms">
            Back to farms
          </Link>
        </div>
      </article>

      <article className="surface-card">
        {error ? (
          <InlineAlert
            title="Unable to create farm"
            message={error}
          />
        ) : null}

        <FarmForm
          cancelTo="/app/farms"
          onChange={(field, value) =>
            setValues((current) => ({ ...current, [field]: value }))
          }
          onSubmit={handleSubmit}
          submitLabel="Create farm"
          submitting={submitting}
          values={values}
        />
      </article>
    </section>
  );
}
