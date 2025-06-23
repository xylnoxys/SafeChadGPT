import os
import requests
from web3 import Web3

ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY")
ETH_RPC = os.getenv("ETH_RPC", "https://eth.llamarpc.com")
web3 = Web3(Web3.HTTPProvider(ETH_RPC))

DEAD = "0x000000000000000000000000000000000000dEaD"
ZERO = "0x0000000000000000000000000000000000000000"
WETH = Web3.to_checksum_address("0xC02aaA39b223FE8D0A0E5C4F27eAD9083C756Cc2")
UNIV2_FACTORY = "0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f"
UNIV2_INIT_CODE_HASH = "0x96e8ac427619fd76c75fb150e68b7bff3dc8fa02043a1e3cc2c5c7e1e77ce9d5"
TEAMFINANCE_API = "https://api.team.finance/proxy/v1/mainnet/lock/token/"


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
        return f"🧾 Transfer gas: {gas} (No obvious tax)"
    except:
        return "⚠️ Possible honeypot or high tax"


def get_univ2_pair_address(token):
    token0, token1 = sorted([token.lower(), WETH.lower()])
    salt = Web3.solidity_keccak(['address', 'address'], [token0, token1])
    raw = Web3.solidity_keccak(['bytes', 'address', 'bytes32', 'bytes32'], [
        b'\xff',
        Web3.to_checksum_address(UNIV2_FACTORY),
        salt,
        bytes.fromhex(UNIV2_INIT_CODE_HASH[2:])
    ])
    return Web3.to_checksum_address(raw[-20:].hex())


def get_lp_lock_status(pair_address):
    try:
        resp = requests.get(TEAMFINANCE_API + pair_address).json()
        if resp.get("data"):
            total_locked = sum(int(lock['amount']) for lock in resp['data'])
            return f"🔒 LP Locked via TeamFinance ({total_locked // 1e18:.2f} tokens)"
        return "⚠️ LP not locked"
    except:
        return "❓ LP lock status unknown"


def analyze_token(address):
    try:
        address = Web3.to_checksum_address(address)
        info = get_token_info(address)
        total_supply = get_total_supply(address)
        burned = get_balance_of(address, DEAD) + get_balance_of(address, ZERO)
        burned_pct = (burned / total_supply) * 100 if total_supply else 0
        renounced = info["owner"] in [DEAD.lower(), ZERO.lower()]
        verified = info["verified"]
        tax = check_tax(address)

        pair_address = get_univ2_pair_address(address)
        lp_lock = get_lp_lock_status(pair_address)

        safe = all([
            verified,
            renounced,
            burned_pct > 1,
            "🔒" in lp_lock,
            "⚠️" not in tax
        ])

        emoji = "🟢" if safe else "🔴"
        return f"""{emoji} {info['name']} ({info['symbol']})

🔹 Contract: `{address}`
🔐 Verified: {'✅ Yes' if verified else '❌ No'}
👨‍💻 Owner: {'Renounced' if renounced else info['owner'] or 'Unknown'}
🔥 Burned Supply: {burned_pct:.2f}%
{lp_lock}
{tax}

📜 https://etherscan.io/address/{address}
📊 https://etherscan.io/token/{address}#balances
"""
    except Exception as e:
        return f"❌ Scan failed: {str(e)}"
