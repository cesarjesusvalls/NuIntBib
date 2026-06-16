import Link from 'next/link';
import { Icon } from '@/components/Icon';
import { footerMore, footerPages, site } from '@/lib/site-data';
import { isStaticHref, withBasePath } from '@/lib/paths';

function FooterLink({ href, label }: { href: string; label: string }) {
  if (isStaticHref(href)) {
    return <a href={withBasePath(href)}>{label}</a>;
  }

  if (href.startsWith('http')) {
    return (
      <a href={href} rel="noreferrer" target="_blank">
        {label}
      </a>
    );
  }

  return <Link href={href}>{label}</Link>;
}

export function SiteFooter() {
  return (
    <footer className="site-footer">
      <div className="container footer-inner">
        <div className="footer-grid">
          <div className="footer-brand">
            <div className="footer-brand-line">
              <span className="footer-brand-name">{site.name}</span>
              <span className="footer-brand-rule" />
              <span className="footer-brand-subtitle">{site.fullName}</span>
            </div>
            <p>{site.description}</p>
          </div>

          <nav aria-label="Footer pages">
            <h3>Pages</h3>
            <ul>
              {footerPages.map((link) => (
                <li key={link.href}>
                  <FooterLink href={link.href} label={link.label} />
                </li>
              ))}
            </ul>
          </nav>

          <nav aria-label="Footer more">
            <h3>More</h3>
            <ul>
              {footerMore.map((link) => (
                <li key={link.href}>
                  <FooterLink href={link.href} label={link.label} />
                </li>
              ))}
            </ul>
          </nav>
        </div>
        <div className="footer-bottom">
          <div className="footer-legal">
            <p>
              Developed &amp; managed by {site.maintainer} ({site.maintainerAffiliation}). Contact:{' '}
              <a href={`mailto:${site.contactEmail}`}>{site.contactEmail}</a>
            </p>
          </div>
          <div className="footer-socials">
            <a
              href={site.githubUrl}
              rel="noreferrer"
              target="_blank"
              aria-label={`${site.name} on GitHub`}
            >
              <Icon name="github" size={20} />
            </a>
          </div>
        </div>
      </div>
    </footer>
  );
}
