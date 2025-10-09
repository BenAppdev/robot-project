import socket
import base64
import requests # You may need to run: pip install requests
import json
import sys

# --- Configuration ---
HOST = '0.0.0.0'  # Listen on all available network interfaces
PORT = 12345
# This is the local URL for the Ollama service. It works since your terminal test passed.
OLLAMA_API_URL = "http://localhost:11434/api/generate"

def get_image_description(image_data):
    """Sends image data to the local Ollama model and gets a description."""
    # Don't print for warm-up, only for real requests.
    if len(image_data) > 100: # The dummy image is very small
      print("Asking AI for a description...")

    try:
        # Encode the binary image data into a base64 string, required by the API
        base64_image = base64.b64encode(image_data).decode('utf-8')

        # Prepare the data payload for the Ollama API
        payload = {
            # *** EDITED: Switched to 'moondream', a smaller, RAM-friendly vision model. ***
            "model": "moondream", # The vision model
            "prompt": "Describe what you see in this image in one short sentence.",
            "stream": False,
            "images": [base64_image]
        }

        # Send the request to the Ollama server
        # *** EDITED: Increased timeout from 60s to 300s to give the AI more time. ***
        response = requests.post(OLLAMA_API_URL, json=payload, timeout=300)
        response.raise_for_status() # This will raise an error for bad responses (like 404 or 500)

        # Parse the JSON response and return the description
        response_data = response.json()
        return response_data.get('response', 'AI could not provide a description.').strip()

    except requests.exceptions.RequestException as e:
        print(f"Error communicating with Ollama AI: {e}")
        print("Please ensure the Ollama service/docker is running and you have the 'moondream' model installed (`ollama pull moondream`).")
        return "Could not connect to the AI service."

def warm_up_ai():
    """
    Sends a dummy request to the AI model to force it to load into memory
    before the server starts accepting connections. This makes the first
    real request much faster.
    """
    print("🤖 Warming up the AI model... (this may take a few minutes on first run)")
    # A base64 encoded 1x1 black pixel PNG image.
    dummy_image_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
    dummy_image_data = base64.b64decode(dummy_image_base64)
    
    # Send the dummy data to the description function
    description = get_image_description(dummy_image_data)
    
    if "Could not connect" in description:
        print("🔴 AI WARM-UP FAILED. Could not connect to Ollama.")
        print("   Please ensure the Ollama Docker container is running.")
        sys.exit(1) # Exit if the AI is not available
    else:
        print("✅ AI model is warmed up and ready.")


def handle_client(conn, addr):
    """Handles a single client connection."""
    print(f"Connected by {addr}")
    try:
        # 1. Send the command to the client
        print("Sending 'CAPTURE' command to client...")
        conn.sendall(b'CAPTURE')

        # 2. Receive the image size (4 bytes)
        image_size_bytes = conn.recv(4)
        if not image_size_bytes:
            raise ConnectionError("Client disconnected before sending image size.")
        image_size = int.from_bytes(image_size_bytes, 'big')
        
        print(f"Expecting image of size: {image_size} bytes")

        # 3. Receive the image data
        image_data = b''
        while len(image_data) < image_size:
            packet = conn.recv(4096)
            if not packet:
                raise ConnectionError("Client disconnected during image transfer.")
            image_data += packet
        
        print("Image received successfully.")

        # This lets you see the exact image the AI is analyzing.
        with open('received_image.jpg', 'wb') as f:
            f.write(image_data)
        print("Image saved as received_image.jpg")
        
        # --- AI SECTION ---
        # 4. Get the description from the AI
        description = get_image_description(image_data)
        
        # 5. Print the result
        print("\n========================================")
        print(f"AI Vision: {description}")
        print("========================================\n")
        
        # 6. Send a new confirmation back to the client
        conn.sendall(b'Image received and analyzed by AI')

    except ConnectionError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred with {addr}: {e}")
    finally:
        print(f"Closing connection with {addr}")
        conn.close()

def main():
    """Main loop to listen for incoming connections."""
    warm_up_ai() # Load the model before starting the server

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        # This allows the socket to be reused immediately after the script closes.
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        s.bind((HOST, PORT))
        s.listen()
        print(f"Server listening on port {PORT}...")
        
        while True:
            # Wait for a client to connect
            conn, addr = s.accept()
            handle_client(conn, addr)

if __name__ == "__main__":
    main()