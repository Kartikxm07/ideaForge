import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  turbopack: {
    root: __dirname,
  },
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: "http://127.0.0.1:8000/api/v1/:path*",
      },
      {
        source: "/thor/:path*",
        destination: "http://127.0.0.1:8000/thor/:path*",
      },
    ];
  },
};

export default nextConfig;
