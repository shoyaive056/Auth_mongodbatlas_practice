import { Navigate, Outlet, useLocation } from "react-router-dom";
import Loading from "../components/Loading.jsx";
import useAuth from "../hooks/useAuth.js";

// Wrap routes that need a logged-in user. This only improves the UX:
// the backend is what really enforces access.
export default function ProtectedRoute() {
  const { isAuthenticated, loading } = useAuth();
  const location = useLocation();

  if (loading) return <Loading />;
  if (!isAuthenticated) return <Navigate to="/login" replace state={{ from: location }} />;
  return <Outlet />;
}
