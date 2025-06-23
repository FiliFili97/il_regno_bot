import os
from dotenv import load_dotenv

# Carica automaticamente variabili da .env (se lo usi)
load_dotenv()

# Telegram
TOKEN = os.getenv("TOKEN")
GROUP_CHAT_ID = None

# Gemini (Gemma 3)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
