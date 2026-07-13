import { Link } from "react-router-dom";

import { useAuth } from "../../auth/auth-store";
import { PermissionDeniedState } from "../../components/ui/Feedback";

export function AdminDashboardPage() {
  const { state } = useAuth();

  if (state.user?.role !== "admin") {
    return <PermissionDeniedState message="Admin dashboard requires an admin account." />;
  }

  return (
    <section className="page-stack">
      <article className="surface-card page-header">
        <div>
          <div className="eyebrow">Admin</div>
          <h2 className="surface-title">Admin dashboard</h2>
          <p className="surface-copy">Manage users, trusted knowledge, intelligence sources, contacts, and platform health.</p>
        </div>
      </article>
      <section className="action-grid">
        <Link className="surface-card button-link" to="/app/admin/users">Users</Link>
        <Link className="surface-card button-link" to="/app/admin/knowledge">Knowledge Documents</Link>
        <Link className="surface-card button-link" to="/app/admin/intelligence-sources">Intelligence Sources</Link>
        <Link className="surface-card button-link" to="/app/admin/escalation-contacts">Escalation Contacts</Link>
        <Link className="surface-card button-link" to="/app/admin/escalations">Escalations</Link>
        <Link className="surface-card button-link" to="/app/admin/system-health">System Health</Link>
      </section>
    </section>
  );
}
