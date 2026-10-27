import { describe, expect, it } from 'vitest';
import { decodeCocoRle, decodeMaskRle } from './rle.js';

// Same vectors as tests/test_sam_service.py — cross-language oracle.
describe('decodeCocoRle', () => {
  it('decodes column-major runs to row-major pixels', () => {
    const { width, height, pixels } = decodeCocoRle([2, 1, 3], 2, 3);
    expect(width).toBe(3);
    expect(height).toBe(2);
    expect(Array.from(pixels)).toEqual([0, 1, 0, 0, 0, 0]);
  });

  it('rejects bad runs', () => {
    expect(() => decodeCocoRle([2, 1], 2, 3)).toThrow();
    expect(() => decodeCocoRle([2, -1, 4], 2, 3)).toThrow();
    expect(() => decodeCocoRle([6], 0, 3)).toThrow();
  });
});

describe('decodeMaskRle', () => {
  it('returns null for bbox-only masks', () => {
    expect(decodeMaskRle(null)).toBeNull();
    expect(decodeMaskRle(undefined)).toBeNull();
  });

  it('decodes COCO dicts and rejects compressed strings', () => {
    const out = decodeMaskRle({ size: [2, 3], counts: [2, 1, 3] });
    expect(Array.from(out.pixels)).toEqual([0, 1, 0, 0, 0, 0]);
    expect(() => decodeMaskRle({ size: [2, 3], counts: 'eN00' })).toThrow();
    expect(() => decodeMaskRle('some-string')).toThrow();
  });
});
