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

  return <Navigate to={state.status === "authenticated" ? "/app" : "/login"} replace />;
}
