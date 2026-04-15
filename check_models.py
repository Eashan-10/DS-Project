import os
from dotenv import load_dotenv
from google import genai

# Load your secure API key
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

print("🔍 SCANNING GOOGLE SERVERS FOR AVAILABLE MODELS...\n")

# Ask the server for every model it currently supports
for model in client.models.list():
    # We only care about the fast "flash" or "lite" vision models
    if 'flash' in model.name or 'lite' in model.name:
        print(f"✅ Found: {model.name}")