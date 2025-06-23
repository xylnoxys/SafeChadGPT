import os
import requests
from flask import Flask, request
from analyze_token import analyze_token

TOKEN = os.getenv("BOT_TOKEN")
URL = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

app = Flask(__name__)

@app.route("/", methods=["GET"])
def index():
    return "SafeChadGPT is alive!", 200

@app.route("/", methods=["POST"])
def webhook():
    data = request.json
    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "")

        if text.startswith("0x") and len(text) == 42:
            try:
                result = analyze_token(text)
            except Exception as e:
                result = f"❌ Scan failed: {str(e)}"
        else:
            result = "❗️Please send a valid Ethereum token contract address (starts with 0x)."

        requests.post(URL, json={
            "chat_id": chat_id,
            "text": result,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True
        })

    return "", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
