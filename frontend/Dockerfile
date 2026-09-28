# syntax=docker/dockerfile:1
ARG NODE_IMAGE=node:24-alpine@sha256:ebfe2f90462722a7a4de65e91990e97fe0d401c70e0e762c5b53302f905ec1c1
ARG CADDY_IMAGE=caddy:2-alpine@sha256:6aeddd44c3078b0f9a35206472a11420648a79c184603ef95957d0a20044cb2b

# ---- development: Vite dev server with /api proxy to the backend ----
FROM ${NODE_IMAGE} AS development
WORKDIR /app/frontend
ENV PNPM_HOME=/pnpm
ENV PATH="$PNPM_HOME:$PATH"
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN corepack enable && pnpm install --frozen-lockfile
COPY --chown=node:node . .
USER node
EXPOSE 8080
# API_PROXY_TARGET is set by compose.dev.yaml (http://backend:8000)
CMD ["pnpm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "8080", "--strictPort"]

# ---- build: static assets ----
FROM development AS build
RUN pnpm run build

# ---- production: Caddy serves dist and proxies /api ----
FROM ${CADDY_IMAGE} AS production
COPY Caddyfile /etc/caddy/Caddyfile
COPY --from=build /app/frontend/dist /srv
EXPOSE 8080
