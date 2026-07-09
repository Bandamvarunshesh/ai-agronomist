import { Navigate, Outlet } from "react-router-dom";

import { useAuth } from "../../auth/auth-store";
import { FullPageLoader } from "../ui/Feedback";

export function GuestOnlyRoute() {
  const { state } = useAuth();

  if (state.status === "checking") {
    return (
      <FullPageLoader
        title="Preparing sign-in"
        message="Connecting to the backend session state."
      />
    );
  }

  if (state.status === "authenticated") {
    return <Navigate to="/app" replace />;
  }

  return <Outlet />;
}
