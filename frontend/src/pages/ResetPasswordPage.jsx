import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { ErrorMessage, SuccessMessage } from "../components/Alert.jsx";
import FormField from "../components/FormField.jsx";
import { getErrorMessage } from "../services/api.js";
import { authService } from "../services/authService.js";
import { PASSWORD_HINT, runValidation, validateMatch, validatePassword } from "../utils/validators.js";

export default function ResetPasswordPage() {
  const [params] = useSearchParams();
  const token = params.get("token");
  const [form, setForm] = useState({ new_password: "", confirm_password: "" });
  const [fieldErrors, setFieldErrors] = useState({});
  const [error, setError] = useState(token ? "" : "This reset link is missing its token.");
  const [success, setSuccess] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleChange = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    const errors = runValidation(form, {
      new_password: validatePassword,
      confirm_password: (value, all) => validateMatch(value, all.new_password),
    });
    setFieldErrors(errors);
    if (!token || Object.keys(errors).length) return;

    setSubmitting(true);
    try {
      const res = await authService.resetPassword({ token, ...form });
      setSuccess(res.message);
      setForm({ new_password: "", confirm_password: "" });
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="card narrow">
      <h1>Reset password</h1>
      <p className="subtitle">Choose a new password</p>
      <ErrorMessage message={error} />
      <SuccessMessage message={success} />
      {!success && (
        <form onSubmit={handleSubmit} noValidate>
          <FormField label="New password" name="new_password" type="password" autoComplete="new-password"
            value={form.new_password} onChange={handleChange} error={fieldErrors.new_password} hint={PASSWORD_HINT} />
          <FormField label="Confirm new password" name="confirm_password" type="password" autoComplete="new-password"
            value={form.confirm_password} onChange={handleChange} error={fieldErrors.confirm_password} />
          <button className="btn block" type="submit" disabled={submitting || !token}>
            {submitting ? "Saving..." : "Reset password"}
          </button>
        </form>
      )}
      <div className="links">
        <Link to="/login">Back to log in</Link>
        <Link to="/forgot-password">Request a new link</Link>
      </div>
    </div>
  );
}
