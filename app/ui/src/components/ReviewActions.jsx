import { useState } from 'react';

export default function ReviewActions({ disabled, onReview, status }) {
  const [busy, setBusy] = useState(null);

  async function decide(decision) {
    setBusy(decision);
    try {
      await onReview(decision);
    } finally {
      setBusy(null);
    }
  }

  return (
    <div>
      <div className="review-actions">
        <button
          className="primary"
          disabled={disabled || busy !== null}
          onClick={() => decide('accept')}
        >
          {busy === 'accept' ? 'Sending…' : 'Accept'}
        </button>
        <button disabled={disabled || busy !== null} onClick={() => decide('reject')}>
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
