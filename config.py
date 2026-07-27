import os

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "BOT_TOKEN_SHU_YERGA")
ADMIN_ID = int(os.getenv("ADMIN_ID", "1819574194"))

# O'z karta raqamingiz va ismingizni shu yerga yozing:
CARD_NUMBER = os.getenv("CARD_NUMBER", "9860100127991279") 
CARD_HOLDER = os.getenv("CARD_HOLDER", "MUHAMMADJON NAZIRJONOV")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "OPENAI_KEY_SHU_YERGA")
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
AI_MODEL = "gpt-3.5-turbo"
