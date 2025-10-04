import socket
import cv2
import numpy as np

SERVER_IP = '192.168.0.203'  # Replace with server’s IP (e.g., '192.168.0.100')
PORT = 12345

def run_client():
    cap = cv2.VideoCapture(0)  # Try 1 if 0 fails
    if not cap.isOpened():
        print("Error: Cannot open camera")
        return
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((SERVER_IP, PORT))
            ret, frame = cap.read()
            if ret:
                _, img_bytes = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                s.sendall(len(img_bytes).to_bytes(4, 'big') + img_bytes.tobytes())
                print("Image sent to server")
            else:
                print("Error: Failed to capture image")
            data = s.recv(1024)
            if data:
                print(f"Received from server: {data.decode()}")
    except ConnectionError as e:
        print(f"Connection failed: {e}")
    cap.release()

if __name__ == "__main__":
    run_client()
