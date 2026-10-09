export default function FormField({ label, name, type = "text", value, onChange, error, hint, ...rest }) {
  return (
    <div className="field">
      <label htmlFor={name}>{label}</label>
      <input id={name} name={name} type={type} value={value} onChange={onChange} {...rest} />
      {hint && !error && <div className="hint">{hint}</div>}
      {error && <div className="error">{error}</div>}
    </div>
  );
}
