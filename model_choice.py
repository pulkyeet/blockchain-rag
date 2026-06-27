import os
from openai import OpenAI
from config import settings
from google import genai
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    base_url=settings.openrouter_base_url,
    api_key=settings.openrouter_api_key,
)
client2 = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])

resp = client2.models.generate_content(
    model="gemini-3.5-flash",
    contents="tell me all you can about block wars of 2015.",
)
print(resp.text)