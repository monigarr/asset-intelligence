function EvidenceChip({ ev, active, onClick }) {
  const label =
    ev.source === 'maintenance_note'
      ? `note [${ev.span ? ev.span.join(':') : '?'}]`
      : `${ev.source}${ev.mask_id ? ` · ${ev.mask_id}` : ''}`;
  return (
    <button className={`chip${active ? ' active' : ''}`} onClick={onClick} title="Highlight evidence">
      {label}
    </button>
  );
}

function NoteView({ note, span }) {
  if (!span) return <div className="note-view">{note}</div>;
  const [start, end] = span;
  return (
    <div className="note-view">
      {note.slice(0, start)}
      <mark>{note.slice(start, end)}</mark>
      {note.slice(end)}
    </div>
  );
}

export default function JsonViewer({
  result,
  note,
  selectedMaskId,
  selectedSpan,
  onEvidenceClick,
}) {
  const trace = result.model_trace || {};
  return (
    <div>
      <h3>Field note</h3>
      <NoteView note={note} span={selectedSpan} />
      <h3>Observations ({result.observations.length})</h3>
      {result.observations.map((ob, i) => (
        <div className="obs" key={i}>
          <p>{ob.text}</p>
          <div className="evidence-chips">
            {ob.evidence.map((ev, j) => {
              const active =
                (ev.mask_id && ev.mask_id === selectedMaskId) ||
                (ev.span &&
                  selectedSpan &&
                  ev.span[0] === selectedSpan[0] &&
                  ev.span[1] === selectedSpan[1]);
              return (
                <EvidenceChip
                  key={j}
                  ev={ev}
                  active={active}
                  onClick={() => onEvidenceClick(ev)}
                />
              );
            })}
            <span className="uncertainty">±{ob.uncertainty.toFixed(2)}</span>
          </div>
        </div>
      ))}
      <h3>Discrepancies ({result.discrepancies.length})</h3>
      {result.discrepancies.length === 0 ? (
        <div className="hint">None flagged.</div>
      ) : (
        <ul className="discrepancy-list">
          {result.discrepancies.map((d, i) => (
            <li key={i} className="warn">
              {d}
            </li>
          ))}
        </ul>
      )}
      <h3>Recommended next step</h3>
      <p>{result.recommended_next_step}</p>
      <h3>Trace</h3>
      <div className="trace">
        {trace.sam} · {trace.vision}
        {trace.vision_fallback_used ? ' (fallback)' : ''} · {trace.reasoning} ·{' '}
        {trace.planning} · {result.cost_cents?.toFixed(2)}¢
        {result.cost_priced ? '' : ' (unpriced)'}
      </div>
      <h3>Raw JSON</h3>
      <pre className="raw-json">{JSON.stringify(result, null, 2)}</pre>
    </div>
  );
}
