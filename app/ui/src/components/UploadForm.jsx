import { useState } from 'react';

export default function UploadForm({ onSubmit, busy, error }) {
  const [files, setFiles] = useState([]);
  const [note, setNote] = useState('');
  const [assetId, setAssetId] = useState('');
  const [apiKey, setApiKey] = useState('');

  const valid = files.length >= 1 && files.length <= 5 && !busy;

  return (
    <form
      className="upload-form"
      onSubmit={(e) => {
        e.preventDefault();
        if (valid) onSubmit({ files, note, assetId, apiKey });
      }}
    >
      <label>
        Inspection photos (1–5, JPEG/PNG)
        <input
          type="file"
          accept="image/jpeg,image/png"
          multiple
          onChange={(e) => setFiles(Array.from(e.target.files || []).slice(0, 5))}
        />
        <span className="hint">{files.length} file(s) selected</span>
      </label>
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
      <label>
        API key
        <input
          type="text"
          value={apiKey}
          placeholder="local-dev-key-123"
          onChange={(e) => setApiKey(e.target.value)}
        />
      </label>
      {error && <div className="error">{error}</div>}
      <div>
        <button type="submit" className="primary" disabled={!valid}>
          {busy ? 'Inspecting…' : 'Run inspection'}
        </button>
      </div>
    </form>
  );
}
