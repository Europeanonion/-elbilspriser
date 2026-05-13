import type { NextConfig } from 'next'

const config: NextConfig = {
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
