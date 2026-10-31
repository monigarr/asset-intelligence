import { describe, expect, it } from 'vitest';
import { ABOUT, SECTIONS, TAGLINE, YOUTUBE_URL } from './about.js';

describe('about content', () => {
  it('links to the repo, hackathon, and product', () => {
    expect(ABOUT.githubUrl).toBe('https://github.com/monigarr/asset-intelligence');
    expect(ABOUT.hackathonUrl).toBe('https://dev.meta.ai/events/global-hackathon');
    expect(ABOUT.contactUrl).toBe('https://manageassets.ca/contact/');
    expect(ABOUT.companyUrl).toBe('https://manageassets.ca/');
  });

  it('has three navigable sections', () => {
    expect(SECTIONS.map((s) => s.id)).toEqual(['about-product', 'extend-customize', 'licensing']);
    expect(SECTIONS.map((s) => s.label)).toEqual(['About', 'Extend & Customize', 'Licensing & Open Source']);
  });

  it('states product purpose and builder credits', () => {
    expect(ABOUT.productLine).toBe('Evidence-linked inspection intelligence');
    expect(ABOUT.purpose).toContain('human review and approval');
    expect(ABOUT.builder).toBe('Monica Peters');
    expect(ABOUT.builderRoles).toContain('Forward Deployed Engineer');
    expect(ABOUT.founderLine).toContain('solo developer');
    expect(ABOUT.company).toBe('Manage Assets Inc.');
    expect(ABOUT.builtForBlurb).toContain('United States and Canada');
    expect(ABOUT.hackathonLine).toContain('Meta AI stack');
    expect(ABOUT.videoNote).toBe('Coming soon.');
  });

  it('states extend and licensing terms', () => {
    expect(ABOUT.extendLead).toContain('engineering support');
    expect(ABOUT.extendBody).toContain('professional engineering services');
    expect(ABOUT.servicesEmail).toBe('monica@ManageAssets.net');
    expect(ABOUT.licenseName).toBe('Apache License 2.0');
    expect(ABOUT.licenseUrl).toContain('LICENSE');
    expect(ABOUT.licenseBlurb).toContain('free to use');
    expect(ABOUT.distinction).toContain('proprietary commercial software');
    expect(ABOUT.attribution).toContain('Copyright 2026 Monica Peters');
  });

  it('tagline is one short sentence', () => {
    expect(TAGLINE.length).toBeGreaterThan(20);
    expect(TAGLINE.length).toBeLessThan(80);
    expect(TAGLINE).toContain('evidence');
  });

  it('youtube placeholder is a string (empty until the link ships)', () => {
    expect(typeof YOUTUBE_URL).toBe('string');
  });
});
