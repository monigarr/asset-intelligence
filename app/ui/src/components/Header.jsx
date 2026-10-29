import { ABOUT } from './about.js';
import { GithubIcon, MailIcon } from './icons.jsx';

export default function Header({ status }) {
  return (
    <header className="app-header">
      <div className="brand">
        <span className="brand-name">Asset Intelligence</span>
        <span className="brand-sub">by ManageAssets.ca</span>
      </div>
      <div className="head-right">
        <nav className="main-nav" aria-label="Main">
          <a
            className="nav-icon"
            href={ABOUT.contactUrl}
            target="_blank"
            rel="noreferrer"
            title="Contact"
          >
            <MailIcon />
            <span className="sr-only">Contact</span>
          </a>
          <a
            className="nav-icon"
            href={ABOUT.githubUrl}
            target="_blank"
            rel="noreferrer"
            title="GitHub"
          >
            <GithubIcon />
            <span className="sr-only">GitHub</span>
          </a>
        </nav>
        {status ? <span className="sub">{status}</span> : null}
      </div>
    </header>
  );
}
