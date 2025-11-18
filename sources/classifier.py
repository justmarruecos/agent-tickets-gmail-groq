from typing import Dict
from groq import Groq

from .config import GROQ_API_KEY, check_config
import unicodedata


CATEGORIES = [
    "Problème technique informatique",
    "Demande administrative",
    "Problème d’accès / authentification",  # forme canonique avec l’apostrophe typographique
    "Demande de support utilisateur",
    "Bug ou dysfonctionnement d’un service",
]

URGENCES = [
    "Critique",
    "Élevée",
    "Modérée",
    "Faible",
    "Anodine",
]


# Fonctions utilitaires

def normalize_label(text: str) -> str:
    """
    Normalise une chaîne pour la comparer de manière tolérante :
    - passe en minuscules
    - remplace les apostrophes typographiques par des apostrophes simples
    - supprime les accents
    - normalise les espaces
    """
    if not isinstance(text, str):
        return ""

    # Retirer espaces en trop au début/fin
    text = text.strip()

    # Unifier les différents types d’apostrophes
    text = text.replace("’", "'")

    # Normalisation Unicode (NFKD), puis suppression des accents
    text_norm = unicodedata.normalize("NFKD", text)
    text_no_accents = "".join(
        c for c in text_norm if unicodedata.category(c) != "Mn"
    )

    # Minuscules
    text_no_accents = text_no_accents.lower()

    # Normaliser les espaces (un seul espace entre les mots)
    text_no_accents = " ".join(text_no_accents.split())

    return text_no_accents


# On prépare des dictionnaires de correspondance "forme normalisée" -> "forme canonique"
NORMALIZED_CATEGORIES = {normalize_label(c): c for c in CATEGORIES}
NORMALIZED_URGENCES = {normalize_label(u): u for u in URGENCES}


# Initialisation du client Groq

def get_groq_client() -> Groq:
    """
    Crée et retourne un client Groq configuré avec la clé API.
    """
    check_config()
    return Groq(api_key=GROQ_API_KEY)


# Construction du prompt

def build_prompt(subject: str, body: str) -> str:
    """
    Construit un prompt relativement court pour économiser les tokens.
    On demande une réponse JSON, sans imposer le JSON mode côté API.
    """
    categories_str = ", ".join(CATEGORIES)
    urgences_str = ", ".join(URGENCES)

    return f"""
You are an assistant that classifies IT support emails.

Given the email subject and body, you must return a JSON object with:
- "categorie": one of [{categories_str}] (in French, exactly as written or with minor variations)
- "urgence": one of [{urgences_str}] (in French, exactly as written or with minor variations)
- "resume": one short sentence in French summarizing the issue.

Subject: "{subject}"
Body: "{body}"

Respond ONLY with the JSON object, no extra text.
Example:
{{
  "categorie": "Demande administrative",
  "urgence": "Modérée",
  "resume": "L'utilisateur demande la mise à jour de ses informations administratives."
}}
"""

# Fonction principale de classification

def classify_email(
    subject: str,
    body: str,
    model: str = "llama-3.1-8b-instant",
) -> Dict[str, str]:
    """
    Appelle le modèle Groq et renvoie un dictionnaire Python avec :
    - categorie
    - urgence
    - resume
    """
    client = get_groq_client()
    prompt = build_prompt(subject, body)

    chat_completion = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You classify IT support emails. "
                    "Always answer with a single valid JSON object."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=0,
        max_tokens=128,   # réponse courte
    )

    content = chat_completion.choices[0].message.content

    if not content or not content.strip():
        raise ValueError(
            "Le modèle a renvoyé une réponse vide. "
            "Vérifie la clé API ou réessaie plus tard."
        )


    # Parsing JSON renvoyé par le modèle

    import json

    try:
        result = json.loads(content)
    except json.JSONDecodeError:
        # Fallback : essayer d'extraire la première partie entre { et }
        content_stripped = content.strip()
        first_brace = content_stripped.find("{")
        last_brace = content_stripped.rfind("}")
        if first_brace != -1 and last_brace != -1:
            json_part = content_stripped[first_brace : last_brace + 1]
            result = json.loads(json_part)
        else:
            raise ValueError(
                "Le modèle n'a pas renvoyé un JSON valide.\n"
                f"Contenu brut reçu :\n{content}"
            )

    raw_categorie = result.get("categorie", "")
    raw_urgence = result.get("urgence", "")
    resume = result.get("resume")

    # Normalisation pour matcher même si le modèle change l'apostrophe ou les accents
    norm_cat = normalize_label(raw_categorie)
    norm_urg = normalize_label(raw_urgence)

    if norm_cat in NORMALIZED_CATEGORIES:
        categorie = NORMALIZED_CATEGORIES[norm_cat]
    else:
        raise ValueError(
            f"Catégorie retournée invalide : {raw_categorie} "
            f"(forme normalisée = '{norm_cat}')"
        )

    if norm_urg in NORMALIZED_URGENCES:
        urgence = NORMALIZED_URGENCES[norm_urg]
    else:
        raise ValueError(
            f"Urgence retournée invalide : {raw_urgence} "
            f"(forme normalisée = '{norm_urg}')"
        )

    if not isinstance(resume, str):
        raise ValueError("Le champ 'resume' doit être une chaîne de caractères.")

    return {
        "categorie": categorie,
        "urgence": urgence,
        "resume": resume,
    }
