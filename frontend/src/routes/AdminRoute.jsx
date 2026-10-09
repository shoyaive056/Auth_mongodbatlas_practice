import { Navigate, Outlet } from "react-router-dom";
import useAuth from "../hooks/useAuth.js";

// Must be nested inside <ProtectedRoute>. Non-admins are sent to the dashboard.
// Even if someone bypasses this check, every /admin API call is rejected by the backend.
export default function AdminRoute() {
  const { isAdmin } = useAuth();
  return isAdmin ? <Outlet /> : <Navigate to="/dashboard" replace />;
}
