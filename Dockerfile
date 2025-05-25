FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    unzip \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download and install MediaMTX
# RUN curl -L -o mediamtx.zip https://github.com/bluenviron/mediamtx/releases/latest/download/mediamtx_linux_amd64.zip && \
#     unzip mediamtx.zip -d /usr/local/bin/ && \
#     rm mediamtx.zip

# Copy application files
COPY . .

# Expose necessary ports
EXPOSE 5000 8554

# Add healthcheck for Flask server
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
    CMD curl -f http://localhost:5000/ || exit 1

# Start MediaMTX and Flask server
# CMD /usr/local/bin/mediamtx --config ./config/mediamtx.yml & python app.py
