import os
from google import genai
from dotenv import load_dotenv

load_dotenv()

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
response = client.models.generate_content(
    model='gemini-3.5-flash-lite',
    contents='Respond with a single word: Hello.'
)
print("LLM Test passed. Response:", response.text)
