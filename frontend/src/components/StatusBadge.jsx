export default function StatusBadge({ ok, label }) {
  return (
    <span className={`status-badge ${ok ? "ok" : "bad"}`}>
      <span className="dot" />
      {label || (ok ? "Online" : "Offline")}
    </span>
  );
}
