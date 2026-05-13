import type { NextConfig } from 'next'

const config: NextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/v1/:path*',
        destination: `${process.env.BACKEND_URL ?? 'http://localhost:8000'}/api/v1/:path*`,
      },
    ]
  },
  async headers() {
    return [
      {
        source: '/api/:path*',
        headers: [{ key: 'Cache-Control', value: 's-maxage=900, stale-while-revalidate=1800' }],
      },
    ]
  },
}

export default config
