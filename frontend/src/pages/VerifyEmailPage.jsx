import { useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { ErrorMessage, SuccessMessage } from "../components/Alert.jsx";
import Loading from "../components/Loading.jsx";
import { getErrorMessage } from "../services/api.js";
import { authService } from "../services/authService.js";

export default function VerifyEmailPage() {
  const [params] = useSearchParams();
  const token = params.get("token");
  const [status, setStatus] = useState(token ? "loading" : "error");
  const [message, setMessage] = useState(token ? "" : "This verification link is missing its token.");
  const calledRef = useRef(false); // tokens are single-use: React StrictMode must not call twice

  useEffect(() => {
    if (!token || calledRef.current) return;
    calledRef.current = true;
    authService
      .verifyEmail(token)
      .then((res) => {
        setStatus("success");
        setMessage(res.message);
      })
      .catch((err) => {
        setStatus("error");
        setMessage(getErrorMessage(err));
      });
  }, [token]);

  return (
    <div className="card narrow">
      <h1>Email verification</h1>
      {status === "loading" && <Loading text="Verifying your email..." />}
      {status === "success" && <SuccessMessage message={message} />}
      {status === "error" && <ErrorMessage message={message} />}
      {status !== "loading" && (
        <p>
          <Link to="/login">Go to log in</Link>
        </p>
      )}
    </div>
  );
}
