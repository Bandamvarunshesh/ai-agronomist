import { Navigate } from "react-router-dom";

import { useAuth } from "../../auth/auth-store";
import { FullPageLoader } from "../../components/ui/Feedback";

export function RootRedirect() {
  const { state } = useAuth();

  if (state.status === "checking") {
    return (
      <FullPageLoader
        title="Preparing application"
        message="Loading your workspace foundation."
      />
    );
  }

  if (state.status === "authenticated") {
    return <Navigate to={state.user?.role === "admin" ? "/app/admin" : "/app"} replace />;
  }

  return <Navigate to="/login" replace />;
}
