/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,

  // API 代理配置 (开发环境)
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8000/api/:path*',
      },
      {
        source: '/ws/:path*',
        destination: 'http://localhost:8000/ws/:path*',
      },
    ];
  },

  // 图片域名白名单
  images: {
    domains: ['localhost'],
  },
};

module.exports = nextConfig;
