// Canvas mask helpers: colorblind redundancy, glove-size picking, rail cycling.
// Pure logic kept out of MaskOverlay.jsx so vitest can cover it (DESIGN.md D).
export const MIN_TARGET_PX = 24;

const LABEL_DASH = {
  crack: [],
  corrosion: [6, 3],
  spall: [2, 3],
  vegetation: [8, 3, 2, 3],
  'water seepage': [4, 2],
  'water intrusion': [4, 2],
};

export function dashForLabel(label) {
  return LABEL_DASH[String(label || '').toLowerCase()] || [];
}

export function confidenceLabel(label, confidence) {
  const n = confidence === null || confidence === undefined || confidence === '' ? NaN : Number(confidence);
  return `${label} \u00b7 SAM ${Number.isFinite(n) ? n.toFixed(2) : '?'}`;
}

export function hitTest(bbox, x, y, slop = 0) {
  const [x1, y1, x2, y2] = bbox;
  return x >= x1 - slop && x <= x2 + slop && y >= y1 - slop && y <= y2 + slop;
}

function area(bbox) {
  return Math.max(0, bbox[2] - bbox[0]) * Math.max(0, bbox[3] - bbox[1]);
}

export function pickMask(segmentations, x, y, slop = 0) {
  const hits = (segmentations || []).filter((s) => hitTest(s.bbox, x, y, slop));
  hits.sort((a, b) => area(a.bbox) - area(b.bbox));
  return hits.length ? hits[0].mask_id : null;
}

export function cycleIndex(count, current, dir) {
  if (!count || count <= 0) return 0;
  return (((current + dir) % count) + count) % count;
}