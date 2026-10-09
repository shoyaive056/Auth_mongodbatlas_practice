import { useCallback, useEffect, useState } from "react";
import { ErrorMessage, SuccessMessage } from "../components/Alert.jsx";
import Loading from "../components/Loading.jsx";
import useAuth from "../hooks/useAuth.js";
import { getErrorMessage } from "../services/api.js";
import { adminService } from "../services/authService.js";

const PAGE_SIZE = 10;

export default function AdminUsersPage() {
  const { user: me } = useAuth();
  const [data, setData] = useState({ items: [], total: 0 });
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setData(await adminService.listUsers(page, PAGE_SIZE));
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [page]);

  useEffect(() => {
    load();
  }, [load]);

  const runAction = async (action, successText) => {
    setError("");
    setNotice("");
    try {
      await action();
      setNotice(successText);
      await load();
    } catch (err) {
      setError(getErrorMessage(err));
    }
  };

  const totalPages = Math.max(1, Math.ceil(data.total / PAGE_SIZE));

  return (
    <div className="card">
      <h1>Users</h1>
      <p className="subtitle">{data.total} registered</p>
      <ErrorMessage message={error} />
      <SuccessMessage message={notice} />
      {loading ? (
        <Loading />
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Username</th><th>Email</th><th>Role</th><th>Verified</th><th>Status</th><th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((u) => {
                const isMe = u.id === me.id;
                return (
                  <tr key={u.id}>
                    <td>{u.username}{isMe && " (you)"}</td>
                    <td>{u.email}</td>
                    <td><span className={`badge ${u.role === "admin" ? "purple" : ""}`}>{u.role}</span></td>
                    <td>{u.is_verified ? "Yes" : "No"}</td>
                    <td><span className={`badge ${u.is_active ? "green" : "red"}`}>{u.is_active ? "Active" : "Inactive"}</span></td>
                    <td>
                      <div className="actions">
                        {u.is_active ? (
                          <button className="btn small danger" disabled={isMe}
                            onClick={() => runAction(() => adminService.deactivate(u.id), `${u.username} deactivated.`)}>
                            Deactivate
                          </button>
                        ) : (
                          <button className="btn small"
                            onClick={() => runAction(() => adminService.activate(u.id), `${u.username} activated.`)}>
                            Activate
                          </button>
                        )}
                        <button className="btn small secondary" disabled={isMe}
                          onClick={() => runAction(
                            () => adminService.setRole(u.id, u.role === "admin" ? "user" : "admin"),
                            `${u.username}'s role updated.`
                          )}>
                          Make {u.role === "admin" ? "user" : "admin"}
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
      <div className="pager">
        <button className="btn small secondary" disabled={page <= 1} onClick={() => setPage(page - 1)}>Previous</button>
        <span>Page {page} of {totalPages}</span>
        <button className="btn small secondary" disabled={page >= totalPages} onClick={() => setPage(page + 1)}>Next</button>
      </div>
    </div>
  );
}
