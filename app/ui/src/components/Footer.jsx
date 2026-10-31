import { FOOTER } from './footer.js';

export default function Footer() {
  const sep = ` ${FOOTER.separator} `;
  return (
    <footer className="app-footer">
      <p>
        {FOOTER.copyright}
        {sep}
        {FOOTER.builtFor}{' '}
        <a href={FOOTER.companyUrl} target="_blank" rel="noreferrer">
          {FOOTER.company}
        </a>
        {sep}
        {FOOTER.middle}
        {sep}
        <a href={FOOTER.eventUrl} target="_blank" rel="noreferrer">
          {FOOTER.event}
        </a>
      </p>
      <p>
        <strong>{FOOTER.product}</strong> {FOOTER.dash} {FOOTER.promise}
      </p>
    </footer>
  );
}
