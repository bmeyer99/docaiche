# Traefik Migration Plan for DocAIche

## Overview
This plan outlines the migration from Next.js-based routing to Traefik as the primary reverse proxy and load balancer. This will resolve the current Grafana subpath routing issues and provide a more robust, scalable architecture.

## Benefits of Migration
1. **Proper reverse proxy handling** - Native support for path-based routing and header preservation
2. **Simplified architecture** - Remove proxy logic from Next.js, making it focus on UI only
3. **Better observability** - Built-in metrics and access logs
4. **WebSocket support** - Native WebSocket proxying without custom handlers
5. **Automatic HTTPS** - Built-in Let's Encrypt support for production
6. **Service discovery** - Automatic routing via Docker labels
7. **Middleware support** - Path stripping, header modification, authentication

## Architecture Changes

### Current Architecture
```
Internet → Port 4080 → admin-ui (Next.js) → Rewrites → Backend Services
                              ↓
                    Handles all routing & proxying
```

### New Architecture with Traefik
```
Internet → Port 4080 → Traefik → Routes based on path → Services
                         ↓
              Dedicated reverse proxy layer
```

## Implementation Steps

### Phase 1: Add Traefik to Docker Compose

Create `traefik.yml` configuration:
```yaml
api:
  dashboard: true
  debug: true

entryPoints:
  web:
    address: ":80"

providers:
  docker:
    endpoint: "unix:///var/run/docker.sock"
    exposedByDefault: false
    network: docaiche

log:
  level: INFO

accessLog: {}

metrics:
  prometheus:
    addEntryPointsLabels: true
    addServicesLabels: true
```

Update `docker-compose.yml` to add Traefik:
```yaml
services:
  traefik:
    image: traefik:v3.2
    ports:
      - "4080:80"
      - "8080:8080"  # Traefik dashboard (optional, for debugging)
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - ./traefik.yml:/traefik.yml:ro
    networks:
      - docaiche
    labels:
      - "docaiche.service=traefik"
    restart: unless-stopped
```

### Phase 2: Configure Service Routing

Update each service in `docker-compose.yml` with Traefik labels:

#### Admin UI Service
```yaml
admin-ui:
  # ... existing config ...
  # Remove ports section - Traefik will handle external access
  labels:
    - "docaiche.service=admin-ui"
    - "traefik.enable=true"
    - "traefik.http.routers.admin-ui.rule=PathPrefix(`/`)"
    - "traefik.http.routers.admin-ui.priority=1"
    - "traefik.http.services.admin-ui.loadbalancer.server.port=3000"
```

#### API Service
```yaml
api:
  # ... existing config ...
  labels:
    - "docaiche.service=api"
    - "traefik.enable=true"
    # Route both /api/* and /ws/* to the API service
    - "traefik.http.routers.api.rule=PathPrefix(`/api/`) || PathPrefix(`/ws/`)"
    - "traefik.http.routers.api.priority=100"
    - "traefik.http.services.api.loadbalancer.server.port=4000"
    # Middleware to rewrite /ws/* to /api/v1/ws/*
    - "traefik.http.middlewares.ws-rewrite.replacepathregex.regex=^/ws/(.*)"
    - "traefik.http.middlewares.ws-rewrite.replacepathregex.replacement=/api/v1/ws/$$1"
    - "traefik.http.routers.api.middlewares=ws-rewrite@docker"
```

#### Grafana Service
```yaml
grafana:
  # ... existing config ...
  environment:
    - GF_SERVER_ROOT_URL=http://localhost:4080/grafana/
    - GF_SERVER_SERVE_FROM_SUB_PATH=true
  labels:
    - "docaiche.service=grafana"
    - "traefik.enable=true"
    - "traefik.http.routers.grafana.rule=PathPrefix(`/grafana`)"
    - "traefik.http.routers.grafana.priority=90"
    - "traefik.http.services.grafana.loadbalancer.server.port=3000"
    # Strip /grafana prefix when forwarding to Grafana
    - "traefik.http.middlewares.grafana-stripprefix.stripprefix.prefixes=/grafana"
    - "traefik.http.routers.grafana.middlewares=grafana-stripprefix@docker"
```

