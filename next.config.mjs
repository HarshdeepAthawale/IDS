/** @type {import('next').NextConfig} */
const nextConfig = {
  typescript: {
    ignoreBuildErrors: true,
  },
  images: {
    unoptimized: true,
  },
  // Turbopack is now the default bundler in Next.js 16
  // No explicit configuration needed - it's enabled by default
}

export default nextConfig
