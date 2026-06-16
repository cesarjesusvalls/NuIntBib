'use client';

import { useEffect } from 'react';

const revealSelectors = [
  '[data-scroll-reveal-item]',
  '.home-hero-copy',
  '.home-hero-visual',
  '.home-highlights .highlight-card',
  '.page-hero-copy',
  '.page-hero-visual',
  '.software-hero-copy',
  '.software-hero-actions',
  '.updates-signup > *',
  '.section-header',
  '.highlight-card',
  '.link-card',
  '.numbered-card',
  '.simple-card',
  '.panel',
  '.news-row',
  '.software-card',
  '.detail-layout > *',
  '.record-row',
  '.data-table-wrap',
  '.article-card',
  '.footer-grid > *',
  '.footer-bottom > *',
].join(',');

export function ScrollReveal() {
  useEffect(() => {
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const elements = Array.from(
      new Set(document.querySelectorAll<HTMLElement>(revealSelectors)),
    );

    if (reduceMotion) {
      elements.forEach((element) => {
        element.dataset.revealVisible = 'true';
      });
      return;
    }

    document.documentElement.dataset.scrollReveal = 'ready';

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;

          const element = entry.target as HTMLElement;
          element.dataset.revealVisible = 'true';
          observer.unobserve(element);
        });
      },
      {
        rootMargin: '0px 0px -3% 0px',
        threshold: 0.03,
      },
    );

    elements.forEach((element, index) => {
      element.dataset.reveal = 'true';
      element.style.setProperty('--reveal-delay', `${Math.min((index % 6) * 55, 275)}ms`);
      observer.observe(element);
    });

    return () => {
      observer.disconnect();
      delete document.documentElement.dataset.scrollReveal;
      elements.forEach((element) => {
        delete element.dataset.reveal;
        delete element.dataset.revealVisible;
        element.style.removeProperty('--reveal-delay');
      });
    };
  }, []);

  return null;
}
