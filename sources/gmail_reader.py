import os
from typing import List, Dict, Any

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# Scopes = ce que l'app a le droit de faire.
# Ici : lecture seule de Gmail 
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def _get_gmail_service():
    """
    Initialise le service Gmail API avec OAuth 2.0.

    - Utilise 'credentials.json' pour lancer le flux OAuth la première fois.
    - Sauvegarde le token dans 'token.json' pour les exécutions suivantes.
    """

    creds: Credentials | None = None

    # Si on a déjà un token enregistré, on le recharge
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    # Si pas de creds ou creds invalides, on lance le flux OAuth
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            # Le token a expiré mais on peut le rafraîchir
            creds.refresh(Request())
        else:
            # Pas encore de token : on lance le flux OAuth dans le navigateur
            if not os.path.exists("credentials.json"):
                raise FileNotFoundError(
                    "Le fichier 'credentials.json' est introuvable.\n"
                    "Place-le à la racine du projet (C:\\25-26\\agents\\credentials.json)."
                )

            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)

        # On sauvegarde les credentials pour les prochaines fois
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    # On construit le service Gmail
    service = build("gmail", "v1", credentials=creds)
    return service


def _get_plain_text_from_payload(payload: Dict[str, Any]) -> str:
    """
    Essaie d'extraire le texte "brut" du message à partir du payload Gmail.
    Le message peut être simple ou multipart (plusieurs parties MIME).
    """
    import base64

    def decode_base64(data: str) -> str:
        decoded_bytes = base64.urlsafe_b64decode(data.encode("UTF-8"))
        return decoded_bytes.decode("utf-8", errors="ignore")

    body_text = ""

    if "parts" in payload:
        # Multipart : on parcourt les différentes parties
        for part in payload["parts"]:
            mime_type = part.get("mimeType", "")
            body = part.get("body", {})
            data = body.get("data")

            # On privilégie text/plain
            if mime_type == "text/plain" and data:
                return decode_base64(data)

        # Si aucun text/plain, on tente le HTML
        for part in payload["parts"]:
            mime_type = part.get("mimeType", "")
            body = part.get("body", {})
            data = body.get("data")

            if mime_type == "text/html" and data:
                return decode_base64(data)

    else:
        # Message simple
        body = payload.get("body", {})
        data = body.get("data")
        if data:
            return decode_base64(data)

    return body_text


def _get_header(headers: list[dict[str, str]], name: str) -> str:
    """
    Récupère la valeur d'un header (ex: 'Subject', 'From', etc.)
    dans la liste des headers du message Gmail.
    """
    for h in headers:
        if h.get("name", "").lower() == name.lower():
            return h.get("value", "")
    return ""


def fetch_emails(limit: int | None = 5) -> List[Dict[str, str]]:
    """
    Récupère les 'limit' derniers emails de la boîte de réception (INBOX)
    via l'API Gmail + OAuth.

    Si limit est None, on récupère TOUTES les conversations de la boîte INBOX.

    Retourne une liste de dictionnaires :
    - "id": identifiant du message
    - "subject": sujet du mail
    - "body": contenu texte du mail
    """
    service = _get_gmail_service()

    emails: List[Dict[str, str]] = []
    page_token: str | None = None

    # On va lire la boîte par "pages" de 100 messages
    # (maxResults peut aller jusqu'à 500, mais 100 c'est confortable).
    while True:
        request_kwargs: Dict[str, Any] = {
            "userId": "me",
            "labelIds": ["INBOX"],
            "maxResults": 100,
        }
        if page_token:
            request_kwargs["pageToken"] = page_token

        results = (
            service.users()
            .messages()
            .list(**request_kwargs)
            .execute()
        )

        messages = results.get("messages", [])
        if not messages:
            break

        for msg_meta in messages:
            msg_id = msg_meta["id"]

            msg = (
                service.users()
                .messages()
                .get(userId="me", id=msg_id, format="full")
                .execute()
            )

            payload = msg.get("payload", {})
            headers = payload.get("headers", [])

            subject = _get_header(headers, "Subject")
            body = _get_plain_text_from_payload(payload)

            emails.append(
                {
                    "id": msg_id,
                    "subject": subject,
                    "body": body,
                }
            )

            # Si on a atteint la limite demandée, on s'arrête
            if limit is not None and len(emails) >= limit:
                return emails

        # Page suivante ?
        page_token = results.get("nextPageToken")
        if not page_token:
            break

    return emails
