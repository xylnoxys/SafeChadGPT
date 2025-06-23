import os
import requests
from flask import Flask, request
from analyze_token import analyze_token

# Get your bot token from environment variable
TOKEN = os.getenv("BOT_TOKEN")
URL = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

app = Flask(__name__)

@app.route("/", methods=["GET"])
def home():
    return "✅ SafeChadGPT is running!", 200

@app.route("/", methods=["POST"])
def webhook():
    data = request.get_json()

    if "message" in data:
        message = data["message"]
        chat_id = message["chat"]["id"]
        text = message.get("text", "").strip()

        # If user sends a valid Ethereum contract address
        if text.startswith("0x") and len(text) == 42:
            result = analyze_token(text)
        else:
            result = "❗️Please send a valid Ethereum token contract address (starts with 0x...)."

        # Send the result back to the user via Telegram
        requests.post(URL, json={
            "chat_id": chat_id,
            "text": result,
            "disable_web_page_preview": True
        })

    return "", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
