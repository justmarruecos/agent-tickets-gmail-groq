import os
from typing import Dict, Any, List

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build


# Configuration Google Sheets

# Scope : accès en lecture/écriture au Google Sheets
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# l'ID de .env du Google Sheet où écrire les tickets
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")

if not SPREADSHEET_ID:
    raise RuntimeError(
        "SPREADSHEET_ID est introuvable dans l'environnement.\n"
        "Ajoute SPREADSHEET_ID=... dans ton fichier .env."
    )

# Mapping entre catégorie et nom de l'onglet (sheet) dans le Google Sheet
CATEGORY_TO_SHEET = {
    "Problème technique informatique": "Problème technique informatique",
    "Demande administrative": "Demande administrative",
    "Problème d’accès / authentification": "Problème d’accès / authentification",
    "Demande de support utilisateur": "Demande de support utilisateur",
    "Bug ou dysfonctionnement d’un service": "Bug ou dysfonctionnement d’un service",
}


def _get_sheets_service():
    """
    Initialise le service Google Sheets API avec OAuth 2.0.

    - Utilise 'credentials.json' (le même que pour Gmail)
    - Crée/Utilise 'token_sheets.json' pour mémoriser l'autorisation.
    """
    creds: Credentials | None = None

    # 1. Si on a déjà un token enregistré pour Sheets, on le recharge
    if os.path.exists("token_sheets.json"):
        creds = Credentials.from_authorized_user_file("token_sheets.json", SCOPES)

    # 2. Si pas de creds ou creds invalides, on lance le flux OAuth
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            # Le token a expiré mais on peut le rafraîchir
            creds.refresh(Request())
        else:
            # Pas encore de token Sheets : on lance le flux OAuth
            if not os.path.exists("credentials.json"):
                raise FileNotFoundError(
                    "Le fichier 'credentials.json' est introuvable.\n"
                    "Place-le à la racine du projet (C:\\25-26\\agents\\credentials.json)."
                )

            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)

        # 3. On sauvegarde les credentials pour les prochaines fois
        with open("token_sheets.json", "w") as token:
            token.write(creds.to_json())

    # 4. On construit le service Google Sheets
    service = build("sheets", "v4", credentials=creds)
    return service


def write_ticket_to_sheet(
    email: Dict[str, Any],
    classification: Dict[str, str],
):

    categorie = classification["categorie"]
    urgence = classification["urgence"]
    resume = classification["resume"]

    sheet_name = CATEGORY_TO_SHEET.get(categorie)

    if not sheet_name:
        raise ValueError(
            f"Aucun onglet défini pour la catégorie : {categorie}\n"
            f"Vérifie CATEGORY_TO_SHEET dans sheets_writer.py "
            f"et les noms d'onglets dans ton Google Sheet."
        )

    # Préparer la ligne à écrire
    row: List[Any] = [
        email.get("id", ""),
        email.get("subject", ""),
        categorie,
        urgence,
        resume,
    ]

    service = _get_sheets_service()

    # On ajoute la ligne à la fin de l'onglet correspondant
    range_name = f"'{sheet_name}'!A:E"  # colonnes A à E
    body = {
        "values": [row]
    }

    result = (
        service.spreadsheets()
        .values()
        .append(
            spreadsheetId=SPREADSHEET_ID,
            range=range_name,
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body=body,
        )
        .execute()
    )

    updated = result.get("updates", {}).get("updatedCells", 0)
    print(
        f"Ligne ajoutée à l'onglet '{sheet_name}' "
        f"(cellules mises à jour : {updated})."
    )
