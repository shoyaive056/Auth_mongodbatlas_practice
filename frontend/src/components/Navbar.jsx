import { Link, useNavigate } from "react-router-dom";
import useAuth from "../hooks/useAuth.js";

export default function Navbar() {
  const { user, isAuthenticated, isAdmin, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  return (
    <nav className="navbar">
      <div className="navbar-inner">
        <Link to="/" className="brand">
          🔐 Auth Practice
        </Link>
        <div className="nav-links">
          {isAuthenticated ? (
            <>
              <Link to="/dashboard">Dashboard</Link>
              <Link to="/profile">Profile</Link>
              <Link to="/change-password">Password</Link>
              {isAdmin && <Link to="/admin/users">Admin</Link>}
              <span style={{ color: "var(--muted)" }}>{user.username}</span>
              <button className="btn small secondary" onClick={handleLogout}>
                Log out
              </button>
            </>
          ) : (
            <>
              <Link to="/login">Log in</Link>
              <Link to="/register">Register</Link>
            </>
          )}
        </div>
      </div>
    </nav>
  );
}
