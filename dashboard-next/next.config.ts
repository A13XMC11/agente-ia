import type { NextConfig } from 'next'

const nextConfig: NextConfig = {
  allowedDevOrigins: ['192.168.100.10'],

  // Turbopack configuration for Vercel
  turbopack: {
    root: process.env.TURBO_ROOT || '.',
  },

  // Experimental features for better build performance
  experimental: {
    optimizePackageImports: ['@supabase/supabase-js', 'jose'],
  },

  // Build configuration
  productionBrowserSourceMaps: false,
  reactStrictMode: true,
}

export default nextConfig


