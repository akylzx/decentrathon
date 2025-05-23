#!/usr/bin/env python3
"""
RTMP to RTSP Stream Converter - Fixed Version
Properly handles different streaming methods and protocols.
"""

import logging
import json
import subprocess
import threading
import time
import os
import signal
import sys
from typing import Dict, Optional, List
from dataclasses import dataclass, field

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('rtmp_rtsp_converter.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class StreamConfig:
    """Configuration for a single stream conversion"""
    name: str
    rtmp_input: str
    rtsp_output_port: int
    rtsp_output_path: str = "stream"
    active: bool = False
    process: Optional[subprocess.Popen] = field(default=None, repr=False, compare=False)

class RTMPToRTSPConverter:
    """Main converter class that manages RTMP to RTSP stream conversions"""
    
    def __init__(self, base_rtsp_port: int = 8554):
        self.base_rtsp_port = base_rtsp_port
        self.streams: Dict[str, StreamConfig] = {}
        self.running = True
        self.monitor_thread = threading.Thread(target=self.monitor_streams, daemon=True)
        self.monitor_thread.start()

    def add_stream(self, name: str, rtmp_input: str, rtsp_port: Optional[int] = None) -> bool:
        """Add a new stream for conversion"""
        if name in self.streams:
            logger.error(f"Stream '{name}' already exists.")
            return False

        if rtsp_port is None:
            rtsp_port = self.base_rtsp_port + len(self.streams)

        # Validate RTSP port uniqueness
        for stream in self.streams.values():
            if stream.rtsp_output_port == rtsp_port:
                logger.error(f"RTSP port {rtsp_port} is already in use.")
                return False

        stream_config = StreamConfig(name=name, rtmp_input=rtmp_input, rtsp_output_port=rtsp_port)
        self.streams[name] = stream_config
        logger.info(f"Added stream '{name}': {rtmp_input} -> rtsp://localhost:{rtsp_port}/{stream_config.rtsp_output_path}")
        return True

    def remove_stream(self, name: str) -> bool:
        """Remove and stop a stream"""
        if name not in self.streams:
            logger.error(f"Stream '{name}' not found.")
            return False

        self.stop_stream(name)
        del self.streams[name]
        logger.info(f"Removed stream '{name}'.")
        return True

    def start_stream(self, name: str) -> bool:
        """Start converting a specific stream"""
        if name not in self.streams:
            logger.error(f"Stream '{name}' not found.")
            return False

        stream = self.streams[name]
        if stream.active:
            logger.warning(f"Stream '{name}' is already active.")
            return True

        cmd = [
            'ffmpeg',
            '-re',
            '-i', stream.rtmp_input,
            '-c', 'copy',
            '-f', 'rtsp',
            '-rtsp_transport', 'tcp',
            '-listen', '1',
            f'rtsp://0.0.0.0:{stream.rtsp_output_port}/{stream.rtsp_output_path}'
        ]

        try:
            logger.info(f"Starting stream '{name}' with command: {' '.join(cmd)}")
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stream.process = process
            stream.active = True

            # Log FFmpeg output for debugging
            threading.Thread(target=self._log_ffmpeg_output, args=(process, name), daemon=True).start()

            logger.info(f"Started stream '{name}'.")
            return True
        except Exception as e:
            logger.error(f"Failed to start stream '{name}': {e}")
            return False

    def _log_ffmpeg_output(self, process: subprocess.Popen, name: str):
        """Log FFmpeg process output."""
        for line in process.stderr:
            logger.info(f"[FFmpeg - {name}] {line.decode().strip()}")

    def stop_stream(self, name: str) -> bool:
        """Stop a specific stream"""
        if name not in self.streams:
            logger.error(f"Stream '{name}' not found.")
            return False

        stream = self.streams[name]
        if not stream.active:
            logger.warning(f"Stream '{name}' is not active.")
            return True

        if stream.process:
            stream.process.terminate()
            stream.process.wait()
            stream.process = None

        stream.active = False
        logger.info(f"Stopped stream '{name}'.")
        return True

    def monitor_streams(self):
        """Monitor stream health and restart failed streams"""
        while self.running:
            for name, stream in list(self.streams.items()):
                if stream.active and (stream.process is None or stream.process.poll() is not None):
                    logger.warning(f"Stream '{name}' has stopped unexpectedly. Restarting...")
                    self.start_stream(name)
            time.sleep(5)

    def start_monitoring(self):
        """Start the monitoring thread explicitly."""
        if not self.monitor_thread.is_alive():
            self.monitor_thread = threading.Thread(target=self.monitor_streams, daemon=True)
            self.monitor_thread.start()
            logger.info("Stream monitoring started.")

    def shutdown(self):
        """Graceful shutdown"""
        self.running = False
        for name in list(self.streams.keys()):
            self.stop_stream(name)
        logger.info("Shutdown complete.")

    def get_all_status(self) -> Dict[str, Dict]:
        """Get the status of all streams."""
        return {
            name: {
                "rtmp_input": stream.rtmp_input,
                "rtsp_url": f"rtsp://localhost:{stream.rtsp_output_port}/{stream.rtsp_output_path}",
                "active": stream.active
            }
            for name, stream in self.streams.items()
        }

def load_config(config_file: str) -> List[Dict]:
    """Load stream configurations from JSON file"""
    try:
        with open(config_file, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"Configuration file '{config_file}' not found.")
        return []
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON from '{config_file}': {e}")
        return []

def create_sample_config(config_file: str):
    """Create a sample configuration file"""
    sample_config = [
        {
            "name": "test_stream",
            "rtmp_input": "rtmp://localhost/live/test",
            "rtsp_port": 8554
        }
    ]
    with open(config_file, 'w') as f:
        json.dump(sample_config, f, indent=4)
    logger.info(f"Sample configuration created: {config_file}")

def signal_handler(signum, frame, converter):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}, shutting down...")
    converter.shutdown()
    sys.exit(0)

def main():
    import argparse

    parser = argparse.ArgumentParser(description="RTMP to RTSP Stream Converter")
    parser.add_argument("--config", default="streams.json", help="Configuration file (default: streams.json)")
    parser.add_argument("--create-config", action="store_true", help="Create sample configuration file")
    args = parser.parse_args()

    if args.create_config:
        create_sample_config(args.config)
        return

    converter = RTMPToRTSPConverter()
    signal.signal(signal.SIGINT, lambda s, f: signal_handler(s, f, converter))

    config = load_config(args.config)
    for stream in config:
        converter.add_stream(stream['name'], stream['rtmp_input'], stream.get('rtsp_port'))

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        converter.shutdown()

if __name__ == "__main__":
    main()