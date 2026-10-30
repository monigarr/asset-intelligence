import { useState } from 'react';

// Global API key management. The key persists in browser local storage and
// is never displayed outside this masked field (New inspection only checks
// that a key exists).
export default function SettingsPanel({ apiKey, onApiKey, theme, onTheme, fontScale, onFontScale, profile = {}, onProfile }) {
  const [draft, setDraft] = useState(apiKey || '');
  const saved = !!apiKey;

  function save(e) {
    e.preventDefault();
    if (!draft.trim()) return;
    onApiKey(draft.trim());
  }

  function clear() {
    setDraft('');
    onApiKey('');
  }

  return (
    <div className="panel">
      <h2>Settings</h2>
      <form
        className="key-form"
        onSubmit={save}
      >
        <label>
          API key
          <input
            type="password"
            value={draft}
            autoComplete="off"
            placeholder={saved ? 'Saved - enter a new key to replace it' : 'Paste your API key'}
            onChange={(e) => setDraft(e.target.value)}
          />
          <span className="hint">
            Stored only in this browser and sent as X-API-Key. Need a key?
            Contact{' '}
            <a href="mailto:monica@manageassets.net">monica@manageassets.net</a>.
          </span>
        </label>
        <div className="filter-actions">
          <button type="submit" className="primary" disabled={!draft.trim()}>
            Save API key
          </button>
          {saved && (
            <button type="button" onClick={clear}>
              Remove
            </button>
          )}
        </div>
      </form>
      {saved && <p className="hint">API key saved in this browser.</p>}
      <h3>Appearance</h3>
      <div className="segmented" role="radiogroup" aria-label="Theme">
        {['light', 'dark', 'contrast'].map((t) => (
          <button
            key={t}
            type="button"
            role="radio"
            aria-checked={theme === t}
            onClick={() => onTheme(t)}
          >
            {t[0].toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>
      <h3>Text size</h3>
      <div className="font-stepper">
        <button
          type="button"
          aria-label="Decrease text size"
          disabled={fontScale <= 0.875}
          onClick={() => onFontScale(fontScale - 0.125)}
        >
          A-
        </button>
        <output>{Math.round(fontScale * 100)}%</output>
        <button
          type="button"
          aria-label="Increase text size"
          disabled={fontScale >= 1.25}
          onClick={() => onFontScale(fontScale + 0.125)}
        >
          A+
        </button>
      </div>
      <h3>Export identity</h3>
      <p>Your full name, email, and export signature are added to the footer of every document you export from this interface.</p>
      <div className="key-form">
        <label>
          Full name
          <input
            type="text"
            value={profile.name || ''}
            autoComplete="off"
            placeholder="Monica Peters"
            onChange={(e) => onProfile({ ...profile, name: e.target.value })}
          />
        </label>
        <label>
          Email
          <input
            type="email"
            value={profile.email || ''}
            autoComplete="off"
            placeholder="monica@manageassets.net"
            onChange={(e) => onProfile({ ...profile, email: e.target.value })}
          />
        </label>
        <label className="review-note">
          Export signature
          <textarea
            value={profile.signature || ''}
            rows={2}
            maxLength={500}
            placeholder="Title, company, credentials"
            onChange={(e) => onProfile({ ...profile, signature: e.target.value })}
          />
        </label>
      </div>
    </div>
  );
}