import os
import requests
from flask import Flask, request
from analyze_token import analyze_token
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

app = Flask(__name__)

@app.route("/", methods=["GET"])
def home():
    return "✅ SafeChadGPT is alive!", 200

@app.route("/", methods=["POST"])
def handle_webhook():
    data = request.json
    if "message" in data:
        message = data["message"]
        chat_id = message["chat"]["id"]
        text = message.get("text", "").strip()

        if text.startswith("0x") and len(text) == 42:
            result = analyze_token(text)
        else:
            result = "❗️ Please send a valid Ethereum token contract address (starts with 0x...)."

        requests.post(TELEGRAM_API_URL, json={
            "chat_id": chat_id,
            "text": result,
            "disable_web_page_preview": True
        })

    return "", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
