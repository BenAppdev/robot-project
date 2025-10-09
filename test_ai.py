import requests
import json

# --- Configuration ---
# The URL for your local Ollama API endpoint.
OLLAMA_API_URL = "http://localhost:11434/api/generate"

# The name of a small, text-only model you have downloaded.
# 'phi3:mini' is a good choice if you have it.
MODEL_NAME = "phi3:mini" 

# The simple question we will ask the AI.
TEST_PROMPT = "In one short sentence, why is the sky blue?"

def test_ai_connection():
    """
    Sends a simple text prompt to the Ollama AI and prints the response.
    """
    print(f"--- Testing AI Model: {MODEL_NAME} ---")
    
    # The payload is the data we send to the AI model.
    payload = {
        "model": MODEL_NAME,
        "prompt": TEST_PROMPT,
        "stream": False  # We want the full response at once, not streamed.
    }
    
    try:
        print("Sending prompt to the AI...")
        # We'll set a reasonable timeout, e.g., 30 seconds.
        response = requests.post(OLLAMA_API_URL, json=payload, timeout=300)
        
        # Check if the request was successful (HTTP status code 200)
        response.raise_for_status()
        
        # Parse the JSON response from the AI
        response_data = response.json()
        ai_answer = response_data.get("response", "No response content found.")
        
        print("\n========================================")
        print("✅ SUCCESS: Connected to the AI.")
        print(f"   Question: {TEST_PROMPT}")
        print(f"   AI Answer: {ai_answer.strip()}")
        print("========================================")

    except requests.exceptions.ConnectionError:
        print("\n========================================")
        print("❌ ERROR: Connection Failed.")
        print("   Could not connect to the Ollama service at the URL below:")
        print(f"   {OLLAMA_API_URL}")
        print("   Is your Ollama Docker container running?")
        print("========================================")
        
    except requests.exceptions.Timeout:
        print("\n========================================")
        print("❌ ERROR: Request Timed Out.")
        print("   The connection was established, but the AI model took too long to respond.")
        print("   The model might be loading or the server might be under heavy load.")
        print("========================================")

    except requests.exceptions.RequestException as e:
        print("\n========================================")
        print(f"❌ ERROR: An unexpected error occurred: {e}")
        print("   Please check the Ollama logs for more details.")
        print("========================================")

if __name__ == "__main__":
    test_ai_connection()

