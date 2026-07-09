import { Link, Outlet } from "react-router-dom";

import { useTheme } from "../ui/ThemeProvider";

export function AuthLayout() {
  const { theme, toggleTheme } = useTheme();

  return (
    <div className="auth-shell">
      <section className="auth-hero">
        <div className="eyebrow">AI Agronomist</div>
        <h1 className="hero-title">Field operations, grounded in real backend data.</h1>
        <p className="hero-copy">
          This foundation is wired for live authentication, protected routes, and
          backend-aware state from the first render.
        </p>
        <div className="theme-toggle-row">
          <button className="button button-ghost" onClick={toggleTheme}>
            Theme: {theme}
          </button>
        </div>
      </section>
      <section className="auth-panel">
        <div className="auth-card">
          <div className="auth-card-header">
            <Link className="brand-link" to="/">
              AI Agronomist
            </Link>
          </div>
          <Outlet />
        </div>
      </section>
    </div>
  );
}
