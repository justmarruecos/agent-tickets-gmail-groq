import os
from dotenv import load_dotenv

# Charger les variables définies dans le fichier .env
# Le fichier .env doit être à la racine du projet : C:\25-26\agents\.env
load_dotenv()

# --- Clé Groq ---

# Clé API pour accéder au LLM via Groq
GROQ_API_KEY = os.getenv("GROQ_API_KEY")


def check_config():
    """
    Vérifie que les variables essentielles sont bien définies.

    Pour l'instant, on vérifie uniquement la présence de la clé Groq.
    Gmail est géré via OAuth (credentials.json + token.json),
    donc il n'y a plus de mot de passe dans les variables d'environnement.
    """

    missing = []

    if not GROQ_API_KEY:
        missing.append("GROQ_API_KEY")

    if missing:
        raise RuntimeError(
            "Les variables suivantes manquent dans ton fichier .env : "
            + ", ".join(missing)
        )
