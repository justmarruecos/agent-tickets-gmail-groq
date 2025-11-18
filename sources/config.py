import os
from dotenv import load_dotenv

# Charger les variables définies dans le fichier .env
load_dotenv()

# Clé API pour accéder au LLM via Groq
GROQ_API_KEY = os.getenv("GROQ_API_KEY")


def check_config():

    missing = []

    if not GROQ_API_KEY:
        missing.append("GROQ_API_KEY")

    if missing:
        raise RuntimeError(
            + ", ".join(missing)
        )
