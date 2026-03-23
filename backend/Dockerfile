FROM node:22-bookworm AS builder

WORKDIR /app/backend

COPY backend/package*.json ./
RUN npm ci

COPY backend/tsconfig.json ./
COPY backend/server.ts ./
RUN npm run build


FROM node:22-bookworm-slim AS runtime

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-pip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN pip3 install --no-cache-dir -r requirements.txt

COPY cli_bridge.py ./
COPY engine ./engine

WORKDIR /app/backend

COPY backend/package*.json ./
RUN npm ci --omit=dev && npm cache clean --force

COPY --from=builder /app/backend/server.js ./server.js

ENV NODE_ENV=production \
    PORT=3000 \
    PYTHON_EXECUTABLE=python3

EXPOSE 3000

CMD ["node", "server.js"]
