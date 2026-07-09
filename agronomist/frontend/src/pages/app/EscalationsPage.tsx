import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { useAuth } from "../../auth/auth-store";
import { InlineAlert } from "../../components/ui/Feedback";
import { useToast } from "../../components/ui/ToastProvider";
import { listFarms, type Farm } from "../../lib/api/farms";
import {
  createEscalation,
  listEscalations,
  lookupFarmEscalationContact,
  type Escalation,
  type EscalationContactLookup,
} from "../../lib/api/intelligence";

const contactTypes = ["", "kvk", "agronomist", "govt_extension", "vet", "emergency"];
const escalationTypes = ["manual", "diagnosis", "chat"];
const priorities = ["normal", "high", "urgent", "low"];

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function EscalationsPage() {
  const { state } = useAuth();
  const { pushToast } = useToast();
  const [searchParams, setSearchParams] = useSearchParams();
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [error, setError] = useState<string | null>(null);
  const [farms, setFarms] = useState<Farm[]>([]);
  const [escalations, setEscalations] = useState<Escalation[]>([]);
  const [lookup, setLookup] = useState<EscalationContactLookup | null>(null);
  const [lookupError, setLookupError] = useState<string | null>(null);
  const [lookingUp, setLookingUp] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState({
    farm_id: searchParams.get("farmId") || "",
    contact_type_requested: "",
    escalation_type: "manual",
    priority: "normal",
    subject: "",
    description: "",
    diagnosis_id: "",
    chat_session_id: "",
  });

  useEffect(() => {
    if (state.status !== "authenticated" || !state.token) {
      return;
    }
    let cancelled = false;

    const loadPage = async () => {
      setStatus("loading");
      setError(null);

      try {
        const [farmResponse, escalationResponse] = await Promise.all([
          listFarms(state.token!),
          listEscalations(state.token!, { limit: 50 }),
        ]);
        if (cancelled) {
          return;
        }
        setFarms(farmResponse);
        setEscalations(escalationResponse);
        setStatus("ready");
      } catch (loadError) {
        if (cancelled) {
          return;
        }
        setError(
          loadError instanceof Error
            ? loadError.message
            : "Unable to load escalations right now.",
        );
        setStatus("error");
      }
    };

    void loadPage();
    return () => {
      cancelled = true;
    };
  }, [state.status, state.token]);

  useEffect(() => {
    const farmId = searchParams.get("farmId") || "";
    setForm((current) => ({ ...current, farm_id: farmId || current.farm_id }));
  }, [searchParams]);

  const farmsById = useMemo(
    () =>
      farms.reduce<Record<string, Farm>>((accumulator, farm) => {
        accumulator[farm.id] = farm;
        return accumulator;
      }, {}),
    [farms],
  );

  const handleLookup = async () => {
    if (!state.token || !form.farm_id) {
      return;
    }
    setLookingUp(true);
    setLookupError(null);

    try {
      const response = await lookupFarmEscalationContact(
        state.token,
        form.farm_id,
        form.contact_type_requested || null,
      );
      setLookup(response);
    } catch (lookupFailure) {
      setLookup(null);
      setLookupError(
        lookupFailure instanceof Error
          ? lookupFailure.message
          : "Unable to lookup escalation contact right now.",
      );
    } finally {
      setLookingUp(false);
    }
  };

  const handleSubmit = async () => {
    if (!state.token) {
      return;
    }
    setSubmitting(true);
    setError(null);

    try {
      const escalation = await createEscalation(state.token, {
        farm_id: form.farm_id,
        escalation_type: form.escalation_type,
        contact_type_requested: form.contact_type_requested || null,
        priority: form.priority,
        subject: form.subject,
        description: form.description || null,
        diagnosis_id: form.diagnosis_id || null,
        chat_session_id: form.chat_session_id || null,
      });
      setEscalations((current) => [escalation, ...current]);
      pushToast({
        title: "Escalation created",
        message: "The escalation request was saved successfully.",
        tone: "success",
      });
      setForm((current) => ({
        ...current,
        subject: "",
        description: "",
        diagnosis_id: "",
        chat_session_id: "",
      }));
    } catch (submitError) {
      const detail =
        submitError instanceof Error
          ? submitError.message
          : "Unable to create escalation right now.";
      setError(detail);
      pushToast({
        title: "Escalation failed",
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
          <div className="eyebrow">Escalations</div>
          <h2 className="surface-title">Human escalation</h2>
          <p className="surface-copy">
            Lookup escalation contacts, create manual escalations, and review escalation history.
          </p>
        </div>
      </article>

      {error ? <InlineAlert title="Escalations unavailable" message={error} /> : null}

      <div className="dashboard-grid">
        <article className="surface-card">
          <div className="panel-header">
            <div>
              <h3 className="section-title">Create escalation</h3>
              <p className="surface-copy">
                Use manual escalation or attach diagnosis/chat identifiers when available.
              </p>
            </div>
          </div>

          <div className="form-grid">
            <label className="field field-span-full">
              <span className="field-label">Farm</span>
              <select
                className="input select-input"
                onChange={(event) => {
                  const farmId = event.target.value;
                  setForm((current) => ({ ...current, farm_id: farmId }));
                  const nextParams = new URLSearchParams(searchParams);
                  if (farmId) {
                    nextParams.set("farmId", farmId);
                  } else {
                    nextParams.delete("farmId");
                  }
                  setSearchParams(nextParams);
                }}
                value={form.farm_id}
              >
                <option value="">Select farm</option>
                {farms.map((farm) => (
                  <option key={farm.id} value={farm.id}>
                    {farm.farm_name}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              <span className="field-label">Escalation type</span>
              <select
                className="input select-input"
                onChange={(event) =>
                  setForm((current) => ({ ...current, escalation_type: event.target.value }))
                }
                value={form.escalation_type}
              >
                {escalationTypes.map((type) => (
                  <option key={type} value={type}>
                    {type}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              <span className="field-label">Priority</span>
              <select
                className="input select-input"
                onChange={(event) =>
                  setForm((current) => ({ ...current, priority: event.target.value }))
                }
                value={form.priority}
              >
                {priorities.map((priority) => (
                  <option key={priority} value={priority}>
                    {priority}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              <span className="field-label">Requested contact type</span>
              <select
                className="input select-input"
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    contact_type_requested: event.target.value,
                  }))
                }
                value={form.contact_type_requested}
              >
                {contactTypes.map((type) => (
                  <option key={type || "default"} value={type}>
                    {type || "Any available"}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              <span className="field-label">Diagnosis ID</span>
              <input
                className="input"
                onChange={(event) =>
                  setForm((current) => ({ ...current, diagnosis_id: event.target.value }))
                }
                value={form.diagnosis_id}
              />
            </label>
            <label className="field">
              <span className="field-label">Chat session ID</span>
              <input
                className="input"
                onChange={(event) =>
                  setForm((current) => ({ ...current, chat_session_id: event.target.value }))
                }
                value={form.chat_session_id}
              />
            </label>
            <label className="field field-span-full">
              <span className="field-label">Subject</span>
              <input
                className="input"
                onChange={(event) =>
                  setForm((current) => ({ ...current, subject: event.target.value }))
                }
                value={form.subject}
              />
            </label>
            <label className="field field-span-full">
              <span className="field-label">Description</span>
              <textarea
                className="input"
                onChange={(event) =>
                  setForm((current) => ({ ...current, description: event.target.value }))
                }
                rows={5}
                value={form.description}
              />
            </label>
          </div>

          <div className="button-row">
            <button
              className="button button-secondary"
              disabled={!form.farm_id || lookingUp}
              onClick={() => void handleLookup()}
              type="button"
            >
              {lookingUp ? "Looking up..." : "Lookup contact"}
            </button>
            <button
              className="button button-primary"
              disabled={!form.farm_id || !form.subject.trim() || submitting}
              onClick={() => void handleSubmit()}
              type="button"
            >
              {submitting ? "Submitting..." : "Create escalation"}
            </button>
          </div>
        </article>

        <article className="surface-card">
          <div className="panel-header">
            <div>
              <h3 className="section-title">Contact lookup</h3>
              <p className="surface-copy">District/state routing and fallback contact details.</p>
            </div>
            {form.farm_id ? (
              <Link className="button button-ghost button-link" to={`/app/farms/${form.farm_id}`}>
                View farm
              </Link>
            ) : null}
          </div>

          {lookupError ? (
            <InlineAlert title="Lookup failed" message={lookupError} />
          ) : lookup ? (
            <div className="list-stack">
              <div className="list-item list-item-block">
                <div className="list-title">{lookup.contact.name}</div>
                <div className="list-meta">
                  {lookup.contact.contact_type} | {lookup.contact.organization || "Independent"} |
                  {" "}priority {lookup.contact.contact_priority}
                </div>
                <div className="list-body">
                  {lookup.contact.phone_number || "No phone"} |{" "}
                  {lookup.contact.email || "No email"}
                </div>
                <div className="list-meta">
                  Routing {lookup.routing_level} | Fallback used{" "}
                  {lookup.fallback_used ? "yes" : "no"}
                </div>
              </div>
            </div>
          ) : (
            <p className="list-body">
              Choose a farm and run lookup to see the best escalation contact.
            </p>
          )}
        </article>
      </div>

      <article className="surface-card">
        <div className="panel-header">
          <div>
            <h3 className="section-title">Escalation history</h3>
            <p className="surface-copy">Recent escalation records returned by the backend.</p>
          </div>
        </div>

        {status === "ready" && escalations.length ? (
          <div className="list-stack">
            {escalations.map((escalation) => (
              <div className="list-item list-item-block" key={escalation.id}>
                <div className="panel-header">
                  <div>
                    <div className="list-title">{escalation.subject}</div>
                    <div className="list-meta">
                      {farmsById[escalation.farm_id]?.farm_name || escalation.farm_id} |{" "}
                      {escalation.escalation_type} | {escalation.priority}
                    </div>
                  </div>
                  <div className="pill">{escalation.status}</div>
                </div>
                {escalation.description ? (
                  <div className="list-body">{escalation.description}</div>
                ) : null}
                <div className="list-meta">
                  Routed {escalation.routing_status} | Created {formatDate(escalation.created_at)}
                </div>
                {escalation.contact ? (
                  <div className="list-meta">
                    Contact {escalation.contact.name} |{" "}
                    {escalation.contact.phone_number || escalation.contact.email || "No direct channel"}
                  </div>
                ) : null}
              </div>
            ))}
          </div>
        ) : status === "ready" ? (
          <p className="list-body">No escalations have been created yet.</p>
        ) : (
          <p className="list-body">Loading escalation history...</p>
        )}
      </article>
    </section>
  );
}
