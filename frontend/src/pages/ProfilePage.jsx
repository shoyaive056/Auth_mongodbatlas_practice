import { useState } from "react";
import { ErrorMessage, SuccessMessage } from "../components/Alert.jsx";
import FormField from "../components/FormField.jsx";
import useAuth from "../hooks/useAuth.js";
import { getErrorMessage } from "../services/api.js";
import { userService } from "../services/authService.js";
import { runValidation, validateRequired, validateUsername } from "../utils/validators.js";

export default function ProfilePage() {
  const { user, setUser } = useAuth();
  const [form, setForm] = useState({
    first_name: user.first_name,
    last_name: user.last_name,
    username: user.username,
  });
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
    });
    setFieldErrors(errors);
    if (Object.keys(errors).length) return;

    setSubmitting(true);
    try {
      const updated = await userService.updateMe(form);
      setUser(updated);
      setSuccess("Profile updated.");
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="card narrow">
      <h1>Your profile</h1>
      <p className="subtitle">{user.email}</p>
      <ErrorMessage message={error} />
      <SuccessMessage message={success} />
      <form onSubmit={handleSubmit} noValidate>
        <div className="row">
          <FormField label="First name" name="first_name" value={form.first_name}
            onChange={handleChange} error={fieldErrors.first_name} />
          <FormField label="Last name" name="last_name" value={form.last_name}
            onChange={handleChange} error={fieldErrors.last_name} />
        </div>
        <FormField label="Username" name="username" value={form.username}
          onChange={handleChange} error={fieldErrors.username} />
        <button className="btn block" type="submit" disabled={submitting}>
          {submitting ? "Saving..." : "Save changes"}
        </button>
      </form>
    </div>
  );
}
