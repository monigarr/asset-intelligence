import { describe, expect, it } from 'vitest';
import {
  MIN_TARGET_PX,
  confidenceLabel,
  cycleIndex,
  dashForLabel,
  hitTest,
  pickMask,
} from './masks.js';

describe('dashForLabel', () => {
  it('returns a distinct dash per known label (not hue-only)', () => {
    expect(dashForLabel('crack')).toEqual([]);
    expect(dashForLabel('Corrosion')).toEqual([6, 3]);
    expect(dashForLabel('SPALL')).toEqual([2, 3]);
    expect(dashForLabel('water intrusion')).toEqual([4, 2]);
  });
  it('falls back to solid for unknown labels', () => {
    expect(dashForLabel('rust bloom')).toEqual([]);
    expect(dashForLabel(null)).toEqual([]);
  });
});

describe('confidenceLabel', () => {
  it('names the model instead of a bare number', () => {
    expect(confidenceLabel('crack', 0.87)).toBe('crack \u00b7 SAM 0.87');
    expect(confidenceLabel('crack', null)).toBe('crack \u00b7 SAM ?');
  });
});

describe('hitTest / pickMask', () => {
  const segs = [
    { mask_id: 'mask_big', bbox: [0, 0, 100, 100] },
    { mask_id: 'mask_small', bbox: [40, 40, 60, 60] },
  ];
  it('hits inside the bbox', () => {
    expect(hitTest([0, 0, 10, 10], 5, 5)).toBe(true);
    expect(hitTest([0, 0, 10, 10], 11, 5)).toBe(false);
  });
  it('expands small targets by slop (glove use)', () => {
    expect(hitTest([0, 0, 4, 4], 8, 2, 10)).toBe(true);
    expect(hitTest([0, 0, 4, 4], 20, 2, 10)).toBe(false);
  });
  it('picks the smallest enclosing mask, else null', () => {
    expect(pickMask(segs, 50, 50)).toBe('mask_small');
    expect(pickMask(segs, 10, 10)).toBe('mask_big');
    expect(pickMask(segs, 500, 500)).toBe(null);
  });
  it('keeps the glove minimum at 24px', () => {
    expect(MIN_TARGET_PX).toBe(24);
  });
});

describe('cycleIndex', () => {
  it('wraps in both directions', () => {
    expect(cycleIndex(3, 2, 1)).toBe(0);
    expect(cycleIndex(3, 0, -1)).toBe(2);
    expect(cycleIndex(3, 1, 1)).toBe(2);
  });
  it('guards empty rails', () => {
    expect(cycleIndex(0, 0, 1)).toBe(0);
  });
});