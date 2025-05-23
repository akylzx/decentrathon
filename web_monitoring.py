#!/usr/bin/env python3
"""
Web Monitor для RTMP to RTSP Converter
Простой веб-интерфейс для мониторинга потоков
"""

from flask import Flask, jsonify, render_template_string
import json
import psutil
import os
from datetime import datetime

app = Flask(__name__)

# HTML шаблон
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>RTMP to RTSP Converter - Monitor</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
        .card { background: white; padding: 20px; border-radius: 8px; margin-bottom: 15px; }
        .status-active { color: #4CAF50; font-weight: bold; }
        .status-inactive { color: #f44336; font-weight: bold; }
        .stream-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 20px; }
        .stream-card { border-left: 4px solid #2196F3; }
        .stream-card.active { border-left-color: #4CAF50; }
        .stream-card.inactive { border-left-color: #f44336; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background-color: #f2f2f2; }
        .btn { padding: 8px 16px; border: none; border-radius: 4px; cursor: pointer; margin: 5px; }
        .btn-success { background-color: #4CAF50; color: white; }
        .btn-danger { background-color: #f44336; color: white; }
        .btn-info { background-color: #2196F3; color: white; }
        .system-info { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px; }
        .metric { text-align: center; padding: 10px; background: #e3f2fd; border-radius: 4px; }
    </style>
    <script>
        function refreshData() {
            fetch('/api/status')
                .then(response => response.json())
                .then(data => updateDisplay(data))
                .catch(error => console.error('Error:', error));
        }
        
        function updateDisplay(data) {
            document.getElementById('timestamp').textContent = new Date(data.timestamp).toLocaleString();
            document.getElementById('active-count').textContent = data.active_streams;
            document.getElementById('total-count').textContent = data.total_streams;
            
            const container = document.getElementById('streams-container');
            container.innerHTML = '';
            
            Object.entries(data.streams).forEach(([streamId, stream]) => {
                const card = document.createElement('div');
                card.className = `card stream-card ${stream.active ? 'active' : 'inactive'}`;
                card.innerHTML = `
                    <h3>${streamId}</h3>
                    <p><strong>Статус:</strong> <span class="${stream.active ? 'status-active' : 'status-inactive'}">${stream.active ? 'Активен' : 'Остановлен'}</span></p>
                    <p><strong>RTMP:</strong> ${stream.rtmp_url}</p>
                    <p><strong>RTSP:</strong> ${stream.rtsp_url}</p>
                    <p><strong>Качество:</strong> ${stream.quality}</p>
                    ${stream.active ? `
                        <p><strong>PID:</strong> ${stream.pid || 'N/A'}</p>
                        <p><strong>Запущен:</strong> ${stream.start_time ? new Date(stream.start_time).toLocaleString() : 'N/A'}</p>
                        <p><strong>Перезапуски:</strong> ${stream.restart_count || 0}</p>
                    ` : ''}
                    <div>
                        <button class="btn ${stream.active ? 'btn-danger' : 'btn-success'}" onclick="${stream.active ? 'stopStream' : 'startStream'}('${streamId}')">
                            ${stream.active ? 'Остановить' : 'Запустить'}
                        </button>
                        <button class="btn btn-info" onclick="testStream('${stream.rtsp_url}')">Тест</button>
                    </div>
                `;
                container.appendChild(card);
            });
        }
        
        function startStream(streamId) {
            fetch(`/api/start/${streamId}`, {method: 'POST'})
                .then(response => response.json())
                .then(data => {
                    alert(data.message);
                    refreshData();
                });
        }
        
        function stopStream(streamId) {
            fetch(`/api/stop/${streamId}`, {method: 'POST'})
                .then(response => response.json())
                .then(data => {
                    alert(data.message);
                    refreshData();
                });
        }
        
        function testStream(rtspUrl) {
            alert(`Тестовые команды для ${rtspUrl}:\\n\\nVLC: vlc ${rtspUrl}\\nFFplay: ffplay ${rtspUrl}`);
        }
        
        // Автообновление каждые 5 секунд
        setInterval(refreshData, 5000);
        
        // Загружаем данные при загрузке страницы
        window.onload = function() {
            refreshData();
            updateSystemInfo();
        };
        
        function updateSystemInfo() {
            fetch('/api/system')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('cpu-usage').textContent = data.cpu_percent + '%';
                    document.getElementById('memory-usage').textContent = data.memory_percent + '%';
                    document.getElementById('disk-usage').textContent = data.disk_percent + '%';
                });
        }
        
        setInterval(updateSystemInfo, 10000);
    </script>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎥 RTMP to RTSP Converter</h1>
            <p>Мониторинг и управление видеопотоками</p>
            <p><strong>Последнее обновление:</strong> <span id="timestamp">-</span></p>
        </div>
        
        <div class="card">
            <h2>📊 Общая статистика</h2>
            <div class="system-info">
                <div class="metric">
                    <h3 id="active-count">0</h3>
                    <p>Активных потоков</p>
                </div>
                <div class="metric">
                    <h3 id="total-count">0</h3>
                    <p>Всего потоков</p>
                </div>
                <div class="metric">
                    <h3 id="cpu-usage">0%</h3>
                    <p>Загрузка CPU</p>
                </div>
                <div class="metric">
                    <h3 id="memory-usage">0%</h3>
                    <p>Загрузка RAM</p>
                </div>
            </div>
        </div>
        
        <div class="card">
            <h2>🎬 Видеопотоки</h2>
            <div class="stream-grid" id="streams-container">
                <!-- Потоки будут загружены через JavaScript -->
            </div>
        </div>
        
        <div class="card">
            <h2>📝 Быстрые команды</h2>
            <div>
                <button class="btn btn-success" onclick="fetch('/api/start_all', {method: 'POST'}).then(() => refreshData())">Запустить все</button>
                <button class="btn btn-danger" onclick="fetch('/api/stop_all', {method: 'POST'}).then(() => refreshData())">Остановить все</button>
                <button class="btn btn-info" onclick="window.open('/api/logs', '_blank')">Просмотр логов</button>
            </div>
        </div>
    </div>
</body>
</html>
"""

def load_config():
    """Загрузка конфигурации"""
    try:
        with open('streams.json', 'r') as f:
            return json.load(f)
    except:
        return {"streams": {}, "settings": {}}

def get_stream_processes():
    """Получение активных процессов конвертера"""
    processes = {}
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if 'ffmpeg' in proc.info['name'] and proc.info['cmdline']:
                cmdline = ' '.join(proc.info['cmdline'])
                if 'rtsp://' in cmdline and 'rtmp://' in cmdline:
                    # Извлекаем RTSP порт из командной строки
                    for part in proc.info['cmdline']:
                        if part.startswith('rtsp://') and ':' in part:
                            port = part.split(':')[2].split('/')[0]
                            processes[port] = {
                                'pid': proc.info['pid'],
                                'cmdline': cmdline
                            }
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return processes

@app.route('/')
def index():
    """Главная страница"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/status')
def api_status():
