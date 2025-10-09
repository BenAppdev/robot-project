import socket
import json
import time
import logging

# Configure logging to see what's happening
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Configuration variables (tune these as needed)
CONFIG = {
    'HOST': '192.168.0.203',  # Xeon's static IP
    'PORT_HANDSHAKE': 5000,   # Port for handshake
    'RESOLUTION': (320, 240), # Width, height for stereo cams
    'FPS_TARGET': 15,         # Total FPS for both cams (~7.5 per cam)
    'CAMERAS': [0, 1],        # Camera indices (/dev/video0, /dev/video1)
    'COMPRESSION_QUALITY': 40,# JPEG quality (0-100, lower = smaller/faster)
    'BUFFER_SIZE': 4096,      # Socket buffer size in bytes
    'FRAME_TIMEOUT': 1.0      # Seconds before dropping a frame
}

def send_handshake():
    """
    Sends config to Xeon, waits for ACK, and measures round-trip time (RTT).
    Returns True if successful, False otherwise.
    """
    try:
        # Create a TCP socket
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.settimeout(5.0)  # Timeout for connection attempts

        # Connect to Xeon server
        logging.info(f"Connecting to {CONFIG['HOST']}:{CONFIG['PORT_HANDSHAKE']}...")
        client.connect((CONFIG['HOST'], CONFIG['PORT_HANDSHAKE']))

        # Prepare JSON payload with config
        payload = {
            'resolution': CONFIG['RESOLUTION'],
            'fps': CONFIG['FPS_TARGET'],
            'cameras': CONFIG['CAMERAS'],
            'timestamp': time.time()
        }
        payload_bytes = json.dumps(payload).encode('utf-8')

        # Send payload length first (4 bytes, big-endian)
        client.sendall(len(payload_bytes).to_bytes(4, byteorder='big'))
        # Send the actual JSON payload
        client.sendall(payload_bytes)
        logging.info("Sent config payload to Xeon")

        # Wait for ACK from Xeon
        ack_bytes = client.recv(CONFIG['BUFFER_SIZE'])
        ack = json.loads(ack_bytes.decode('utf-8'))
        logging.info(f"Received ACK: {ack}")

        # Check if ACK is valid and measure RTT
        if ack.get('status') == 'ACK':
            rtt = time.time() - payload['timestamp']
            logging.info(f"Handshake successful, RTT: {rtt*1000:.2f}ms")
            return True
        else:
            logging.error("Invalid ACK received")
            return False

    except socket.timeout:
        logging.error("Connection timed out")
        return False
    except ConnectionRefusedError:
        logging.error("Connection refused by Xeon")
        return False
    except Exception as e:
        logging.error(f"Handshake failed: {e}")
        return False
    finally:
        client.close()

def main():
    """Main loop with retry logic for handshake."""
    max_retries = 3
    for attempt in range(max_retries):
        logging.info(f"Attempting handshake (try {attempt+1}/{max_retries})")
        if send_handshake():
            logging.info("Handshake completed successfully")
            return
        time.sleep(2)  # Wait before retrying
    logging.error("Handshake failed after all retries")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.info("Handshake script terminated by user")
