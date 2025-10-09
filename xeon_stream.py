import socket
import cv2
import numpy as np
import logging
import struct
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Configuration variables (match Pi)
CONFIG = {
    'HOST': '',               # Bind to all interfaces
    'PORT_STREAM': 5001,      # Port for video stream
    'BUFFER_SIZE': 4096,      # Socket buffer size
    'FRAME_TIMEOUT': 1.0      # Seconds before dropping frame
}

def receive_frame(client):
    """Receives a frame with header (cam_id, frame_size) and decodes it."""
    try:
        # Receive header (8 bytes: 4 for cam_id, 4 for frame_size)
        header = client.recv(8)
        if len(header) != 8:
            logging.warning("Incomplete header received")
            return None, None

        cam_id, frame_size = struct.unpack('!II', header)
        logging.debug(f"Received header: cam_id={cam_id}, frame_size={frame_size}")

        # Receive frame data
        frame_data = b''
        bytes_received = 0
        while bytes_received < frame_size:
            chunk = client.recv(min(CONFIG['BUFFER_SIZE'], frame_size - bytes_received))
            if not chunk:
                logging.warning("Connection closed during frame receive")
                return None, None
            frame_data += chunk
            bytes_received += len(chunk)

        # Decode JPEG to OpenCV image
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
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 100, 200)  # Thresholds for edge detection
    return edges

def main():
    """Main loop to receive and process stereo stream."""
    # Create TCP server socket
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((CONFIG['HOST'], CONFIG['PORT_STREAM']))
    server.listen(1)
    server.settimeout(10.0)
    logging.info(f"Listening for stream on port {CONFIG['PORT_STREAM']}...")

    try:
        # Accept connection from Pi
        client, addr = server.accept()
        logging.info(f"Connected to Pi at {addr}")

        # Main receiving loop
        last_frame_time = time.time()
        while True:
            cam_id, frame = receive_frame(client)
            if frame is None or cam_id is None:
                logging.warning("Skipping invalid frame")
                continue

            # Apply edge detection
            edges = apply_edge_detection(frame)

            # Display the result
            window_name = f"Edges Cam {cam_id}"
            cv2.imshow(window_name, edges)

            # Check for timeout or user exit
            if time.time() - last_frame_time > CONFIG['FRAME_TIMEOUT']:
                logging.warning("Frame timeout, possible lag")
            last_frame_time = time.time()

            # Exit on 'q' key press
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    except Exception as e:
        logging.error(f"Streaming error: {e}")
    finally:
        # Clean up
        client.close()
        server.close()
        cv2.destroyAllWindows()
        logging.info("Streaming stopped, resources released")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.info("Streaming server terminated by user")
