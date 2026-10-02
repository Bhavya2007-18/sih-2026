import type { NextConfig } from "next";

// Server configuration only; never expose MAYA_API_URL as NEXT_PUBLIC_*.
const backend = (process.env.MAYA_API_URL || "http://127.0.0.1:8000").replace(/\/$/, "");
const config: NextConfig = {
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${backend}/api/:path*` }];
  },
};
export default config;
