# Multi-stage Dockerfile for IDS Backend and Frontend

# Stage 1: Backend
FROM python:3.11-slim as backend

WORKDIR /app/backend

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpcap-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ .

# Expose backend port
EXPOSE 3002

# Stage 2: Frontend
FROM node:18-alpine as frontend

WORKDIR /app

# Copy package files
COPY package*.json ./
COPY next.config.mjs ./
COPY tsconfig.json ./

# Install dependencies
RUN npm ci

# Copy frontend source
COPY app ./app
COPY components ./components
COPY lib ./lib
COPY public ./public
COPY hooks ./hooks

# Build frontend
RUN npm run build

# Stage 3: Production
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for backend
RUN apt-get update && apt-get install -y \
    gcc \
    libpcap-dev \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# Copy backend from stage 1
COPY --from=backend /app/backend ./backend
COPY --from=backend /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=backend /usr/local/bin /usr/local/bin

# Copy frontend build from stage 2
COPY --from=frontend /app/.next ./.next
COPY --from=frontend /app/node_modules ./node_modules
COPY --from=frontend /app/package.json ./
COPY --from=frontend /app/public ./public

# Create startup script
RUN echo '#!/bin/bash\n\
set -e\n\
cd /app/backend\n\
if [ ! -f .env ]; then\n\
  echo "ERROR: .env file not found. Please mount it as a volume or create it."\n\
  exit 1\n\
fi\n\
echo "Starting backend..."\n\
python app.py &\n\
BACKEND_PID=$!\n\
cd /app\n\
echo "Starting frontend..."\n\
npm start &\n\
FRONTEND_PID=$!\n\
echo "Both services started. PIDs: Backend=$BACKEND_PID, Frontend=$FRONTEND_PID"\n\
wait $BACKEND_PID $FRONTEND_PID\n\
' > /app/start.sh && chmod +x /app/start.sh

EXPOSE 3000 3002

CMD ["/app/start.sh"]
