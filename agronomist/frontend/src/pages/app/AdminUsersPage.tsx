import { useEffect, useState } from "react";

import { useAuth } from "../../auth/auth-store";
import { EmptyState, InlineAlert, PageSkeleton, PermissionDeniedState } from "../../components/ui/Feedback";
import { listAdminUsers } from "../../lib/api/admin";
import type { UserProfile } from "../../lib/api/account";

export function AdminUsersPage() {
  const { state } = useAuth();
  const [users, setUsers] = useState<UserProfile[]>([]);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");

  useEffect(() => {
    if (state.user?.role !== "admin" || !state.token) {
      return;
    }
    let cancelled = false;
    const load = async () => {
      setStatus("loading");
      try {
        const response = await listAdminUsers(state.token!);
        if (!cancelled) {
          setUsers(response);
          setStatus("ready");
        }
      } catch {
        if (!cancelled) {
          setStatus("error");
        }
      }
    };
    void load();
    return () => {
      cancelled = true;
    };
  }, [state.token, state.user?.role]);

  if (state.user?.role !== "admin") {
    return <PermissionDeniedState message="User management requires an admin account." />;
  }

  return (
    <section className="page-stack">
      <article className="surface-card page-header">
        <div><div className="eyebrow">Management</div><h2 className="surface-title">Users</h2></div>
      </article>
      {status === "loading" ? <PageSkeleton title="Loading users" /> : null}
      {status === "error" ? <InlineAlert title="Users unavailable" message="Unable to load users right now." action={<button className="button button-primary" onClick={() => window.location.reload()} type="button">Retry</button>} /> : null}
      {status === "ready" && !users.length ? <EmptyState title="No users found." message="Users will appear here after accounts are created." /> : null}
      {users.length ? (
        <article className="surface-card">
          <div className="list-stack">
            {users.map((user) => (
              <div className="list-item" key={user.id}>
                <div>
                  <div className="list-title">{user.full_name || user.email || user.id}</div>
                  <div className="list-meta">{user.email || "No email"} | {user.phone_number || "No phone"}</div>
                </div>
                <div className="pill">{user.role}</div>
              </div>
            ))}
          </div>
        </article>
      ) : null}
    </section>
  );
}
