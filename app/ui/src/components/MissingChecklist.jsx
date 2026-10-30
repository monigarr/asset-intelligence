// Missing information as high-visibility tape chips (DESIGN.md C.2).
export default function MissingChecklist({ items }) {
  if (!items || items.length === 0) {
    return <div className="hint">Nothing missing - evidence is complete.</div>;
  }
  return (
    <div className="missing-chips">
      {items.map((m, i) => (
        <span className="missing-chip" key={i}>
          Missing: {m}
        </span>
      ))}
    </div>
  );
}