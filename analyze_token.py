import os
import requests
from web3 import Web3
from eth_abi import encode
from datetime import datetime

ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY")
ETH_RPC = os.getenv("ETH_RPC", "https://eth.llamarpc.com")
web3 = Web3(Web3.HTTPProvider(ETH_RPC))

ZERO = "0x0000000000000000000000000000000000000000"
DEAD = "0x000000000000000000000000000000000000dEaD"
WETH = Web3.toChecksumAddress("0xC02aaA39b223FE8D0A0E5C4F27eAD9083C756Cc2")
UNIV2_FACTORY = Web3.toChecksumAddress("0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f")
UNIV2_INIT_CODE_HASH = "0x96e8ac427619fd76c75fb150e68b7bff3dc8fa02043a1e3cc2c5c7e1e77ce9d5"


def get_token_info(address):
    res = requests.get("https://api.etherscan.io/api", params={
        "module": "contract",
        "action": "getsourcecode",
        "address": address,
        "apikey": ETHERSCAN_API_KEY
    }).json()
    info = res['result'][0]
    verified = info['ABI'] not in ('', 'Contract source code not verified')
    return {
        "name": info.get("ContractName", "???"),
        "symbol": info.get("Symbol", "???"),
        "owner": info.get("Owner", "Unknown").lower(),
        "verified": verified,
        "creation": get_token_age(address)
    }


def get_token_age(address):
    res = requests.get("https://api.etherscan.io/api", params={
        "module": "contract",
        "action": "getcontractcreation",
        "contractaddresses": address,
        "apikey": ETHERSCAN_API_KEY
    }).json()
    result = res.get("result", [{}])[0]
    if not result:
        return "Unknown"
    ts = int(result.get("timeStamp", 0))
    age = datetime.utcnow() - datetime.utcfromtimestamp(ts)
    hours, remainder = divmod(int(age.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours}h {minutes}m {seconds}s"


def get_contract(address, abi):
    return web3.eth.contract(Web3.toChecksumAddress(address), abi=abi)


def get_total_supply(address):
    try:
        token = get_contract(address, [{"constant": True, "name": "totalSupply", "outputs": [{"name": "", "type": "uint256"}], "inputs": [], "type": "function"}])
        return token.functions.totalSupply().call()
    except:
        return 0


def get_balance(address, wallet):
    try:
        token = get_contract(address, [{"constant": True, "name": "balanceOf", "outputs": [{"name": "", "type": "uint256"}], "inputs": [{"name": "", "type": "address"}], "type": "function"}])
        return token.functions.balanceOf(Web3.toChecksumAddress(wallet)).call()
    except:
        return 0


def check_renounced(owner):
    return owner in [ZERO.lower(), DEAD.lower()]


def check_tax(address, decimals=18):
    try:
        wallet = web3.eth.account.create()
        token = get_contract(address, [{"name": "transfer", "type": "function", "inputs": [{"name": "to", "type": "address"}, {"name": "value", "type": "uint256"}], "outputs": [{"name": "", "type": "bool"}]}])
        value = 100 * (10 ** decimals)
        token.functions.transfer(wallet.address, value).estimate_gas({'from': wallet.address})
        return "✅ No Tax Detected"
    except:
        return "⚠️ Honeypot or Tax detected"


def get_univ2_lp_status(token_address):
    try:
        token0, token1 = sorted([Web3.toChecksumAddress(token_address), WETH])
        salt = Web3.solidityKeccak(['address', 'address'], [token0, token1])
        raw = Web3.solidityKeccak(['bytes', 'address', 'bytes32', 'bytes32'], [b'\xff', UNIV2_FACTORY, salt, bytes.fromhex(UNIV2_INIT_CODE_HASH[2:])])
        pair = Web3.toChecksumAddress(raw[-20:].hex())
        lp_supply = get_total_supply(pair)
        burned = get_balance(pair, ZERO) + get_balance(pair, DEAD)
        burned_pct = (burned / lp_supply) * 100 if lp_supply else 0
        return f"{'🔒' if burned_pct >= 99 else '⚠️'} LP Lock: {burned_pct:.2f}% burned"
    except:
        return "❓ V2 LP: Unknown"


def get_univ3_lp_status(token_address):
    try:
        query = {
            "query": f"""
            {{
              pools(where: {{token0: \"{token_address.lower()}\"}}, first: 1, orderBy: totalValueLockedUSD, orderDirection: desc) {{
                liquidity
              }}
            }}
            """
        }
        res = requests.post("https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v3", json=query).json()
        pool = res.get("data", {}).get("pools", [{}])[0]
        if not pool:
            return "❌ No V3 pool"
        if int(pool.get("liquidity", 0)) == 0:
            return "✅ V3 LP burned"
        return "⚠️ V3 LP detected"
    except:
        return "❓ V3 LP: Unknown"


def analyze_token(address):
    try:
        info = get_token_info(address)
        supply = get_total_supply(address)
        burned = get_balance(address, DEAD) + get_balance(address, ZERO)
        burned_pct = (burned / supply * 100) if supply else 0

        result = f"""
{'🟢' if all([info['verified'], check_renounced(info['owner']), burned_pct > 1]) else '🔴'} {info['name']} ({info['symbol']})

🔹ETH: `{address}`
👨‍💻Owner: {'RENOUNCED' if check_renounced(info['owner']) else info['owner'] or 'Unknown'}
🔥Burned Supply: {burned_pct:.2f}%
🔐Verified: {'✅ Yes' if info['verified'] else '❌ No'}
V2 LP: {get_univ2_lp_status(address)}
V3 LP: {get_univ3_lp_status(address)}
{check_tax(address)}

📜 https://etherscan.io/address/{address}
📊 https://etherscan.io/token/{address}#balances
🕰Age: {info['creation']}
"""
        return result.strip()
    except Exception as e:
        return f"❌ Scan failed: {str(e)}"
