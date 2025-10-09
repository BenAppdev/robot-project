import requests
import json

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "phi3:mini"

def query_llama(prompt):
    data = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False
    }
    try:
        response = requests.post(OLLAMA_URL, json=data)
        if response.status_code == 200:
            return response.json()["response"]
        else:
            print(f"Error: {response.status_code} - {response.text}")
            return None
    except requests.ConnectionError:
        print("Error: Cannot connect to Ollama server. Ensure 'docker start ollama' is running.")
        return None

if __name__ == "__main__":
    prompt = "Describe a robot's next action in a simple task."
    result = query_llama(prompt)
    if result:
        print(f"Llama response: {result}")
