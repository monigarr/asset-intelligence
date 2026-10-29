// Pure review-decision helpers (tested; no React here).
// Decisions mirror POST /v1/inspections/{id}/review: accept / edit / reject.

export const REVIEW_DECISIONS = ['accept', 'edit', 'reject'];

export function correctionNoteRequired(decision) {
  return decision === 'edit';
}

export function canSubmitReview(decision, note) {
  if (!REVIEW_DECISIONS.includes(decision)) return false;
  if (decision === 'edit') return (note || '').trim().length > 0;
  return true;
}
