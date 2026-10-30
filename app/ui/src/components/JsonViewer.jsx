import CostLine from './CostLine.jsx';

function EvidenceChip({ ev, active, kind, onClick }) {
  const label =
    ev.source === 'maintenance_note'
      ? `note [${ev.span ? ev.span.join(':') : '?'}]`
      : `${ev.source}${ev.mask_id ? ` · ${ev.mask_id}` : ''}`;
  if (!onClick) {
    return (
      <span className={`chip chip-${kind}${active ? ' active' : ''}`} title="Evidence reference">
        {label}
      </span>
    );
  }
  return (
    <button className={`chip chip-${kind}${active ? ' active' : ''}`} onClick={onClick} title="Highlight evidence">
      {label}
    </button>
  );
}

function NoteView({ note, span, citedBy }) {
  if (!note) return <div className="hint">Field note is not stored after validation.</div>;
  if (!span) return <div className="note-view">{note}</div>;
  const [start, end] = span;
  return (
    <div className="note-view">
      {note.slice(0, start)}
      <mark title={citedBy ? 'Cited by ' + citedBy : 'Cited evidence'}>{note.slice(start, end)}</mark>
      {note.slice(end)}
    </div>
  );
}

export default function JsonViewer({
  result,
  note,
  showNextStep = true,
  selectedMaskId,
  selectedSpan,
  onEvidenceClick,
}) {
  const trace = result.model_trace || {};
  return (
    <div>
      <h3>Field note</h3>
      <NoteView note={note} span={selectedSpan} citedBy={selectedMaskId} />
      {result.discrepancies.length > 0 && (
        <div className="discrepancy-banner" role="alert">
          <h3>Discrepancies ({result.discrepancies.length})</h3>
          <ul>
            {result.discrepancies.map((d, i) => (
              <li key={i} className="warn">
                {d}
              </li>
            ))}
          </ul>
        </div>
      )}
      <h3>Observations ({result.observations.length})</h3>
      {result.observations.map((ob, i) => (
        <div
          className="obs"
          key={i}
          data-evidence-masks={(ob.evidence || []).map((ev) => ev.mask_id).filter(Boolean).join(' ')}
        >
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
                  kind={ev.source === 'maintenance_note' ? 'note' : 'mask'}
                  onClick={onEvidenceClick ? () => onEvidenceClick(ev) : null}
                />
              );
            })}
            <span className="uncertainty">±{ob.uncertainty.toFixed(2)}</span>
          </div>
        </div>
      ))}
      {result.discrepancies.length === 0 && (
        <>
          <h3>Discrepancies</h3>
          <div className="hint">None flagged.</div>
        </>
      )}
      {showNextStep && (
        <>
          <h3>Recommended next step</h3>
          <p>{result.recommended_next_step}</p>
        </>
      )}
      <h3>Trace</h3>
      <div className="trace">
        {trace.sam} · {trace.vision}
        {trace.vision_fallback_used ? ' (fallback)' : ''} · {trace.reasoning} ·{' '}
        {trace.planning} · <CostLine item={result} />
      </div>
      <h3>Raw JSON</h3>
      <pre className="raw-json">{JSON.stringify(result, null, 2)}</pre>
    </div>
  );
}
