import { useEffect, useRef, useState } from 'react';
import {
  ACCEPT_ATTR,
  MAX_FILES,
  formatBytes,
  mergeFiles,
  rejectionMessage,
} from './fileList.js';

export default function UploadForm({ onSubmit, busy, error, apiKeySet }) {
  const [files, setFiles] = useState([]);
  const [previews, setPreviews] = useState([]);
  const [rejected, setRejected] = useState([]);
  const [dragging, setDragging] = useState(false);
  const [note, setNote] = useState('');
  const [assetId, setAssetId] = useState('');
  const inputRef = useRef(null);
  const previewsRef = useRef([]);
  previewsRef.current = previews;

  useEffect(() => () => previewsRef.current.forEach((u) => URL.revokeObjectURL(u)), []);

  const valid = files.length >= 1 && files.length <= MAX_FILES && !busy && apiKeySet;
  const zoneClass = ['dropzone', dragging && 'dragging', files.length === 0 && !dragging && 'blueprint']
    .filter(Boolean)
    .join(' ');

  function addIncoming(list) {
    const { files: next, rejected: rej } = mergeFiles(files, Array.from(list || []));
    const fresh = next.slice(files.length).map((f) => URL.createObjectURL(f));
    setFiles(next);
    setPreviews((p) => [...p, ...fresh]);
    setRejected(rej.map(rejectionMessage));
  }

  function removeAt(i) {
    URL.revokeObjectURL(previews[i]);
    setFiles(files.filter((_, j) => j !== i));
    setPreviews(previews.filter((_, j) => j !== i));
  }

  return (
    <form
      className="upload-form"
      onSubmit={(e) => {
        e.preventDefault();
        if (valid) onSubmit({ files, note, assetId });
      }}
    >
      <div
        className={zoneClass}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          if (!busy) addIncoming(e.dataTransfer.files);
        }}
      >
        <p>
          Inspection photos ({files.length}/{MAX_FILES}) — JPEG/PNG/WebP, ≤15MB each
        </p>
        <p className="hint">Drop 1-5 photos + field note. Drag &amp; drop here, or</p>
        <button
          type="button"
          disabled={busy}
          onClick={() => inputRef.current && inputRef.current.click()}
        >
          Add images
        </button>
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPT_ATTR}
          multiple
          hidden
          onChange={(e) => {
            addIncoming(e.target.files);
            e.target.value = '';
          }}
        />
      </div>
      {rejected.length > 0 && (
        <ul className="rejected">
          {rejected.map((m, i) => (
            <li key={i}>{m}</li>
          ))}
        </ul>
      )}
      {files.length > 0 && (
        <ul className="thumbs">
          {files.map((f, i) => (
            <li key={`${f.name}-${i}`}>
              <img src={previews[i]} alt={f.name} />
              <span className="thumb-name">{f.name}</span>
              <span className="hint">{formatBytes(f.size)}</span>
              <button
                type="button"
                className="chip"
                disabled={busy}
                onClick={() => removeAt(i)}
                aria-label={`Remove ${f.name}`}
              >
                ×
              </button>
            </li>
          ))}
        </ul>
      )}
      <label>
        Field note
        <textarea
          value={note}
          maxLength={10000}
          placeholder="Crack near top edge, seepage observed"
          onChange={(e) => setNote(e.target.value)}
        />
      </label>
      <label>
        Asset ID (optional)
        <input
          type="text"
          value={assetId}
          placeholder="DEMO-DRAIN-001"
          onChange={(e) => setAssetId(e.target.value)}
        />
      </label>
      {!apiKeySet && (
        <p className="hint">Add your API key in Settings to run inspections.</p>
      )}
      {error && <div className="error">{error}</div>}
      <div>
        <button type="submit" className="primary" disabled={!valid}>
          {busy ? 'Inspecting\u2026' : 'Run inspection'}
        </button>
      </div>
    </form>
  );
}
