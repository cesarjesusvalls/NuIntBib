import type { Metadata } from 'next';
import { Roboto_Mono, Source_Sans_3, Source_Serif_4 } from 'next/font/google';
import type { ReactNode } from 'react';
import { ScrollReveal } from '@/components/ScrollReveal';
import { SiteFooter } from '@/components/SiteFooter';
import { SiteHeader } from '@/components/SiteHeader';
import { site } from '@/lib/site-data';
import 'katex/dist/katex.min.css';
import './globals.css';

const sourceSerif = Source_Serif_4({
  subsets: ['latin'],
  display: 'swap',
  variable: '--font-source-serif',
});

const sourceSans = Source_Sans_3({
  subsets: ['latin'],
  display: 'swap',
  variable: '--font-source-sans',
});

const robotoMono = Roboto_Mono({
  subsets: ['latin'],
  display: 'swap',
  variable: '--font-roboto-mono',
});

export const metadata: Metadata = {
  title: {
    default: site.title,
    template: '%s | NuIntBib',
  },
  description: site.description,
  icons: {
    icon: '/icon.svg',
  },
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body className={`${sourceSerif.variable} ${sourceSans.variable} ${robotoMono.variable}`}>
        <a className="skip-link" href="#main-content">
          Skip to main content
        </a>
        <SiteHeader />
        <main id="main-content">{children}</main>
        <SiteFooter />
        <ScrollReveal />
      </body>
    </html>
  );
}
