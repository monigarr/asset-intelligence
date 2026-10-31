// Pure helpers for the Insights tab (tested; no React here).

export function statusOf(item) {
  switch (item.review_status) {
    case 'accept':
      return { word: 'Accepted', tone: 'ok' };
    case 'edit':
      return { word: 'Corrected', tone: 'ok' };
    case 'reject':
      return { word: 'Rejected', tone: 'bad' };
    default:
      return { word: 'Needs review', tone: 'warn' };
  }
}

export function toneClass(tone) {
  if (tone === 'warn') return 'warn';
  if (tone === 'bad') return 'error';
  return '';
}

export function costText(item) {
  if (!item.cost_priced) return { text: 'not yet priced', priced: false };
  return { text: formatUSD(item.cost_cents), priced: true };
}

export function formatUSD(cents) {
  const dollars = Number(cents) / 100;
  if (!Number.isFinite(dollars)) return '$0.00';
  return '$' + dollars.toFixed(2);
}

export function formatLatency(ms) {
  if (ms == null) return '—';
  if (ms < 1000) return `${Math.round(ms)} ms`;
  return `${(ms / 1000).toFixed(1)} s`;
}

export function formatTime(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '—';
  return d.toLocaleString();
}

const SORTERS = {
  created_at: (a, b) => (a.created_at < b.created_at ? -1 : a.created_at > b.created_at ? 1 : 0),
  latency_ms_total: (a, b) => (a.latency_ms_total || 0) - (b.latency_ms_total || 0),
  cost_cents: (a, b) => (a.cost_cents || 0) - (b.cost_cents || 0),
};

export function sortRows(rows, key, dir = 'desc') {
  const cmp = SORTERS[key] || SORTERS.created_at;
  const sorted = [...rows].sort(cmp);
  return dir === 'desc' ? sorted.reverse() : sorted;
}

const STAGE_LABELS = {
  sam: 'Find defects',
  vision: 'Read photo + note',
  spark: 'Draft findings',
  wonder: 'Check gaps',
  validate: 'Validate',
};

export function stageLabel(key) {
  return STAGE_LABELS[key] || key;
}

export function summarize(record) {
  const obs = (record.observations || []).length;
  const disc = (record.discrepancies || []).length;
  const miss = (record.missing_information || []).length;
  const durations = record.durations_ms || {};
  let slowest = null;
  for (const [stage, ms] of Object.entries(durations)) {
    if (!slowest || ms > slowest.ms) slowest = { stage, ms };
  }
  return { obs, disc, miss, slowest };
}

export function formatTokens(n) {
  if (n == null) return '\u2014';
  const v = Number(n);
  if (!Number.isFinite(v)) return '\u2014';
  return Math.max(0, Math.floor(v)).toLocaleString('en-US');
}

export function usageTotals(record) {
  const legs = Array.isArray(record.model_usage) ? record.model_usage : [];
  const durations = record.durations_ms || {};
  const rows = legs.map((leg) => ({
    stage: leg.stage,
    model: leg.model,
    prompt: Number(leg.prompt_tokens) || 0,
    completion: Number(leg.completion_tokens) || 0,
    images: Number(leg.images) || 0,
    ms: durations[leg.stage] ?? null,
    costCents: Number(leg.cost_cents) || 0,
    priced: leg.cost_priced === true,
  }));
  const prompt = rows.reduce((a, r) => a + r.prompt, 0);
  const completion = rows.reduce((a, r) => a + r.completion, 0);
  const latencies = Object.values(durations)
    .map(Number)
    .filter((v) => Number.isFinite(v));
  return {
    rows,
    prompt,
    completion,
    images: rows.reduce((a, r) => a + r.images, 0),
    tokens: prompt + completion,
    latencyMs: latencies.length ? latencies.reduce((a, b) => a + b, 0) : null,
    costCents: Number(record.cost_cents) || 0,
    priced: !!record.cost_priced,
  };
}
