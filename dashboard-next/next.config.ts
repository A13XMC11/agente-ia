import type { NextConfig } from 'next'

// Security headers applied to every route.
// References: OWASP Secure Headers Project, MDN Web Docs.
const securityHeaders = [
  // Prevent MIME-type sniffing (e.g. serving a text file as JS).
  { key: 'X-Content-Type-Options', value: 'nosniff' },

  // Deny framing from any origin — prevents clickjacking attacks.
  { key: 'X-Frame-Options', value: 'DENY' },

  // Modern browsers use CSP for XSS; set to 0 to disable legacy heuristic filter
  // which can itself introduce vulnerabilities.
  { key: 'X-XSS-Protection', value: '0' },

  // HSTS: 2 years, include subdomains. Tells browsers to always use HTTPS.
  // Only activate after TLS is confirmed on all subdomains.
  {
    key: 'Strict-Transport-Security',
    value: 'max-age=63072000; includeSubDomains; preload',
  },

  // Don't send full referrer to third-party sites.
  { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },

  // Opt out of browser features this dashboard never uses.
  {
    key: 'Permissions-Policy',
    value: 'geolocation=(), microphone=(), camera=(), payment=()',
  },

  // Content-Security-Policy:
  // - default-src 'self'          : only load resources from same origin by default
  // - script-src 'self'           : no inline scripts, no eval
  // - style-src 'self' 'unsafe-inline' : Tailwind inlines styles via className; required
  // - img-src 'self' data: blob:  : allow data URIs and blob URLs for images
  // - font-src 'self'             : fonts from same origin only
  // - connect-src 'self' https:   : API calls over HTTPS allowed
  // - frame-ancestors 'none'      : belt-and-suspenders clickjacking protection
  // - base-uri 'self'             : prevent <base> injection
  // - form-action 'self'          : prevent form hijacking
  {
    key: 'Content-Security-Policy',
    value: [
      "default-src 'self'",
      "script-src 'self' 'unsafe-inline'",   // 'unsafe-inline' required by Next.js hydration
      "style-src 'self' 'unsafe-inline'",
      "img-src 'self' data: blob: https:",
      "font-src 'self'",
      "connect-src 'self' https:",
      "frame-ancestors 'none'",
      "base-uri 'self'",
      "form-action 'self'",
    ].join('; '),
  },
]

const nextConfig: NextConfig = {
  allowedDevOrigins: ['192.168.100.10'],

  compress: true,

  headers: () => Promise.resolve([
    {
      // Apply security headers to all routes
      source: '/(.*)',
      headers: securityHeaders,
    },
  ]),

  experimental: {
    optimizePackageImports: [
      '@supabase/supabase-js',
      'jose',
      'lucide-react',
      'date-fns',
    ],
  },

  images: {
    formats: ['image/avif', 'image/webp'],
    minimumCacheTTL: 3600,
  },

  productionBrowserSourceMaps: false,
  reactStrictMode: true,
}

export default nextConfig


