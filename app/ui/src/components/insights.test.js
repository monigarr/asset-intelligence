import { describe, expect, it } from 'vitest';
import {
  costText,
  formatLatency,
  formatTime,
  formatTokens,
  formatUSD,
  sortRows,
  stageLabel,
  statusOf,
  summarize,
  toneClass,
  usageTotals,
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
      text: '$0.13',
      priced: true,
    });
  });
});

describe('formatUSD', () => {
  it('renders dollars and cents', () => {
    expect(formatUSD(59.2)).toBe('$0.59');
    expect(formatUSD(125.222)).toBe('$1.25');
    expect(formatUSD(75.23)).toBe('$0.75');
    expect(formatUSD(150)).toBe('$1.50');
    expect(formatUSD(0)).toBe('$0.00');
    expect(formatUSD(NaN)).toBe('$0.00');
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

describe('formatTokens', () => {
  it('groups thousands and guards bad input', () => {
    expect(formatTokens(0)).toBe('0');
    expect(formatTokens(1234567)).toBe('1,234,567');
    expect(formatTokens(null)).toBe('\u2014');
    expect(formatTokens(NaN)).toBe('\u2014');
  });
});

describe('usageTotals', () => {
  it('merges legs with stage latencies and totals', () => {
    const record = {
      cost_cents: 6.66,
      cost_priced: true,
      durations_ms: { sam: 1000, vision: 2000, validate: 50 },
      model_usage: [
        { stage: 'sam', model: 'sam-3.1', images: 1, cost_cents: 0.25, cost_priced: true },
        { stage: 'vision', model: 'muse-spark-1.3', prompt_tokens: 100, completion_tokens: 200, cost_cents: 1.0, cost_priced: true },
      ],
    };
    expect(usageTotals(record)).toEqual({
      rows: [
        { stage: 'sam', model: 'sam-3.1', prompt: 0, completion: 0, images: 1, ms: 1000, costCents: 0.25, priced: true },
        { stage: 'vision', model: 'muse-spark-1.3', prompt: 100, completion: 200, images: 0, ms: 2000, costCents: 1.0, priced: true },
      ],
      prompt: 100,
      completion: 200,
      images: 1,
      tokens: 300,
      latencyMs: 3050,
      costCents: 6.66,
      priced: true,
    });
    expect(usageTotals({})).toEqual({
      rows: [],
      prompt: 0,
      completion: 0,
      images: 0,
      tokens: 0,
      latencyMs: null,
      costCents: 0,
      priced: false,
    });
  });
});
