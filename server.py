import socket
import time

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
            conn.sendall(b'Hello from server! Communication test successful.')
            data = conn.recv(1024)
            if data:
                print(f"Received from Pi: {data.decode()}")
            else:
                print("No response from Pi.")

if __name__ == "__main__":
    run_server()