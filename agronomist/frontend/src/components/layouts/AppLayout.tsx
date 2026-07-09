import { Link, NavLink, Outlet } from "react-router-dom";

import { useAuth } from "../../auth/auth-store";
import { API_BASE_URL } from "../../lib/api/client";
import { useTheme } from "../ui/ThemeProvider";

export function AppLayout() {
  const { state, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();

  return (
    <div className="app-shell">
      <aside className="app-sidebar">
        <div>
          <Link className="brand-link" to="/app">
            AI Agronomist
          </Link>
          <div className="sidebar-caption">Operations workspace</div>
        </div>

        <nav className="sidebar-nav">
          <NavLink
            className={({ isActive }) =>
              isActive ? "sidebar-link sidebar-link-active" : "sidebar-link"
            }
            to="/app"
            end
          >
            Dashboard
          </NavLink>
          <NavLink
            className={({ isActive }) =>
              isActive ? "sidebar-link sidebar-link-active" : "sidebar-link"
            }
            to="/app/farms"
          >
            Farms
          </NavLink>
          <NavLink
            className={({ isActive }) =>
              isActive ? "sidebar-link sidebar-link-active" : "sidebar-link"
            }
            to="/app/chat"
          >
            AI Chat
          </NavLink>
          <NavLink
            className={({ isActive }) =>
              isActive ? "sidebar-link sidebar-link-active" : "sidebar-link"
            }
            to="/app/notifications"
          >
            Notifications
          </NavLink>
          <NavLink
            className={({ isActive }) =>
              isActive ? "sidebar-link sidebar-link-active" : "sidebar-link"
            }
            to="/app/knowledge"
          >
            Knowledge
          </NavLink>
          <NavLink
            className={({ isActive }) =>
              isActive ? "sidebar-link sidebar-link-active" : "sidebar-link"
            }
            to="/app/escalations"
          >
            Escalations
          </NavLink>
        </nav>

        <div className="sidebar-footer">
          <div className="meta-label">API</div>
          <div className="meta-value">{API_BASE_URL}</div>
        </div>
      </aside>

      <main className="app-main">
        <header className="topbar">
          <div>
            <div className="eyebrow">Authenticated shell</div>
            <div className="topbar-title">Operations dashboard</div>
          </div>
          <div className="topbar-actions">
            <button className="button button-secondary" onClick={toggleTheme}>
              Theme: {theme}
            </button>
            <button className="button button-ghost" onClick={logout}>
              Sign out
            </button>
          </div>
        </header>

        <section className="content-shell">
          <div className="status-card">
            <div className="status-card-title">
              {state.user?.full_name || state.user?.email || "Authenticated user"}
            </div>
            <div className="status-card-meta">
              Role: {state.user?.role || "unknown"} | Language:{" "}
              {state.user?.preferred_language || "en"}
            </div>
          </div>
          <Outlet />
        </section>
      </main>
    </div>
  );
}
