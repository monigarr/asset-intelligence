import { Fragment, useCallback, useEffect, useRef, useState } from 'react';
import {
  fetchInspection,
  fetchInspections,
  fetchOverlays,
  fetchStats,
  submitReview,
} from '../api.js';
import CostLine from './CostLine.jsx';
import ExportDocument from './ExportDocument.jsx';
import JsonViewer from './JsonViewer.jsx';
import MissingChecklist from './MissingChecklist.jsx';
import ReviewActions from './ReviewActions.jsx';
import {
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

const STAGE_ORDER = ['sam', 'vision', 'spark', 'wonder', 'validate'];

function UsageCell({ item }) {
  const legs = Array.isArray(item.model_usage) ? item.model_usage : [];
  if (legs.length === 0) {
    return <span className="mono">{item.usage_total_tokens || 0} tokens</span>;
  }
  return (
    <span className="usage-cell">
      {legs.map((leg, i) => (
        <span key={i} className="mono usage-line">
          {leg.stage === 'sam'
            ? `${leg.model} ${leg.images} img`
            : `${leg.model} ${leg.prompt_tokens}/${leg.completion_tokens}`}
        </span>
      ))}
    </span>
  );
}

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

function UsageBreakdown({ record }) {
  const t = usageTotals(record);
  if (t.rows.length === 0) {
    return (
      <p>
        <CostLine item={record} />
        {' - '}
        {formatTokens((record.usage || {}).total_tokens || 0)} tokens
      </p>
    );
  }
  return (
    <table className="data-table usage-breakdown">
      <thead>
        <tr>
          <th>Stage</th>
          <th>Model</th>
          <th>Tokens in / out</th>
          <th>Latency</th>
          <th>Cost</th>
        </tr>
      </thead>
      <tbody>
        {t.rows.map((r, i) => (
          <tr key={i}>
            <td>{stageLabel(r.stage)}</td>
            <td className="mono">{r.model}</td>
            <td className="mono">
              {r.stage === 'sam'
                ? `${formatTokens(r.images)} img`
                : `${formatTokens(r.prompt)} / ${formatTokens(r.completion)}`}
            </td>
            <td className="mono">{formatLatency(r.ms)}</td>
            <td className="mono">{r.priced ? formatUSD(r.costCents) : 'not yet priced'}</td>
          </tr>
        ))}
      </tbody>
      <tfoot>
        <tr>
          <td>Total</td>
          <td className="mono">{'\u2014'}</td>
          <td className="mono">
            {formatTokens(t.tokens)}
            {t.images > 0 ? ` + ${formatTokens(t.images)} img` : ''}
          </td>
          <td className="mono">{formatLatency(t.latencyMs)}</td>
          <td className="mono">{t.priced ? `${formatUSD(t.costCents)} estimated` : 'not yet priced'}</td>
        </tr>
      </tfoot>
    </table>
  );
}

function DetailCard({ record, onClose, apiKey, onReviewed, profile }) {
  const status = statusOf({ review_status: record.review_status });
  const sum = summarize(record);
  const [overlays, setOverlays] = useState([]);
  const [overlayNote, setOverlayNote] = useState('');
  const [reviewStatus, setReviewStatus] = useState('');

  useEffect(() => {
    let cancelled = false;
    setOverlays([]);
    setOverlayNote('');
    fetchOverlays(record.request_id, apiKey)
      .then((items) => {
        if (cancelled) {
          items.forEach((o) => URL.revokeObjectURL(o.url));
          return;
        }
        setOverlays(items);
        if (items.length === 0) {
          setOverlayNote('No overlay images stored for this inspection.');
        }
      })
      .catch((e) => {
        if (!cancelled) setOverlayNote('Overlays unavailable: ' + (e.message || e));
      });
    return () => {
      cancelled = true;
    };
  }, [record.request_id, apiKey]);

  useEffect(
    () => () => {
      overlays.forEach((o) => URL.revokeObjectURL(o.url));
    },
    [overlays],
  );

  async function handleReview(decision, note) {
    setReviewStatus('');
    try {
      const res = await submitReview(record.request_id, decision, note, apiKey);
      setReviewStatus('Saved: ' + res.review_status + ' (reviewed ' + (res.reviewed_at || 'just now') + ').');
      if (onReviewed) onReviewed();
    } catch (e) {
      setReviewStatus('Review failed: ' + (e.message || e));
    }
  }

  const hasPayload = Array.isArray(record.observations);

  return (
    <div className="panel detail-card">
      <h2>
        Inspection detail <span className="muted">({record.request_id})</span>
      </h2>
      <p>
        <span className={'status-chip ' + toneClass(status.tone)}>{status.word}</span>
      </p>
      <p>
        {sum.obs} observations, {sum.disc} discrepancies, {sum.miss} missing items.
        {sum.slowest ? (
          <span>
            {' '}
            Slowest stage: {stageLabel(sum.slowest.stage)} (
            {formatLatency(sum.slowest.ms)}).
          </span>
        ) : null}
      </p>
      <h3>Stage timeline</h3>
      <StageTimeline durations={record.durations_ms || {}} />
      <h3>Cost and usage</h3>
      <UsageBreakdown record={record} />
      {overlays.length > 0 && (
        <div>
          <h3>Segmentation overlays</h3>
          <div className="overlay-row">
            {overlays.map((o) => (
              <img key={o.index} src={o.url} alt={'Overlay for image ' + (o.index + 1)} />
            ))}
          </div>
        </div>
      )}
      {overlayNote && <p className="hint">{overlayNote}</p>}
      <h3>Missing information</h3>
      <MissingChecklist items={record.missing || []} />
      {hasPayload ? (
        <JsonViewer result={record} note={record.field_note} />
      ) : (
        <p className="hint">Full result payload is not available for this record.</p>
      )}
      <h3>Review decision</h3>
      <ReviewActions onReview={handleReview} status={reviewStatus} />
      <h3>Export</h3>
      <ExportDocument record={record} profile={profile} apiKey={apiKey} />
      <p>
        <button type="button" onClick={onClose}>
          Close detail
        </button>
      </p>
    </div>
  );
}

export default function InsightsPanel({ apiKey, onApiKey, profile }) {
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
  const loadToken = useRef(0);

  const load = useCallback(async () => {
    if (!apiKey) return;
    setLoading(true);
    setError('');
    try {
      const [s, h] = await Promise.all([
        fetchStats(apiKey),
        fetchInspections(apiKey, {
          limit: 200,
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
    loadToken.current += 1;
    const token = loadToken.current;
    if (id === selectedId) {
      setSelectedId(null);
      setDetail(null);
      setDetailError('');
      return;
    }
    setSelectedId(id);
    setDetail(null);
    setDetailError('');
    try {
      const rec = await fetchInspection(id, apiKey);
      if (loadToken.current === token) setDetail(rec);
    } catch (e) {
      if (loadToken.current === token) setDetailError(e.message || String(e));
    }
  }

  async function refreshDetail(id) {
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
          className="key-form"
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
                stats.cost_priced_cents > 0 ? formatUSD(stats.cost_priced_cents) : '\u2014'
              }
              hint={
                stats.cost_unpriced_count > 0
                  ? `${stats.cost_unpriced_count} calls not yet priced`
                  : 'metered at Meta rate card'
              }
            />
            <Stat
              label="tokens metered"
              value={formatTokens(rows.reduce((a, r) => a + (r.usage_total_tokens || 0), 0))}
              hint={`across ${rows.length} loaded inspections`}
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
            setSelectedId(null);
            setDetail(null);
            setDetailError('');
          }}
        >
          <label>
            Review status
            <select value={statusFilter} onChange={(e) => { setStatusFilter(e.target.value); setSelectedId(null); setDetail(null); setDetailError(''); }}>;
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
        {stats && rows.length < stats.n && (
          <p className="hint">
            Showing {rows.length} of {stats.n} inspections (refine filters to narrow).
          </p>
        )}
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
                <th>Model usage</th>
                <th aria-sort={ariaSort('cost_cents')}>
                  <button type="button" onClick={() => toggleSort('cost_cents')}>
                    Model cost{sortMark('cost_cents')}
                  </button>
                </th>
              </tr>
            </thead>
            <tbody>
              {visible.map((item) => {
                const status = statusOf(item);
                const selected = item.request_id === selectedId;
                return (
                  <Fragment key={item.request_id}>
                    <tr>
                    <td>
                      <button
                        type="button"
                        className="linklike"
                        aria-current={selected ? 'true' : undefined}
                        aria-expanded={selected}
                        onClick={() => selectRow(item.request_id)}
                      >
                        <span className="mono">{formatTime(item.created_at)}</span>
                      </button>
                    </td>
                    <td className="mono">{item.asset_id}</td>
                    <td>
                      <span className={`status-chip ${toneClass(status.tone)}`}>
                        {status.word}
                      </span>
                    </td>
                    <td className="mono">{formatLatency(item.latency_ms_total)}</td>
                    <td>
                      <UsageCell item={item} />
                    </td>
                    <td className="mono">
                      {item.cost_priced ? formatUSD(item.cost_cents) : 'not yet priced'}
                    </td>
                    </tr>
                    {selected && (
                      <tr className="detail-row">
                        <td colSpan={6}>
                          {detailError && <div className="error">{detailError}</div>}
                          {!detail && !detailError && <p>Loading inspection...</p>}
                          {detail && (
                            <DetailCard
                              record={detail}
                              apiKey={apiKey}
                              profile={profile}
                              onClose={() => {
                                setDetail(null);
                                setSelectedId(null);
                              }}
                              onReviewed={() => {
                                refreshDetail(detail.request_id);
                                load();
                              }}
                            />
                          )}
                        </td>
                      </tr>
                    )}
                  </Fragment>
                );
              })}
            </tbody>
          </table>
        )}
      </div>


    </div>
  );
}
