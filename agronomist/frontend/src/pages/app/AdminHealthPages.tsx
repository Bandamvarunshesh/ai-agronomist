import { useEffect, useState } from "react";

import { useAuth } from "../../auth/auth-store";
import { InlineAlert, PageSkeleton, PermissionDeniedState } from "../../components/ui/Feedback";
import { getProviderHealth, getSystemHealth, type HealthReport } from "../../lib/api/admin";

function JsonPanel({ data }: { data: unknown }) {
  return <pre className="json-block">{JSON.stringify(data, null, 2)}</pre>;
}

export function AdminSystemHealthPage() {
  const { state } = useAuth();
  const [report, setReport] = useState<HealthReport | null>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");

  const load = async () => {
    if (!state.token) return;
    setStatus("loading");
    try {
      setReport(await getSystemHealth(state.token));
      setStatus("ready");
    } catch {
      setStatus("error");
    }
  };

  useEffect(() => {
    if (state.user?.role === "admin") void load();
  }, [state.token, state.user?.role]);

  if (state.user?.role !== "admin") return <PermissionDeniedState message="System health requires an admin account." />;

  return (
    <section className="page-stack">
      <article className="surface-card page-header"><div><div className="eyebrow">Operations</div><h2 className="surface-title">System health</h2></div><button className="button button-secondary" onClick={() => void load()} type="button">Refresh</button></article>
      {status === "loading" ? <PageSkeleton title="Checking system health" /> : null}
      {status === "error" ? <InlineAlert title="Health unavailable" message="Unable to load system health." /> : null}
      {report ? <article className="surface-card"><JsonPanel data={report} /></article> : null}
    </section>
  );
}

export function AdminProviderHealthPage() {
  const { state } = useAuth();
  const [report, setReport] = useState<unknown>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");

  const load = async () => {
    if (!state.token) return;
    setStatus("loading");
    try {
      setReport(await getProviderHealth(state.token));
      setStatus("ready");
    } catch {
      setStatus("error");
    }
  };

  useEffect(() => {
    if (state.user?.role === "admin") void load();
  }, [state.token, state.user?.role]);

  if (state.user?.role !== "admin") return <PermissionDeniedState message="Provider health requires an admin account." />;

  return (
    <section className="page-stack">
      <article className="surface-card page-header"><div><div className="eyebrow">Operations</div><h2 className="surface-title">Provider health</h2></div><button className="button button-secondary" onClick={() => void load()} type="button">Refresh</button></article>
      {status === "loading" ? <PageSkeleton title="Checking providers" /> : null}
      {status === "error" ? <InlineAlert title="Provider health unavailable" message="Unable to load provider health." /> : null}
      {report ? <article className="surface-card"><JsonPanel data={report} /></article> : null}
    </section>
  );
}
