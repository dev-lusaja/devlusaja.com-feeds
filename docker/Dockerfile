FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias del sistema para mysql-client y Playwright
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    default-mysql-client \
    # Dependencias para Playwright/Chromium
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    libatspi2.0-0 \
    libxshmfence1 \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY docker/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Instalar navegadores de Playwright
RUN playwright install chromium

# yt-dlp se rompe cuando TikTok cambia su API: YTDLP_DATE (fecha, desde run.sh)
# invalida solo esta capa una vez al día para traer la última versión.
ARG YTDLP_DATE
RUN echo "yt-dlp update ${YTDLP_DATE}" && pip install --no-cache-dir -U yt-dlp

COPY src ./src
COPY feeds_config.yaml .

CMD ["python", "src/feed_fetcher.py"]
