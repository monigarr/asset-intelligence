// Day-7 API contract client. Tolerant of two POST shapes:
//  - sync: POST /v1/inspections returns the full InspectionResult
//  - async: POST returns {request_id}; result polled via GET until complete.

export async function submitInspection({ images, note, assetMeta, apiKey }) {
  const form = new FormData();
  for (const file of images) form.append('images', file);
  form.append('note', note);
  form.append('asset_meta', JSON.stringify(assetMeta || {}));
  const res = await fetch('/v1/inspections', {
    method: 'POST',
    headers: apiKey ? { 'X-API-Key': apiKey } : {},
    body: form,
  });
  if (!res.ok) throw new Error(`submit failed: ${res.status} ${await res.text()}`);
  const data = await res.json();
  if (data && Array.isArray(data.observations)) return data; // sync shape
  if (data && data.request_id) return pollResult(data.request_id, apiKey);
  throw new Error('unexpected submit response shape');
}

export async function pollResult(requestId, apiKey, { tries = 30, delayMs = 1000 } = {}) {
  for (let i = 0; i < tries; i++) {
    const res = await fetch(`/v1/inspections/${encodeURIComponent(requestId)}`, {
      headers: apiKey ? { 'X-API-Key': apiKey } : {},
    });
    if (!res.ok) throw new Error(`poll failed: ${res.status}`);
    const data = await res.json();
    if (data && Array.isArray(data.observations)) return data;
    if (data && data.status === 'failed') {
      throw new Error(`inspection failed: ${data.error || 'unknown error'}`);
    }
    await new Promise((r) => setTimeout(r, delayMs));
  }
  throw new Error('timed out waiting for inspection result');
}

export function overlayUrl(requestId, imageIndex) {
  return `/v1/inspections/${encodeURIComponent(requestId)}/overlay?image=${imageIndex}`;
}

export async function submitReview(requestId, decision, note, apiKey) {
  const res = await fetch(`/v1/inspections/${encodeURIComponent(requestId)}/review`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(apiKey ? { 'X-API-Key': apiKey } : {}),
    },
    body: JSON.stringify({ decision, note: note || null }),
  });
  if (!res.ok) throw new Error(`review failed: ${res.status} ${await res.text()}`);
  return res.json();
}

export async function fetchInspections(apiKey, { limit = 50, reviewStatus = '', assetId = '' } = {}) {
  const params = new URLSearchParams({ limit: String(limit) });
  if (reviewStatus) params.set('review_status', reviewStatus);
  if (assetId) params.set('asset_id', assetId);
  const res = await fetch(`/v1/inspections?${params}`, {
    headers: apiKey ? { 'X-API-Key': apiKey } : {},
  });
  if (!res.ok) throw new Error(`history failed: ${res.status} ${await res.text()}`);
  return res.json();
}

export async function fetchStats(apiKey) {
  const res = await fetch('/v1/stats', {
    headers: apiKey ? { 'X-API-Key': apiKey } : {},
  });
  if (!res.ok) throw new Error(`stats failed: ${res.status} ${await res.text()}`);
  return res.json();
}

export async function fetchInspection(requestId, apiKey) {
  const res = await fetch(`/v1/inspections/${encodeURIComponent(requestId)}`, {
    headers: apiKey ? { 'X-API-Key': apiKey } : {},
  });
  if (!res.ok) throw new Error(`inspection failed: ${res.status} ${await res.text()}`);
  return res.json();
}

export async function fetchOverlays(requestId, apiKey, maxImages = 5) {
  const out = [];
  for (let i = 0; i < maxImages; i += 1) {
    const res = await fetch(`/v1/inspections/${encodeURIComponent(requestId)}/overlay?image=${i}`, {
      headers: apiKey ? { 'X-API-Key': apiKey } : {},
    });
    if (!res.ok) break; // indices are contiguous; first miss ends the set
    const blob = await res.blob();
    out.push({ index: i, url: URL.createObjectURL(blob) });
  }
  return out;
}
