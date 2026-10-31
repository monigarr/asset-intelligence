import { describe, expect, it } from 'vitest';
import { buildDocument, escapeHtml, EXPORT_FORMATS, mergeInspectionImages } from './exportDocument.js';

const RECORD = {
  request_id: 'req_123',
  asset_id: 'DRAIN-1',
  review_status: 'accept',
  observations: [{ text: 'Crack <b>big</b>' }],
  discrepancies: [],
  missing_information: ['scale'],
  recommended_next_step: 'Re-photograph with a scale reference.',
  cost_cents: 59.2,
  cost_priced: true,
  durations_ms: {},
  model_trace: { sam: 'sam-3.1', vision: 'muse-spark-1.3', reasoning: 'muse-spark-1.3', planning: 'muse-wonder-1.0' },
};
const AT = '2026-10-30T01:02:03.000Z';

describe('buildDocument', () => {
  it('leads markdown with the bold next step and export timestamp', () => {
    const doc = buildDocument(RECORD, 'md', AT);
    expect(doc.filename).toBe('inspection-req_123-20261030T010203.md');
    expect(doc.mime).toBe('text/markdown');
    const lines = doc.text.split('\n');
    expect(lines[2]).toBe('**Recommended next step:** Re-photograph with a scale reference.');
    expect(doc.text).toContain(`Exported: ${AT}`);
    expect(doc.text).toContain('$0.59 estimated');
    expect(doc.text).toContain('Crack <b>big</b>');
  });

  it('renders plain text with caps emphasis', () => {
    const doc = buildDocument(RECORD, 'txt', AT);
    expect(doc.filename.endsWith('.txt')).toBe(true);
    expect(doc.text).toContain('RECOMMENDED NEXT STEP: Re-photograph with a scale reference.');
    expect(doc.text).toContain(`Exported: ${AT}`);
  });

  it('escapes html and falls back to markdown', () => {
    const doc = buildDocument(RECORD, 'html', AT);
    expect(doc.text).toContain('<strong>Recommended next step:</strong>');
    expect(doc.text).toContain('Crack &lt;b&gt;big&lt;/b&gt;');
    expect(doc.text).not.toContain('<b>big</b>');
    expect(buildDocument(RECORD, 'bogus', AT).mime).toBe('text/markdown');
    expect(escapeHtml(null)).toBe('');
  });
});

describe('export footer', () => {
  const profile = {
    name: 'Monica Peters',
    email: 'monica@example.org',
    signature: 'Founder, Manage Assets Inc.',
  };
  it('stamps timestamp, id, email, name, and signature', () => {
    const md = buildDocument(RECORD, 'md', AT, profile).text;
    expect(md).toContain(`Exported: ${AT}\nRequest ID: req_123\nmonica@example.org\nMonica Peters`);
    expect(md).toContain('Manage Assets Inc. Website: ManageAssets.net');
    expect(md).toContain('Founder, Manage Assets Inc.');
    expect(md).toContain('This document is prepared by Asset Intelligence Software for Manage Assets Inc.');
    expect(buildDocument(RECORD, 'txt', AT, profile).text).toContain('Manage Assets Inc. Website: ManageAssets.net');
    const html = buildDocument(RECORD, 'html', AT, profile).text;
    expect(html).toContain('<footer>');
    expect(html).toContain('prepared by Asset Intelligence Software');
    expect(html).toContain('<address>');
    expect(html).toContain('Founder, Manage Assets Inc.');
  });
  it('omits missing identity fields without artifacts', () => {
    const md = buildDocument(RECORD, 'md', AT, {}).text;
    expect(md).toContain(`Exported: ${AT}\nRequest ID: req_123\nManage Assets Inc. Website: ManageAssets.net`);
    expect(md).not.toContain('undefined');
    expect(md).not.toContain('<>');
  });
});

describe('export images', () => {
  const IMGS = [
    { index: 0, kind: 'photo', dataUrl: 'data:image/jpeg;base64,AAA' },
    { index: 0, kind: 'overlay', dataUrl: 'data:image/png;base64,BBB' },
  ];
  it('embeds photo then overlay per image in markdown and html', () => {
    const md = buildDocument(RECORD, 'md', AT, {}, IMGS).text;
    expect(md).toContain('![image 1 (no masks)](data:image/jpeg;base64,AAA)');
    expect(md).toContain('![image 1 (with masks)](data:image/png;base64,BBB)');
    expect(md.indexOf('no masks')).toBeLessThan(md.indexOf('with masks'));
    const html = buildDocument(RECORD, 'html', AT, {}, IMGS).text;
    expect(html).toContain('<figcaption>image 1 (no masks)</figcaption>');
    expect(html).toContain('<figcaption>image 1 (with masks)</figcaption>');
    expect(buildDocument(RECORD, 'txt', AT, {}, IMGS).text).toContain(
      'see Markdown or HTML export for 1 photo and 1 overlay'
    );
  });
  it('notes honestly when a kind is missing', () => {
    const overlaysOnly = buildDocument(
      RECORD, 'md', AT, {}, [{ index: 0, kind: 'overlay', dataUrl: 'data:image/png;base64,BBB' }],
    ).text;
    expect(overlaysOnly).toContain('(original photos were not stored for this inspection.)');
    const photosOnly = buildDocument(
      RECORD, 'md', AT, {}, [{ index: 0, kind: 'photo', dataUrl: 'data:image/jpeg;base64,AAA' }],
    ).text;
    expect(photosOnly).toContain('(no overlay images stored for this inspection.)');
    expect(buildDocument(RECORD, 'md', AT, {}, []).text).toContain(
      '(no images stored for this inspection)'
    );
  });
});

describe('mergeInspectionImages', () => {
  it('interleaves photo before overlay per index', () => {
    const photo = { index: 1, blob: 'pb', mime: 'image/jpeg' };
    const overlay0 = { index: 0, blob: 'ob0', mime: 'image/png' };
    const overlay1 = { index: 1, blob: 'ob1', mime: 'image/png' };
    expect(mergeInspectionImages([photo], [overlay0, overlay1])).toEqual([
      { index: 0, kind: 'overlay', blob: 'ob0' },
      { index: 1, kind: 'photo', blob: 'pb' },
      { index: 1, kind: 'overlay', blob: 'ob1' },
    ]);
    expect(mergeInspectionImages([], [])).toEqual([]);
    expect(mergeInspectionImages(null, undefined)).toEqual([]);
  });
});

describe('EXPORT_FORMATS', () => {
  it('offers three text formats', () => {
    expect(EXPORT_FORMATS.map((f) => f.id)).toEqual(['md', 'txt', 'html']);
  });
});