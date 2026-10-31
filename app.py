import os
from flask import Flask, request, jsonify
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
6. DÉTRESSE : si la personne dit être très triste, désespérée ou avoir des
   idées de mort ou de suicide, réponds avec beaucoup de bienveillance, dis que
   tu es là pour l'écouter, et encourage-la à parler tout de suite à un proche
   de confiance ou à un professionnel de santé. Si elle est en danger immédiat,
   dis-lui d'aller aux urgences ou d'appeler les secours et de ne pas rester seule.
   Ne donne jamais de moyen de se faire du mal et ne minimise jamais ce qu'elle ressent.
7. NUMÉROS : ne cite jamais un numéro de téléphone que tu ne connais pas
   avec certitude. Les seuls numéros que tu peux donner sont : pompiers 118 et
   police 117. Pour toute autre structure, dis d'aller au centre de santé ou à
   l'hôpital le plus proche, sans inventer de numéro.

STYLE
- Français simple, phrases courtes, ton chaleureux et respectueux.
- Vouvoie toujours la personne.
- Réponses courtes (6 phrases maximum), adaptées à WhatsApp.
- Pas de tableaux, pas de Markdown, pas de titres.
- Termine toujours par une action claire : quoi faire maintenant.
- Rappelle que tu ne remplaces pas un médecin quand c'est utile.
"""

PAGE = r"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Assistant Santé</title>
<style>
*{box-sizing:border-box}
body{margin:0;font-family:Segoe UI,Roboto,Arial,sans-serif;background:#d9d4cc;display:flex;justify-content:center}
#app{width:100%;max-width:480px;height:100vh;display:flex;flex-direction:column;background:#efe9df}
header{background:#0B6B5E;color:#fff;padding:12px 16px;display:flex;align-items:center;gap:10px;font-weight:700}
.logo{width:40px;height:40px;border-radius:50%;background:#fff;color:#0B6B5E;display:flex;align-items:center;justify-content:center;font-size:24px}
header small{display:block;color:#cfe9e4;font-size:12px;font-weight:400}
#msgs{flex:1;overflow-y:auto;padding:12px;display:flex;flex-direction:column;gap:8px}
.m{max-width:80%;padding:8px 10px;border-radius:10px;font-size:15px;line-height:1.4;white-space:pre-wrap;color:#1b2b29}
.bot{background:#fff;align-self:flex-start}
.moi{background:#d8f3c9;align-self:flex-end}
form{display:flex;gap:8px;padding:10px;background:#f6f3ee}
input{flex:1;height:44px;border:0;border-radius:22px;padding:0 16px;font-size:15px}
button{width:44px;height:44px;border:0;border-radius:50%;background:#0B6B5E;color:#fff;font-size:18px;cursor:pointer}
</style></head>
<body><div id="app">
<header><div class="logo">+</div><div>Assistant Santé<small>assistant IA · ne remplace pas un médecin</small></div></header>
<div id="msgs"></div>
<form id="f"><input id="t" placeholder="Message" autocomplete="off"><button type="submit" aria-label="Envoyer">&#10148;</button></form>
</div>
<script>
const msgs = document.getElementById("msgs");
const f = document.getElementById("f");
const t = document.getElementById("t");

function ajouter(texte, cls) {
  const d = document.createElement("div");
  d.className = "m " + cls;
  d.textContent = texte;
  msgs.appendChild(d);
  msgs.scrollTop = msgs.scrollHeight;
  return d;
}

ajouter("Bonjour ! Je peux vous aider à comprendre vos symptômes et à savoir quoi faire. Je ne remplace pas un médecin. En cas d'urgence, allez tout de suite au centre de santé le plus proche. Décrivez-moi ce qui ne va pas.", "bot");

f.addEventListener("submit", async (e) => {
  e.preventDefault();
  const q = t.value.trim();
  if (!q) return;
  t.value = "";
  ajouter(q, "moi");
  const attente = ajouter("...", "bot");
  try {
    const r = await fetch("/chat", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({message: q})
    });
    const d = await r.json();
    attente.textContent = d.reponse;
  } catch (err) {
    attente.textContent = "Erreur de connexion. Réessayez.";
  }
  msgs.scrollTop = msgs.scrollHeight;
});
</script></body></html>"""


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
app = Flask(__name__)


@app.get("/")
def accueil():
    return PAGE


@app.post("/chat")
def chat():
    question = (request.get_json(silent=True) or {}).get("message", "").strip()
    if not question:
        return jsonify({"reponse": "Écrivez votre message d'abord."}), 400

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
                historique.append(
                    types.Content(role="model", parts=[types.Part(text=texte)])
                )
                print(f"[{modele}] ok")
                return jsonify({"reponse": texte})
        except Exception as erreur:
            print(f"[{modele}] échec : {str(erreur)[:200]}")

    return jsonify({"reponse": "Désolé, le service est très sollicité en ce moment. Réessayez dans un instant."}), 503


if __name__ == "__main__":
    app.run(port=5000)