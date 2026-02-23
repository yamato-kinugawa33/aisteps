import os
from dotenv import load_dotenv

load_dotenv()
key = os.getenv("GEMINI_API_KEY")
print("Key loaded:", bool(key))
print("Key prefix:", key[:10] if key else "NONE")
