import Link from 'next/link';
import type { ReactNode } from 'react';
import { Icon } from './Icon';
import { isStaticHref, withBasePath } from '@/lib/paths';

type ButtonLinkProps = {
  href: string;
  children: ReactNode;
  variant?: 'primary' | 'secondary' | 'ghost';
  className?: string;
};

type SectionHeaderProps = {
  eyebrow?: string;
  title: string;
  body?: string;
  align?: 'left' | 'center';
};

type LinkCardProps = {
  eyebrow?: string;
  title: string;
  body: string;
  href: string;
  label: string;
  accent?: string;
  icon?: string;
};

type PageHeroProps = {
  eyebrow: string;
  title: string;
  titleClassName?: string;
  body: string;
  actions?: ReactNode;
  visual?: ReactNode;
  className?: string;
};

function isExternal(href: string) {
  return href.startsWith('http');
}

export function Container({
  children,
  className = '',
}: {
  children: ReactNode;
  className?: string;
}) {
  return <div className={`container ${className}`.trim()}>{children}</div>;
}

export function ButtonLink({
  href,
  children,
  variant = 'primary',
  className = '',
}: ButtonLinkProps) {
  const classes = `button button-${variant} ${className}`.trim();

  if (isExternal(href) || isStaticHref(href)) {
    return (
      <a
        className={classes}
        href={withBasePath(href)}
        rel={isExternal(href) ? 'noreferrer' : undefined}
        target={isExternal(href) ? '_blank' : undefined}
      >
        {children}
      </a>
    );
  }

  return (
    <Link className={classes} href={href}>
      {children}
    </Link>
  );
}

export function SectionHeader({
  eyebrow,
  title,
  body,
  align = 'left',
}: SectionHeaderProps) {
  return (
    <div className={`section-header section-header-${align}`}>
      {eyebrow ? <p className="eyebrow">{eyebrow}</p> : null}
      <h2 className="type-h2">{title}</h2>
      {body ? <p>{body}</p> : null}
    </div>
  );
}

export function LinkCard({
  eyebrow,
  title,
  body,
  href,
  label,
  accent = 'palo',
  icon = 'arrow',
}: LinkCardProps) {
  return (
    <article className={`panel link-card panel-accent-${accent}`}>
      <div className="link-card-top">
        <span className={`icon-chip accent-${accent}`}>
          <Icon name={icon} size={24} />
        </span>
        {eyebrow ? (
          <p className={`eyebrow text-${accent}`}>{eyebrow}</p>
        ) : null}
      </div>
      <h3 className="type-h3">{title}</h3>
      <p>{body}</p>
      <ButtonLink href={href} variant="ghost">
        {label}
        <Icon name="arrow" size={14} />
      </ButtonLink>
    </article>
  );
}

export function PageHero({
  eyebrow,
  title,
  titleClassName = '',
  body,
  actions,
  visual,
  className = '',
}: PageHeroProps) {
  return (
    <section className={`page-hero ${className}`.trim()}>
      <Container className="page-hero-inner">
        <div className="page-hero-copy">
          <p className="eyebrow">{eyebrow}</p>
          <h1 className={`type-h1 ${titleClassName}`.trim()}>{title}</h1>
          <p>{body}</p>
          {actions ? <div className="hero-actions">{actions}</div> : null}
        </div>
        {visual ? <div className="page-hero-visual">{visual}</div> : null}
      </Container>
    </section>
  );
}

export function NumberedCard({
  number,
  title,
  body,
  accent = 'palo',
  icon,
}: {
  number: string;
  title: string;
  body: string;
  accent?: string;
  icon?: string;
}) {
  return (
    <article className={`panel numbered-card panel-accent-${accent}`}>
      {icon ? (
        <span className={`icon-ghost accent-${accent}`}>
          <Icon name={icon} size={28} />
        </span>
      ) : null}
      <span className={`number text-${accent}`}>{number}</span>
      <h3 className="type-h3">{title}</h3>
      <p>{body}</p>
    </article>
  );
}

export function SimpleCard({
  eyebrow,
  title,
  body,
  accent = 'palo',
}: {
  eyebrow?: string;
  title: string;
  body: string;
  accent?: string;
}) {
  return (
    <article className={`panel simple-card panel-accent-${accent}`}>
      {eyebrow ? <p className={`eyebrow text-${accent}`}>{eyebrow}</p> : null}
      <h3 className="type-h3">{title}</h3>
      <p>{body}</p>
    </article>
  );
}
