import { useEffect, useRef, useState } from 'react';
import { overlayUrl, submitInspection, submitReview } from './api.js';
import { loadFixture, loadFixtureIndex } from './demo/fixtures.js';
import JsonViewer from './components/JsonViewer.jsx';
import MaskOverlay from './components/MaskOverlay.jsx';
import MaskRail from './components/MaskRail.jsx';
import NextStepCta from './components/NextStepCta.jsx';
import ExportDocument from './components/ExportDocument.jsx';
import { CostPill } from './components/CostLine.jsx';
import { costText } from './components/insights.js';
import MissingChecklist from './components/MissingChecklist.jsx';
import ReviewActions from './components/ReviewActions.jsx';
import UploadForm from './components/UploadForm.jsx';
import Header from './components/Header.jsx';
import AboutPanel from './components/AboutPanel.jsx';
import SettingsPanel from './components/SettingsPanel.jsx';
import InsightsPanel from './components/InsightsPanel.jsx';
import Footer from './components/Footer.jsx';
import { ChartIcon, CodeIcon, GearIcon, InfoIcon, PlayIcon } from './components/icons.jsx';

const FALLBACK_DIMS = { width: 800, height: 600 };

// Pending preloads must stay referenced: a detached Image with no live
// references can be garbage-collected before onload/onerror fires,
// hanging the dimension lookup forever (no error, no timeout).
const pendingImages = new Set();

function imageDims(file) {
  return new Promise((resolve) => {
    const url = URL.createObjectURL(file);
    const img = new Image();
    pendingImages.add(img);
    const done = (value) => {
      pendingImages.delete(img);
      resolve(value);
    };
    img.onload = () => done({ url, width: img.naturalWidth, height: img.naturalHeight });
    img.onerror = () => done({ url, width: 640, height: 480 });
    img.src = url;
  });
}

// Evidence tether (DESIGN.md B): a 1px steel leader from the selected mask
// centroid to its observation row. Static line (instant under reduced motion);
// renders only when both endpoints exist.
function TetherLine({ containerRef, selectedMaskId, segmentations, canvasW, canvasH }) {
  const [line, setLine] = useState(null);

  useEffect(() => {
    function compute() {
      const container = containerRef.current;
      const seg = (segmentations || []).find((s) => s.mask_id === selectedMaskId);
      if (!container || !seg) {
        setLine(null);
        return;
      }
      const canvas = container.querySelector('[data-tether-origin] canvas');
      const row = container.querySelector('[data-evidence-masks~="' + selectedMaskId + '"]');
      if (!canvas || !row) {
        setLine(null);
        return;
      }
      const rr0 = row.getBoundingClientRect();
      const vh0 = window.innerHeight || 0;
      if (rr0.bottom <= 0 || rr0.top >= vh0) {
        const calm =
          window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        try {
          row.scrollIntoView({ block: 'nearest', behavior: calm ? 'auto' : 'smooth' });
        } catch {
          row.scrollIntoView();
        }
      }
      const c = container.getBoundingClientRect();
      const r = canvas.getBoundingClientRect();
      const rr = row.getBoundingClientRect();
      const sx = r.width / canvasW;
      const sy = r.height / canvasH;
      setLine({
        x1: r.left - c.left + ((seg.bbox[0] + seg.bbox[2]) / 2) * sx,
        y1: r.top - c.top + ((seg.bbox[1] + seg.bbox[3]) / 2) * sy,
        x2: rr.left - c.left,
        y2: rr.top - c.top + rr.height / 2,
      });
    }
    compute();
    window.addEventListener('resize', compute);
    window.addEventListener('scroll', compute, { passive: true });
    return () => {
      window.removeEventListener('resize', compute);
      window.removeEventListener('scroll', compute);
    };
  }, [containerRef, selectedMaskId, segmentations, canvasW, canvasH]);

  if (!line) return null;
  return (
    <svg className="tether-svg" aria-hidden="true">
      <line x1={line.x1} y1={line.y1} x2={line.x2} y2={line.y2} />
    </svg>
  );
}

