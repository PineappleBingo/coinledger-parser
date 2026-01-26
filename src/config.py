import os
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()

# Configuration
DEPLOYMENT_TIER = os.getenv("DEPLOYMENT_TIER", "development")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
QUICKNODE_RPC_URL = os.getenv("QUICKNODE_RPC_URL")

# Gemini Configuration
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

def get_gemini_model(model_name="gemini-2.0-flash"):
    """Returns a configured Gemini model instance."""
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY not found in environment variables.")
    return genai.GenerativeModel(model_name)
