import { describe, expect, it } from 'vitest';
import { ABOUT, YOUTUBE_URL } from './about.js';

describe('about content', () => {
  it('links to the repo, hackathon, and product', () => {
    expect(ABOUT.githubUrl).toBe('https://github.com/monigarr/asset-intelligence');
    expect(ABOUT.hackathonUrl).toBe('https://dev.meta.ai/');
    expect(ABOUT.contactUrl).toBe('https://manageassets.ca/contact/');
  });

  it('has a short public blurb and credits', () => {
    expect(ABOUT.blurb.length).toBeGreaterThan(20);
    expect(ABOUT.blurb.length).toBeLessThan(400);
    expect(ABOUT.builder).toBe('Monica Peters');
    expect(ABOUT.productBlurb).toContain('Self-hosted');
  });

  it('youtube placeholder is a string (empty until the link ships)', () => {
    expect(typeof YOUTUBE_URL).toBe('string');
  });
});
