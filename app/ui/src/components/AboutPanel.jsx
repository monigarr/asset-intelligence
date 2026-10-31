import { ABOUT, SECTIONS, YOUTUBE_URL } from './about.js';

export default function AboutPanel() {
  return (
    <div className="panel about-panel">
      <h2>{ABOUT.title}</h2>
      <nav className="about-nav" aria-label="About sections">
        {SECTIONS.map((s) => (
          <a key={s.id} href={`#${s.id}`}>
            {s.label}
          </a>
        ))}
      </nav>
      <section id="about-product" aria-label="About">
        <h3>Asset Intelligence</h3>
        <p>
          <strong>{ABOUT.productLine}</strong>
        </p>
        <p>{ABOUT.purpose}</p>
        <h3>Built by {ABOUT.builder}</h3>
        <p>
          <strong>{ABOUT.builderRoles}</strong>
        </p>
        <p>{ABOUT.founderLine}</p>
        <h3>Built for {ABOUT.company}</h3>
        <p>{ABOUT.builtForBlurb}</p>
        <h3>
          <a href={ABOUT.hackathonUrl} target="_blank" rel="noreferrer">
            {ABOUT.hackathonName}
          </a>
        </h3>
        <p>{ABOUT.hackathonLine}</p>
        <p>
          <strong>Demo video:</strong>{' '}
          {YOUTUBE_URL ? (
            <a href={YOUTUBE_URL} target="_blank" rel="noreferrer">
              Watch on YouTube
            </a>
          ) : (
            ABOUT.videoNote
          )}
        </p>
      </section>
      <section id="extend-customize" aria-label="Extend and customize">
        <h3>{ABOUT.extendHeading}</h3>
        <p>
          <strong>{ABOUT.extendLead}</strong>
        </p>
        <p>{ABOUT.extendBody}</p>
        <p>
          <a href={`mailto:${ABOUT.servicesEmail}`}>{ABOUT.servicesEmail}</a>
          <br />
          <a href={ABOUT.companyUrl} target="_blank" rel="noreferrer">
            {ABOUT.product}
          </a>
        </p>
      </section>
      <section id="licensing" aria-label="Licensing and open source">
        <h3>{ABOUT.licenseHeading}</h3>
        <p>{ABOUT.licenseBlurb}</p>
        <p>
          <a href={ABOUT.licenseUrl} target="_blank" rel="noreferrer">
            Read the {ABOUT.licenseName}
          </a>
          {' \u00b7 '}
          <a href={ABOUT.githubUrl} target="_blank" rel="noreferrer">
            Repository
          </a>
        </p>
        <p>{ABOUT.distinction}</p>
        <p>{ABOUT.attribution}</p>
      </section>
    </div>
  );
}