#### Prometheus Service
```yaml
prometheus:
  # ... existing config ...
  labels:
    - "docaiche.service=prometheus"
    - "traefik.enable=true"
    - "traefik.http.routers.prometheus.rule=PathPrefix(`/prometheus`)"
    - "traefik.http.routers.prometheus.priority=80"
    - "traefik.http.services.prometheus.loadbalancer.server.port=9090"
```

#### Loki Service
```yaml
loki:
  # ... existing config ...
  labels:
    - "docaiche.service=loki"
    - "traefik.enable=true"
    - "traefik.http.routers.loki.rule=PathPrefix(`/loki`)"
    - "traefik.http.routers.loki.priority=70"
    - "traefik.http.services.loki.loadbalancer.server.port=3100"
```

### Phase 3: Remove Next.js Proxy Configuration

1. **Remove rewrites from `next.config.ts`**:
```typescript
// Remove the entire rewrites() function
// Keep only UI-specific configuration
```

2. **Update API proxy route**:
   - Keep `/app/api/[...path]/route.ts` for API calls from the UI
   - Update to use the service name directly without path manipulation

3. **Update WebSocket connections**:
   - Update `analytics-provider.tsx` to use `/ws/analytics/clean` directly
   - The path will be properly routed by Traefik

### Phase 4: Testing and Validation

1. **Test routing priorities**:
   - `/grafana/*` → Grafana (strip prefix)
   - `/prometheus/*` → Prometheus  
   - `/loki/*` → Loki
   - `/api/*` → API service
   - `/ws/*` → API service (with rewrite to `/api/v1/ws/*`)
   - `/` → Admin UI (catch-all)

2. **Verify WebSocket connections**:
   - Analytics WebSocket at `/ws/analytics/clean`
   - Progressive analytics at `/ws/analytics/progressive`

3. **Test Grafana access**:
   - Navigate to `http://localhost:4080/grafana`
   - Verify proper routing without redirect issues
   - Check that all assets load correctly

4. **Monitor performance**:
   - Use Traefik dashboard to monitor request routing
   - Check service health via Traefik health checks
   - Verify no increase in latency

### Phase 5: Production Considerations

1. **HTTPS Configuration** (for production):
```yaml
traefik:
  ports:
    - "80:80"
    - "443:443"
  volumes:
    - ./acme.json:/acme.json
  command:
    - "--certificatesresolvers.letsencrypt.acme.email=your-email@example.com"
    - "--certificatesresolvers.letsencrypt.acme.storage=/acme.json"
    - "--certificatesresolvers.letsencrypt.acme.httpchallenge.entrypoint=web"
```

2. **Rate Limiting**:
```yaml
labels:
  - "traefik.http.middlewares.rate-limit.ratelimit.average=100"
  - "traefik.http.middlewares.rate-limit.ratelimit.burst=50"
```

3. **Access Control**:
```yaml
labels:
  - "traefik.http.middlewares.admin-auth.basicauth.users=admin:$$2y$$10$$..."
```

## Rollback Plan

If issues arise during migration:

1. **Quick rollback**:
   - Stop Traefik container
   - Restore original `docker-compose.yml`
   - Restore `next.config.ts` with rewrites
   - Rebuild and restart admin-ui

2. **Gradual rollback**:
   - Keep Traefik but route specific services back through Next.js
   - Monitor and fix issues incrementally

## Migration Checklist

- [ ] Backup current configuration
- [ ] Create Traefik configuration file
- [ ] Update docker-compose.yml with Traefik service
- [ ] Add routing labels to all services
- [ ] Update Grafana environment variables
- [ ] Test all service endpoints
- [ ] Remove Next.js rewrites
- [ ] Update WebSocket connection paths
- [ ] Verify Grafana access at /grafana
- [ ] Test WebSocket connections
- [ ] Monitor performance metrics
- [ ] Document any custom middleware needed

## Expected Outcomes

1. **Grafana** accessible at `http://localhost:4080/grafana` without redirect issues
2. **API** properly handling all requests at `/api/*`
3. **WebSockets** working seamlessly at `/ws/*`
4. **Admin UI** serving as the default route
5. **Better performance** due to dedicated reverse proxy layer
6. **Easier debugging** with Traefik dashboard and access logs

## Notes

- Traefik labels take precedence over manual configuration
- Path matching is case-sensitive by default
- Higher priority numbers are evaluated first
- WebSocket support is automatic when HTTP routing is configured
- The `/api/*` routing future-proofs API versioning changes