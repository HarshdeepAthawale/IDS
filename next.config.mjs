/** @type {import('next').NextConfig} */
const nextConfig = {
  typescript: {
    // Recommended: fix TypeScript errors and set to false for stricter builds
    ignoreBuildErrors: true,
  },
  images: {
    unoptimized: true,
  },
  // Turbopack is now the default bundler in Next.js 16
  // No explicit configuration needed - it's enabled by default
}

export default nextConfig
