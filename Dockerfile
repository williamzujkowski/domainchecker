# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Install cron and other system dependencies
RUN apt-get update && apt-get install -y cron wget && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download NLTK words corpus so first-run downloads are not needed
RUN python -c "import nltk; nltk.download('words')"

# Copy application code
COPY . /app

# Create directories for logs and output
RUN mkdir -p logs output

# Setup cron job to run the check_domains.py script daily.
# CRON_EXPR can be overridden via build-args or environment variables.
ARG CRON_EXPR="0 0 * * *"
RUN echo "$CRON_EXPR root python /app/check_domains.py >> /app/logs/cron.log 2>&1" > /etc/cron.d/domain-checker && \
    chmod 0644 /etc/cron.d/domain-checker && \
    crontab /etc/cron.d/domain-checker

# Expose volume mounts for logs and output (optional)
VOLUME ["/app/logs", "/app/output"]

# Default command: start cron in foreground
CMD ["cron", "-f"]
