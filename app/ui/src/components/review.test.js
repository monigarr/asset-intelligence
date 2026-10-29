import { describe, expect, it } from 'vitest';
import { REVIEW_DECISIONS, canSubmitReview, correctionNoteRequired } from './review.js';

describe('review decisions', () => {
  it('matches the API contract', () => {
    expect(REVIEW_DECISIONS).toEqual(['accept', 'edit', 'reject']);
  });

  it('requires a note for corrections only', () => {
    expect(correctionNoteRequired('edit')).toBe(true);
    expect(correctionNoteRequired('accept')).toBe(false);
    expect(correctionNoteRequired('reject')).toBe(false);
  });

  it('gates submission on decision + note', () => {
    expect(canSubmitReview('accept', '')).toBe(true);
    expect(canSubmitReview('reject', '')).toBe(true);
    expect(canSubmitReview('edit', '')).toBe(false);
    expect(canSubmitReview('edit', '   ')).toBe(false);
    expect(canSubmitReview('edit', 'fix the date')).toBe(true);
    expect(canSubmitReview('bogus', 'x')).toBe(false);
  });
});
