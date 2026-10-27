# Review UI image: build with node, serve statically via nginx (/v1 proxied to api).
FROM node:22-alpine AS build
WORKDIR /ui
COPY package.json package-lock.json* ./
# npm ci when the lockfile is present (committed), plain install otherwise.
RUN npm ci --no-audit --no-fund || npm install --no-audit --no-fund
COPY . .
RUN npm run build

FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /ui/dist /usr/share/nginx/html
EXPOSE 80
