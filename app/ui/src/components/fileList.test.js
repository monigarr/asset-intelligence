import { describe, expect, it } from 'vitest';
import {
  ACCEPT_ATTR,
  MAX_BYTES,
  MAX_FILES,
  formatBytes,
  mergeFiles,
  rejectionMessage,
} from './fileList.js';

function fake(name, size = 100, type = 'image/jpeg') {
  return { name, size, type, lastModified: 1 };
}

describe('fileList', () => {
  it('exposes backend-matching limits', () => {
    expect(MAX_FILES).toBe(5);
    expect(MAX_BYTES).toBe(15 * 1024 * 1024);
    expect(ACCEPT_ATTR).toBe('image/jpeg,image/png,image/webp');
  });

  it('merges picks incrementally without mutating', () => {
    const a = [fake('a.jpg')];
    const { files, rejected } = mergeFiles(a, [fake('b.png'), fake('c.webp')]);
    expect(files.map((f) => f.name)).toEqual(['a.jpg', 'b.png', 'c.webp']);
    expect(rejected).toEqual([]);
    expect(a).toHaveLength(1);
  });

  it('skips duplicates by fingerprint', () => {
    const { files, rejected } = mergeFiles([fake('a.jpg', 100)], [fake('a.jpg', 100)]);
    expect(files).toHaveLength(1);
    expect(rejected).toEqual([{ name: 'a.jpg', reason: 'duplicate' }]);
  });

  it('enforces type, size, and count limits', () => {
    const full = [0, 1, 2, 3, 4].map((i) => fake(`${i}.jpg`));
    const { files, rejected } = mergeFiles(full, [
      fake('doc.pdf', 100, 'application/pdf'),
      fake('huge.jpg', MAX_BYTES + 1),
      fake('extra.jpg'),
    ]);
    expect(files).toHaveLength(5);
    expect(rejected.map((r) => r.reason)).toEqual(['type', 'too-large', 'too-many']);
  });

  it('accepts by extension when MIME type is missing', () => {
    const { files, rejected } = mergeFiles([], [{ name: 'a.png', size: 10, type: '' }]);
    expect(files).toHaveLength(1);
    expect(rejected).toEqual([]);
  });

  it('formats bytes and rejection messages', () => {
    expect(formatBytes(500)).toBe('500 B');
    expect(formatBytes(2048)).toBe('2.0 KB');
    expect(rejectionMessage({ name: 'x', reason: 'too-many' })).toContain('max 5');
  });
});
