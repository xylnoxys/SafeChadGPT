# analyze_token.py

import os
import requests
from web3 import Web3
from datetime import datetime

ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY")
ETH_RPC = os.getenv("ETH_RPC", "https://eth.llamarpc.com")
web3 = Web3(Web3.HTTPProvider(ETH_RPC))

ZERO = "0x0000000000000000000000000000000000000000"
DEAD = "0x000000000000000000000000000000000000dEaD"
WETH = "0xC02aaA39b223FE8D0A0E5C4F27eAD9083C756Cc2"
UNIV2_FACTORY = "0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f"
UNIV2_INIT_CODE_HASH = "0x96e8ac427619fd76c75fb150e68b7bff3dc8fa02043a1e3cc2c5c7e1e77ce9d5"
UNIV3_SUBGRAPH = "https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v3"

HEADERS = {"accept": "application/json"}

def get_source_code(address):
    url = "https://api.etherscan.io/api"
    params = {
        "module": "contract",
        "action": "getsourcecode",
        "address": address,
        "apikey": ETHERSCAN_API_KEY
    }
    return requests.get(url, params=params).json()["result"][0]

def get_token_info(address):
    info = get_source_code(address)
    return {
        "name": info.get("ContractName", "Unknown"),
        "symbol": info.get("Symbol", "???"),
        "verified": info.get("ABI") not in ("", "Contract source code not verified"),
        "owner": info.get("Owner", "Unknown").lower(),
        "creation_ts": int(info.get("CreationDate", "0")) if info.get("CreationDate") else None
    }

def get_total_supply(token):
    try:
        contract = web3.eth.contract(address=Web3.toChecksumAddress(token), abi=[
            {"constant": True, "inputs": [], "name": "totalSupply", "outputs": [{"name": "", "type": "uint256"}], "type": "function"}
        ])
        return contract.functions.totalSupply().call()
    except:
        return 0

def get_balance_of(token, wallet):
    try:
        contract = web3.eth.contract(address=Web3.toChecksumAddress(token), abi=[
            {"constant": True, "inputs": [{"name": "owner", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "", "type": "uint256"}], "type": "function"}
        ])
        return contract.functions.balanceOf(Web3.toChecksumAddress(wallet)).call()
    except:
        return 0

def check_renounced(owner):
    return owner in [ZERO.lower(), DEAD.lower()]

def get_univ2_lp_address(token):
    token0, token1 = sorted([token, WETH])
    salt = Web3.solidityKeccak(['address', 'address'], [token0, token1])
    raw = Web3.solidityKeccak(['bytes', 'address', 'bytes32', 'bytes32'], [
        b'\xff',
        Web3.toChecksumAddress(UNIV2_FACTORY),
        salt,
        bytes.fromhex(UNIV2_INIT_CODE_HASH[2:])
    ])
    return Web3.toChecksumAddress(raw[-20:].hex())

def check_lp_status(token):
    try:
        v2_addr = get_univ2_lp_address(token)
        total = get_total_supply(v2_addr)
        burned = get_balance_of(v2_addr, DEAD) + get_balance_of(v2_addr, ZERO)
        pct = (burned / total) * 100 if total else 0
        return f"✅ LP burned ({pct:.1f}%)" if pct > 90 else f"⚠️ LP not fully burned ({pct:.1f}%)"
    except:
        return "❓ LP status unknown"

def check_v3_lp(token):
    query = {
        "query": f"""
        {{ pools(where: {{ token0: \"{token.lower()}\" }}, first: 1, orderBy: totalValueLockedToken0, orderDirection: desc) {{ id, liquidity }} }}
        """
    }
    try:
        res = requests.post(UNIV3_SUBGRAPH, json=query).json()
        pools = res.get("data", {}).get("pools", [])
        if not pools:
            return "❌ No V3 pool"
        if int(pools[0]['liquidity']) == 0:
            return "✅ V3 LP burned"
        return "⚠️ V3 LP exists"
    except:
        return "❓ V3 status unknown"

def analyze_token(address):
    try:
        address = Web3.toChecksumAddress(address)
        info = get_token_info(address)
        total_supply = get_total_supply(address)
        burned = get_balance_of(address, DEAD) + get_balance_of(address, ZERO)
        burned_pct = (burned / total_supply) * 100 if total_supply else 0

        renounced = check_renounced(info['owner'])
        lp_status = check_lp_status(address)
        v3_status = check_v3_lp(address)

        creation = info.get("creation_ts")
        age = "?"
        if creation:
            dt = datetime.utcfromtimestamp(creation)
            now = datetime.utcnow()
            delta = now - dt
            age = f"{delta.days}d {delta.seconds//3600}h {(delta.seconds//60)%60}m"

        emoji = "🟢" if renounced and burned_pct > 1 and "✅" in (lp_status + v3_status) else "🔴"

        return f"""
{emoji} {info['name']} ({info['symbol']})

🔹ETH: `{address}`
👨‍💻Owner: {'***RENOUNCED***' if renounced else info['owner'] or 'Unknown'}
💧LP Status: {lp_status}
💧V3: {v3_status}
🔥Burned Supply: {burned_pct:.2f}%
🕰Age: {age}
📜 https://etherscan.io/address/{address}
📊 https://etherscan.io/token/{address}#balances
"""
    except Exception as e:
        return f"❌ Scan failed: {str(e)}"
