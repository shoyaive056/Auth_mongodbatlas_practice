export function ErrorMessage({ message }) {
  if (!message) return null;
  return (
    <div className="alert error" role="alert">
      {message}
    </div>
  );
}

export function SuccessMessage({ message }) {
  if (!message) return null;
  return (
    <div className="alert success" role="status">
      {message}
    </div>
  );
}
