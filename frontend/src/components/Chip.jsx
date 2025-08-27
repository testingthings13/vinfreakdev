export default function Chip({ label, onClear }) {
  return (
    <span className="chip">
      {label}
      {onClear && <button className="chip-x" onClick={onClear} aria-label="Clear">×</button>}
    </span>
  );
}
