import logging
import subprocess
import threading
import time
import os
import re
from typing import Dict, Optional, List, Union
from dataclasses import dataclass, field

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
    """Configuration and state for a single stream conversion."""
    name: str
    rtmp_input: Union[str, List[str]]
    rtsp_output_port: int
    rtsp_output_path: str
    active: bool = False
    process: Optional[subprocess.Popen] = field(default=None, repr=False, compare=False)
    current_input_index: int = 0
    metrics: Dict[str, Union[str, int, float]] = field(default_factory=dict)

class RTMPToRTSPConverter:
    """Manages RTMP to RTSP stream conversions."""
    
    def __init__(self):
        self.streams: Dict[str, StreamConfig] = {}
        self.running = True
        self.monitor_thread = None

    def add_stream(self, name: str, rtmp_input: str, rtsp_port: int, rtsp_output_path: str) -> bool:
        """Add a new stream for conversion."""
        if name in self.streams:
            logger.error(f"Stream '{name}' already exists.")
            return False
        
        stream_config = StreamConfig(
            name=name,
            rtmp_input=rtmp_input,
            rtsp_output_port=rtsp_port,
            rtsp_output_path=rtsp_output_path
        )
        self.streams[name] = stream_config
        logger.info(f"Added stream '{name}': {rtmp_input} -> rtsp://localhost:{rtsp_port}/{rtsp_output_path}")
        return True

    def remove_stream(self, name: str) -> bool:
        """Remove and stop a stream."""
        if name not in self.streams:
            logger.error(f"Stream '{name}' not found.")
            return False

        self.stop_stream(name)
        del self.streams[name]
        logger.info(f"Removed stream '{name}'.")
        return True

    def start_stream(self, name: str) -> bool:
        """Start converting a specific stream."""
        stream = self.streams.get(name)
        if not stream:
            logger.error(f"Stream '{name}' not found.")
            return False

        if stream.active:
            logger.warning(f"Stream '{name}' is already active.")
            return True
        
        current_input = stream.rtmp_input

        cmd = [
            'ffmpeg',
            '-re',
            '-i', current_input,
            '-c:v', 'copy',
            '-c:a', 'copy',
            '-f', 'rtsp',
            '-rtsp_transport', 'tcp',
            '-progress', 'pipe:2',
            f'rtsp://localhost:{stream.rtsp_output_port}/{stream.rtsp_output_path}'
        ]

        try:
            logger.info(f"Starting stream '{name}' with command: {' '.join(cmd)}")
            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid if hasattr(os, 'setsid') else None
            )
            stream.process = process
            stream.active = True

            threading.Thread(target=self._log_ffmpeg_output, args=(process, name), daemon=True).start()

            logger.info(f"Stream '{name}' started. Access via: rtsp://localhost:{stream.rtsp_output_port}/{stream.rtsp_output_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to start stream '{name}': {e}")
            return False

    def _parse_metrics_from_line(self, line: str, stream: StreamConfig):
        """Parse metrics from FFmpeg output line."""
        key_value_pattern = re.compile(r'^\s*([a-zA-Z_0-9\.]+?)(?:=(\s*\S.*))?$')
        
        kv_match = key_value_pattern.match(line)
        if kv_match:
            key = kv_match.group(1).strip()
            value_str = kv_match.group(2)
            if value_str:
                value_str = value_str.strip()

            if key == 'frame':
                stream.metrics[key] = int(value_str) if value_str and value_str.isdigit() else 0
            elif key == 'fps':
                try:
                    stream.metrics[key] = float(value_str) if value_str else 0.0
                except ValueError:
                    stream.metrics[key] = 0.0
            elif key.startswith('stream_') and key.endswith('_q'):
                try:
                    stream.metrics['q'] = float(value_str) if value_str else -1.0
                except ValueError:
                    stream.metrics['q'] = -1.0
            elif key == 'size' or key == 'total_size':
                if value_str == 'N/A':
                    stream.metrics['size'] = 'N/A'
                else:
                    if 'KiB' in value_str:
                        num_val = float(value_str.replace('KiB', '').strip())
                        stream.metrics['size'] = int(round(num_val * 1024 / 1000))
                    elif 'kB' in value_str:
                        stream.metrics['size'] = int(value_str.replace('kB', '').strip())
                    else:
                        try:
                            stream.metrics['size'] = int(value_str)
                        except ValueError:
                            stream.metrics['size'] = 'N/A'
            elif key == 'time' or key == 'out_time':
                stream.metrics['time'] = value_str.split('.')[0] if value_str else "00:00:00"
            elif key == 'speed':
                try:
                    stream.metrics[key] = float(value_str.replace('x', '').strip()) if value_str else 0.0
                except ValueError:
                    stream.metrics[key] = 0.0
            elif key == 'drop_frames':
                stream.metrics['drop'] = int(value_str) if value_str and value_str.isdigit() else 0
            elif key == 'dup_frames':
                stream.metrics['dup'] = int(value_str) if value_str and value_str.isdigit() else 0
            
            if "Connection to" in line and "failed" in line:
                stream.metrics['connection_status'] = 'failed'
            elif "Stream mapping:" in line:
                stream.metrics['connection_status'] = 'connected'
            elif "Opening" in line and "for writing" in line:
                stream.metrics['connection_status'] = 'connecting'
            
            return

        multi_metric_patterns = {
            'frame': r'frame=\s*(\d+)',
            'fps': r'fps=\s*([\d.]+)',
            'q': r'q=\s*([-\d.]+)',
            'size': r'size=\s*(\s*\d+(?:KiB|kB)|N/A)',
            'time': r'time=(\d{2}:\d{2}:\d{2}\.\d{2})',
            'speed': r'speed=\s*([\d.]+)x',
            'drop': r'drop=(\s*\d+)',
            'dup': r'dup=(\s*\d+)'
        }
        
        for key, pattern in multi_metric_patterns.items():
            match = re.search(pattern, line)
            if match:
                value = match.group(1).strip()
                if key == 'size' and value == 'N/A':
                    stream.metrics['size'] = 'N/A'
                elif key == 'size':
                    if 'KiB' in value:
                        num_val = float(value.replace('KiB', '').strip())
                        stream.metrics[key] = int(round(num_val * 1024 / 1000))
                    elif 'kB' in value:
                        stream.metrics[key] = int(value.replace('kB', '').strip())
                    else:
                        try:
                            stream.metrics[key] = int(value.strip())
                        except ValueError:
                            stream.metrics[key] = 'N/A'
                elif key == 'drop' or key == 'dup':
                    try:
                        stream.metrics[key] = int(value)
                    except ValueError:
                        stream.metrics[key] = 0
                else:
                    try:
                        if key in ['frame', 'drop', 'dup']:
                            stream.metrics[key] = int(value)
                        elif key in ['fps', 'speed', 'q']:
                            stream.metrics[key] = float(value)
                        else:
                            stream.metrics[key] = value
                    except ValueError:
                        stream.metrics[key] = value

        if "Connection to" in line and "failed" in line:
            stream.metrics['connection_status'] = 'failed'
        elif "Stream mapping:" in line:
            stream.metrics['connection_status'] = 'connected'
        elif "Opening" in line and "for writing" in line:
            stream.metrics['connection_status'] = 'connecting'


    def _log_ffmpeg_output(self, process: subprocess.Popen, name: str):
        """Log FFmpeg process output and parse metrics."""
        stream = self.streams.get(name)
        if not stream:
            return
        
        try:
            for line_bytes in iter(process.stderr.readline, b''):
                if not line_bytes:
                    break
                    
                line = line_bytes.decode('utf-8', errors='ignore').strip()
                
                if not line:
                    continue

                logger.debug(f"[FFmpeg - {name}] {line}")

                self._parse_metrics_from_line(line, stream)

                if any(keyword in line.lower() for keyword in ['error', 'failed', 'warning']):
                    logger.warning(f"[FFmpeg - {name}] {line}")
                elif 'frame=' in line and 'fps=' in line and 'time=' in line:
                    logger.info(f"[FFmpeg - {name}] Progress: {line}")

        except Exception as e:
            logger.error(f"Error reading FFmpeg output for {name}: {e}")
        finally:
            if stream and stream.active:
                stream.active = False
                stream.metrics.clear()
                logger.warning(f"FFmpeg process for stream '{name}' has ended.")

    def stop_stream(self, name: str) -> bool:
        """Stop a specific stream."""
        stream = self.streams.get(name)
        if not stream:
            logger.error(f"Stream '{name}' not found.")
            return False

        if not stream.active:
            logger.warning(f"Stream '{name}' is not active.")
            return True

        if stream.process:
            try:
                stream.process.terminate()
                stream.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                stream.process.kill()
                stream.process.wait()
            except Exception as e:
                logger.error(f"Error stopping stream '{name}': {e}")
            stream.process = None

        stream.active = False
        stream.metrics.clear()
        logger.info(f"Stopped stream '{name}'.")
        return True

    def monitor_streams(self):
        """Monitor stream health and restart failed streams."""
        while self.running:
            try:
                for name, stream in list(self.streams.items()):
                    if stream.active and (stream.process is None or stream.process.poll() is not None):
                        logger.warning(f"Stream '{name}' has stopped unexpectedly. Restarting...")
                        stream.active = False
                        self.start_stream(name)
                time.sleep(5)
            except Exception as e:
                logger.error(f"Error in stream monitoring: {e}")
                time.sleep(5)

    def start_monitoring(self):
        """Start the monitoring thread."""
        if self.monitor_thread is None or not self.monitor_thread.is_alive():
            self.monitor_thread = threading.Thread(target=self.monitor_streams, daemon=True)
            self.monitor_thread.start()
            logger.info("Stream monitoring started.")

    def shutdown(self):
        """Gracefully shut down all active streams and the monitoring thread."""
        self.running = False
        for name in list(self.streams.keys()):
            self.stop_stream(name)
        
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=10)
            if self.monitor_thread.is_alive():
                logger.warning("Monitor thread did not shut down gracefully.")
        logger.info("Shutdown complete.")

    def get_all_status(self) -> Dict[str, Dict]:
        """Get the status of all streams."""
        return {
            name: {
                "rtmp_input": stream.rtmp_input,
                "rtsp_url": f"rtsp://localhost:{stream.rtsp_output_port}/{stream.rtsp_output_path}",
                "active": stream.active,
                "metrics": stream.metrics.copy() if stream.metrics else {}
            }
            for name, stream in self.streams.items()
        }
    
    def get_stream_status(self, name) -> Optional[Dict]:
        """Get the status of a specific stream."""
        stream = self.streams.get(name)
        if not stream:
            return None
        return {
            "rtmp_input": stream.rtmp_input,
            "rtsp_url": f"rtsp://localhost:{stream.rtsp_output_port}/{stream.rtsp_output_path}",
            "active": stream.active,
            "metrics": stream.metrics.copy() if stream.metrics else {}
        }