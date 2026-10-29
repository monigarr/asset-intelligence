import { useEffect, useState } from 'react';
import { overlayUrl, submitInspection, submitReview } from './api.js';
import { loadFixture, loadFixtureIndex } from './demo/fixtures.js';
import JsonViewer from './components/JsonViewer.jsx';
import MaskOverlay from './components/MaskOverlay.jsx';
import MissingChecklist from './components/MissingChecklist.jsx';
import ReviewActions from './components/ReviewActions.jsx';
import UploadForm from './components/UploadForm.jsx';
import Header from './components/Header.jsx';
import AboutPanel from './components/AboutPanel.jsx';
import InsightsPanel from './components/InsightsPanel.jsx';
import { ChartIcon, CodeIcon, InfoIcon, PlayIcon } from './components/icons.jsx';

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
  const [apiKey, setApiKey] = useState('');
  const [selectedMaskId, setSelectedMaskId] = useState(null);
  const [selectedSpan, setSelectedSpan] = useState(null);
  const [reviewStatus, setReviewStatus] = useState('');

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

  async function onSubmit({ files, note: n, assetId, apiKey: key }) {
    setBusy(true);
    setError('');
    setReviewStatus('');
    try {
      const loaded = await Promise.all(files.map(imageDims));
      const out = await submitInspection({
        images: files,
        note: n,
        assetMeta: assetId ? { asset_id: assetId } : {},
        apiKey: key,
      });
      setMode('new');
      setApiData({ result: out, note: n, images: loaded });
      setTab(0);
      setApiKey(key);
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
        status={result ? `${result.asset_id} \u00b7 ${result.request_id}` : 'no inspection loaded'}
      />


      <div className="mode-toggle" role="tablist" aria-label="Views">
        <button
          role="tab"
          aria-selected={demo}
          className={demo ? 'active' : ''}
          onClick={() => switchTab('demo')}
        >
          <PlayIcon size={16} /> Demo
        </button>
        <button
          role="tab"
          aria-selected={mode === 'new'}
          className={mode === 'new' ? 'active' : ''}
          onClick={() => switchTab('new')}
        >
          <CodeIcon size={16} /> New inspection
        </button>
        <button
          role="tab"
          aria-selected={mode === 'about'}
          className={mode === 'about' ? 'active' : ''}
          onClick={() => switchTab('about')}
        >
          <InfoIcon size={16} /> About
        </button>
        <button
          role="tab"
          aria-selected={mode === 'insights'}
          className={mode === 'insights' ? 'active' : ''}
          onClick={() => switchTab('insights')}
        >
          <ChartIcon size={16} /> Insights
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

      {mode === 'about' && <AboutPanel />}

      {mode === 'insights' && <InsightsPanel apiKey={apiKey} onApiKey={setApiKey} />}

      {mode === 'new' && (
        <div className="panel">
          <h2>New inspection</h2>
          <UploadForm onSubmit={onSubmit} busy={busy} error={error} />
        </div>
      )}

      {result && (mode === 'demo' || mode === 'new') && (
        <div className="layout">
          <div>
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
            </div>
            <div className="panel">
              <h2>Human review {result.human_review_required ? '(required)' : ''}</h2>
              <ReviewActions
                disabled={mode !== 'new'}
                status={reviewStatus}
                onReview={onReview}
              />
            </div>
          </div>
          <div>
            <div className="panel">
              <h2>Missing information</h2>
              <MissingChecklist items={result.missing_information} />
            </div>
            <div className="panel">
              <h2>Evidence</h2>
              <JsonViewer
                result={result}
                note={note}
                selectedMaskId={selectedMaskId}
                selectedSpan={selectedSpan}
                onEvidenceClick={onEvidenceClick}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
