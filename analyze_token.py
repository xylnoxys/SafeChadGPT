import os
import requests

ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY")

def analyze_token(address):
    try:
        # Get contract source code (for verified + owner info)
        source = requests.get("https://api.etherscan.io/api", params={
            "module": "contract",
            "action": "getsourcecode",
            "address": address,
            "apikey": ETHERSCAN_API_KEY
        }).json()

        info = source["result"][0]
        verified = info.get("ABI") not in ("", "Contract source code not verified")
        name = info.get("ContractName", "Unknown")
        symbol = info.get("Symbol", "???")
        owner = info.get("Owner", "").lower()
        renounced = owner in [
            "0x0000000000000000000000000000000000000000",
            "0x000000000000000000000000000000000000dead"
        ]

        safety = "🟢" if verified and renounced else "🔴"

        # Return basic info — more logic (tax, LP, etc.) will be added
        return f"""{safety} {name} ({symbol})

🔹 Contract: `{address}`
🔐 Verified: {"Yes" if verified else "No"}
👨‍💻 Owner: {"Renounced" if renounced else owner or "Unknown"}
🧾 Tax: (Scanning soon)
💧 LP: (Scanning soon)
🔥 Burned: (Calculating soon)

🔎 https://etherscan.io/address/{address}
📊 https://etherscan.io/token/{address}#balances
"""
    except Exception as e:
        return f"❌ Error: {str(e)}"
