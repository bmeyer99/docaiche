# syntax=docker/dockerfile:1
# Multi-stage build for Docaiche Admin UI with optimized caching
FROM node:20-alpine AS base

# Install dependencies in a separate stage for better caching
FROM base AS deps
WORKDIR /app

# Copy package files
COPY package.json package-lock.json* ./

# Install dependencies with cache mount for npm
RUN --mount=type=cache,target=/root/.npm \
    npm install \
    --legacy-peer-deps \
    --no-audit \
    --no-fund \
    --ignore-scripts

# Build stage with source code
FROM base AS builder
WORKDIR /app

# Copy dependencies from deps stage
COPY --from=deps /app/node_modules ./node_modules

# Copy package files and configuration
COPY package.json package-lock.json* ./
COPY tsconfig.json next.config.ts ./
COPY postcss.config.mjs tailwind.config.js components.json ./

# Copy source files
COPY public ./public
COPY src ./src

# Disable telemetry and Sentry during build
ENV NEXT_TELEMETRY_DISABLED=1
ENV NEXT_PUBLIC_SENTRY_DISABLED=true
ENV SENTRY_SKIP_SOURCE_MAPS=true

# Set build-time environment variables
ARG NEXT_PUBLIC_API_URL=http://api:8000/api/v1
ARG NEXT_PUBLIC_APP_NAME=Docaiche Admin
ARG NEXT_PUBLIC_ENABLE_AUTH=false
ARG NEXT_PUBLIC_AI_LOGS_ENABLED=true
ARG NEXT_PUBLIC_AI_LOGS_WEBSOCKET_ENABLED=true
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
ENV NEXT_PUBLIC_APP_NAME=${NEXT_PUBLIC_APP_NAME}
ENV NEXT_PUBLIC_ENABLE_AUTH=${NEXT_PUBLIC_ENABLE_AUTH}
ENV NEXT_PUBLIC_AI_LOGS_ENABLED=${NEXT_PUBLIC_AI_LOGS_ENABLED}
ENV NEXT_PUBLIC_AI_LOGS_WEBSOCKET_ENABLED=${NEXT_PUBLIC_AI_LOGS_WEBSOCKET_ENABLED}

# Build the application with cache mount
RUN --mount=type=cache,target=/app/.next/cache \
    npm run build

# Production image
FROM base AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV NEXT_PUBLIC_SENTRY_DISABLED=true

# Create a non-root user
RUN addgroup -g 1001 -S nodejs && \
    adduser -S nextjs -u 1001

# Copy built application
COPY --from=builder /app/public ./public

# Automatically leverage output traces to reduce image size
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

# Start the application
CMD ["node", "server.js"]