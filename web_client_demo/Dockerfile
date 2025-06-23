FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project structure
COPY . .
COPY ../src ./src
COPY ../data ./data

# Create necessary directories
RUN mkdir -p audio_output \
    && mkdir -p data/live \
    && mkdir -p data/sequential_agent_v3_outputs \
    && mkdir -p data/static \
    && mkdir -p static

# Set environment variables
ENV PORT=8080
ENV FLASK_ENV=production
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8080/ || exit 1

# Run the application
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "--timeout", "300", "--worker-class", "eventlet", "--worker-connections", "1000", "app:app"] 