# docker/frontend.Dockerfile
FROM node:23.5.0-slim

WORKDIR /app

COPY package*.json ./
RUN npm cache clean --force && \
    rm -rf .next && \
    npm install

COPY . .
RUN npm run build

EXPOSE 3000
CMD ["npm", "run", "dev"]