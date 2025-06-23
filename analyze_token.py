import random

def analyze_token(address):
    # Dummy scanner simulation — replace with real Etherscan/Uniswap/graph API later
    is_safe = random.choice([True, False])
    emoji = "🟢" if is_safe else "🔴"
    token_name = "SampleToken"
    token_symbol = "STK"
    tax_info = "Buy: 0%, Sell: 0%, Transfer: 0%"
    renounced = "Yes"
    lp_status = "100% Burned"
    burned_pct = "0.00%"
    verified = "Yes"

    return f"""{emoji} {token_name} ({token_symbol})

🔹 Contract: `{address}`
🔐 Verified: {verified}
👨‍💻 Owner: {renounced}
💰 LP Status: {lp_status}
🔥 Burned Supply: {burned_pct}
🧾 Tax: {tax_info}

🔎 https://etherscan.io/address/{address}
📊 https://etherscan.io/token/{address}#balances
"""
