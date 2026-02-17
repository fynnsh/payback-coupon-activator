FROM mcr.microsoft.com/playwright/python:v1.58.0-jammy

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Europe/Berlin
ENV COOKIES_FILE=/app/data/cookies.json
ENV WEB_PORT=8080
RUN pip install --no-cache-dir -r requirements.txt \
    && apt-get update && apt-get install -y --no-install-recommends tzdata \
    && ln -sf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*

# Copy source code
COPY src/ ./src/

# Create directories
RUN mkdir -p /app/logs /app/data

EXPOSE 8080

# Run as non-root user for security (UID 1000 exists in playwright base image)
RUN useradd -m appuser 2>/dev/null || true && chown -R appuser:appuser /app
USER appuser

CMD ["python", "-m", "src.main"]
