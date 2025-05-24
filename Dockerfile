
FROM python:3.11-slim

# Install FFmpeg and required system packages
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy all application files
COPY . .

# Create logs directory
RUN mkdir -p logs

# Create a default configuration if none exists
RUN echo '[]' > streams.json

# Expose Flask port and RTSP ports
EXPOSE 5000 8554-8560

# Run the Flask application
CMD ["python", "app.py"]