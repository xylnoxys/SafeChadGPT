# SafeChadGPT (Full Version)

This is a Flask-powered Telegram bot that screens Ethereum token contract addresses.
You send a contract address, it replies with token info (renounce, LP, tax, safety, etc).

## 🚀 How to Use

1. Upload all files in this folder to your GitHub repo (replace the old ones)
2. Railway will automatically redeploy your bot
3. Set the webhook again if needed (only once)

https://api.telegram.org/bot<YOUR_TOKEN>/setWebhook?url=https://your-app-name.up.railway.app

Send any `0x...` token contract address to your Telegram bot and it will return a scan.
