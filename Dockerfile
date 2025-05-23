FROM python:3.11-slim

# Install FFmpeg and required system packages
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy application files
COPY converter.py .
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create logs directory
RUN mkdir -p logs

# Create a default configuration if none exists
RUN echo '[]' > streams.json

# Expose RTSP ports (8554-8560 range)
EXPOSE 8554-8560

# Run the application
CMD ["python", "rtmp_rtsp_converter.py", "--config", "streams.json"]