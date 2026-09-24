# ─────────────────────────────────────────────────────────────────────────────
# Dockerfile — used by Railway for both API and bot services
# API service:  CMD ["python", "api.py"]
# Bot service:  override start command to: python bot.py
# ─────────────────────────────────────────────────────────────────────────────

FROM python:3.12-slim

# Install Node.js 20 (needed to build the React dashboard)
RUN apt-get update && \
    apt-get install -y curl ca-certificates && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ── Python deps ───────────────────────────────────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── React dashboard build ─────────────────────────────────────────────────────
COPY dashboard/package*.json dashboard/
RUN cd dashboard && npm install

COPY dashboard/ dashboard/
RUN cd dashboard && npm run build

# ── Copy the rest of the app ──────────────────────────────────────────────────
COPY . .

# Default: start the API server (bot service overrides this in Railway UI)
EXPOSE 8000
CMD ["python", "api.py"]
