import os
import time
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY"),
    http_options=types.HttpOptions(timeout=20000),
)

MODELES = ["gemini-3.1-flash-lite", "gemini-3.5-flash-lite", "gemini-3.8-flash"]

SYSTEM_PROMPT = """Tu es « Assistant Santé », un assistant d'orientation en santé
qui répond sur WhatsApp à des personnes au Togo.

TON RÔLE
- Aider la personne à comprendre ses symptômes et à savoir quoi faire ensuite
  (soins à la maison, consulter un centre de santé, aller aux urgences).
- Tu orientes. Tu ne poses JAMAIS de diagnostic certain : tu dis « cela peut être
  lié à... » et tu recommandes un test ou une consultation.

RÈGLES DE SÉCURITÉ
1. URGENCES : difficulté à respirer, convulsions, perte de connaissance,
   saignement abondant, douleur forte à la poitrine, signes d'AVC, bébé qui
   ne réagit plus, forte fièvre chez un nourrisson, grossesse avec saignement
   ou douleurs fortes. Dans ces cas, réponds en premier, en 2 ou 3 phrases :
   c'est une urgence, aller IMMÉDIATEMENT à l'hôpital le plus proche ou
   appeler les secours. Ne pose pas de questions avant.
2. Ne donne JAMAIS de doses de médicaments ni d'ordonnance. Renvoie vers un
   pharmacien, un médecin ou la notice.
3. Si les informations manquent, pose 2 ou 3 questions courtes (âge, durée,
   autres signes), pas plus.
4. Si la situation te semble sérieuse ou si les symptômes durent, recommande
   de consulter un professionnel de santé.
5. Si la question n'est pas liée à la santé, dis poliment que tu ne peux aider
   que pour la santé.

STYLE
- Français simple, phrases courtes, ton chaleureux et respectueux.
- Réponses courtes (6 phrases maximum), adaptées à WhatsApp.
- Pas de tableaux, pas de Markdown, pas de titres.
- Termine toujours par une action claire : quoi faire maintenant.
- Rappelle que tu ne remplaces pas un médecin quand c'est utile.
"""


def config_pour(modele):
    if "lite" in modele:
        return types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            max_output_tokens=800,
        )
    return types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        max_output_tokens=800,
        thinking_config=types.ThinkingConfig(thinking_level="LOW"),
    )


historique = []

print("Assistant Santé (tape 'q' pour quitter)\n")

while True:
    question = input("Toi : ").strip()
    if question.lower() in ("q", "quit", "exit"):
        break
    if not question:
        continue

    message = types.Content(role="user", parts=[types.Part(text=question)])
    debut = time.time()
    termine = False

    for modele in MODELES:
        texte_complet = ""
        premier_mot = None
        try:
            for morceau in client.models.generate_content_stream(
                model=modele,
                contents=historique + [message],
                config=config_pour(modele),
            ):
                if morceau.text:
                    if premier_mot is None:
                        premier_mot = time.time() - debut
                        print("\nAssistant : ", end="", flush=True)
                    print(morceau.text, end="", flush=True)
                    texte_complet += morceau.text

            if texte_complet:
                historique.append(message)
                historique.append(
                    types.Content(role="model", parts=[types.Part(text=texte_complet)])
                )
                total = time.time() - debut
                print(f"\n\n({modele} · premier mot : {premier_mot:.1f} s · total : {total:.1f} s)\n")
                termine = True
                break
            else:
                print(f"[{modele}] réponse vide après {time.time() - debut:.1f} s")
        except Exception as erreur:
            print(f"\n[{modele}] échec après {time.time() - debut:.1f} s : {str(erreur)[:200]}")
            if texte_complet:
                termine = True
                break
            continue

    if not termine:
        print("\nAssistant : Désolé, le service est très sollicité en ce moment. Réessaie dans un instant.\n")