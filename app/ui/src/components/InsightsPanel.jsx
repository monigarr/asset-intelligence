import { useCallback, useEffect, useState } from 'react';
import { fetchInspection, fetchInspections, fetchStats } from '../api.js';
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

const STAGE_ORDER = ['sam', 'vision', 'spark', 'wonder', 'validate'];

function Stat({ label, value, hint }) {
  return (
    <div className="stat">
      <div className="stat-value">{value}</div>
      <div className="stat-label">{label}</div>
      {hint ? <div className="hint">{hint}</div> : null}
    </div>
  );
}

function StageTimeline({ durations }) {
  const ordered = STAGE_ORDER.filter((s) => durations[s] != null);
  const extra = Object.keys(durations).filter((s) => !STAGE_ORDER.includes(s));
  const rows = [...ordered, ...extra].map((s) => [s, durations[s]]);
  if (!rows.length) return <p className="hint">No stage timings recorded.</p>;
  const total = rows.reduce((a, [, ms]) => a + ms, 0) || 1;
  return (
    <ul className="timeline">
      {rows.map(([stage, ms]) => (
        <li key={stage}>
          <span className="stage-name">{stageLabel(stage)}</span>
          <span className="stage-track">
            <span
              className="stage-fill"
              style={{ width: `${Math.max(2, (ms / total) * 100)}%` }}
            />
          </span>
          <span className="stage-ms">{formatLatency(ms)}</span>
        </li>
      ))}
    </ul>
  );
}

function CostLine({ item }) {
  const cost = costText(item);
  if (!cost.priced) return <span className="muted">not yet priced</span>;
  return (
    <span>
      {cost.text} <span className="muted">estimated</span>
    </span>
  );
}

function DetailCard({ record, onClose }) {
  const status = statusOf({ review_status: record.review_status });
  const sum = summarize(record);
  const trace = record.model_trace || {};
  const usage = record.usage || {};
  return (
    <div className="panel">
      <h2>
        Inspection detail <span className="muted">({record.request_id})</span>
      </h2>
      <p>
        <span className={`status-chip ${toneClass(status.tone)}`}>{status.word}</span>
      </p>
      <p>
        {sum.obs} observations, {sum.disc} discrepancies, {sum.miss} missing items.
        {sum.slowest ? (
          <>
            {' '}
            Slowest stage: {stageLabel(sum.slowest.stage)} (
            {formatLatency(sum.slowest.ms)}).
          </>
        ) : null}
      </p>
      <h3>Stage timeline</h3>
      <StageTimeline durations={record.durations_ms || {}} />
      <h3>Cost &amp; usage</h3>
      <p>
        <CostLine item={record} />
        {' · '}
        {usage.total_tokens || 0} tokens
        {' · '}
        models: {trace.sam}, {trace.vision}
        {trace.vision_fallback_used ? ' (fallback)' : ''}, {trace.reasoning},{' '}
        {trace.planning}
      </p>
      <button type="button" onClick={onClose}>
        Close detail
      </button>
    </div>
  );
}

