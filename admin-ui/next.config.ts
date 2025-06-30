import type { NextConfig } from 'next';
import { withSentryConfig } from '@sentry/nextjs';

// Define the base Next.js configuration
const baseConfig: NextConfig = {
  // Enable standalone output for Docker deployment
  output: 'standalone',
  
  // Disable static optimization to avoid hanging during build
  trailingSlash: false,
  skipTrailingSlashRedirect: true,
  
  // Experimental features for Docker ESM compatibility
  experimental: {
    esmExternals: 'loose',
  },
  
  // Webpack configuration for Docker ESM compatibility
  webpack: (config, { isServer }) => {
    // Handle ESM packages in Docker builds
    if (!isServer) {
      config.externals = config.externals || []
      config.externals.push({
        '@jridgewell/trace-mapping': 'commonjs @jridgewell/trace-mapping',
        '@jridgewell/sourcemap-codec': 'commonjs @jridgewell/sourcemap-codec',
        '@ampproject/remapping': 'commonjs @ampproject/remapping',
      })
    }
    return config
  },
  
  async rewrites() {
    return [
      {
        source: '/api/v1/:path*',
        destination: 'http://api:4000/api/v1/:path*',
      },
      {
        source: '/ws/:path*',
        destination: 'http://api:4000/api/v1/ws/:path*',
      },
      {
        source: '/grafana/:path*',
        destination: 'http://grafana:3000/:path*',
      },
      {
        source: '/prometheus/:path*',
        destination: 'http://prometheus:9090/:path*',
      },
      {
        source: '/loki/:path*',
        destination: 'http://loki:3100/:path*',
      },
    ]
  },

  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'api.slingacademy.com',
        port: ''
      }
    ]
  },
  
  transpilePackages: ['geist'],
  
  // Environment variable configuration
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
    NEXT_PUBLIC_APP_NAME: process.env.NEXT_PUBLIC_APP_NAME,
    NEXT_PUBLIC_ENABLE_AUTH: process.env.NEXT_PUBLIC_ENABLE_AUTH
  }
};

let configWithPlugins = baseConfig;

// Conditionally enable Sentry configuration
if (!process.env.NEXT_PUBLIC_SENTRY_DISABLED) {
  configWithPlugins = withSentryConfig(configWithPlugins, {
    // For all available options, see:
    // https://www.npmjs.com/package/@sentry/webpack-plugin#options
    // FIXME: Add your Sentry organization and project names
    org: process.env.NEXT_PUBLIC_SENTRY_ORG,
    project: process.env.NEXT_PUBLIC_SENTRY_PROJECT,
    // Only print logs for uploading source maps in CI
    silent: !process.env.CI,

    // For all available options, see:
    // https://docs.sentry.io/platforms/javascript/guides/nextjs/manual-setup/

    // Upload a larger set of source maps for prettier stack traces (increases build time)
    widenClientFileUpload: true,

    // Upload a larger set of source maps for prettier stack traces (increases build time)
    reactComponentAnnotation: {
      enabled: true
    },

    // Route browser requests to Sentry through a Next.js rewrite to circumvent ad-blockers.
    // This can increase your server load as well as your hosting bill.
    // Note: Check that the configured route will not match with your Next.js middleware, otherwise reporting of client-
    // side errors will fail.
    tunnelRoute: '/monitoring',

    // Automatically tree-shake Sentry logger statements to reduce bundle size
    disableLogger: true,

    // Disable Sentry telemetry
    telemetry: false
  });
}

const nextConfig = configWithPlugins;
export default nextConfig;
