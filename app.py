import subprocess
import threading
from flask import Flask, request
import requests
import xml.etree.ElementTree as ET

app = Flask(__name__)

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "VOTRE_DISCORD_WEBHOOK_URL_ICI")

@app.route("/")
def home():
    return "Le bot est en ligne !"

@app.route("/youtube/callback", methods=["GET", "POST"])
def youtube_callback():
    if request.method == "GET":
        challenge = request.args.get("hub.challenge")
        if challenge:
            return challenge, 200
        return "Bad Request", 400

    if request.method == "POST":
        xml_data = request.data
        try:
            root = ET.fromstring(xml_data)
            for entry in root.findall('{http://www.w3.org/2005/Atom}entry'):
                author = entry.find('{http://www.w3.org/2005/Atom}name')
                if author is not None:
                    pseudo = author.text
                    payload = {
                        "content": f"🎉 **Nouveau membre dans la communauté !**\nMerci à **{pseudo}** de s'être abonné(e) à la chaîne YouTube ! ❤️"
                    }
                    requests.post(DISCORD_WEBHOOK_URL, json=payload)
        except Exception as e:
            print(f"Erreur : {e}")
        return "", 200

def start_bot():
    subprocess.run([python Bot.py", "arg1", "arg2"], check=True)

_bot_started = False
if not _bot_started:
    _bot_started = True
    threading.Thread(target=start_bot, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