export default function InsightsPanel({ apiKey, onApiKey }) {
  const [keyInput, setKeyInput] = useState('');
  const [stats, setStats] = useState(null);
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [assetDraft, setAssetDraft] = useState('');
  const [assetFilter, setAssetFilter] = useState('');
  const [sortKey, setSortKey] = useState('created_at');
  const [sortDir, setSortDir] = useState('desc');
  const [selectedId, setSelectedId] = useState(null);
  const [detail, setDetail] = useState(null);
  const [detailError, setDetailError] = useState('');

  const load = useCallback(async () => {
    if (!apiKey) return;
    setLoading(true);
    setError('');
    try {
      const [s, h] = await Promise.all([
        fetchStats(apiKey),
        fetchInspections(apiKey, {
          limit: 100,
          reviewStatus: statusFilter,
          assetId: assetFilter,
        }),
      ]);
      setStats(s);
      setRows(h.inspections || []);
    } catch (e) {
      setError(e.message || String(e));
    } finally {
      setLoading(false);
    }
  }, [apiKey, statusFilter, assetFilter]);

  useEffect(() => {
    load();
  }, [load]);

  async function selectRow(id) {
    setSelectedId(id);
    setDetail(null);
    setDetailError('');
    try {
      setDetail(await fetchInspection(id, apiKey));
    } catch (e) {
      setDetailError(e.message || String(e));
    }
  }

  function toggleSort(key) {
    if (key === sortKey) {
      setSortDir((d) => (d === 'desc' ? 'asc' : 'desc'));
    } else {
      setSortKey(key);
      setSortDir('desc');
    }
  }

  if (!apiKey) {
    return (
      <div className="panel">
        <h2>Insights</h2>
        <p>
          Recent inspections (24 hours): what ran, what needs review, and what it
          cost. An API key is required to load inspection history.
        </p>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (keyInput.trim()) onApiKey(keyInput.trim());
          }}
        >
          <label>
            API key
            <input
              type="text"
              value={keyInput}
              placeholder="local-dev-key-123"
              onChange={(e) => setKeyInput(e.target.value)}
            />
            <span className="hint">
              Need an API key? Contact{' '}
              <a href="mailto:monica@manageassets.net">monica@manageassets.net</a>{' '}
              to request one.
            </span>
          </label>
          <div>
            <button type="submit" className="primary" disabled={!keyInput.trim()}>
              Load insights
            </button>
          </div>
        </form>
      </div>
    );
  }

  const visible = sortRows(rows, sortKey, sortDir);
  const sortMark = (key) => {
    if (key !== sortKey) return null;
    return sortDir === 'desc' ? ' ▼' : ' ▲';
  };
  const ariaSort = (key) => {
    if (key !== sortKey) return 'none';
    return sortDir === 'desc' ? 'descending' : 'ascending';
  };

  return (
    <div>
      <div className="panel">
        <h2>Insights</h2>
        <p className="hint">
          Recent inspections (24 hours): what ran, what needs review, and what it
          cost.
        </p>
        {loading && <p>Loading insights…</p>}
        {error && <div className="error">{error}</div>}
        {stats && (
          <div className="stat-grid">
            <Stat label="inspections" value={stats.n} hint="in the last 24 hours" />
            <Stat
              label="need review"
              value={stats.by_review_status.pending}
              hint={`${Math.round((stats.review_rate || 0) * 100)}% reviewed`}
            />
            <Stat
              label="estimated cost"
              value={
                stats.cost_priced_cents > 0
                  ? `${stats.cost_priced_cents.toFixed(2)}¢`
                  : '—'
              }
              hint={
                stats.cost_unpriced_count > 0
                  ? `${stats.cost_unpriced_count} calls not yet priced`
                  : 'metered at Meta rate card'
              }
            />
            <Stat
              label="slowest typical call (p95)"
              value={
                stats.latency_p95_ms != null ? formatLatency(stats.latency_p95_ms) : '—'
              }
              hint="target: under 8 seconds"
            />
          </div>
        )}
      </div>

      <div className="panel">
        <h2>History</h2>
        <form
          className="filter-row"
          onSubmit={(e) => {
            e.preventDefault();
            setAssetFilter(assetDraft.trim());
          }}
        >
          <label>
            Review status
            <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
              <option value="">All</option>
              <option value="pending">Needs review</option>
              <option value="accept">Accepted</option>
              <option value="edit">Corrected</option>
              <option value="reject">Rejected</option>
            </select>
          </label>
          <label>
            Asset ID
            <input
              type="text"
              value={assetDraft}
              placeholder="DEMO-DRAIN-001"
              onChange={(e) => setAssetDraft(e.target.value)}
            />
          </label>
          <div className="filter-actions">
            <button type="submit">Apply</button>
            <button type="button" onClick={load}>
              Refresh
            </button>
          </div>
        </form>
        {visible.length === 0 && !loading ? (
          <p className="hint">No inspections match these filters.</p>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th aria-sort={ariaSort('created_at')}>
                  <button type="button" onClick={() => toggleSort('created_at')}>
                    Time{sortMark('created_at')}
                  </button>
                </th>
                <th>Asset</th>
                <th>Status</th>
                <th aria-sort={ariaSort('latency_ms_total')}>
                  <button type="button" onClick={() => toggleSort('latency_ms_total')}>
                    Latency{sortMark('latency_ms_total')}
                  </button>
                </th>
                <th aria-sort={ariaSort('cost_cents')}>
                  <button type="button" onClick={() => toggleSort('cost_cents')}>
                    Cost{sortMark('cost_cents')}
                  </button>
                </th>
              </tr>
            </thead>
            <tbody>
              {visible.map((item) => {
                const status = statusOf(item);
                const selected = item.request_id === selectedId;
                return (
                  <tr key={item.request_id}>
                    <td>
                      <button
                        type="button"
                        className="linklike"
                        aria-current={selected ? 'true' : undefined}
                        onClick={() => selectRow(item.request_id)}
                      >
                        {formatTime(item.created_at)}
                      </button>
                    </td>
                    <td>{item.asset_id}</td>
                    <td>
                      <span className={`status-chip ${toneClass(status.tone)}`}>
                        {status.word}
                      </span>
                    </td>
                    <td>{formatLatency(item.latency_ms_total)}</td>
                    <td>
                      <CostLine item={item} />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {detailError && (
        <div className="panel">
          <div className="error">{detailError}</div>
        </div>
      )}
      {detail && (
        <DetailCard
          record={detail}
          onClose={() => {
            setDetail(null);
            setSelectedId(null);
          }}
        />
      )}
    </div>
  );
}
