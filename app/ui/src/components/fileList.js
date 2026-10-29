// Pure file-list helpers for the upload form (tested in node, no DOM).
// Mirrors backend limits: 1-5 images, JPEG/PNG/WebP, 15 MB each.

export const MAX_FILES = 5;
export const MAX_BYTES = 15 * 1024 * 1024;
export const ACCEPTED_TYPES = ['image/jpeg', 'image/png', 'image/webp'];
export const ACCEPT_ATTR = ACCEPTED_TYPES.join(',');

export function formatBytes(n) {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

function fingerprint(f) {
  return `${f.name}::${f.size}::${f.lastModified || 0}`;
}

function extensionOk(name) {
  return /\.(jpe?g|png|webp)$/i.test(name || '');
}

// Merge newly picked files into the existing list. Returns { files, rejected }
// where rejected is [{ name, reason }] with reason in
// duplicate | too-many | type | too-large. Never mutates inputs.
export function mergeFiles(existing, incoming, opts = {}) {
  const max = opts.maxFiles || MAX_FILES;
  const maxBytes = opts.maxBytes || MAX_BYTES;
  const seen = new Set((existing || []).map(fingerprint));
  const files = [...(existing || [])];
  const rejected = [];
  for (const f of incoming || []) {
    const name = f.name || 'unnamed';
    if (seen.has(fingerprint(f))) {
      rejected.push({ name, reason: 'duplicate' });
      continue;
    }
    if (!ACCEPTED_TYPES.includes(f.type) && !extensionOk(name)) {
      rejected.push({ name, reason: 'type' });
      continue;
    }
    if (f.size > maxBytes) {
      rejected.push({ name, reason: 'too-large' });
      continue;
    }
    if (files.length >= max) {
      rejected.push({ name, reason: 'too-many' });
      continue;
    }
    seen.add(fingerprint(f));
    files.push(f);
  }
  return { files, rejected };
}

export function rejectionMessage({ name, reason }) {
  switch (reason) {
    case 'duplicate':
      return `${name}: already added`;
    case 'too-many':
      return `${name}: rejected (max ${MAX_FILES} images)`;
    case 'type':
      return `${name}: rejected (JPEG/PNG/WebP only)`;
    case 'too-large':
      return `${name}: rejected (over ${formatBytes(MAX_BYTES)})`;
    default:
      return `${name}: rejected`;
  }
}
