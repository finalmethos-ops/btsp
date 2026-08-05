FROM node:20-alpine@sha256:fb4cd12c85ee03686f6af5362a0b0d56d50c58a04632e6c0fb8363f609372293

ARG BUILD_VERSION=development
ARG BUILD_REVISION=unknown
ARG BUILD_CREATED=unknown

LABEL org.opencontainers.image.title="BTSP Frontend" \
    org.opencontainers.image.description="Buddy's Technology Services Platform web application" \
    org.opencontainers.image.source="https://github.com/finalmethos-ops/btsp" \
    org.opencontainers.image.version="$BUILD_VERSION" \
    org.opencontainers.image.revision="$BUILD_REVISION" \
    org.opencontainers.image.created="$BUILD_CREATED"

WORKDIR /app

RUN chown node:node /app

USER node

ARG NEXT_PUBLIC_API_BASE_URL=""
ENV NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL

COPY --chown=node:node package.json package-lock.json ./
RUN npm ci

COPY --chown=node:node . .
RUN npm run build

EXPOSE 3000

CMD ["npm", "run", "dev"]
