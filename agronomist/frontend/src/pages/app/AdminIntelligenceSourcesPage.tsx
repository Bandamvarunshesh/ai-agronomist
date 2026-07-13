import { useEffect, useState } from "react";

import { useAuth } from "../../auth/auth-store";
import { EmptyState, InlineAlert, PageSkeleton, PermissionDeniedState } from "../../components/ui/Feedback";
import { listIntelligenceSources, syncIntelligenceSources, type IntelligenceSource } from "../../lib/api/admin";
import { useToast } from "../../components/ui/ToastProvider";

export function AdminIntelligenceSourcesPage() {
  const { state } = useAuth();
  const { pushToast } = useToast();
  const [sources, setSources] = useState<IntelligenceSource[]>([]);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [syncing, setSyncing] = useState(false);

  const load = async () => {
    if (!state.token) return;
    setStatus("loading");
    try {
      setSources(await listIntelligenceSources(state.token));
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
    return <PermissionDeniedState message="Intelligence source management requires an admin account." />;
  }

  const handleDryRunSync = async () => {
    if (!state.token) return;
    setSyncing(true);
    try {
      await syncIntelligenceSources(state.token, true);
      pushToast({ title: "Dry run complete", message: "Source sync validation completed.", tone: "success" });
      await load();
    } catch {
      pushToast({ title: "Sync unavailable", message: "Unable to validate intelligence sources right now.", tone: "error" });
    } finally {
      setSyncing(false);
    }
  };

  return (
    <section className="page-stack">
      <article className="surface-card page-header">
        <div><div className="eyebrow">Management</div><h2 className="surface-title">Intelligence sources</h2></div>
        <button className="button button-secondary" disabled={syncing} onClick={() => void handleDryRunSync()} type="button">{syncing ? "Validating..." : "Dry-run sync"}</button>
      </article>
      {status === "loading" ? <PageSkeleton title="Loading sources" /> : null}
      {status === "error" ? <InlineAlert title="Sources unavailable" message="Unable to load intelligence sources." action={<button className="button button-primary" onClick={() => void load()} type="button">Retry</button>} /> : null}
      {status === "ready" && !sources.length ? <EmptyState title="No intelligence sources configured." message="Load trusted source configuration from the backend admin flow before syncing." /> : null}
      {sources.length ? (
        <article className="surface-card">
          <div className="list-stack">
            {sources.map((source) => (
              <div className="list-item list-item-block" key={source.id}>
                <div className="list-row"><div className="list-title">{source.name}</div><div className={source.is_active ? "pill pill-strong" : "pill"}>{source.is_active ? "Active" : "Inactive"}</div></div>
                <div className="list-meta">{source.source_type} | {source.source_format} | {source.language}</div>
                <p className="list-body">{source.url}</p>
              </div>
            ))}
          </div>
        </article>
      ) : null}
    </section>
  );
}
