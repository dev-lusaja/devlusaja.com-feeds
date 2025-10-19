FROM python:3.11-slim

WORKDIR /app

# Instalar mysql-client para mysqldump
RUN apt-get update && \
    apt-get install -y --no-install-recommends default-mysql-client && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY docker/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY src ./src
COPY feeds_config.yaml .

CMD ["python", "src/feed_fetcher.py"]
