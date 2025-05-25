# RTMP to RTSP Converter

## 📡 Overview

This project provides a simple and efficient way to convert RTMP streams to RTSP streams using **FFmpeg** and **MediaMTX**. It includes a web interface for managing streams and monitoring their status in real-time.

## ✨ Features

- Convert RTMP streams to RTSP streams.
- Web interface for adding, managing, and monitoring streams.
- Real-time metrics for active streams.
- Dockerized setup for easy deployment.
- Auto-restart for failed streams.

## 🚀 Quick Start

### Prerequisites

Ensure you have the following installed:

- **Python 3.7+** - Core runtime environment
  ```bash
  python --version
  # Ensure pip is up-to-date
  python -m pip install --upgrade pip
  ```

- **FFmpeg** - Media processing engine
  ```bash
  # Ubuntu/Debian
  sudo apt update && sudo apt install ffmpeg
  
  # macOS
  brew install ffmpeg
  
  # Windows
  # Download from https://ffmpeg.org/download.html
  ```

- **Docker** - For containerized deployment
  ```bash
  # Verify Docker installation
  docker --version
  
  # Install docker-compose if not included
  docker-compose --version || sudo apt install docker-compose
  ```

> **Note:** MediaMTX is included in the project setup and does not require separate installation.

### Installation

#### Method 1: Direct Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/akylzx/decentrathon.git
   cd decentrathon/
   ```

2. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Verify FFmpeg installation:**
   ```bash
   ffmpeg -version
   ```

#### Method 2: Docker Installation

1. **Clone and build:**
   ```bash
   git clone https://github.com/akylzx/decentrathon.git
   cd decentrathon/rtmp-rtsp-converter
   docker-compose up --build
   ```

### Running the Application

#### Standard Deployment

1. **Start the Flask server:**
   ```bash
   python app.py
   ```

2. **Access the web interface:**
   ```
   http://localhost:5000
   ```

#### Docker Deployment

```bash
docker-compose up -d
```

The application will be available at `http://localhost:5000`.

### Default Ports

- Flask API: `5000`
- RTSP Server: `8554`
- RTMP Input: `1935`

## 📖 Usage Guide

### Web Interface

1. **Navigate to the dashboard** at `http://localhost:5000`
2. **Add a new stream:**
   - Enter stream name (e.g., "drone_feed")
   - Input RTMP URL (e.g., `rtmp://source.example.com/live/stream`)
   - Configure RTSP port (default: 8554)
   - Click "Add Stream"

3. **Manage streams:**
   - **Start/Stop** streams with toggle buttons
   - **Monitor metrics** in real-time
   - **Delete** unused streams
   - **Preview** streams using built-in player

### Stream Preview Methods

#### VLC Media Player
```bash
vlc rtsp://localhost:8554/your_stream_name
```

#### FFplay
```bash
ffplay rtsp://localhost:8554/your_stream_name
```

## 📁 Project Structure

```
decentrathon/rtmp-rtsp-converter/
├── app.py                 # Flask application and API routes
├── converter.py           # Core RTMP→RTSP conversion logic
├── docker-compose.yml    
├── Dockerfile          
├── templates/
│   └── web.html           # Web interface dashboard
├── streams.json           # Stream configurations
├── config/
│   └── mediamtx.yml       # MediaMTX configuration
├── rtmp_rtsp_converter.logs # Application logs
└── README.md          
```

## 🔍 Monitoring and Troubleshooting

### Common Issues

#### 1. FFmpeg Not Found
```bash
# Check FFmpeg installation
ffmpeg -version

# If not installed:
# Ubuntu/Debian: sudo apt install ffmpeg
# macOS: brew install ffmpeg
# Windows: Download from ffmpeg.org
```

#### 2. Port Already in Use
```bash
# Check port usage
netstat -tulpn | grep :5000

# Use different port
export FLASK_RUN_PORT=5001
python app.py
```

#### 3. Docker Issues
```bash
# Check Docker logs
docker-compose logs

# Restart containers
docker-compose down && docker-compose up -d
```

### Stream Testing
```bash
# Test with sample RTMP stream
ffmpeg -re -i sample.mp4 -c copy -f flv rtmp://localhost:1935/live/test

# Verify RTSP output
ffplay rtsp://localhost:8554/test
```

## 🚀 Production Deployment

### Performance Optimization

1. **Use Production WSGI Server:**
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:5000 app:app
   ```

2. **Enable Hardware Acceleration:**
   ```bash
   # NVIDIA GPU
   ffmpeg -hwaccel cuda ...
   
   # Intel Quick Sync
   ffmpeg -hwaccel qsv ...
   ```

3. **Optimize System:**
   ```bash
   # Increase file descriptors
   ulimit -n 65536
   
   # Optimize network buffers
   echo 'net.core.rmem_max = 16777216' >> /etc/sysctl.conf
   ```

### Development Setup

```bash
# Clone and setup development environment
git clone https://github.com/akylzx/decentrathon.git
cd decentrathon/rtmp-rtsp-converter

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate    # Windows

# Install development dependencies
pip install -r requirements-dev.txt

# Run in development mode
export FLASK_ENV=development
python app.py
```

