export const basePath = process.env.NEXT_PUBLIC_BASE_PATH ?? '';

export function withBasePath(href: string) {
  if (!basePath || href.startsWith('http') || href.startsWith('#') || href.startsWith('mailto:')) {
    return href;
  }

  return `${basePath}${href.startsWith('/') ? href : `/${href}`}`;
}

export function isStaticHref(href: string) {
  return href.startsWith('/documentation') || href.endsWith('.xml');
}
