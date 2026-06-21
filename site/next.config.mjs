const basePath = process.env.NEXT_PUBLIC_BASE_PATH ?? '';

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'export',
  trailingSlash: true,
  basePath,
  assetPrefix: basePath || undefined,
  images: {
    unoptimized: true,
  },
  // Dev-only: allow the Cloudflare quick-tunnel origin so client interactivity
  // (hydration/HMR) works when previewing through the tunnel. Ignored in `next build`.
  allowedDevOrigins: ['*.trycloudflare.com'],
};

export default nextConfig;
