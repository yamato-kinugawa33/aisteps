import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

print("=== Testing generate_content ===")
try:
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents="こんにちは"
    )
    print("Success:", response.text)
except Exception as e:
    print("Error type:", type(e).__name__)
    print("Error:", e)
