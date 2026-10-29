import { ABOUT, YOUTUBE_URL } from './about.js';

export default function AboutPanel() {
  return (
    <div className="panel">
      <h2>{ABOUT.title}</h2>
      <p>{ABOUT.blurb}</p>
      {YOUTUBE_URL ? (
        <p>
          <a href={YOUTUBE_URL} target="_blank" rel="noreferrer">
            Watch the demo video
          </a>
        </p>
      ) : (
        <p className="video-placeholder">Demo video (YouTube link coming soon)</p>
      )}
      <p>
        {ABOUT.builder} built and shipped this while participating as a competitor in the{' '}
        <a href={ABOUT.hackathonUrl} target="_blank" rel="noreferrer">
          {ABOUT.hackathonName}
        </a>
        .
      </p>
      <p>
        Developed to work with {ABOUT.product}: {ABOUT.productBlurb}
      </p>
    </div>
  );
}
