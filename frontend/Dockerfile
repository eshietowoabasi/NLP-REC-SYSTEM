# Frontend image.
#   dev   - Vite dev server with hot reload (used by docker-compose.yml)
#   build - compiled static assets, copied into the Nginx image in production
FROM node:24-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM deps AS dev
COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev"]

FROM deps AS build
COPY . .
RUN npm run build
