'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useState } from 'react';
import { navItems, site } from '@/lib/site-data';
import { isStaticHref, withBasePath } from '@/lib/paths';

function isExternal(href: string) {
  return href.startsWith('http');
}

export function SiteHeader() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  const isActive = (href: string) =>
    href === '/' ? pathname === '/' : !isExternal(href) && pathname.startsWith(href);

  return (
    <header className="site-header">
      <div className="site-header-inner">
        <Link className="brand" href="/" onClick={() => setOpen(false)}>
          <span className="brand-name">{site.name}</span>
          <span className="brand-rule" />
          <span className="brand-subtitle">{site.fullName}</span>
        </Link>

        <nav aria-label="Main navigation" className="desktop-nav">
          {navItems.map((item) =>
            isExternal(item.href) || isStaticHref(item.href) ? (
              <a
                className={`nav-link ${isActive(item.href) ? 'is-active' : ''}`}
                href={withBasePath(item.href)}
                key={item.href}
                rel={isExternal(item.href) ? 'noreferrer' : undefined}
                target={isExternal(item.href) ? '_blank' : undefined}
              >
                {item.label}
              </a>
            ) : (
              <Link
                className={`nav-link ${isActive(item.href) ? 'is-active' : ''}`}
                href={item.href}
                key={item.href}
              >
                {item.label}
              </Link>
            ),
          )}
        </nav>

        <button
          aria-expanded={open}
          aria-label="Toggle navigation menu"
          className="menu-button"
          onClick={() => setOpen((value) => !value)}
          type="button"
        >
          {open ? 'Close' : 'Menu'}
        </button>
      </div>

      {open ? (
        <div className="mobile-nav">
          <nav aria-label="Mobile navigation">
            {navItems.map((item) =>
              isExternal(item.href) || isStaticHref(item.href) ? (
                <a
                  className={isActive(item.href) ? 'is-active' : ''}
                  href={withBasePath(item.href)}
                  key={item.href}
                  onClick={() => setOpen(false)}
                  rel={isExternal(item.href) ? 'noreferrer' : undefined}
                  target={isExternal(item.href) ? '_blank' : undefined}
                >
                  {item.label}
                </a>
              ) : (
                <Link
                  className={isActive(item.href) ? 'is-active' : ''}
                  href={item.href}
                  key={item.href}
                  onClick={() => setOpen(false)}
                >
                  {item.label}
                </Link>
              ),
            )}
          </nav>
        </div>
      ) : null}
    </header>
  );
}
