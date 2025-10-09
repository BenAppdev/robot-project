import socket
import cv2
import numpy as np
import logging
import struct
import time
from flask import Flask, Response
from threading import Thread, Lock

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Configuration variables
CONFIG = {
    'HOST': '',               # Bind to all interfaces for TCP
    'PORT_STREAM': 5001,      # Port for video stream
    'BUFFER_SIZE': 4096,      # Socket buffer size
    'FRAME_TIMEOUT': 1.0,     # Seconds before dropping frame
    'WEB_PORT': 8080,         # Port for Flask web server
    'EXPECTED_CAMERA': 0       # Single camera index
}

# Initialize Flask app
app = Flask(__name__)

# Store latest frame and edges in memory with thread-safe lock
latest_frame = None
latest_edges = None
frame_lock = Lock()

def receive_frame(client):
    """Receives a frame with header (cam_id, frame_size) and decodes it."""
    try:
        header = client.recv(8)
        if len(header) != 8:
            logging.warning("Incomplete header received")
            return None, None
        cam_id, frame_size = struct.unpack('!II', header)
        logging.debug(f"Received header: cam_id={cam_id}, frame_size={frame_size}")

        frame_data = b''
        bytes_received = 0
        while bytes_received < frame_size:
            chunk = client.recv(min(CONFIG['BUFFER_SIZE'], frame_size - bytes_received))
            if not chunk:
                logging.warning("Connection closed during frame receive")
                return None, None
            frame_data += chunk
            bytes_received += len(chunk)

        frame_array = np.frombuffer(frame_data, dtype=np.uint8)
        frame = cv2.imdecode(frame_array, cv2.IMREAD_COLOR)
        if frame is None:
            logging.error(f"Failed to decode frame for cam {cam_id}")
            return None, None
        return cam_id, frame
    except Exception as e:
        logging.error(f"Error receiving frame: {e}")
        return None, None

def apply_edge_detection(frame):
    """Applies Canny edge detection to the frame."""
    if frame is None:
        return None, None
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 100, 200)
    return frame, edges

def generate_mjpeg_stream(data_type):
    """Generates MJPEG stream for frame or edges."""
    while True:
        with frame_lock:
            frame = latest_frame if data_type == 'frame' else latest_edges
        if frame is not None:
            ret, jpeg = cv2.imencode('.jpg', frame)
            if ret:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')
        time.sleep(0.1)

@app.route('/')
def index():
    """HTML page to display frame and edge map."""
    return '''
    <html>
        <body>
            <h1>Single Camera Stream</h1>
            <h2>Camera Feed</h2>
            <img src="/video_feed/frame" width="320">
            <h2>Edge Map</h2>
            <img src="/video_feed/edges" width="320">
        </body>
    </html>
    '''

@app.route('/video_feed/<data_type>')
def video_feed(data_type):
    """Serves MJPEG stream for frame or edges."""
    return Response(generate_mjpeg_stream(data_type),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

def run_flask():
    """Runs Flask web server in a separate thread."""
    app.run(host='0.0.0.0', port=CONFIG['WEB_PORT'], threaded=True)

def main():
    """Main loop to receive stream, apply edge detection, and update web frames."""
    flask_thread = Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    logging.info(f"Flask web server started at http://0.0.0.0:{CONFIG['WEB_PORT']}")

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((CONFIG['HOST'], CONFIG['PORT_STREAM']))
    server.listen(1)
    server.settimeout(10.0)
    logging.info(f"Listening for stream on port {CONFIG['PORT_STREAM']}...")

    try:
        client, addr = server.accept()
        logging.info(f"Connected to Pi at {addr}")

        last_frame_time = time.time()
        while True:
            cam_id, frame = receive_frame(client)
            if frame is None or cam_id is None:
                logging.warning("Skipping invalid frame")
                continue
            if cam_id != CONFIG['EXPECTED_CAMERA']:
                logging.warning(f"Unexpected cam_id {cam_id}, expected {CONFIG['EXPECTED_CAMERA']}")
                continue

            # Apply edge detection
            output_frame, edges = apply_edge_detection(frame)

            # Update latest frames
            with frame_lock:
                latest_frame = output_frame
                latest_edges = edges
            logging.debug(f"Updated frame for cam {cam_id}")

            if time.time() - last_frame_time > CONFIG['FRAME_TIMEOUT']:
                logging.warning("Frame timeout, possible lag")
            last_frame_time = time.time()

    except Exception as e:
        logging.error(f"Streaming error: {e}")
    finally:
        client.close()
        server.close()
        logging.info("Streaming stopped, resources released")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.info("Streaming server terminated by user")
