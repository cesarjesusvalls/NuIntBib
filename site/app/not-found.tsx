import { ButtonLink, Container } from '@/components/UI';

export default function NotFound() {
  return (
    <section className="not-found-page">
      <Container className="not-found-inner">
        <div className="not-found-copy">
          <p className="eyebrow">404</p>
          <h1 className="type-display">Page not found</h1>
          <p>That page does not exist. Try browsing the papers instead.</p>
          <div className="hero-actions">
            <ButtonLink href="/papers">Browse papers</ButtonLink>
            <ButtonLink href="/" variant="secondary">
              Return home
            </ButtonLink>
          </div>
        </div>
      </Container>
    </section>
  );
}
