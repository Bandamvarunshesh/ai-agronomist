import { Navigate, Outlet, useLocation } from "react-router-dom";

import { useAuth } from "../../auth/auth-store";
import { FullPageLoader, InlineAlert } from "../ui/Feedback";

export function ProtectedRoute() {
  const { state, retrySession, logout } = useAuth();
  const location = useLocation();

  if (state.status === "checking") {
    return (
      <FullPageLoader
        title="Restoring workspace"
        message="Checking your session with the backend."
      />
    );
  }

  if (state.status === "error") {
    return (
      <div className="route-shell">
        <InlineAlert
          title="Session check failed"
          message={state.error || "Unable to reach the backend right now."}
          action={
            <div className="button-row">
              <button className="button button-primary" onClick={() => void retrySession()}>
                Retry
              </button>
              <button className="button button-secondary" onClick={logout}>
                Clear session
              </button>
            </div>
          }
        />
      </div>
    );
  }

  if (state.status !== "authenticated") {
    const redirectPath = `${location.pathname}${location.search}`;
    return <Navigate to={`/login?redirect=${encodeURIComponent(redirectPath)}`} replace />;
  }

  return <Outlet />;
}
