const allowedDevOrigins = (process.env.NEXT_ALLOWED_DEV_ORIGINS ?? "")
  .split(",")
  .map((origin) => origin.trim())
  .filter(Boolean);

/** @type {import('next').NextConfig} */
const nextConfig = {
  ...(allowedDevOrigins.length ? { allowedDevOrigins } : {}),
  poweredByHeader: false,
  reactStrictMode: true,
};

export default nextConfig;
