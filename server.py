import socket
import cv2
import numpy as np

HOST = '0.0.0.0'
PORT = 12345

def run_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        print(f"Server listening on port {PORT}...")
        conn, addr = s.accept()
        with conn:
            print(f"Connected by {addr}")
            len_bytes = conn.recv(4)
            if len_bytes:
                img_len = int.from_bytes(len_bytes, 'big')
                img_bytes = b''
                while len(img_bytes) < img_len:
                    img_bytes += conn.recv(img_len - len(img_bytes))
                nparr = np.frombuffer(img_bytes, np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                if img is not None:
                    cv2.imwrite('received_image.jpg', img)
                    print("Image saved as received_image.jpg")
                    conn.sendall(b'Image received successfully')
                else:
                    print("Error: Failed to decode image")
                    conn.sendall(b'Error: Invalid image')
            else:
                print("Error: No image data received")
                conn.sendall(b'Error: No data')

if __name__ == "__main__":
    run_server()
