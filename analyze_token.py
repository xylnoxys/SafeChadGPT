import os
import requests
from web3 import Web3
from datetime import datetime

ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY")
ETH_RPC = os.getenv("ETH_RPC", "https://eth.llamarpc.com")
web3 = Web3(Web3.HTTPProvider(ETH_RPC))

DEAD = "0x000000000000000000000000000000000000dEaD"
ZERO = "0x0000000000000000000000000000000000000000"
UNIV2_FACTORY = "0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f"
UNIV2_INIT_CODE_HASH = "0x96e8ac427619fd76c75fb150e68b7bff3dc8fa02043a1e3cc2c5c7e1e77ce9d5"
UNIV3_SUBGRAPH = "https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v3"


def get_token_info(address):
    url = f"https://api.etherscan.io/api"
    params = {
        "module": "contract",
        "action": "getsourcecode",
        "address": address,
        "apikey": ETHERSCAN_API_KEY
    }
    r = requests.get(url, params=params).json()
    data = r["result"][0]
    return {
        "name": data.get("ContractName", "Unknown"),
        "symbol": data.get("Symbol", "???"),
        "verified": data.get("ABI") not in ("", "Contract source code not verified"),
        "owner": data.get("Owner", "Unknown"),
        "created": data.get("ContractCreationDate", None)
    }


def get_total_supply(token):
    try:
        contract = web3.eth.contract(address=Web3.toChecksumAddress(token), abi=[
            {"constant": True, "inputs": [], "name": "totalSupply", "outputs": [{"name": "", "type": "uint256"}], "type": "function"}
        ])
        return contract.functions.totalSupply().call()
    except:
        return 0


def get_balance(token, wallet):
    try:
        contract = web3.eth.contract(address=Web3.toChecksumAddress(token), abi=[
            {"constant": True, "inputs": [{"name": "owner", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "", "type": "uint256"}], "type": "function"}
        ])
        return contract.functions.balanceOf(Web3.toChecksumAddress(wallet)).call()
    except:
        return 0


def is_renounced(owner):
    return owner.lower() in [DEAD.lower(), ZERO.lower()]


def check_tax(token):
    try:
        w1 = web3.eth.account.create()
        w2 = web3.eth.account.create()
        contract = web3.eth.contract(address=Web3.toChecksumAddress(token), abi=[
            {"name": "transfer", "type": "function", "inputs": [
                {"type": "address", "name": "to"}, {"type": "uint256", "name": "amount"}
            ], "outputs": [{"type": "bool"}], "stateMutability": "nonpayable"}
        ])
        amt = 100 * (10 ** 18)
        contract.functions.transfer(w2.address, amt).estimate_gas({'from': w1.address})
        return "Buy/Sell/Transfer Tax: 0%"
    except:
        return "⚠️ Honeypot or Tax detected"


def get_univ2_lp(token):
    try:
        weth = Web3.toChecksumAddress("0xC02aaA39b223FE8D0A0E5C4F27eAD9083C756Cc2")
        token = Web3.toChecksumAddress(token)
        token0, token1 = sorted([token, weth])
        salt = Web3.solidityKeccak(['address', 'address'], [token0, token1])
        raw = Web3.solidityKeccak(['bytes', 'address', 'bytes32', 'bytes32'], [
            b'\xff', Web3.toChecksumAddress(UNIV2_FACTORY), salt, bytes.fromhex(UNIV2_INIT_CODE_HASH[2:])
        ])
        pair = Web3.toChecksumAddress("0x" + raw.hex()[-40:])
        burned = get_balance(pair, DEAD) + get_balance(pair, ZERO)
        supply = get_total_supply(pair)
        ratio = (burned / supply) * 100 if supply else 0
        return f"V2 LP Burned: {ratio:.2f}%" if ratio > 10 else f"V2 LP only {ratio:.2f}% burned"
    except:
        return "V2 LP: Unknown"


def get_univ3_lp(token):
    try:
        query = {
            "query": f"""
            {{
              pools(where: {{token0: \"{token.lower()}\"}}, first: 1, orderBy: totalValueLockedUSD, orderDirection: desc) {{
                id
                liquidity
              }}
            }}
            """
        }
        r = requests.post(UNIV3_SUBGRAPH, json=query).json()
        pool = r.get("data", {}).get("pools", [])[0]
        if int(pool['liquidity']) == 0:
            return "✅ V3 LP burned"
        else:
            return "⚠️ V3 LP liquidity exists"
    except:
        return "V3 LP: Unknown"


def analyze_token(address):
    try:
        info = get_token_info(address)
        total = get_total_supply(address)
        burned = get_balance(address, DEAD) + get_balance(address, ZERO)
        burned_pct = (burned / total) * 100 if total else 0

        emoji = "🟢" if is_renounced(info['owner']) and burned_pct > 1 and info['verified'] else "🔴"

        return f"""{emoji} {info['name']} ({info['symbol']})

🔹ETH: `{address}`
👨‍💻Owner: {'RENOUNCED' if is_renounced(info['owner']) else info['owner']}
🔥Burned Supply: {burned_pct:.2f}%
🔐Verified: {'✅ Yes' if info['verified'] else '❌ No'}
{get_univ2_lp(address)}
{get_univ3_lp(address)}
{check_tax(address)}

📜 https://etherscan.io/address/{address}
📊 https://etherscan.io/token/{address}#balances
"""
    except Exception as e:
        return f"❌ Scan failed: {str(e)}"
