import os
from dotenv import load_dotenv

# Load variables from .env file in backend folder
load_dotenv()

# Read the Groq API key
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Check if the key exists
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY is missing. Add it to your .env file.")