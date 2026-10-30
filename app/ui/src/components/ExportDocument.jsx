import { useState } from 'react';
import { fetchOriginalBlobs, fetchOverlayBlobs } from '../api.js';
import { blobToDataUrl, buildDocument, EXPORT_FORMATS, mergeInspectionImages } from './exportDocument.js';

// Export the inspection detail as a downloadable document (Markdown / text /
// HTML) with photo + overlay images embedded. Fetch failures cancel the export.
export default function ExportDocument({ record, profile, apiKey }) {
  const [formatId, setFormatId] = useState('md');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  async function download() {
    setBusy(true);
    setError('');
    try {
      const [overlayRaws, photoRaws] = await Promise.all([
        fetchOverlayBlobs(record.request_id, apiKey),
        fetchOriginalBlobs(record.request_id, apiKey),
      ]);
      const images = [];
      for (const m of mergeInspectionImages(photoRaws, overlayRaws)) {
        images.push({ index: m.index, kind: m.kind, dataUrl: await blobToDataUrl(m.blob) });
      }
      const doc = buildDocument(record, formatId, undefined, profile, images);
      const blob = new Blob([doc.text], { type: `${doc.mime};charset=utf-8` });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = doc.filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (e) {
      setError('Could not load inspection images. Export cancelled.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <label>
        Format
        <select value={formatId} onChange={(e) => setFormatId(e.target.value)}>
          {EXPORT_FORMATS.map((f) => (
            <option key={f.id} value={f.id}>
              {f.label}
            </option>
          ))}
        </select>
      </label>
      <div>
        <button type="button" className="primary" disabled={busy} onClick={download}>
          {busy ? 'Preparing...' : 'Export document'}
        </button>
      </div>
      {error && <div className="error">{error}</div>}
      <p className="hint">Saves to your computer. Nothing leaves this browser.</p>
    </div>
  );
}