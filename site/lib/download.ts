/** Trigger a client-side download of a text payload as a file. */
export function downloadText(filename: string, content: string, mime = 'text/plain') {
  const blob = new Blob([content], { type: `${mime};charset=utf-8` });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

/** Build a filesystem-safe slug from active filter values (e.g. "T2K-CC0pi"). */
export function fileSlug(parts: (string | undefined)[], fallback = 'export'): string {
  const cleaned = parts
    .filter((p): p is string => Boolean(p))
    .map((p) => p.replace(/[^A-Za-z0-9]+/g, ''))
    .filter(Boolean);
  return cleaned.length ? cleaned.join('-') : fallback;
}
