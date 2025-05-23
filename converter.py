import subprocess
import threading
import time
import logging
import json
import signal
import sys
import os
from datetime import datetime
from typing import Dict, Optional

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/converter.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class StreamConverter:
    """Упрощенный RTMP to RTSP конвертер"""
    
    def __init__(self, config_file='streams.json'):
        self.config_file = config_file
        self.processes = {}  # Активные процессы FFmpeg
        self.config = {}     # Конфигурация потоков
        self.running = True
        
        # Создаем директорию для логов
        os.makedirs('logs', exist_ok=True)
        
        # Загружаем конфигурацию
        self.load_config()
        
        # Обработчик сигналов
        signal.signal(signal.SIGINT, self.shutdown)
        signal.signal(signal.SIGTERM, self.shutdown)
    
    def load_config(self):
        """Загрузка конфигурации"""
        try:
            with open(self.config_file, 'r') as f:
                self.config = json.load(f)
            logger.info(f"Загружено {len(self.config.get('streams', {}))} потоков")
        except FileNotFoundError:
            logger.warning("Файл конфигурации не найден, создаем пример")
            self.create_default_config()
        except Exception as e:
            logger.error(f"Ошибка загрузки конфигурации: {e}")
            sys.exit(1)
    
    def create_default_config(self):
        """Создание конфигурации по умолчанию"""
        default_config = {
            "streams": {
                "test": {
                    "rtmp_url": "rtmp://localhost:1935/live/test",
                    "rtsp_port": 8554,
                    "stream_name": "test",
                    "quality": "medium"
                }
            },
            "settings": {
                "restart_delay": 10,
                "max_restart_attempts": 5,
                "log_level": "INFO"
            }
        }
        
        with open(self.config_file, 'w') as f:
            json.dump(default_config, f, indent=2)
        
        self.config = default_config
        logger.info(f"Создана конфигурация по умолчанию: {self.config_file}")
    
    def get_ffmpeg_cmd(self, stream_config):
        """Создание команды FFmpeg"""
        quality_settings = {
            "low": ["-s", "640x480", "-b:v", "500k", "-r", "15"],
            "medium": ["-s", "1280x720", "-b:v", "1500k", "-r", "25"], 
            "high": ["-s", "1920x1080", "-b:v", "3000k", "-r", "30"]
        }
        
        quality = stream_config.get("quality", "medium")
        quality_params = quality_settings.get(quality, quality_settings["medium"])
        
        cmd = [
            "ffmpeg",
            "-i", stream_config["rtmp_url"],
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-tune", "zerolatency",
            "-c:a", "aac",
            *quality_params,
            "-f", "rtsp",
            f"rtsp://0.0.0.0:{stream_config['rtsp_port']}/{stream_config['stream_name']}"
        ]
        
        return cmd
    
    def start_stream(self, stream_id):
        """Запуск потока"""
        if stream_id in self.processes:
            logger.warning(f"Поток {stream_id} уже запущен")
            return False
        
        stream_config = self.config["streams"].get(stream_id)
        if not stream_config:
            logger.error(f"Конфигурация для {stream_id} не найдена")
            return False
        
        try:
            cmd = self.get_ffmpeg_cmd(stream_config)
            logger.info(f"Запуск {stream_id}: {stream_config['rtmp_url']} -> RTSP:{stream_config['rtsp_port']}")
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            self.processes[stream_id] = {
                'process': process,
                'config': stream_config,
                'start_time': datetime.now(),
                'restart_count': 0
            }
            
            # Мониторинг в отдельном потоке
            monitor_thread = threading.Thread(
                target=self.monitor_stream,
                args=(stream_id,),
                daemon=True
            )
            monitor_thread.start()
            
            logger.info(f"Поток {stream_id} запущен (PID: {process.pid})")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка запуска {stream_id}: {e}")
            return False
    
    def monitor_stream(self, stream_id):
        """Мониторинг потока"""
        while self.running and stream_id in self.processes:
            stream_info = self.processes[stream_id]
            process = stream_info['process']
            
            # Проверяем статус процесса
            if process.poll() is not None:
                # Процесс завершился
                logger.warning(f"Процесс {stream_id} завершился с кодом {process.returncode}")
                
                # Попытка перезапуска
                if stream_info['restart_count'] < self.config['settings']['max_restart_attempts']:
                    stream_info['restart_count'] += 1
                    logger.info(f"Перезапуск {stream_id} (попытка {stream_info['restart_count']})")
                    
                    # Удаляем старый процесс
                    del self.processes[stream_id]
                    
                    # Ждем и перезапускаем
                    time.sleep(self.config['settings']['restart_delay'])
                    self.start_stream(stream_id)
                else:
                    logger.error(f"Превышено максимальное количество перезапусков для {stream_id}")
                    del self.processes[stream_id]
                break
            
            time.sleep(5)  # Проверяем каждые 5 секунд
    
    def stop_stream(self, stream_id):
        """Остановка потока"""
        if stream_id not in self.processes:
            logger.warning(f"Поток {stream_id} не запущен")
            return False
        
        try:
            process_info = self.processes[stream_id]
            process = process_info['process']
            
            process.terminate()
            
            # Ждем завершения
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
            
            del self.processes[stream_id]
            logger.info(f"Поток {stream_id} остановлен")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка остановки {stream_id}: {e}")
            return False
    
    def get_status(self):
        """Получение статуса всех потоков"""
        status = {
            "timestamp": datetime.now().isoformat(),
            "total_streams": len(self.config.get('streams', {})),
            "active_streams": len(self.processes),
            "streams": {}
        }
        
        for stream_id, stream_config in self.config.get('streams', {}).items():
            is_active = stream_id in self.processes
            stream_status = {
                "active": is_active,
                "rtmp_url": stream_config["rtmp_url"],
                "rtsp_url": f"rtsp://localhost:{stream_config['rtsp_port']}/{stream_config['stream_name']}",
                "quality": stream_config["quality"]
            }
            
            if is_active:
                process_info = self.processes[stream_id]
                stream_status.update({
                    "pid": process_info['process'].pid,
                    "start_time": process_info['start_time'].isoformat(),
                    "restart_count": process_info['restart_count']
                })
            
            status["streams"][stream_id] = stream_status
        
        return status
    
    def start_all(self):
        """Запуск всех потоков"""
        logger.info("Запуск всех потоков...")
        for stream_id in self.config.get('streams', {}):
            self.start_stream(stream_id)
            time.sleep(2)  # Задержка между запусками
    
    def stop_all(self):
        """Остановка всех потоков"""
        logger.info("Остановка всех потоков...")
        for stream_id in list(self.processes.keys()):
            self.stop_stream(stream_id)
    
    def shutdown(self, signum=None, frame=None):
        """Корректное завершение"""
        logger.info("Завершение работы конвертера...")
        self.running = False
        self.stop_all()
        sys.exit(0)
    
    def run(self):
        """Главный цикл"""
        logger.info("=== RTMP to RTSP Converter запущен ===")
        
        # Показываем информацию о конфигурации
        status = self.get_status()
        print(f"\nНастроено потоков: {status['total_streams']}")
        
        for stream_id, stream_info in status['streams'].items():
            print(f"  {stream_id}: {stream_info['rtmp_url']} -> {stream_info['rtsp_url']}")
        
        print("\nДля просмотра RTSP потока:")
        print("  vlc rtsp://localhost:PORT/STREAM_NAME")
        print("  ffplay rtsp://localhost:PORT/STREAM_NAME")
        print("\nДля остановки нажмите Ctrl+C\n")
        
        # Запускаем все потоки
        self.start_all()
        
        # Главный цикл мониторинга
        try:
            while self.running:
                time.sleep(30)
                
                # Показываем статус каждые 30 секунд
                status = self.get_status()
                logger.info(f"Активных потоков: {status['active_streams']}/{status['total_streams']}")
                
        except KeyboardInterrupt:
            logger.info("Получен сигнал остановки")
        finally:
            self.shutdown()

if __name__ == "__main__":
    converter = StreamConverter()
    converter.run()
