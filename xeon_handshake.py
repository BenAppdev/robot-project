import socket
import json
import logging

# Configure logging for debugging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Configuration variables (must match Pi's config)
CONFIG = {
    'HOST': '',               # Empty string binds to all interfaces
    'PORT_HANDSHAKE': 5000,   # Port to listen for handshake
    'BUFFER_SIZE': 4096,      # Socket buffer size in bytes
    'EXPECTED_CAMERAS': [0, 1] # Expected camera indices from Pi
}

def validate_payload(payload):
    """
    Validates the received config payload.
    Returns True if valid, False otherwise.
    """
    required_keys = {'resolution', 'fps', 'cameras', 'timestamp'}
    if not all(key in payload for key in required_keys):
        logging.error("Payload missing required keys")
        return False
    if payload['cameras'] != CONFIG['EXPECTED_CAMERAS']:
        logging.error(f"Expected cameras {CONFIG['EXPECTED_CAMERAS']}, got {payload['cameras']}")
        return False
    if not isinstance(payload['resolution'], (list, tuple)) or len(payload['resolution']) != 2:
        logging.error("Invalid resolution format")
        return False
    return True

def handle_handshake():
    """Listens for Pi's handshake and sends ACK."""
    try:
        # Create TCP server socket
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((CONFIG['HOST'], CONFIG['PORT_HANDSHAKE']))
        server.listen(1)
        server.settimeout(10.0)  # Timeout for incoming connections
        logging.info(f"Listening for handshake on port {CONFIG['PORT_HANDSHAKE']}...")

        # Accept connection from Pi
        client, addr = server.accept()
        logging.info(f"Connected to Pi at {addr}")

        # Receive payload length (4 bytes)
        length_bytes = client.recv(4)
        if not length_bytes:
            logging.error("No data received")
            return
        length = int.from_bytes(length_bytes, byteorder='big')

        # Receive JSON payload
        payload_bytes = client.recv(length)
        payload = json.loads(payload_bytes.decode('utf-8'))
        logging.info(f"Received payload: {payload}")

        # Validate payload
        if validate_payload(payload):
            # Send ACK with current timestamp
            ack = {'status': 'ACK', 'timestamp': payload['timestamp']}
            client.sendall(json.dumps(ack).encode('utf-8'))
            logging.info("Sent ACK to Pi")
        else:
            logging.error("Payload validation failed, no ACK sent")

    except socket.timeout:
        logging.error("No connection received within timeout")
    except Exception as e:
        logging.error(f"Handshake error: {e}")
    finally:
        client.close()
        server.close()

def main():
    """Main loop to run handshake server."""
    try:
        handle_handshake()
    except KeyboardInterrupt:
        logging.info("Handshake server terminated by user")

if __name__ == "__main__":
    main()
