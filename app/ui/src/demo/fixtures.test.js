import { existsSync, readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import { decodeMaskRle } from '../rle.js';
import { fixtureUrls } from './fixtures.js';

const dir = join(dirname(fileURLToPath(import.meta.url)), '../../public/fixtures');
const index = JSON.parse(readFileSync(join(dir, 'index.json'), 'utf8'));

describe('demo fixtures', () => {
  it('index lists fixtures with files on disk', () => {
    expect(index.length).toBeGreaterThan(0);
    for (const f of index) {
      expect(f.id).toMatch(/^[a-z0-9-]+$/);
      expect(f.label).toBeTruthy();
      expect(existsSync(join(dir, `${f.id}.jpg`))).toBe(true);
      expect(existsSync(join(dir, `${f.id}.json`))).toBe(true);
    }
  });

  it.each(index.map((f) => [f.id]))('fixture %s validates', (id) => {
    const fx = JSON.parse(readFileSync(join(dir, `${id}.json`), 'utf8'));
    expect(fx.note).toBeTruthy();
    const r = fx.result;
    expect(r.human_review_required).toBe(true);
    expect(r.observations.length).toBeGreaterThan(0);
    const masks = new Set(r.segmentations.map((s) => s.mask_id));
    for (const s of r.segmentations) {
      expect(s.bbox).toHaveLength(4);
      decodeMaskRle(s.rle); // throws when malformed
    }
    for (const ob of r.observations) {
      expect(ob.evidence.length).toBeGreaterThan(0);
      for (const ev of ob.evidence) {
        if (ev.mask_id) expect(masks.has(ev.mask_id)).toBe(true);
        if (ev.span) {
          const [a, b] = ev.span;
          expect(a).toBeGreaterThanOrEqual(0);
          expect(b).toBeLessThanOrEqual(fx.note.length);
        }
      }
    }
  });

  it('fixtureUrls builds stable paths', () => {
    expect(fixtureUrls('x')).toEqual({ json: '/fixtures/x.json', image: '/fixtures/x.jpg' });
  });
});
