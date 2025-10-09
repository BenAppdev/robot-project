import socket
import cv2
import numpy as np
import logging
import struct
import time
from flask import Flask, Response
from threading import Thread, Lock
import io

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Configuration variables (match Pi)
CONFIG = {
    'HOST': '',               # Bind to all interfaces for TCP
    'PORT_STREAM': 5001,      # Port for video stream
    'BUFFER_SIZE': 4096,      # Socket buffer size
    'FRAME_TIMEOUT': 1.0,     # Seconds before dropping frame
    'WEB_PORT': 8080,         # Port for Flask web server
    'BASELINE': 0.1,          # Distance between cameras in meters (adjust to your setup)
    'FOCAL_LENGTH': 500.0     # Focal length in pixels (rough estimate for 320x240)
}

# Initialize Flask app
app = Flask(__name__)

# Store latest frames and depth map in memory with thread-safe lock
latest_frames = {0: None, 1: None}  # cam_id: original frame
latest_depth = None  # Depth map
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

def compute_depth_map(left_frame, right_frame):
    """Computes depth map from stereo pair using StereoBM."""
    if left_frame is None or right_frame is None:
        return None
    # Convert to grayscale
    left_gray = cv2.cvtColor(left_frame, cv2.COLOR_BGR2GRAY)
    right_gray = cv2.cvtColor(right_frame, cv2.COLOR_BGR2GRAY)
    
    # Create StereoBM object
    stereo = cv2.StereoBM_create(numDisparities=16, blockSize=15)
    # Compute disparity
    disparity = stereo.compute(left_gray, right_gray)
    # Normalize for visualization
    disparity = cv2.normalize(disparity, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_8U)
    return disparity

def detect_objects_and_depth(frame, depth_map):
    """Detects large objects, draws bounding boxes, and estimates depth."""
    if frame is None or depth_map is None:
        return frame
    # Apply Canny edge detection
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 100, 200)
    
    # Find contours
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    output_frame = frame.copy()
    
    # Filter large contours (area > 10% of frame)
    min_area = 0.1 * frame.shape[0] * frame.shape[1]
    for contour in contours:
        if cv2.contourArea(contour) > min_area:
            # Get bounding box
            x, y, w, h = cv2.boundingRect(contour)
            # Estimate average depth in the bounding box
            depth_roi = depth_map[y:y+h, x:x+w]
            valid_depth = depth_roi[depth_roi > 0]  # Ignore zero disparity
            if len(valid_depth) > 0:
                avg_disparity = np.mean(valid_depth)
                if avg_disparity > 0:  # Avoid division by zero
                    depth_meters = (CONFIG['FOCAL_LENGTH'] * CONFIG['BASELINE']) / avg_disparity
                    # Draw bounding box and depth label
                    cv2.rectangle(output_frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                    cv2.putText(output_frame, f"{depth_meters:.2f}m", (x, y-10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
    return output_frame

def generate_mjpeg_stream(data_type):
    """Generates MJPEG stream for original frame (cam0/1) or depth map."""
    while True:
        with frame_lock:
            if data_type == 'depth':
                frame = latest_depth
            else:
                cam_id = int(data_type)
                frame = latest_frames.get(cam_id)
        if frame is not None:
            ret, jpeg = cv2.imencode('.jpg', frame)
            if ret:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')
        time.sleep(0.1)  # Limit refresh rate

@app.route('/')
def index():
    """HTML page to display stereo frames and depth map."""
    return '''
    <html>
        <body>
            <h1>Stereo Camera Depth Mapping</h1>
            <h2>Camera 0 (Left)</h2>
            <img src="/video_feed/0" width="320">
            <h2>Camera 1 (Right)</h2>
            <img src="/video_feed/1" width="320">
            <h2>Depth Map</h2>
            <img src="/video_feed/depth" width="320">
        </body>
    </html>
    '''

@app.route('/video_feed/<data_type>')
def video_feed(data_type):
    """Serves MJPEG stream for a camera or depth map."""
    return Response(generate_mjpeg_stream(data_type),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

def run_flask():
    """Runs Flask web server in a separate thread."""
    app.run(host='0.0.0.0', port=CONFIG['WEB_PORT'], threaded=True)

def main():
    """Main loop to receive stereo stream, compute depth, and update web frames."""
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

            # Update latest frame
            with frame_lock:
                latest_frames[cam_id] = frame
                # Compute depth map if both frames available
                if latest_frames[0] is not None and latest_frames[1] is not None:
                    latest_depth = compute_depth_map(latest_frames[0], latest_frames[1])
                    # Update frames with bounding boxes and depth
                    latest_frames[0] = detect_objects_and_depth(latest_frames[0], latest_depth)
                    latest_frames[1] = detect_objects_and_depth(latest_frames[1], latest_depth)
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
