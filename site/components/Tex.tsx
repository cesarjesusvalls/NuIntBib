import { texToHtml } from '@/lib/tex';

/** Server component: render text with inline `$...$` math as HTML. */
export function Tex({ text, className }: { text: string | null | undefined; className?: string }) {
  return <span className={className} dangerouslySetInnerHTML={{ __html: texToHtml(text) }} />;
}
