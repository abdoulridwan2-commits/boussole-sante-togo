import os
import threading
import requests
from flask import Flask, request
from dotenv import load_dotenv
from google.genai import types
from app import client, MODELES, config_pour

load_dotenv()
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")

app = Flask(__name__)
historiques = {}
deja_traites = set()


def repondre_ia(numero, question):
    historique = historiques.setdefault(numero, [])
    message = types.Content(role="user", parts=[types.Part(text=question)])
    for modele in MODELES:
        try:
            r = client.models.generate_content(
                model=modele,
                contents=historique + [message],
                config=config_pour(modele),
            )
            texte = (r.text or "").strip()
            if texte:
                historique.append(message)
                historique.append(types.Content(role="model", parts=[types.Part(text=texte)]))
                del historique[:-12]
                print(f"[{modele}] ok")
                return texte
        except Exception as erreur:
            print(f"[{modele}] échec : {str(erreur)[:200]}")
    return "Désolé, le service est très sollicité en ce moment. Réessaie dans un instant."


def envoyer(numero, texte):
    r = requests.post(
        f"https://graph.facebook.com/v23.0/{PHONE_NUMBER_ID}/messages",
        headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}"},
        json={
            "messaging_product": "whatsapp",
            "to": numero,
            "type": "text",
            "text": {"body": texte},
        },
        timeout=20,
    )
    print("Envoi WhatsApp :", r.status_code, r.text[:200])


def traiter(numero, question):
    envoyer(numero, repondre_ia(numero, question))


@app.get("/webhook")
def verifier():
    if (
        request.args.get("hub.mode") == "subscribe"
        and request.args.get("hub.verify_token") == VERIFY_TOKEN
    ):
        return request.args.get("hub.challenge", ""), 200
    return "Interdit", 403


@app.post("/webhook")
def recevoir():
    donnees = request.get_json(silent=True) or {}
    for entree in donnees.get("entry", []):
        for changement in entree.get("changes", []):
            for m in changement.get("value", {}).get("messages", []):
                if m.get("id") in deja_traites:
                    continue
                deja_traites.add(m.get("id"))
                numero = m.get("from")
                if m.get("type") == "text":
                    question = m["text"]["body"]
                    threading.Thread(target=traiter, args=(numero, question)).start()
                else:
                    threading.Thread(
                        target=envoyer,
                        args=(numero, "Je comprends seulement les messages écrits pour le moment."),
                    ).start()
    return "ok", 200


if __name__ == "__main__":
    app.run(port=5000)