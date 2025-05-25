# from flask import Flask, render_template, jsonify, request
# from flask_cors import CORS
# import logging
# import re
# from converter import RTMPToRTSPConverter

# app = Flask(__name__)
# CORS(app)

# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# # Initialize converter
# converter = RTMPToRTSPConverter()
# converter.start_monitoring()

# def is_valid_rtmp_url(url):
#     """Validate RTMP URL format."""
#     pattern = re.compile(r'^rtmp://[\w.-]+(:[0-9]+)?/.*$')
#     return bool(pattern.match(url))

# @app.route('/')
# def index():
#     """Serve the main dashboard page"""
#     return render_template('web.html')

# @app.route('/api/streams', methods=['GET'])
# def list_streams():
#     """Get all streams status"""
#     return jsonify(converter.get_all_status())

# @app.route('/api/streams', methods=['POST'])
# def add_stream():
#     """Add a new stream"""
#     data = request.json
#     name = data.get('name') # This will be the unique path
#     rtmp_input = data.get('rtmp_input')
    
#     # We will now allow multiple streams on the same port, but they must have unique 'name' (path)
#     try:
#         rtsp_port = int(data.get('rtsp_port', 8554))
#         if rtsp_port < 1024 or rtsp_port > 65535:
#             return jsonify({"error": "RTSP port must be between 1024 and 65535"}), 400
#     except (ValueError, TypeError):
#         return jsonify({"error": "Invalid RTSP port"}), 400

#     if not name or not rtmp_input:
#         return jsonify({"error": "Missing name or RTMP URL"}), 400

#     if not is_valid_rtmp_url(rtmp_input):
#         return jsonify({"error": "Invalid RTMP URL"}), 400

#     # The 'name' must be unique as it serves as the RTSP path
#     if name in converter.streams:
#         return jsonify({"error": f"Stream with name '{name}' already exists. Please choose a unique name."}), 400

#     logger.info(f"Adding stream '{name}' with RTSP port {rtsp_port}")
#     # Pass the 'name' as the rtsp_output_path
#     if converter.add_stream(name, rtmp_input, rtsp_port, name):
#         if converter.start_stream(name):
#             return jsonify({
#                 "status": "success",
#                 "message": f"Stream added and started on port {rtsp_port} with path /{name}",
#                 "stream": converter.get_stream_status(name)
#             })
#         converter.remove_stream(name) # Clean up if start fails
#         return jsonify({"error": "Failed to start stream"}), 500

#     return jsonify({"error": "Failed to add stream"}), 400

# @app.route('/api/streams/<name>/toggle', methods=['POST'])
# def toggle_stream(name):
#     """Toggle stream state (start/stop)"""
#     stream = converter.get_stream_status(name)
#     if not stream:
#         return jsonify({"error": "Stream not found"}), 404

#     if stream['active']:
#         converter.stop_stream(name)
#     else:
#         converter.start_stream(name)
    
#     return jsonify(converter.get_stream_status(name))

# @app.route('/api/streams/<name>', methods=['DELETE'])
# def delete_stream(name):
#     """Delete a stream"""
#     if converter.remove_stream(name):
#         return jsonify({"status": "success", "message": f"Stream '{name}' deleted."})
#     return jsonify({"error": "Failed to delete stream or stream not found"}), 404

# if __name__ == '__main__':
#     app.run(host='0.0.0.0', debug=True)

from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import logging
import re
from converter import RTMPToRTSPConverter

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize stream converter and monitoring
converter = RTMPToRTSPConverter()
converter.start_monitoring()

def is_valid_rtmp_url(url):
    pattern = re.compile(r'^rtmp://[\w.-]+(:[0-9]+)?/.*$')
    return bool(pattern.match(url))

@app.route('/')
def index():
    return render_template('web.html')

@app.route('/api/streams', methods=['GET'])
def list_streams():
    return jsonify(converter.get_all_status())

@app.route('/api/streams', methods=['POST'])
def add_stream():
    data = request.json
    name = data.get('name')
    rtmp_input = data.get('rtmp_input')

    try:
        rtsp_port = int(data.get('rtsp_port', 8554))
        if rtsp_port < 1024 or rtsp_port > 65535:
            return jsonify({"error": "RTSP port must be between 1024 and 65535"}), 400
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid RTSP port"}), 400

    if not name or not rtmp_input:
        return jsonify({"error": "Missing name or RTMP URL"}), 400
    if not is_valid_rtmp_url(rtmp_input):
        return jsonify({"error": "Invalid RTMP URL"}), 400
    if name in converter.streams:
        return jsonify({"error": f"Stream with name '{name}' already exists."}), 400

    logger.info(f"Adding stream '{name}' with RTSP port {rtsp_port}")

    # Add and start the stream
    if converter.add_stream(name, rtmp_input, rtsp_port, name):
        if converter.start_stream(name):
            return jsonify({
                "status": "success",
                "message": f"Stream added and started on port {rtsp_port} with path /{name}",
                "stream": converter.get_stream_status(name)
            })
        converter.remove_stream(name)
        return jsonify({"error": "Failed to start stream"}), 500

    return jsonify({"error": "Failed to add stream"}), 400

@app.route('/api/streams/<name>/toggle', methods=['POST'])
def toggle_stream(name):
    # Start or stop a stream by name
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
    # Remove a stream by name
    if converter.remove_stream(name):
        return jsonify({"status": "success", "message": f"Stream '{name}' deleted."})
    return jsonify({"error": "Failed to delete stream or stream not found"}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
