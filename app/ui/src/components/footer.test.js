import { describe, expect, it } from 'vitest';
import { FOOTER } from './footer.js';

describe('FOOTER', () => {
  it('states copyright, company link parts, and event', () => {
    expect(FOOTER.copyright).toBe('\u00a9 2026 Monica Peters');
    expect(FOOTER.builtFor).toBe('Built for');
    expect(FOOTER.company).toBe('Manage Assets Inc.');
    expect(FOOTER.companyUrl).toBe('https://manageassets.ca/');
    expect(FOOTER.middle).toBe('Open-Source AI Extension');
    expect(FOOTER.event).toBe('Meta Global AI Hackathon');
    expect(FOOTER.separator).toBe('\u00b7');
  });

  it('states product promise with em dash', () => {
    expect(FOOTER.product).toBe('Asset Intelligence');
    expect(FOOTER.dash).toBe('\u2014');
    expect(FOOTER.promise).toBe('Evidence-linked AI. Human-approved decisions. Infrastructure intelligence you can trust.');
  });
});
