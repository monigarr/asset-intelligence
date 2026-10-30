import { afterEach, describe, expect, it, vi } from 'vitest';
import { fetchOriginalBlobs, submitReview } from './api.js';

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

describe('fetchOriginalBlobs', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('walks /image indices until the first miss', async () => {
    const seen = [];
    vi.stubGlobal('fetch', async (url, init) => {
      seen.push([url, init.headers]);
      if (url.endsWith('image?image=0')) {
        return { ok: true, blob: async () => ({ type: 'image/jpeg' }) };
      }
      return { ok: false };
    });
    const out = await fetchOriginalBlobs('req_1', 'k');
    expect(seen.map(([url]) => url)).toEqual([
      '/v1/inspections/req_1/image?image=0',
      '/v1/inspections/req_1/image?image=1',
    ]);
    expect(seen[0][1]).toEqual({ 'X-API-Key': 'k' });
    expect(out).toEqual([{ index: 0, blob: { type: 'image/jpeg' }, mime: 'image/jpeg' }]);
  });
});
