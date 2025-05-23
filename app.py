from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import logging
import re
from converter import RTMPToRTSPConverter

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize converter
converter = RTMPToRTSPConverter()
converter.start_monitoring()

def is_valid_rtmp_url(url):
    """Validate RTMP URL format."""
    pattern = re.compile(r'^rtmp://[\w.-]+(:[0-9]+)?/.*$')
    return bool(pattern.match(url))

@app.route('/')
def index():
    """Serve the main dashboard page"""
    return render_template('web.html')

@app.route('/api/streams', methods=['GET'])
def list_streams():
    """Get all streams status"""
    return jsonify(converter.get_all_status())

@app.route('/api/streams', methods=['POST'])
def add_stream():
    """Add a new stream"""
    data = request.json
    name = data.get('name')
    rtmp_input = data.get('rtmp_input')
    rtsp_port = int(data.get('rtsp_port', 8554))

    if not name or not rtmp_input:
        return jsonify({"error": "Missing name or RTMP URL"}), 400

    if not is_valid_rtmp_url(rtmp_input):
        return jsonify({"error": "Invalid RTMP URL"}), 400

    # Check if the RTSP port is already in use
    for stream in converter.streams.values():
        if stream.rtsp_output_port == rtsp_port:
            return jsonify({"error": "RTSP port is already in use"}), 400

    # Add and start the stream
    if converter.add_stream(name, rtmp_input, rtsp_port):
        if converter.start_stream(name):
            return jsonify({
                "status": "success",
                "message": "Stream added and started",
                "stream": converter.get_stream_status(name)
            })
        converter.remove_stream(name)
        return jsonify({"error": "Failed to start stream"}), 500

    return jsonify({"error": "Failed to add stream"}), 400

@app.route('/api/streams/<name>/toggle', methods=['POST'])
def toggle_stream(name):
    """Toggle stream state"""
    stream = converter.get_stream_status(name)
    if not stream:
        return jsonify({"error": "Stream not found"}), 404

    if stream['active']:
        converter.stop_stream(name)
    else:
        converter.start_stream(name)
    
    return jsonify(converter.get_stream_status(name))

@app.route('/api/streams/<name>', methods=['DELETE'])
def delete_stream(name):
    """Delete a stream"""
    if converter.remove_stream(name):
        return jsonify({"status": "success"})
    return jsonify({"error": "Failed to delete stream"}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)