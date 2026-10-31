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

SYSTEM_PROMPT = """Tu es « Boussole Santé Togo », un assistant d'orientation en santé
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
<title>Boussole Santé Togo</title>
<style>
*{box-sizing:border-box}
body{margin:0;font-family:Segoe UI,Roboto,Arial,sans-serif;background:#d9d4cc;display:flex;justify-content:center}
#app{width:100%;max-width:480px;height:100vh;display:flex;flex-direction:column;background:#efe9df}
header{background:#0B6B5E;color:#fff;padding:12px 16px;display:flex;align-items:center;gap:10px;font-weight:700}
header svg{flex:none}
header small{display:block;color:#cfe9e4;font-size:12px;font-weight:400}
#msgs{flex:1;overflow-y:auto;padding:12px;display:flex;flex-direction:column;gap:8px}
.m{max-width:80%;padding:8px 10px;border-radius:10px;font-size:15px;line-height:1.4;white-space:pre-wrap;color:#1b2b29}
.bot{background:#fff;align-self:flex-start}
.moi{background:#d8f3c9;align-self:flex-end}
#astuce{display:none;padding:6px 14px;background:#fff8dc;color:#4a3b00;font-size:13px}
#astuce.visible{display:block}
form{display:flex;align-items:flex-end;gap:8px;padding:10px;background:#f6f3ee}
textarea{flex:1;min-height:44px;max-height:120px;border:0;border-radius:22px;padding:11px 16px;font-size:15px;font-family:inherit;line-height:1.3;resize:none}
button{width:44px;height:44px;border:0;border-radius:50%;background:#0B6B5E;color:#fff;font-size:18px;cursor:pointer;display:flex;align-items:center;justify-content:center;flex:none}
button:disabled{opacity:.5;cursor:default}
#mic{background:#fff;color:#0B6B5E;border:2px solid #0B6B5E}
#mic.actif{background:#B3261E;border-color:#B3261E;color:#fff}
</style></head>
<body><div id="app">
<header>
<svg width="40" height="40" viewBox="0 0 120 120" role="img" aria-label="Logo Boussole Santé Togo"><circle cx="60" cy="60" r="60" fill="#fff"/><circle cx="60" cy="60" r="50" fill="none" stroke="#0B6B5E" stroke-opacity=".35" stroke-width="2"/><path d="M60 18L67 53L102 60L67 67L60 102L53 67L18 60L53 53Z" fill="#0B6B5E" stroke="#0B6B5E" stroke-width="2" stroke-linejoin="round"/><path d="M60 18L67 53L53 53Z" fill="#3BB59A" stroke="#3BB59A" stroke-width="2" stroke-linejoin="round"/><circle cx="60" cy="60" r="5" fill="#fff" stroke="#0B6B5E" stroke-width="2"/></svg>
<div>Boussole Santé Togo<small>assistant IA · ne remplace pas un médecin</small></div>
</header>
<div id="msgs"></div>
<div id="astuce" role="status"></div>
<form id="f">
<textarea id="t" rows="1" placeholder="Message" aria-label="Message"></textarea>
<button type="button" id="mic" aria-label="Enregistrer un message vocal"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="9" y="3" width="6" height="12" rx="3"/><path d="M5 11a7 7 0 0 0 14 0M12 18v3"/></svg></button>
<button type="submit" id="envoi" aria-label="Envoyer">&#10148;</button>
</form>
</div>
<script>
const msgs = document.getElementById("msgs");
const f = document.getElementById("f");
const t = document.getElementById("t");
const micro = document.getElementById("mic");
const envoi = document.getElementById("envoi");
const astuce = document.getElementById("astuce");

function ajouter(texte, cls) {
  const d = document.createElement("div");
  d.className = "m " + cls;
  d.textContent = texte;
  msgs.appendChild(d);
  msgs.scrollTop = msgs.scrollHeight;
  return d;
}

function ajuster() {
  t.style.height = "auto";
  t.style.height = Math.min(t.scrollHeight, 120) + "px";
}

function montrerAstuce(texte) {
  astuce.textContent = texte;
  astuce.classList.add("visible");
}

function cacherAstuce() {
  astuce.classList.remove("visible");
}

ajouter("Bonjour ! Je peux vous aider à comprendre vos symptômes et à savoir quoi faire. Je ne remplace pas un médecin. En cas d'urgence, allez tout de suite au centre de santé le plus proche. Vous pouvez écrire ou toucher le micro pour parler : le texte s'affichera pour que vous puissiez le corriger avant d'envoyer. Décrivez-moi ce qui ne va pas.", "bot");

t.addEventListener("input", ajuster);
t.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    f.requestSubmit();
  }
});

f.addEventListener("submit", async (e) => {
  e.preventDefault();
  const q = t.value.trim();
  if (!q) return;
  t.value = "";
  ajuster();
  cacherAstuce();
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

let enregistreur = null;
let flux = null;
let morceaux = [];
let minuteur = null;

async function demarrer() {
  try {
    flux = await navigator.mediaDevices.getUserMedia({audio: true});
  } catch (err) {
    ajouter("Le micro n'est pas autorisé. Autorisez-le dans le navigateur, puis réessayez.", "bot");
    return;
  }
  cacherAstuce();
  morceaux = [];
  enregistreur = new MediaRecorder(flux);
  enregistreur.ondataavailable = (e) => morceaux.push(e.data);
  enregistreur.onstop = transcrireAudio;
  enregistreur.start();
  micro.classList.add("actif");
  micro.setAttribute("aria-label", "Arrêter l'enregistrement");
  t.placeholder = "Enregistrement... touchez le micro pour arrêter";
  minuteur = setTimeout(arreter, 60000);
}

function arreter() {
  clearTimeout(minuteur);
  if (enregistreur && enregistreur.state === "recording") enregistreur.stop();
  if (flux) flux.getTracks().forEach((p) => p.stop());
  micro.classList.remove("actif");
  micro.setAttribute("aria-label", "Enregistrer un message vocal");
}

micro.addEventListener("click", () => {
  if (enregistreur && enregistreur.state === "recording") arreter();
  else demarrer();
});

async function versWav(blob) {
  const contexte = new AudioContext({sampleRate: 16000});
  const tampon = await contexte.decodeAudioData(await blob.arrayBuffer());
  const donnees = tampon.getChannelData(0);
  const frequence = tampon.sampleRate;
  const buf = new ArrayBuffer(44 + donnees.length * 2);
  const v = new DataView(buf);
  const ecrire = (o, s) => { for (let i = 0; i < s.length; i++) v.setUint8(o + i, s.charCodeAt(i)); };
  ecrire(0, "RIFF"); v.setUint32(4, 36 + donnees.length * 2, true); ecrire(8, "WAVE"); ecrire(12, "fmt ");
  v.setUint32(16, 16, true); v.setUint16(20, 1, true); v.setUint16(22, 1, true);
  v.setUint32(24, frequence, true); v.setUint32(28, frequence * 2, true);
  v.setUint16(32, 2, true); v.setUint16(34, 16, true);
  ecrire(36, "data"); v.setUint32(40, donnees.length * 2, true);
  for (let i = 0; i < donnees.length; i++) {
    const s = Math.max(-1, Math.min(1, donnees[i]));
    v.setInt16(44 + i * 2, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
  }
  contexte.close();
  return new Blob([buf], {type: "audio/wav"});
}

async function transcrireAudio() {
  const blob = new Blob(morceaux, {type: enregistreur.mimeType});
  t.value = "";
  ajuster();
  t.placeholder = "Transcription en cours...";
  t.disabled = true;
  micro.disabled = true;
  envoi.disabled = true;
  try {
    const wav = await versWav(blob);
    const r = await fetch("/transcrire", {
      method: "POST",
      headers: {"Content-Type": "audio/wav"},
      body: wav
    });
    const d = await r.json();
    if (d.transcription) {
      t.value = d.transcription;
      ajuster();
      montrerAstuce("Vérifiez le texte, corrigez-le si besoin, puis touchez Envoyer.");
    } else {
      ajouter(d.erreur || "Je n'ai pas bien entendu votre message. Réessayez, ou écrivez-le.", "bot");
    }
  } catch (err) {
    ajouter("Impossible de transcrire le message vocal. Réessayez ou écrivez votre message.", "bot");
  }
  t.disabled = false;
  micro.disabled = false;
  envoi.disabled = false;
  t.placeholder = "Message";
  t.focus();
}
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


def config_simple(modele):
    if "lite" in modele:
        return types.GenerateContentConfig(max_output_tokens=500)
    return types.GenerateContentConfig(
        max_output_tokens=500,
        thinking_config=types.ThinkingConfig(thinking_level="LOW"),
    )


historique = []
app = Flask(__name__)


def repondre(question):
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
                return texte
        except Exception as erreur:
            print(f"[{modele}] échec : {str(erreur)[:200]}")
    return None


def transcrire(audio_bytes):
    consigne = (
        "Transcris fidèlement ce message vocal. Réponds uniquement par la "
        "transcription, dans la langue parlée, sans commentaire. "
        "Si tu n'entends aucune parole, réponds exactement INAUDIBLE."
    )
    for modele in MODELES:
        try:
            r = client.models.generate_content(
                model=modele,
                contents=[
                    types.Part.from_bytes(data=audio_bytes, mime_type="audio/wav"),
                    consigne,
                ],
                config=config_simple(modele),
            )
            texte = (r.text or "").strip()
            if texte:
                print(f"[{modele}] transcription ok")
                return "" if "INAUDIBLE" in texte.upper() else texte
        except Exception as erreur:
            print(f"[{modele}] transcription échec : {str(erreur)[:200]}")
    return None


@app.get("/")
def accueil():
    return PAGE


@app.post("/chat")
def chat():
    question = (request.get_json(silent=True) or {}).get("message", "").strip()
    if not question:
        return jsonify({"reponse": "Écrivez votre message d'abord."}), 400

    texte = repondre(question)
    if texte is None:
        return jsonify({"reponse": "Désolé, le service est très sollicité en ce moment. Réessayez dans un instant."}), 503
    return jsonify({"reponse": texte})


@app.post("/transcrire")
def transcrire_route():
    donnees = request.get_data()
    if len(donnees) < 2000:
        return jsonify({"transcription": "", "erreur": "Je n'ai rien entendu. Réessayez en parlant plus près du micro."}), 400

    transcription = transcrire(donnees)
    if transcription is None:
        return jsonify({"transcription": "", "erreur": "Désolé, le service est très sollicité en ce moment. Réessayez dans un instant."}), 503
    if not transcription:
        return jsonify({"transcription": "", "erreur": "Je n'ai pas bien entendu votre message. Réessayez, ou écrivez-le."})
    return jsonify({"transcription": transcription})


if __name__ == "__main__":
    app.run(port=5000)