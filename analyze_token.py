import os
import requests
from web3 import Web3
from datetime import datetime

ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY")
ETH_RPC = os.getenv("ETH_RPC", "https://eth.llamarpc.com")
web3 = Web3(Web3.HTTPProvider(ETH_RPC))

DEAD = "0x000000000000000000000000000000000000dEaD"
ZERO = "0x0000000000000000000000000000000000000000"
WETH = Web3.to_checksum_address("0xC02aaA39b223FE8D0A0E5C4F27eAD9083C756Cc2")
UNIV2_FACTORY = "0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f"
UNIV2_INIT_CODE_HASH = "0x96e8ac427619fd76c75fb150e68b7bff3dc8fa02043a1e3cc2c5c7e1e77ce9d5"

def get_token_info(address):
    res = requests.get("https://api.etherscan.io/api", params={
        "module": "contract",
        "action": "getsourcecode",
        "address": address,
        "apikey": ETHERSCAN_API_KEY
    }).json()
    info = res["result"][0]
    return {
        "name": info.get("ContractName") or "Unknown",
        "symbol": info.get("Symbol") or "???",
        "verified": info.get("ABI") not in ("", "Contract source code not verified"),
        "owner": info.get("Owner", "").lower(),
        "creation": info.get("CreationDate", None)
    }

def get_total_supply(address):
    try:
        token = web3.eth.contract(address=Web3.to_checksum_address(address), abi=[
            {"constant": True, "inputs": [], "name": "totalSupply", "outputs": [{"name": "", "type": "uint256"}], "type": "function"}
        ])
        return token.functions.totalSupply().call()
    except:
        return 0

def get_balance_of(address, wallet):
    try:
        token = web3.eth.contract(address=Web3.to_checksum_address(address), abi=[
            {"constant": True, "inputs": [{"name": "owner", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "", "type": "uint256"}], "type": "function"}
        ])
        return token.functions.balanceOf(Web3.to_checksum_address(wallet)).call()
    except:
        return 0

def check_tax(address, decimals=18):
    try:
        w1 = web3.eth.account.create()
        w2 = web3.eth.account.create()
        token = web3.eth.contract(address=Web3.to_checksum_address(address), abi=[
            {"constant": False, "inputs": [{"name": "to", "type": "address"}, {"name": "value", "type": "uint256"}], "name": "transfer", "outputs": [{"name": "", "type": "bool"}], "type": "function"}
        ])
        amt = 100 * (10 ** decimals)
        gas = token.functions.transfer(w2.address, amt).estimate_gas({'from': w1.address})
        return f"🟢 No honeypot or tax detected (est. gas {gas})"
    except:
        return "⚠️ Honeypot or Tax detected"

def get_univ2_lp_status(token_address):
    try:
        token0, token1 = sorted([Web3.to_checksum_address(token_address), WETH])
        salt = Web3.solidity_keccak(['address', 'address'], [token0, token1])
        raw = Web3.solidity_keccak(['bytes', 'address', 'bytes32'], [
            b'\xff',
            Web3.to_checksum_address(UNIV2_FACTORY),
            salt,
            bytes.fromhex(UNIV2_INIT_CODE_HASH[2:])
        ])
        pair_address = Web3.to_checksum_address(raw[-20:].hex())
        lp_balance = get_balance_of(pair_address, DEAD) + get_balance_of(pair_address, ZERO)
        total_lp = get_total_supply(pair_address)
        pct = (lp_balance / total_lp) * 100 if total_lp else 0
        if pct > 90:
            return f"✅ V2 LP burned ({pct:.1f}%)"
        elif pct > 0:
            return f"⚠️ V2 LP partially burned ({pct:.1f}%)"
        else:
            return "❌ V2 LP not burned"
    except:
        return "❓ V2 LP unknown"

def get_univ3_lp_status(token_address):
    try:
        query = {
            "query": f"""
            {{
              pools(where: {{
                token0: "{token_address.lower()}"
              }}, first: 1, orderBy: totalValueLockedUSD, orderDirection: desc) {{
                id
                liquidity
              }}
            }}
            """
        }
        res = requests.post("https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v3", json=query).json()
        pool = res.get("data", {}).get("pools", [])
        if not pool:
            return "❌ No V3 pool found"
        liquidity = int(pool[0]["liquidity"])
        if liquidity == 0:
            return "✅ V3 LP burned"
        return f"⚠️ V3 LP exists (liquidity > 0)"
    except:
        return "❓ V3 LP unknown"

def analyze_token(address):
    try:
        address = Web3.to_checksum_address(address)
        info = get_token_info(address)
        total_supply = get_total_supply(address)
        burned = get_balance_of(address, DEAD) + get_balance_of(address, ZERO)
        burned_pct = (burned / total_supply) * 100 if total_supply else 0

        renounced = info["owner"] in [DEAD.lower(), ZERO.lower()]
        verified = info["verified"]
        tax_result = check_tax(address)
        v2_status = get_univ2_lp_status(address)
        v3_status = get_univ3_lp_status(address)

        safe = all([
            verified,
            renounced,
            burned_pct > 1,
            "✅" in v2_status or "✅" in v3_status,
            "⚠️" not in tax_result
        ])

        emoji = "🟢" if safe else "🔴"
        creation_date = info.get("creation", None)
        age_text = ""
        if creation_date:
            try:
                dt = datetime.strptime(creation_date, "%Y-%m-%d")
                age_days = (datetime.utcnow() - dt).days
                age_text = f"\n📅 Age: {age_days} day(s)"
            except:
                pass

        return f"""{emoji} {info['name']} ({info['symbol']})

🔹 ETH: `{address}`
👨‍💻 Owner: {"Renounced" if renounced else info['owner'] or "Unknown"}
🔥 Burned Supply: {burned_pct:.2f}%
🔐 Verified: {"✅ Yes" if verified else "❌ No"}
{v2_status}
{v3_status}
{tax_result}{age_text}

📜 https://etherscan.io/address/{address}
📊 https://etherscan.io/token/{address}#balances
"""
    except Exception as e:
        return f"❌ Scan failed: {str(e)}"
