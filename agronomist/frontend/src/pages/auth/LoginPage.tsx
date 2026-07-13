import { FormEvent, useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../../auth/auth-store";
import { InlineAlert } from "../../components/ui/Feedback";
import { useToast } from "../../components/ui/ToastProvider";

function useRedirectTarget() {
  const location = useLocation();
  const params = new URLSearchParams(location.search);
  return params.get("redirect") || "/app";
}

export function LoginPage() {
  const { state, login, clearError } = useAuth();
  const { pushToast } = useToast();
  const navigate = useNavigate();
  const redirectTarget = useRedirectTarget();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  useEffect(() => {
    if (state.status === "authenticated") {
      if (!state.user) {
        return;
      }
      const navigationStartedAt = performance.now();
      const target =
        redirectTarget === "/app" && state.user.role === "admin"
          ? "/app/admin"
          : redirectTarget;
      navigate(target, { replace: true });
      if (import.meta.env.DEV) {
        console.info("[auth] dashboard navigation", {
          elapsedMs: Math.round(performance.now() - navigationStartedAt),
          target,
        });
      }
    }
  }, [navigate, redirectTarget, state.status, state.user]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    clearError();

    try {
      await login({ email, password });
      pushToast({
        title: "Signed in",
        message: "Your backend session is ready.",
        tone: "success",
      });
    } catch (error) {
      pushToast({
        title: "Sign-in failed",
        message:
          error instanceof Error ? error.message : "Unable to sign in right now.",
        tone: "error",
      });
    }
  };

  return (
    <div className="form-stack">
      <div>
        <h2 className="section-title">Sign in</h2>
        <p className="section-copy">
          Use your real backend credentials to enter the app shell.
        </p>
      </div>

      {state.error ? (
        <InlineAlert
          title="Authentication error"
          message={state.error}
        />
      ) : null}

      {state.notice ? (
        <InlineAlert
          title="Server is starting"
          message={state.notice}
          tone="info"
        />
      ) : null}

      <form className="form-stack" onSubmit={handleSubmit}>
        <label className="field">
          <span className="field-label">Email</span>
          <input
            className="input"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
          />
        </label>

        <label className="field">
          <span className="field-label">Password</span>
          <input
            className="input"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />
        </label>

        <button
          className="button button-primary button-block"
          disabled={state.isSubmitting}
          type="submit"
        >
          {state.isSubmitting ? "Signing in..." : "Sign in"}
        </button>
      </form>

      <div className="footer-copy">
        Need an account? <Link to="/signup">Create one</Link>
      </div>
    </div>
  );
}
