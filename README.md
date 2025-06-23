# SafeChadGPT

A Flask-based Telegram bot that screens Ethereum token contracts for safety checks.

## Setup (for Railway / Render)

1. Deploy this repo to Railway or Render.com as a web service.
2. Add environment variable:
   - `BOT_TOKEN`: your Telegram bot token
3. Set the webhook with the public URL after deployment:
   ```
   https://api.telegram.org/bot<YOUR_TOKEN>/setWebhook?url=https://your-deployed-url.com
   ```

Once deployed, the bot will respond to Ethereum contract addresses sent to it.
