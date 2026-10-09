export default function Loading({ text = "Loading..." }) {
  return (
    <div className="loading" role="status">
      <div className="spinner" />
      <span>{text}</span>
    </div>
  );
}
