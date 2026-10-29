import { afterEach, describe, expect, it, vi } from 'vitest';
import { submitReview } from './api.js';

describe('submitReview', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('posts decision and note (no edits key)', async () => {
    const seen = {};
    vi.stubGlobal(
      'fetch',
      async (url, init) => {
        seen.url = url;
        seen.body = JSON.parse(init.body);
        return { ok: true, json: async () => ({ status: 'edit' }) };
      },
    );
    await submitReview('req_1', 'edit', 'fix the date', 'k');
    expect(seen.url).toBe('/v1/inspections/req_1/review');
    expect(seen.body).toEqual({ decision: 'edit', note: 'fix the date' });
  });

  it('sends null note when empty', async () => {
    let body;
    vi.stubGlobal('fetch', async (url, init) => {
      body = JSON.parse(init.body);
      return { ok: true, json: async () => ({ status: 'accept' }) };
    });
    await submitReview('req_1', 'accept', null, 'k');
    expect(body).toEqual({ decision: 'accept', note: null });
  });
});
