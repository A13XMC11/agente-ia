import type { NextConfig } from 'next'

const nextConfig: NextConfig = {
  allowedDevOrigins: ['192.168.100.10'],

  // Gzip compression for all responses
  compress: true,

  // Turbopack configuration for Vercel
  turbopack: {
    root: process.env.TURBO_ROOT || '.',
  },

  // Tree-shake large packages at build time — reduces JS bundle per route
  experimental: {
    optimizePackageImports: [
      '@supabase/supabase-js',
      'jose',
      'lucide-react',
      'date-fns',
    ],
  },

  // Image optimization
  images: {
    formats: ['image/avif', 'image/webp'],
    minimumCacheTTL: 3600,
  },

  productionBrowserSourceMaps: false,
  reactStrictMode: true,
}

export default nextConfig


