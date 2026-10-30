import { describe, expect, it } from 'vitest';
import { ABOUT, TAGLINE, YOUTUBE_URL } from './about.js';

describe('about content', () => {
  it('links to the repo, hackathon, and product', () => {
    expect(ABOUT.githubUrl).toBe('https://github.com/monigarr/asset-intelligence');
    expect(ABOUT.hackathonUrl).toBe('https://dev.meta.ai/');
    expect(ABOUT.contactUrl).toBe('https://manageassets.ca/contact/');
    expect(ABOUT.companyUrl).toBe('https://manageassets.ca/');
  });

  it('has a short public blurb and credits', () => {
    expect(ABOUT.blurb.length).toBeGreaterThan(20);
    expect(ABOUT.blurb.length).toBeLessThan(400);
    expect(ABOUT.builder).toBe('Monica Peters');
    expect(ABOUT.company).toBe('Manage Assets Inc.');
    expect(ABOUT.builderRoles).toContain('Forward Deployed Engineer');
    expect(ABOUT.approach).toContain('Human-approved decisions');
    expect(ABOUT.projectLine).toContain('Open-Source Extension');
    expect(ABOUT.productBlurb).toContain('Self-hosted');
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