export default function App() {
  const [mode, setMode] = useState('demo');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [demoData, setDemoData] = useState({ result: null, note: '', images: [] });
  const [apiData, setApiData] = useState({ result: null, note: '', images: [] });
  const [fixtures, setFixtures] = useState([]);
  const [fixtureId, setFixtureId] = useState('');
  const [fixtureLoading, setFixtureLoading] = useState(true);
  const [fixtureCase, setFixtureCase] = useState('');
  const [tab, setTab] = useState(0);
  const [apiKey, setApiKey] = useState(() => {
    try {
      return localStorage.getItem('assetintel.apiKey') || '';
    } catch {
      return '';
    }
  });
  const [selectedMaskId, setSelectedMaskId] = useState(null);
  const [selectedSpan, setSelectedSpan] = useState(null);
  const [reviewStatus, setReviewStatus] = useState('');
  const resultRef = useRef(null);

  useEffect(() => {
    try {
      if (apiKey) localStorage.setItem('assetintel.apiKey', apiKey);
      else localStorage.removeItem('assetintel.apiKey');
    } catch {
      /* private mode: key lives for this session only */
    }
  }, [apiKey]);

  const [theme, setTheme] = useState(() => {
    try {
      const saved = localStorage.getItem('assetintel.theme');
      if (saved === 'light' || saved === 'dark' || saved === 'contrast') return saved;
      if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
        return 'dark';
      }
    } catch {
      /* ignore */
    }
    return 'light';
  });
  const [fontScale, setFontScale] = useState(() => {
    try {
      const v = parseFloat(localStorage.getItem('assetintel.fontScale') || '');
      if (v >= 0.875 && v <= 1.25) return v;
    } catch {
      /* ignore */
    }
    return 1;
  });

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    document.documentElement.style.setProperty('--font-scale', String(fontScale));
    try {
      localStorage.setItem('assetintel.theme', theme);
      localStorage.setItem('assetintel.fontScale', String(fontScale));
    } catch {
      /* private mode: prefs live for this session only */
    }
  }, [theme, fontScale]);

  const [profile, setProfile] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem('assetintel.profile') || '{}') || {};
    } catch {
      return {};
    }
  });

  useEffect(() => {
    try {
      localStorage.setItem('assetintel.profile', JSON.stringify(profile));
    } catch {
      /* private mode: profile lives for this session only */
    }
  }, [profile]);

  const demo = mode === 'demo';
  const fixtureLabel = (fixtures.find((f) => f.id === fixtureId) || {}).label || '';
  const fixtureBlurb = (fixtures.find((f) => f.id === fixtureId) || {}).blurb || '';
  const activeData = mode === 'new' ? apiData : demoData;
  const result = activeData.result;
  const note = activeData.note;
  const images = activeData.images;
  const activeImage = images[tab] || null;
  const canvasW = activeImage ? activeImage.width : FALLBACK_DIMS.width;
  const canvasH = activeImage ? activeImage.height : FALLBACK_DIMS.height;
  const segs = (result ? result.segmentations : []).filter(
    (s) => s.source_image === `image_${tab}`
  );
  const headerStatus = (() => {
    if (!result) return 'no inspection loaded';
    const cost = costText(result);
    const costPart = cost.priced ? `${cost.text} estimated` : 'not yet priced';
    return `${result.asset_id} · ${result.request_id} · ${costPart}`;
  })();

  function switchTab(next) {
    setMode(next);
    setTab(0);
    setSelectedMaskId(null);
    setSelectedSpan(null);
    setReviewStatus('');
    setError('');
  }

  async function showFixture(id) {
    setFixtureLoading(true);
    setError('');
    try {
      const loaded = await loadFixture(id);
      setMode('demo');
      setFixtureId(id);
      setFixtureCase(`${loaded.data.suite} \u00b7 ${loaded.data.case_id}`);
      setDemoData({
        result: loaded.data.result,
        note: loaded.data.note,
        images: [{ url: loaded.imageUrl, width: loaded.width, height: loaded.height }],
      });
      setTab(0);
      setReviewStatus('');
      setSelectedMaskId(null);
      setSelectedSpan(null);
    } catch (e) {
      setError(e.message || String(e));
    } finally {
      setFixtureLoading(false);
    }
  }

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const list = await loadFixtureIndex();
        if (cancelled) return;
        if (!list.length) {
          setFixtureLoading(false);
          return;
        }
        setFixtures(list);
        await showFixture(list[0].id);
      } catch (e) {
        if (!cancelled) {
          setError(e.message || String(e));
          setFixtureLoading(false);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function onSubmit({ files, note: n, assetId }) {
    setBusy(true);
    setError('');
    setReviewStatus('');
    try {
      const loaded = await Promise.all(files.map(imageDims));
      const out = await submitInspection({
        images: files,
        note: n,
        assetMeta: assetId ? { asset_id: assetId } : {},
        apiKey,
      });
      setMode('new');
      setApiData({ result: out, note: n, images: loaded });
      setTab(0);
      setSelectedMaskId(null);
      setSelectedSpan(null);
    } catch (e) {
      setError(e.message || String(e));
    } finally {
      setBusy(false);
    }
  }

  function onEvidenceClick(ev) {
    setSelectedMaskId(ev.mask_id || null);
    setSelectedSpan(ev.span || null);
  }

  async function onReview(decision, note) {
    if (!result) return;
    const res = await submitReview(result.request_id, decision, note, apiKey);
    setReviewStatus(`Recorded: ${res.status || decision}`);
  }

  return (
    <div className="app">
      <Header
        status={headerStatus}
      />


      <div className="mode-toggle" role="tablist" aria-label="Views">
        <button
          role="tab"
          aria-selected={demo}
          className={demo ? 'active tab-demo' : 'tab-demo'}
          onClick={() => switchTab('demo')}
        >
          <PlayIcon size={16} /> Demo
        </button>
        <button
          role="tab"
          aria-selected={mode === 'new'}
          className={mode === 'new' ? 'active tab-new' : 'tab-new'}
          onClick={() => switchTab('new')}
        >
          <CodeIcon size={16} /> New inspection
        </button>
        <button
          role="tab"
          aria-selected={mode === 'insights'}
          className={mode === 'insights' ? 'active tab-insights' : 'tab-insights'}
          onClick={() => switchTab('insights')}
        >
          <ChartIcon size={16} /> Insights
        </button>
        <button
          role="tab"
          aria-selected={mode === 'settings'}
          className={mode === 'settings' ? 'active tab-settings' : 'tab-settings'}
          onClick={() => switchTab('settings')}
        >
          <GearIcon size={16} /> Settings
        </button>
        <button
          role="tab"
          aria-selected={mode === 'about'}
          className={mode === 'about' ? 'active tab-about' : 'tab-about'}
          onClick={() => switchTab('about')}
        >
          <InfoIcon size={16} /> About
        </button>
      </div>

      {demo && (
        <div className="panel">
          <h2>Demo fixture</h2>
          <label className="fixture-picker">
            Choose a case:
            <select
              value={fixtureId}
              disabled={fixtureLoading || fixtures.length === 0}
              onChange={(e) => showFixture(e.target.value)}
            >
              {fixtures.map((f) => (
                <option key={f.id} value={f.id}>
                  {f.label}
                </option>
              ))}
            </select>
          </label>
        </div>
      )}

      {demo && fixtureBlurb && (
        <p className="fixture-blurb">
          {fixtureBlurb} <span className="muted">({fixtureCase})</span>
        </p>
      )}

      {demo && !result && !error && (
        <div className="panel">
          <p>Loading fixtures…</p>
        </div>
      )}

      {demo && error && (
        <div className="panel">
          <p className="warn">{error}</p>
        </div>
      )}

      {mode === 'settings' && (
        <SettingsPanel
          apiKey={apiKey}
          onApiKey={setApiKey}
          theme={theme}
          onTheme={setTheme}
          fontScale={fontScale}
          onFontScale={(v) => setFontScale(Math.min(1.25, Math.max(0.875, Math.round(v * 8) / 8)))}
          profile={profile}
          onProfile={setProfile}
        />
      )}

      {mode === 'about' && <AboutPanel />}

      {mode === 'insights' && <InsightsPanel apiKey={apiKey} onApiKey={setApiKey} profile={profile} />}

      {mode === 'new' && (
        <div className="panel">
          <h2>New inspection</h2>
          <UploadForm onSubmit={onSubmit} busy={busy} error={error} apiKeySet={!!apiKey} />
        </div>
      )}

      {result && (mode === 'demo' || mode === 'new') && (
        <div className="layout result-layout" ref={resultRef}>
          <div className="ledger-sticky">
            <div className="panel">
              <h2>
                Overlay {demo && fixtureLabel && (
                <span className="warn">({fixtureLabel} — fixture data)</span>
              )}
              </h2>
              {images.length > 1 && (
                <div className="image-tabs">
                  {images.map((_, i) => (
                    <button
                      key={i}
                      className={tab === i ? 'active' : ''}
                      onClick={() => {
                        setTab(i);
                        setSelectedMaskId(null);
                      }}
                    >
                      image_{i}
                    </button>
                  ))}
                </div>
              )}
              <MaskOverlay
                imageUrl={activeImage ? activeImage.url : null}
                apiKey={apiKey}
                overlayUrl={
                  mode === 'new' && result.request_id ? overlayUrl(result.request_id, tab) : null
                }
                width={canvasW}
                height={canvasH}
                segmentations={segs}
                selectedMaskId={selectedMaskId}
                onMaskClick={(id) => {
                  setSelectedMaskId(id);
                  setSelectedSpan(null);
                }}
              />
              <MaskRail
                segmentations={segs}
                selectedMaskId={selectedMaskId}
                onSelect={(id) => {
                  setSelectedMaskId(id);
                  setSelectedSpan(null);
                }}
              />
            </div>
          </div>
          <div>
            <div className="cta-group">
              <CostPill item={result} />
              <NextStepCta text={result.recommended_next_step} />
              <div className="panel">
                <h2>Human review {result.human_review_required ? '(required)' : ''}</h2>
                <ReviewActions
                  disabled={mode !== 'new'}
                  status={reviewStatus}
                  onReview={onReview}
                />
              </div>
              {mode === 'new' && (
                <div className="panel">
                  <h2>Export</h2>
                  <ExportDocument record={result} profile={profile} apiKey={apiKey} />
                </div>
              )}
            </div>
            <div className="panel evidence-card">
              <h2>Evidence</h2>
              <JsonViewer
                result={result}
                note={note}
                selectedMaskId={selectedMaskId}
                selectedSpan={selectedSpan}
                onEvidenceClick={onEvidenceClick}
                showNextStep={false}
              />
            </div>
            <div className="panel">
              <h2>Missing information</h2>
              <MissingChecklist items={result.missing_information} />
            </div>
          </div>
          <TetherLine
            containerRef={resultRef}
            selectedMaskId={selectedMaskId}
            segmentations={segs}
            canvasW={canvasW}
            canvasH={canvasH}
          />
        </div>
      )}

      <Footer />

    </div>
  );
}
