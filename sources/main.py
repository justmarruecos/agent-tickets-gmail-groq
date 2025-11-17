from pprint import pprint

from .classifier import classify_email
from .gmail_reader import fetch_emails
from .sheets_writer import write_ticket_to_sheet


def main():
    # On passe à 549 pour traiter tous les mails
    NB_EMAILS = None # 549

    print("=== Récupération des emails dans la boîte de tickets ===")
    emails = fetch_emails(limit=NB_EMAILS)

    print(f"{len(emails)} emails récupérés.\n")

    for idx, mail in enumerate(emails, start=1):
        print("=" * 70)
        print(f"Mail #{idx} (ID IMAP: {mail['id']})")
        print(f"Sujet : {mail['subject']}")
        print("\n--- Début du contenu ---")
        body_preview = (mail["body"][:400] + "...") if len(mail["body"]) > 400 else mail["body"]
        print(body_preview)
        print("--- Fin de l'aperçu ---\n")

        # On limite fortement la taille du texte envoyé au LLM
        body_for_llm = mail["body"]
        MAX_CHARS = 800  # suffisant pour comprendre le problème
        if len(body_for_llm) > MAX_CHARS:
            body_for_llm = body_for_llm[:MAX_CHARS]

        # 1) Classification via LLM (Groq)
        result = classify_email(mail["subject"], body_for_llm)

        print(">>> Résultat de classification :")
        pprint(result)
        print()

        # 2) Écriture dans Google Sheets
        print(">>> Écriture du ticket dans Google Sheets...")
        write_ticket_to_sheet(mail, result)
        print()


if __name__ == "__main__":
    main()
