import { useState } from "react";
import { ErrorMessage, SuccessMessage } from "../components/Alert.jsx";
import FormField from "../components/FormField.jsx";
import { getErrorMessage } from "../services/api.js";
import { userService } from "../services/authService.js";
import {
  PASSWORD_HINT, runValidation, validateMatch, validatePassword, validateRequired,
} from "../utils/validators.js";

const EMPTY = { current_password: "", new_password: "", confirm_password: "" };

export default function ChangePasswordPage() {
  const [form, setForm] = useState(EMPTY);
  const [fieldErrors, setFieldErrors] = useState({});
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleChange = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setSuccess("");
    const errors = runValidation(form, {
      current_password: validateRequired,
      new_password: validatePassword,
      confirm_password: (value, all) => validateMatch(value, all.new_password),
    });
    setFieldErrors(errors);
    if (Object.keys(errors).length) return;

    setSubmitting(true);
    try {
      const res = await userService.changePassword(form);
      setSuccess(res.message);
      setForm(EMPTY);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="card narrow">
      <h1>Change password</h1>
      <p className="subtitle">Other devices will be logged out</p>
      <ErrorMessage message={error} />
      <SuccessMessage message={success} />
      <form onSubmit={handleSubmit} noValidate>
        <FormField label="Current password" name="current_password" type="password" autoComplete="current-password"
          value={form.current_password} onChange={handleChange} error={fieldErrors.current_password} />
        <FormField label="New password" name="new_password" type="password" autoComplete="new-password"
          value={form.new_password} onChange={handleChange} error={fieldErrors.new_password} hint={PASSWORD_HINT} />
        <FormField label="Confirm new password" name="confirm_password" type="password" autoComplete="new-password"
          value={form.confirm_password} onChange={handleChange} error={fieldErrors.confirm_password} />
        <button className="btn block" type="submit" disabled={submitting}>
          {submitting ? "Saving..." : "Change password"}
        </button>
      </form>
    </div>
  );
}
