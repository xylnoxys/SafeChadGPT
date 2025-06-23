import os
import requests
from web3 import Web3

ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY")
ETH_RPC = os.getenv("ETH_RPC", "https://eth.llamarpc.com")  # or use Infura/Alchemy
web3 = Web3(Web3.HTTPProvider(ETH_RPC))

DEAD = "0x000000000000000000000000000000000000dEaD"
ZERO = "0x0000000000000000000000000000000000000000"

def get_token_info(address):
    res = requests.get("https://api.etherscan.io/api", params={
        "module": "contract",
        "action": "getsourcecode",
        "address": address,
        "apikey": ETHERSCAN_API_KEY
    }).json()
    info = res["result"][0]
    return {
        "name": info.get("ContractName", "Unknown"),
        "symbol": info.get("Symbol", "???"),
        "verified": info.get("ABI") not in ("", "Contract source code not verified"),
        "owner": info.get("Owner", "").lower()
    }

def get_total_supply(address):
    try:
        token = web3.eth.contract(address=Web3.toChecksumAddress(address), abi=[
            {"constant":True,"inputs":[],"name":"totalSupply","outputs":[{"name":"","type":"uint256"}],"type":"function"}
        ])
        return token.functions.totalSupply().call()
    except: return 0

def get_balance_of(address, wallet):
    try:
        token = web3.eth.contract(address=Web3.toChecksumAddress(address), abi=[
            {"constant":True,"inputs":[{"name":"owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"","type":"uint256"}],"type":"function"}
        ])
        return token.functions.balanceOf(Web3.toChecksumAddress(wallet)).call()
    except: return 0

def check_tax(address, decimals=18):
    try:
        wallet1 = web3.eth.account.create()
        wallet2 = web3.eth.account.create()
        token = web3.eth.contract(address=Web3.toChecksumAddress(address), abi=[
            {"constant":False,"inputs":[{"name":"to","type":"address"},{"name":"value","type":"uint256"}],"name":"transfer","outputs":[{"name":"","type":"bool"}],"type":"function"},
            {"constant":False,"inputs":[{"name":"from","type":"address"},{"name":"to","type":"address"},{"name":"value","type":"uint256"}],"name":"transferFrom","outputs":[{"name":"","type":"bool"}],"type":"function"}
        ])
        amt = 100 * (10 ** decimals)
        gas_transfer = token.functions.transfer(wallet2.address, amt).estimate_gas({'from': wallet1.address})
        return f"Estimated Gas: {gas_transfer} (No obvious tax)"
    except Exception as e:
        return "⚠️ High tax or transfer may fail (possible honeypot)"

def analyze_token(address):
    try:
        info = get_token_info(address)
        total_supply = get_total_supply(address)
        dead_bal = get_balance_of(address, DEAD)
        zero_bal = get_balance_of(address, ZERO)
        burned = dead_bal + zero_bal
        burned_pct = (burned / total_supply) * 100 if total_supply > 0 else 0

        renounced = info["owner"] in [DEAD, ZERO]
        verified = info["verified"]
        tax_info = check_tax(address)
        safety = "🟢" if renounced and verified and burned_pct > 1 else "🔴"

        return f"""{safety} {info['name']} ({info['symbol']})

🔹 Contract: `{address}`
🔐 Verified: {"✅ Yes" if verified else "❌ No"}
👨‍💻 Owner: {"Renounced" if renounced else info['owner'] or "Unknown"}
🔥 Burned: {burned_pct:.2f}%
🧾 Tax: {tax_info}

🔗 Etherscan:
📜 https://etherscan.io/address/{address}
📊 https://etherscan.io/token/{address}#balances
"""
    except Exception as e:
        return f"❌ Scan failed: {str(e)}"
