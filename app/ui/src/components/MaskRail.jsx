import { useRef } from 'react';
import { confidenceLabel, cycleIndex } from './masks.js';

// Keyboard + glove-friendly mirror of the canvas masks (DESIGN.md C.1/C.2).
// Arrow keys cycle selection; each pill is a 32px+ target driving onSelect.
export default function MaskRail({ segmentations, selectedMaskId, onSelect }) {
  const refs = useRef([]);
  const segs = segmentations || [];
  if (segs.length === 0) return null;

  function focusIdx(i) {
    const el = refs.current[i];
    if (el) el.focus();
    onSelect(segs[i].mask_id);
  }

  function onKeyDown(e, i) {
    if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
      e.preventDefault();
      focusIdx(cycleIndex(segs.length, i, 1));
    } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
      e.preventDefault();
      focusIdx(cycleIndex(segs.length, i, -1));
    } else if (e.key === 'Home') {
      e.preventDefault();
      focusIdx(0);
    } else if (e.key === 'End') {
      e.preventDefault();
      focusIdx(segs.length - 1);
    }
  }

  return (
    <div className="mask-rail" role="group" aria-label="Masks">
      {segs.map((s, i) => (
        <button
          key={s.mask_id}
          ref={(el) => {
            refs.current[i] = el;
          }}
          type="button"
          aria-pressed={s.mask_id === selectedMaskId}
          onClick={() => onSelect(s.mask_id)}
          onKeyDown={(e) => onKeyDown(e, i)}
        >
          {s.mask_id} {confidenceLabel(s.label, s.confidence)}
        </button>
      ))}
    </div>
  );
}