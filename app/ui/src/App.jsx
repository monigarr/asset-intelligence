import { useState } from 'react';
import { overlayUrl, submitInspection, submitReview } from './api.js';
import { DEMO_IMAGE, DEMO_NOTE, DEMO_RESULT } from './demo/fixture.js';
import JsonViewer from './components/JsonViewer.jsx';
import MaskOverlay from './components/MaskOverlay.jsx';
import MissingChecklist from './components/MissingChecklist.jsx';
import ReviewActions from './components/ReviewActions.jsx';
import UploadForm from './components/UploadForm.jsx';

function imageDims(file) {
  return new Promise((resolve) => {
    const url = URL.createObjectURL(file);
    const img = new Image();
    img.onload = () => resolve({ url, width: img.naturalWidth, height: img.naturalHeight });
    img.onerror = () => resolve({ url, width: 640, height: 480 });
  });
}

export default function App() {
  const [mode, setMode] = useState('demo');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState(DEMO_RESULT);
  const [note, setNote] = useState(DEMO_NOTE);
  const [images, setImages] = useState([]); // [{url, width, height}]
  const [tab, setTab] = useState(0);
  const [apiKey, setApiKey] = useState('');
  const [selectedMaskId, setSelectedMaskId] = useState(null);
  const [selectedSpan, setSelectedSpan] = useState(null);
  const [reviewStatus, setReviewStatus] = useState('');

  const demo = mode === 'demo';
  const activeImage = images[tab] || null;
  const canvasW = activeImage ? activeImage.width : DEMO_IMAGE.width;
  const canvasH = activeImage ? activeImage.height : DEMO_IMAGE.height;
  const segs = (result ? result.segmentations : []).filter(
    (s) => s.source_image === `image_${tab}`
  );

  function showDemo() {
    setMode('demo');
    setResult(DEMO_RESULT);
    setNote(DEMO_NOTE);
    setImages([]);
    setTab(0);
    setError('');
    setReviewStatus('');
    setSelectedMaskId(null);
    setSelectedSpan(null);
  }

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
      setMode('api');
      setResult(out);
      setNote(n);
      setImages(loaded);
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

  async function onReview(decision) {
    if (!result) return;
    const res = await submitReview(result.request_id, decision, null, apiKey);
    setReviewStatus(`Recorded: ${res.status || decision}`);
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>Asset Intelligence — Review</h1>
        <span className="sub">
          {result ? `${result.asset_id} · ${result.request_id}` : 'no inspection loaded'}
        </span>
      </header>

      <div className="mode-toggle">
        <button className={demo ? 'active' : ''} onClick={showDemo}>
          Demo fixture
        </button>
        <button className={!demo ? 'active' : ''} onClick={() => setMode('api')}>
          API inspection
        </button>
      </div>

      {!demo && (
        <div className="panel">
          <h2>New inspection</h2>
          <UploadForm onSubmit={onSubmit} busy={busy} error={error} />
        </div>
      )}

      {result && (
        <div className="layout">
          <div>
            <div className="panel">
              <h2>
                Overlay {demo && <span className="warn">(demo schematic + fixture RLE)</span>}
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
                overlayUrl={
                  !demo && result.request_id ? overlayUrl(result.request_id, tab) : null
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
                disabled={demo}
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
