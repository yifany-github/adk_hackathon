# NHL Commentary System - Cloud Run Deployment
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy entire project
COPY . .

# Create data directories
RUN mkdir -p data/live data/static data/sequential_agent_outputs data/data_agent_outputs data/commentary_agent_outputs

# Expose port for Cloud Run
EXPOSE 8080

# Run the commentary server
CMD ["python", "commentary_server.py"]