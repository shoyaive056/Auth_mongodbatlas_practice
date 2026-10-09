// Client-side checks give fast feedback. The backend repeats every check,
// because the browser can never be trusted.
export const validateEmail = (value) =>
  /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value) ? "" : "Enter a valid email address";

export const validatePassword = (value) => {
  if (value.length < 8) return "At least 8 characters";
  if (!/[a-z]/.test(value)) return "Add a lowercase letter";
  if (!/[A-Z]/.test(value)) return "Add an uppercase letter";
  if (!/\d/.test(value)) return "Add a number";
  return "";
};

export const validateUsername = (value) =>
  /^[A-Za-z0-9_]{3,30}$/.test(value) ? "" : "3-30 characters: letters, numbers, underscores";

export const validateRequired = (value) => (value.trim() ? "" : "This field is required");

export const validateMatch = (value, other) => (value === other ? "" : "Passwords do not match");

export const PASSWORD_HINT = "At least 8 characters with an uppercase letter, a lowercase letter and a number";

/** Run a {field: validatorFn} map; returns {field: message} for failing fields. */
export function runValidation(values, rules) {
  const errors = {};
  for (const [field, rule] of Object.entries(rules)) {
    const message = rule(values[field] ?? "", values);
    if (message) errors[field] = message;
  }
  return errors;
}
