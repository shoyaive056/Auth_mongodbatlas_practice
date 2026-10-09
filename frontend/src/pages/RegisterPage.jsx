import { useState } from "react";
import { Link } from "react-router-dom";
import { ErrorMessage, SuccessMessage } from "../components/Alert.jsx";
import FormField from "../components/FormField.jsx";
import { getErrorMessage } from "../services/api.js";
import { authService } from "../services/authService.js";
import {
  PASSWORD_HINT, runValidation, validateEmail, validateMatch,
  validatePassword, validateRequired, validateUsername,
} from "../utils/validators.js";

const EMPTY = { first_name: "", last_name: "", username: "", email: "", password: "", confirm_password: "" };

export default function RegisterPage() {
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
      first_name: validateRequired,
      last_name: validateRequired,
      username: validateUsername,
      email: validateEmail,
      password: validatePassword,
      confirm_password: (value, all) => validateMatch(value, all.password),
    });
    setFieldErrors(errors);
    if (Object.keys(errors).length) return;

    setSubmitting(true);
    try {
      const res = await authService.register({ ...form, email: form.email.trim(), username: form.username.trim() });
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
      <h1>Create account</h1>
      <p className="subtitle">Sign up to get started</p>
      <ErrorMessage message={error} />
      <SuccessMessage message={success} />
      <form onSubmit={handleSubmit} noValidate>
        <div className="row">
          <FormField label="First name" name="first_name" value={form.first_name}
            onChange={handleChange} error={fieldErrors.first_name} />
          <FormField label="Last name" name="last_name" value={form.last_name}
            onChange={handleChange} error={fieldErrors.last_name} />
        </div>
        <FormField label="Username" name="username" autoComplete="username" value={form.username}
          onChange={handleChange} error={fieldErrors.username} />
        <FormField label="Email" name="email" type="email" autoComplete="email" value={form.email}
          onChange={handleChange} error={fieldErrors.email} />
        <FormField label="Password" name="password" type="password" autoComplete="new-password"
          value={form.password} onChange={handleChange} error={fieldErrors.password} hint={PASSWORD_HINT} />
        <FormField label="Confirm password" name="confirm_password" type="password" autoComplete="new-password"
          value={form.confirm_password} onChange={handleChange} error={fieldErrors.confirm_password} />
        <button className="btn block" type="submit" disabled={submitting}>
          {submitting ? "Creating account..." : "Register"}
        </button>
      </form>
      <div className="links">
        <span>Already registered?</span>
        <Link to="/login">Log in</Link>
      </div>
    </div>
  );
}
