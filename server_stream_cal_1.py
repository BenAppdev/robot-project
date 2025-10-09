import socket
import cv2
import numpy as np
import logging
import struct
import time
from flask import Flask, Response
from threading import Thread, Lock
import io
import pickle

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Configuration variables
CONFIG = {
    'HOST': '',               # Bind to all interfaces for TCP
    'PORT_STREAM': 5001,      # Port for video stream
    'BUFFER_SIZE': 4096,      # Socket buffer size
    'FRAME_TIMEOUT': 1.0,     # Seconds before dropping frame
    'WEB_PORT': 8080,         # Port for Flask web server
    'EXPECTED_CAMERA': 0,      # Single camera index
    'SQUARE_DIMS': (0.6096, 0.4064)  # Framing square size in meters (24x16 inches)
}

# Initialize Flask app
app = Flask(__name__)

# Store latest frame and edges in memory with thread-safe lock
latest_frame = None
latest_edges = None
frame_lock = Lock()

# Load camera intrinsics (assume pre-calibrated)
try:
    with open('camera_calibration.pkl', 'rb') as f:
        calib_data = pickle.load(f)
        CAMERA_MATRIX = calib_data['mtx']
        DIST_COEFFS = calib_data['dist']
except FileNotFoundError:
    logging.warning("Calibration file not found, using default intrinsics")
    CAMERA_MATRIX = np.array([[500, 0, 160], [0, 500, 120], [0, 0, 1]], dtype=np.float32)  # Rough estimate for 320x240
    DIST_COEFFS = np.zeros((5,), dtype=np.float32)

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

def detect_framing_square(frame):
    """Detects blue framing square and estimates distance."""
    if frame is None:
        return None, None

    # Convert to HSV for blue color segmentation
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    lower_blue = np.array([100, 50, 50])  # Adjust for your square’s blue
    upper_blue = np.array([140, 255, 255])
    mask = cv2.inRange(hsv, lower_blue, upper_blue)
    mask = cv2.erode(mask, None, iterations=2)
    mask = cv2.dilate(mask, None, iterations=2)

    # Find contours
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    output_frame = frame.copy()
    distance = None

    # Filter for large rectangular contour
    min_area = 0.1 * frame.shape[0] * frame.shape[1]  # 10% of frame
    for contour in contours:
        if cv2.contourArea(contour) > min_area:
            # Approximate to polygon
            peri = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.04 * peri, True)
            if len(approx) == 4:  # Quadrilateral
                # Get bounding box
                x, y, w, h = cv2.boundingRect(approx)
                # Define object points (24x16 inches in meters)
                obj_points = np.array([
                    [0, 0, 0],  # Top-left
                    [CONFIG['SQUARE_DIMS'][0], 0, 0],  # Top-right
                    [CONFIG['SQUARE_DIMS'][0], CONFIG['SQUARE_DIMS'][1], 0],  # Bottom-right
                    [0, CONFIG['SQUARE_DIMS'][1], 0]  # Bottom-left
                ], dtype=np.float32)
                # Image points from contour
                img_points = approx.reshape(4, 2).astype(np.float32)
                # Solve PnP to estimate pose
                ret, rvec, tvec = cv2.solvePnP(obj_points, img_points, CAMERA_MATRIX, DIST_COEFFS)
                if ret:
                    # Distance is Z-component of translation vector (in meters)
                    distance = tvec[2][0]
                    # Draw bounding box and distance label
                    cv2.drawContours(output_frame, [approx], -1, (0, 255, 0), 2)
                    cv2.putText(output_frame, f"Distance: {distance:.2f}m", (x, y-10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                break  # Process only the largest valid contour
    # Edge detection for visualization
    edges = cv2.Canny(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), 100, 200)
    return output_frame, edges, distance

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
    """HTML page to display frame with bounding box and edge map."""
    return '''
    <html>
        <body>
            <h1>Framing Square Distance Estimation</h1>
            <h2>Camera with Distance</h2>
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
    """Main loop to receive stream, detect square, and update web frames."""
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

            # Detect framing square and estimate distance
            output_frame, edges, distance = detect_framing_square(frame)
            if distance is not None:
                logging.info(f"Detected square at {distance:.2f}m")

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
