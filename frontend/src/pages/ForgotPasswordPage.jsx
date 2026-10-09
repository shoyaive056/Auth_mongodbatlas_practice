import { useState } from "react";
import { Link } from "react-router-dom";
import { ErrorMessage, SuccessMessage } from "../components/Alert.jsx";
import FormField from "../components/FormField.jsx";
import { getErrorMessage } from "../services/api.js";
import { authService } from "../services/authService.js";
import { validateEmail } from "../utils/validators.js";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [fieldError, setFieldError] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setSuccess("");
    const problem = validateEmail(email);
    setFieldError(problem);
    if (problem) return;

    setSubmitting(true);
    try {
      const res = await authService.forgotPassword(email.trim());
      setSuccess(res.message);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="card narrow">
      <h1>Forgot password</h1>
      <p className="subtitle">We will email you a reset link</p>
      <ErrorMessage message={error} />
      <SuccessMessage message={success} />
      <form onSubmit={handleSubmit} noValidate>
        <FormField label="Email" name="email" type="email" value={email}
          onChange={(e) => setEmail(e.target.value)} error={fieldError} />
        <button className="btn block" type="submit" disabled={submitting}>
          {submitting ? "Sending..." : "Send reset link"}
        </button>
      </form>
      <div className="links">
        <Link to="/login">Back to log in</Link>
      </div>
    </div>
  );
}
