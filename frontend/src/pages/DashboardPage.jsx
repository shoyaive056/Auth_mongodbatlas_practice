import { Link } from "react-router-dom";
import useAuth from "../hooks/useAuth.js";

export default function DashboardPage() {
  const { user, isAdmin } = useAuth();
  return (
    <div className="card">
      <h1>Hello, {user.first_name} 👋</h1>
      <p className="subtitle">You are logged in. This page is protected.</p>
      <dl className="details">
        <dt>Email</dt>
        <dd>{user.email}</dd>
        <dt>Role</dt>
        <dd><span className={`badge ${isAdmin ? "purple" : ""}`}>{user.role}</span></dd>
        <dt>Email verified</dt>
        <dd>{user.is_verified ? "Yes" : "No"}</dd>
        <dt>Last login</dt>
        <dd>{user.last_login ? new Date(user.last_login).toLocaleString() : "—"}</dd>
      </dl>
      <p style={{ marginTop: 20 }}>
        <Link to="/profile" className="btn small">Edit profile</Link>{" "}
        {isAdmin && <Link to="/admin/users" className="btn small secondary">Manage users</Link>}
      </p>
    </div>
  );
}
