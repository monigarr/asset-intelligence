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

export async function submitReview(requestId, decision, edits, apiKey) {
  const res = await fetch(`/v1/inspections/${encodeURIComponent(requestId)}/review`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(apiKey ? { 'X-API-Key': apiKey } : {}),
    },
    body: JSON.stringify({ decision, edits: edits || null }),
  });
  if (!res.ok) throw new Error(`review failed: ${res.status} ${await res.text()}`);
  return res.json();
}
