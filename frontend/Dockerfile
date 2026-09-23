FROM node:24-alpine@sha256:ebfe2f90462722a7a4de65e91990e97fe0d401c70e0e762c5b53302f905ec1c1 AS development
WORKDIR /app/frontend
COPY package.json package-lock.json ./
RUN npm ci && chown -R node:node /app
COPY --chown=node:node . .
USER node
CMD ["npm", "run", "dev"]

FROM development AS build
RUN npm run build

FROM caddy:2-alpine@sha256:6aeddd44c3078b0f9a35206472a11420648a79c184603ef95957d0a20044cb2b AS production
COPY Caddyfile /etc/caddy/Caddyfile
COPY --from=build /app/frontend/dist /srv
EXPOSE 8080