FROM node:20-alpine

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
