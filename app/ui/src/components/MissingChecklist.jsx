export default function MissingChecklist({ items }) {
  if (!items || items.length === 0) {
    return <div className="hint">Nothing missing — evidence is complete.</div>;
  }
  return (
    <ul className="missing-list">
      {items.map((m, i) => (
        <li key={i}>{m}</li>
      ))}
    </ul>
  );
}
