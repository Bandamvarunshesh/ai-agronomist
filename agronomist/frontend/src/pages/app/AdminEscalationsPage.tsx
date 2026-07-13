import { useEffect, useState } from "react";

import { useAuth } from "../../auth/auth-store";
import { EmptyState, InlineAlert, PageSkeleton, PermissionDeniedState } from "../../components/ui/Feedback";
import { listAdminEscalations } from "../../lib/api/admin";
import type { Escalation } from "../../lib/api/intelligence";

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

export function AdminEscalationsPage() {
  const { state } = useAuth();
  const [escalations, setEscalations] = useState<Escalation[]>([]);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");

  const load = async () => {
    if (!state.token) return;
    setStatus("loading");
    try {
      setEscalations(await listAdminEscalations(state.token));
      setStatus("ready");
    } catch {
      setStatus("error");
    }
  };

  useEffect(() => {
    if (state.user?.role === "admin") {
      void load();
    }
  }, [state.token, state.user?.role]);

  if (state.user?.role !== "admin") {
    return <PermissionDeniedState message="Escalation operations require an admin account." />;
  }

  return (
    <section className="page-stack">
      <article className="surface-card page-header"><div><div className="eyebrow">Operations</div><h2 className="surface-title">Escalations</h2></div></article>
      {status === "loading" ? <PageSkeleton title="Loading escalations" /> : null}
      {status === "error" ? <InlineAlert title="Escalations unavailable" message="Unable to load escalation history." action={<button className="button button-primary" onClick={() => void load()} type="button">Retry</button>} /> : null}
      {status === "ready" && !escalations.length ? <EmptyState title="No escalations yet." message="Farmer escalation requests will appear here after routing." /> : null}
      {escalations.length ? (
        <article className="surface-card">
          <div className="list-stack">
            {escalations.map((escalation) => (
              <div className="list-item list-item-block" key={escalation.id}>
                <div className="list-row"><div className="list-title">{escalation.subject}</div><div className="pill">{escalation.status}</div></div>
                <div className="list-meta">{escalation.escalation_type} | {escalation.priority} | {escalation.routing_status} | {formatDate(escalation.escalated_at)}</div>
                <p className="list-body">{escalation.description || "No description"} {escalation.contact ? `Contact: ${escalation.contact.name}` : "No contact routed"}</p>
              </div>
            ))}
          </div>
        </article>
      ) : null}
    </section>
  );
}
