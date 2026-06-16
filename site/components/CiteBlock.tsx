'use client';

import { useState } from 'react';
import { Icon } from '@/components/Icon';

export function CiteBlock({ bibtex }: { bibtex: string }) {
  const [copied, setCopied] = useState(false);
  async function copy() {
    try {
      await navigator.clipboard.writeText(bibtex);
    } catch {
      const ta = document.createElement('textarea');
      ta.value = bibtex;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      ta.remove();
    }
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1600);
  }
  return (
    <div className="cite-block">
      <button className="cite-block-copy" onClick={copy} type="button">
        <Icon name={copied ? 'check' : 'copy'} size={14} />
        {copied ? 'Copied' : 'Copy BibTeX'}
      </button>
      <pre>
        <code>{bibtex}</code>
      </pre>
    </div>
  );
}
