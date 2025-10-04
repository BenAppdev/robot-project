import socket

SERVER_IP = '192.168.0.203'  # Replace with server's IP (e.g., '192.168.0.100')
PORT = 12345

def run_client():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.connect((SERVER_IP, PORT))
            data = s.recv(1024)
            if data:
                print(f"Received from server: {data.decode()}")
            s.sendall(b'Hello from Pi! Communication test successful.')
        except ConnectionError as e:
            print(f"Connection failed: {e}")

if __name__ == "__main__":
    run_client()