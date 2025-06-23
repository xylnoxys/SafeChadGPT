import os
import requests
from flask import Flask, request

TOKEN = os.getenv("BOT_TOKEN")
URL = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

app = Flask(__name__)

@app.route('/', methods=['POST'])
def webhook():
    data = request.json
    if 'message' in data:
        chat_id = data['message']['chat']['id']
        text = data['message'].get('text', '')
        if text.startswith("0x") and len(text) == 42:
            reply = f"🧠 Scanning token:\n{str(text)}\n(More logic will be added here...)"
        else:
            reply = "Send me an Ethereum token address to scan."
        requests.post(URL, json={"chat_id": chat_id, "text": reply})
    return '', 200

@app.route('/', methods=['GET'])
def home():
    return 'SafeChadGPT is live', 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
