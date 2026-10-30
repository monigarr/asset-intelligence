import { useState } from 'react';
import { canSubmitReview } from './review.js';

export default function ReviewActions({ disabled, onReview, status }) {
  const [busy, setBusy] = useState(null);
  const [note, setNote] = useState('');

  async function decide(decision) {
    if (!canSubmitReview(decision, note)) return;
    setBusy(decision);
    try {
      await onReview(decision, note.trim() || null);
    } finally {
      setBusy(null);
    }
  }

  const off = disabled || busy !== null;
  return (
    <div>
      <p className="disclaimer">Does not certify safety. Requires qualified inspection.</p>
      <label className="review-note">
        Correction note
        <textarea
          value={note}
          rows={2}
          maxLength={2000}
          disabled={off}
          placeholder="Required for corrections — what should change?"
          onChange={(e) => setNote(e.target.value)}
        />
      </label>
      <div className="review-actions">
        <button
          className="primary"
          disabled={off}
          onClick={() => decide('accept')}
        >
          {busy === 'accept' ? 'Sending…' : 'Accept'}
        </button>
        <button
          disabled={off || !canSubmitReview('edit', note)}
          onClick={() => decide('edit')}
          title="Record a correction (requires a note)"
        >
          {busy === 'edit' ? 'Sending…' : 'Correct'}
        </button>
        <button disabled={off} onClick={() => decide('reject')}>
          {busy === 'reject' ? 'Sending…' : 'Reject'}
        </button>
      </div>
      {status && (
        <div className="hint" style={{ marginTop: 6 }}>
          {status}
        </div>
      )}
      {disabled && (
        <div className="hint" style={{ marginTop: 6 }}>
          Review is disabled in demo mode.
        </div>
      )}
    </div>
  );
}
