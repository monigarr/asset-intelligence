import { ABOUT, YOUTUBE_URL } from './about.js';

export default function AboutPanel() {
  return (
    <div className="panel">
      <h2>{ABOUT.title}</h2>
      <p>
        <strong>Asset Intelligence</strong> {ABOUT.blurb}
      </p>
      <h3>Built by {ABOUT.builder}</h3>
      <p>
        <strong>{ABOUT.builderRoles}</strong>
      </p>
      <p>
        I am the founder of{' '}
        <a href={ABOUT.companyUrl} target="_blank" rel="noreferrer">
          {ABOUT.company}
        </a>
        {ABOUT.builderFounderRest}
      </p>
      <p>{ABOUT.builderSolo}</p>
      <p>{ABOUT.builderScope}</p>
      <h3>Built for {ABOUT.company}</h3>
      <p>{ABOUT.platformPara}</p>
      <p>
        <strong>Our approach:</strong> {ABOUT.approach}
      </p>
      <h3>{ABOUT.hackathonName}</h3>
      <p>
        Developed as an open-source project for the{' '}
        <a href={ABOUT.hackathonUrl} target="_blank" rel="noreferrer">
          {ABOUT.hackathonName}
        </a>
        {ABOUT.hackathonRest}
      </p>
      <p>
        <strong>Company:</strong>{' '}
        <a href={ABOUT.companyUrl} target="_blank" rel="noreferrer">
          {ABOUT.company}
        </a>
        <br />
        <strong>Founder &amp; Developer:</strong> {ABOUT.builder}
        <br />
        <strong>Project:</strong> {ABOUT.projectLine}
        <br />
        <strong>Demo:</strong>{' '}
        {YOUTUBE_URL ? (
          <a href={YOUTUBE_URL} target="_blank" rel="noreferrer">
            Watch on YouTube
          </a>
        ) : (
          ABOUT.videoNote
        )}
      </p>
    </div>
  );
}