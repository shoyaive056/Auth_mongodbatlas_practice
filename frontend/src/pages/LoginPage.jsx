import { useState } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { ErrorMessage, SuccessMessage } from "../components/Alert.jsx";
import FormField from "../components/FormField.jsx";
import useAuth from "../hooks/useAuth.js";
import { getErrorCode, getErrorMessage } from "../services/api.js";
import { authService } from "../services/authService.js";
import { runValidation, validateEmail, validateRequired } from "../utils/validators.js";

export default function LoginPage() {
  const { login, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const redirectTo = location.state?.from?.pathname || "/dashboard";

  const [form, setForm] = useState({ email: "", password: "" });
  const [fieldErrors, setFieldErrors] = useState({});
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [needsVerification, setNeedsVerification] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  if (isAuthenticated) return <Navigate to={redirectTo} replace />;

  const handleChange = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setNotice("");
    setNeedsVerification(false);
    const errors = runValidation(form, { email: validateEmail, password: validateRequired });
    setFieldErrors(errors);
    if (Object.keys(errors).length) return;

    setSubmitting(true);
    try {
      await login(form.email.trim(), form.password);
      navigate(redirectTo, { replace: true });
    } catch (err) {
      setError(getErrorMessage(err));
      setNeedsVerification(getErrorCode(err) === "EMAIL_NOT_VERIFIED");
    } finally {
      setSubmitting(false);
    }
  };

  const handleResend = async () => {
    try {
      const res = await authService.resendVerification(form.email.trim());
      setNotice(res.message);
    } catch (err) {
      setError(getErrorMessage(err));
    }
  };

  return (
    <div className="card narrow">
      <h1>Welcome back</h1>
      <p className="subtitle">Log in to your account</p>
      <ErrorMessage message={error} />
      <SuccessMessage message={notice} />
      {needsVerification && (
        <p>
          <button type="button" className="link-button" onClick={handleResend}>
            Resend verification email
          </button>
        </p>
      )}
      <form onSubmit={handleSubmit} noValidate>
        <FormField label="Email" name="email" type="email" autoComplete="email"
          value={form.email} onChange={handleChange} error={fieldErrors.email} />
        <FormField label="Password" name="password" type="password" autoComplete="current-password"
          value={form.password} onChange={handleChange} error={fieldErrors.password} />
        <button className="btn block" type="submit" disabled={submitting}>
          {submitting ? "Logging in..." : "Log in"}
        </button>
      </form>
      <div className="links">
        <Link to="/forgot-password">Forgot password?</Link>
        <Link to="/register">Create account</Link>
      </div>
    </div>
  );
}
