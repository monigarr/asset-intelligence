import { describe, expect, it } from 'vitest';
import {
  costText,
  formatLatency,
  formatTime,
  sortRows,
  stageLabel,
  statusOf,
  summarize,
  toneClass,
} from './insights.js';

describe('statusOf', () => {
  it('maps review states to plain words', () => {
    expect(statusOf({ review_status: null })).toEqual({ word: 'Needs review', tone: 'warn' });
    expect(statusOf({ review_status: 'accept' })).toEqual({ word: 'Accepted', tone: 'ok' });
    expect(statusOf({ review_status: 'edit' })).toEqual({ word: 'Corrected', tone: 'ok' });
    expect(statusOf({ review_status: 'reject' })).toEqual({ word: 'Rejected', tone: 'bad' });
  });

  it('maps tones to existing stylesheet classes', () => {
    expect(toneClass('warn')).toBe('warn');
    expect(toneClass('bad')).toBe('error');
    expect(toneClass('ok')).toBe('');
  });
});

describe('costText', () => {
  it('never presents unpriced cost as a figure', () => {
    expect(costText({ cost_cents: 0, cost_priced: false })).toEqual({
      text: 'not yet priced',
      priced: false,
    });
    expect(costText({ cost_cents: 12.5, cost_priced: true })).toEqual({
      text: '12.50¢',
      priced: true,
    });
  });
});

describe('formatLatency', () => {
  it('switches units at one second', () => {
    expect(formatLatency(null)).toBe('—');
    expect(formatLatency(350)).toBe('350 ms');
    expect(formatLatency(12340)).toBe('12.3 s');
  });
});

describe('formatTime', () => {
  it('rejects empty and invalid input', () => {
    expect(formatTime(null)).toBe('—');
    expect(formatTime('not-a-date')).toBe('—');
    expect(formatTime('2026-10-29T12:00:00+00:00')).not.toBe('—');
  });
});

describe('sortRows', () => {
  const rows = [
    { created_at: '2026-10-29T12:00:00+00:00', latency_ms_total: 100, cost_cents: 5 },
    { created_at: '2026-10-29T13:00:00+00:00', latency_ms_total: 300, cost_cents: 1 },
  ];

  it('sorts descending by default and flips on request', () => {
    expect(sortRows(rows, 'latency_ms_total').map((r) => r.latency_ms_total)).toEqual([300, 100]);
    expect(sortRows(rows, 'cost_cents', 'asc').map((r) => r.cost_cents)).toEqual([1, 5]);
    expect(sortRows(rows, 'created_at')[0].created_at).toContain('13:00');
  });

  it('falls back to time for unknown keys and never mutates', () => {
    const before = rows.map((r) => r.latency_ms_total);
    expect(sortRows(rows, 'bogus')[0].created_at).toContain('13:00');
    expect(rows.map((r) => r.latency_ms_total)).toEqual(before);
  });
});

describe('stageLabel', () => {
  it('translates known stages and passes the rest through', () => {
    expect(stageLabel('wonder')).toBe('Check gaps');
    expect(stageLabel('custom_stage')).toBe('custom_stage');
  });
});

describe('summarize', () => {
  it('counts findings and finds the slowest stage', () => {
    const record = {
      observations: [{}, {}],
      discrepancies: ['x'],
      missing_information: ['a', 'b', 'c'],
      durations_ms: { sam: 100, wonder: 500, validate: 10 },
    };
    expect(summarize(record)).toEqual({
      obs: 2,
      disc: 1,
      miss: 3,
      slowest: { stage: 'wonder', ms: 500 },
    });
    expect(summarize({}).slowest).toBeNull();
  });
});
