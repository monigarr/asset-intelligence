import { costText, formatUSD, summarize } from './insights.js';

export const EXPORT_FORMATS = [
  { id: 'md', label: 'Markdown (.md)', ext: 'md', mime: 'text/markdown' },
  { id: 'txt', label: 'Plain text (.txt)', ext: 'txt', mime: 'text/plain' },
  { id: 'html', label: 'Web page (.html)', ext: 'html', mime: 'text/html' },
];

export function escapeHtml(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function identityParts(profile) {
  const p = profile || {};
  return {
    email: (p.email || '').trim(),
    name: (p.name || '').trim(),
    signature: (p.signature || '').trim(),
  };
}

function footerParts(item, createdAt, profile) {
  const { email, name, signature } = identityParts(profile);
  const lines = [`Exported: ${createdAt}`, `Request ID: ${item.request_id || 'unknown id'}`];
  if (email) lines.push(email);
  if (name) lines.push(name);
  if (signature) lines.push(signature);
  lines.push('Manage Assets Inc. Website: ManageAssets.net');
  lines.push(PREPARED_BY);
  return lines;
}

const PREPARED_BY = 'This document is prepared by Asset Intelligence Software for Manage Assets Inc.';

function footerText(item, createdAt, profile) {
  return ['---', ...footerParts(item, createdAt, profile)];
}

function stampName(requestId, createdAt, ext) {
  const safe = String(requestId || 'inspection').replace(/[^a-zA-Z0-9_-]/g, '-');
  const slug = createdAt.replace(/[-:]/g, '').slice(0, 15);
  return `inspection-${safe}-${slug}.${ext}`;
}

function rows(item) {
  const sum = summarize(item);
  const cost = costText(item);
  const trace = item.model_trace || {};
  return { sum, cost, trace };
}

function buildMarkdown(item, createdAt, profile, images) {
  const { sum, cost, trace } = rows(item);
  const out = [
    `# Inspection report: ${item.asset_id || 'unknown asset'} (${item.request_id || 'unknown id'})`,
    '',
    `**Recommended next step:** ${item.recommended_next_step || '(none recorded)'}`,
    '',
    `Exported: ${createdAt}`,
    '',
    ...imageMarkdown(images),
    `Status: ${item.review_status || 'pending'}`,
    `Findings: ${sum.obs} observations, ${sum.disc} discrepancies, ${sum.miss} missing items.`,
    `Cost: ${cost.priced ? `${formatUSD(item.cost_cents)} estimated` : 'not yet priced'}`,
    `Models: ${[trace.sam, trace.vision, trace.reasoning, trace.planning].filter(Boolean).join(', ')}`,
    '',
    '## Observations',
    ...(item.observations || []).map((ob) => `- ${ob.text || ''}`),
    '',
    '## Discrepancies',
    ...((item.discrepancies || []).length ? item.discrepancies.map((d) => `- ${d}`) : ['None flagged.']),
    '',
    '## Missing information',
    ...((item.missing_information || []).length
      ? item.missing_information.map((m) => `- ${m}`)
      : ['Nothing missing.']),
    '',
    ...footerText(item, createdAt, profile),
    '',
  ];
  return out.join('\n');
}

function buildText(item, createdAt, profile, images) {
  const { sum, cost, trace } = rows(item);
  const out = [
    `INSPECTION REPORT: ${item.asset_id || 'unknown asset'} (${item.request_id || 'unknown id'})`,
    '',
    `RECOMMENDED NEXT STEP: ${item.recommended_next_step || '(none recorded)'}`,
    '',
    `Exported: ${createdAt}`,
    '',
    ...imageTextNote(images),
    `Status: ${item.review_status || 'pending'}`,
    `Findings: ${sum.obs} observations, ${sum.disc} discrepancies, ${sum.miss} missing items.`,
    `Cost: ${cost.priced ? `${formatUSD(item.cost_cents)} estimated` : 'not yet priced'}`,
    `Models: ${[trace.sam, trace.vision, trace.reasoning, trace.planning].filter(Boolean).join(', ')}`,
    '',
    'OBSERVATIONS',
    ...(item.observations || []).map((ob) => `- ${ob.text || ''}`),
    '',
    'DISCREPANCIES',
    ...((item.discrepancies || []).length ? item.discrepancies.map((d) => `- ${d}`) : ['None flagged.']),
    '',
    'MISSING INFORMATION',
    ...((item.missing_information || []).length
      ? item.missing_information.map((m) => `- ${m}`)
      : ['Nothing missing.']),
    '',
    ...footerText(item, createdAt, profile),
    '',
  ];
  return out.join('\n');
}

function buildHtml(item, createdAt, profile, images) {
  const { sum, cost, trace } = rows(item);
  const footerHtml = footerParts(item, createdAt, profile).map(escapeHtml).join('<br />');
  const li = (arr, empty) =>
    arr.length ? arr.map((x) => `      <li>${escapeHtml(x)}</li>`).join('\n') : `      <li>${empty}</li>`;
  const obs = (item.observations || []).map((ob) => ob.text || '');
  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Inspection report: ${escapeHtml(item.asset_id || 'unknown asset')}</title>
  <style>body{font-family:system-ui,sans-serif;max-width:70ch;margin:24px;line-height:1.5}</style>
</head>
<body>
  <h1>Inspection report: ${escapeHtml(item.asset_id || 'unknown asset')} (${escapeHtml(item.request_id || 'unknown id')})</h1>
  <p><strong>Recommended next step:</strong> ${escapeHtml(item.recommended_next_step || '(none recorded)')}</p>
  <p>Exported: ${escapeHtml(createdAt)}</p>
${images.length ? images.map((img) => `  <figure>\n    <img src="${img.dataUrl}" alt="${captionFor(img)}" style="max-width:100%" />\n    <figcaption>${captionFor(img)}</figcaption>\n  </figure>`).join('\n') : '  <p>(no images stored for this inspection)</p>'}
${missingKindNote(images).filter(Boolean).map((line) => `  <p>${escapeHtml(line)}</p>`).join('\n')}
  <p>Status: ${escapeHtml(item.review_status || 'pending')}<br />
  Findings: ${sum.obs} observations, ${sum.disc} discrepancies, ${sum.miss} missing items.<br />
  Cost: ${escapeHtml(cost.priced ? `${formatUSD(item.cost_cents)} estimated` : 'not yet priced')}<br />
  Models: ${escapeHtml([trace.sam, trace.vision, trace.reasoning, trace.planning].filter(Boolean).join(', '))}</p>
  <h2>Observations</h2>
  <ul>
${li(obs, 'None.')}
  </ul>
  <h2>Discrepancies</h2>
  <ul>
${li(item.discrepancies || [], 'None flagged.')}
  </ul>
  <h2>Missing information</h2>
  <ul>
${li(item.missing_information || [], 'Nothing missing.')}
  </ul>
  <hr />
  <footer>
    <address>${footerHtml}</address>
  </footer>
</body>
</html>
`;
}

export function blobToDataUrl(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => reject(new Error('overlay read failed'));
    reader.readAsDataURL(blob);
  });
}

export function mergeInspectionImages(photoRaws, overlayRaws) {
  const byIndex = new Map();
  for (const r of photoRaws || []) byIndex.set(r.index, { photo: r });
  for (const r of overlayRaws || []) byIndex.set(r.index, { ...byIndex.get(r.index), overlay: r });
  const merged = [];
  for (const [index, pair] of [...byIndex.entries()].sort((a, b) => a[0] - b[0])) {
    if (pair.photo) merged.push({ index, kind: 'photo', blob: pair.photo.blob });
    if (pair.overlay) merged.push({ index, kind: 'overlay', blob: pair.overlay.blob });
  }
  return merged;
}

function captionFor(img) {
  const n = img.index + 1;
  return img.kind === 'photo' ? `image ${n} (no masks)` : `image ${n} (with masks)`;
}

function missingKindNote(images) {
  const kinds = new Set(images.map((img) => img.kind));
  if (kinds.has('overlay') && !kinds.has('photo')) {
    return ['(original photos were not stored for this inspection.)', ''];
  }
  if (kinds.has('photo') && !kinds.has('overlay')) {
    return ['(no overlay images stored for this inspection.)', ''];
  }
  return [];
}

function imageMarkdown(images) {
  if (!images.length) return ['(no images stored for this inspection)', ''];
  return [
    ...images.flatMap((img) => [`![${captionFor(img)}](${img.dataUrl})`, '']),
    ...missingKindNote(images),
  ];
}

function imageTextNote(images) {
  if (!images.length) return ['(no images stored for this inspection)', ''];
  const photos = images.filter((img) => img.kind === 'photo').length;
  const overlays = images.length - photos;
  const count = (n, word) => `${n} ${word}${n === 1 ? '' : 's'}`;
  const parts = [];
  if (photos) parts.push(count(photos, 'photo'));
  if (overlays) parts.push(count(overlays, 'overlay'));
  return [`(images: see Markdown or HTML export for ${parts.join(' and ')}.)`, '', ...missingKindNote(images)];
}

export function buildDocument(record, formatId, createdAt, profile, images = []) {
  const item = record || {};
  const format = EXPORT_FORMATS.find((f) => f.id === formatId) || EXPORT_FORMATS[0];
  const at = createdAt || new Date().toISOString();
  const text =
    format.id === 'html'
      ? buildHtml(item, at, profile, images)
      : format.id === 'txt'
        ? buildText(item, at, profile, images)
        : buildMarkdown(item, at, profile, images);
  return { filename: stampName(item.request_id, at, format.ext), mime: format.mime, text };
}