import socket
import cv2
import numpy as np
##T1 server with some extra
#new line addefd
SERVER_IP = '192.168.0.203'  # Server’s IP
PORT = 12345

def run_client():
    cap = cv2.VideoCapture(0)  # Confirmed working
    if not cap.isOpened():
        print("Error: Cannot open camera")
        return
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(5)  # 5-second timeout
            s.connect((SERVER_IP, PORT))
            ret, frame = cap.read()
            if ret:
                _, img_bytes = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                if img_bytes is not None:
                    s.sendall(len(img_bytes).to_bytes(4, 'big') + img_bytes.tobytes())
                    print("Image sent to server")
                else:
                    print("Error: Failed to encode image")
            else:
                print("Error: Failed to capture image")
            data = s.recv(1024)
            if data:
                print(f"Received from server: {data.decode()}")
    except (socket.timeout, ConnectionError) as e:
        print(f"Connection failed: {e}")
    finally:
        cap.release()

if __name__ == "__main__":
    run_client()
