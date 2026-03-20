"""
CRYPTO NATAL — Stellaris-13 Cryptocurrency Birth Data Registry

Every cryptocurrency has a verifiable birth moment: the genesis block timestamp.
This module maintains a curated registry of verified genesis data and supports
user-input custom coins. Charts are computed through the Stellaris-13 engine
just like human charts — full placements, aspects, angles, minor bodies.

HOUSE SYSTEM NOTE:
Coins don't have a birth "location" in the geographic sense. We use 0°N 0°E
(Null Island) as the default, which produces a neutral house framework.
If the location of the genesis miner/deployer is known, that can be specified
for a more nuanced house interpretation.
"""

from typing import Optional, List

# ═══════════════════════════════════════════════════════════════════════════════
# CURATED GENESIS REGISTRY
# ═══════════════════════════════════════════════════════════════════════════════

GENESIS_REGISTRY = {
    # ── Bitcoin & original forks ───────────────────────────────────────────
    "BTC": {
        "name": "Bitcoin", "symbol": "BTC",
        "genesis_date": "2009-01-03", "genesis_time": "18:15:05",
        "tz_offset": 0, "lat": 0.0, "lon": 0.0,
        "source": "Block 0 timestamp (Unix 1231006505, on-chain verified)",
        "rectified": False,
        "notes": "The original. Times headline embedded in coinbase.",
    },
    "LTC": {
        "name": "Litecoin", "symbol": "LTC",
        "genesis_date": "2011-10-07", "genesis_time": "07:31:05",
        "tz_offset": 0, "lat": 0.0, "lon": 0.0,
        "source": "Block 0 timestamp (on-chain verified)", "rectified": False,
        "notes": "Silver to Bitcoin's gold. Scrypt-based fork.",
    },
    "BCH": {
        "name": "Bitcoin Cash", "symbol": "BCH",
        "genesis_date": "2017-08-01", "genesis_time": "12:37:11",
        "tz_offset": 0, "lat": 0.0, "lon": 0.0,
        "source": "Block 478559 fork timestamp (on-chain verified)", "rectified": False,
        "notes": "Born from the blocksize war.",
    },

    # ── Smart contract platforms ───────────────────────────────────────────
    "ETH": {
        "name": "Ethereum", "symbol": "ETH",
        "genesis_date": "2015-07-30", "genesis_time": "15:26:13",
        "tz_offset": 0, "lat": 0.0, "lon": 0.0,
        "source": "Block 0 timestamp (on-chain verified)", "rectified": False,
        "notes": "The world computer. Frontier launch.",
    },
    "SOL": {
        "name": "Solana", "symbol": "SOL",
        "genesis_date": "2020-03-16", "genesis_time": "00:00:00",
        "tz_offset": 0, "lat": 0.0, "lon": 0.0,
        "source": "Mainnet beta genesis slot timestamp", "rectified": False,
        "notes": "High-throughput chain. Born during COVID crash.",
    },
    "ADA": {
        "name": "Cardano", "symbol": "ADA",
        "genesis_date": "2017-09-23", "genesis_time": "21:44:51",
        "tz_offset": 0, "lat": 0.0, "lon": 0.0,
        "source": "Byron mainnet genesis block", "rectified": False,
        "notes": "Peer-reviewed blockchain. Academic approach.",
    },
    "AVAX": {
        "name": "Avalanche", "symbol": "AVAX",
        "genesis_date": "2020-09-21", "genesis_time": "18:00:00",
        "tz_offset": 0, "lat": 0.0, "lon": 0.0,
        "source": "Mainnet launch timestamp", "rectified": False,
        "notes": "Sub-second finality. Cornell origins.",
    },
    "DOT": {
        "name": "Polkadot", "symbol": "DOT",
        "genesis_date": "2020-05-26", "genesis_time": "16:36:18",
        "tz_offset": 0, "lat": 0.0, "lon": 0.0,
        "source": "Relay chain genesis block", "rectified": False,
        "notes": "Interoperability. Web3 Foundation.",
    },
    "ATOM": {
        "name": "Cosmos", "symbol": "ATOM",
        "genesis_date": "2019-03-14", "genesis_time": "00:00:00",
        "tz_offset": 0, "lat": 0.0, "lon": 0.0,
        "source": "Cosmos Hub genesis block", "rectified": False,
        "notes": "Internet of blockchains. IBC protocol.",
    },

    # ── Privacy coins ──────────────────────────────────────────────────────
    "XMR": {
        "name": "Monero", "symbol": "XMR",
        "genesis_date": "2014-04-19", "genesis_time": "07:21:00",
        "tz_offset": 0, "lat": 0.0, "lon": 0.0,
        "source": "RECTIFIED via Stellaris-13 (score: 1089.08)", "rectified": True,
        "notes": "Sun at Aries 0° (zodiac zero point). Moon in Ophiuchus. The Shadow.",
    },
    "ZEC": {
        "name": "Zcash", "symbol": "ZEC",
        "genesis_date": "2016-10-28", "genesis_time": "14:56:18",
        "tz_offset": 0, "lat": 0.0, "lon": 0.0,
        "source": "Block 0 timestamp (on-chain verified)", "rectified": False,
        "notes": "zk-SNARK pioneer. Optional privacy.",
    },

    # ── Payment / transfer ─────────────────────────────────────────────────
    "XRP": {
        "name": "XRP Ledger", "symbol": "XRP",
        "genesis_date": "2012-06-02", "genesis_time": "00:00:00",
        "tz_offset": 0, "lat": 0.0, "lon": 0.0,
        "source": "Ledger activation date (exact time estimated — pre-mined)", "rectified": False,
        "notes": "Pre-mined. Institutional focus. SEC battle-tested.",
    },
    "XLM": {
        "name": "Stellar", "symbol": "XLM",
        "genesis_date": "2014-07-31", "genesis_time": "18:00:00",
        "tz_offset": 0, "lat": 0.0, "lon": 0.0,
        "source": "Network launch timestamp (approximate)", "rectified": False,
        "notes": "Financial inclusion focus.",
    },

    # ── Meme / cultural ────────────────────────────────────────────────────
    "DOGE": {
        "name": "Dogecoin", "symbol": "DOGE",
        "genesis_date": "2013-12-06", "genesis_time": "22:28:52",
        "tz_offset": 0, "lat": 0.0, "lon": 0.0,
        "source": "Block 0 timestamp (on-chain verified)", "rectified": False,
        "notes": "The joke that became a movement.",
    },
    "SHIB": {
        "name": "Shiba Inu", "symbol": "SHIB",
        "genesis_date": "2020-08-01", "genesis_time": "00:00:00",
        "tz_offset": 0, "lat": 0.0, "lon": 0.0,
        "source": "ERC-20 contract deployment (approximate)", "rectified": False,
        "notes": "The Dogecoin killer. ERC-20 token.",
    },

    # ── DeFi / Infrastructure ──────────────────────────────────────────────
    "LINK": {
        "name": "Chainlink", "symbol": "LINK",
        "genesis_date": "2017-09-19", "genesis_time": "00:00:00",
        "tz_offset": 0, "lat": 0.0, "lon": 0.0,
        "source": "ERC-20 contract deployment", "rectified": False,
        "notes": "The oracle network.",
    },
    "UNI": {
        "name": "Uniswap", "symbol": "UNI",
        "genesis_date": "2018-11-02", "genesis_time": "10:00:45",
        "tz_offset": 0, "lat": 0.0, "lon": 0.0,
        "source": "Uniswap V1 factory contract deployment", "rectified": False,
        "notes": "AMM pioneer.",
    },
    "AAVE": {
        "name": "Aave", "symbol": "AAVE",
        "genesis_date": "2020-01-08", "genesis_time": "00:00:00",
        "tz_offset": 0, "lat": 0.0, "lon": 0.0,
        "source": "Protocol V1 mainnet launch", "rectified": False,
        "notes": "Flash loans inventor.",
    },

    # ── Other notable ──────────────────────────────────────────────────────
    "TRX": {
        "name": "TRON", "symbol": "TRX",
        "genesis_date": "2018-06-25", "genesis_time": "00:00:00",
        "tz_offset": 0, "lat": 0.0, "lon": 0.0,
        "source": "TRON mainnet genesis block", "rectified": False,
        "notes": "Content-focused.",
    },
    "ETC": {
        "name": "Ethereum Classic", "symbol": "ETC",
        "genesis_date": "2016-07-20", "genesis_time": "13:36:00",
        "tz_offset": 0, "lat": 0.0, "lon": 0.0,
        "source": "DAO fork block 1920000", "rectified": False,
        "notes": "Code is law. The chain that refused to roll back.",
    },
    "NEAR": {
        "name": "NEAR Protocol", "symbol": "NEAR",
        "genesis_date": "2020-04-22", "genesis_time": "00:00:00",
        "tz_offset": 0, "lat": 0.0, "lon": 0.0,
        "source": "Mainnet genesis block", "rectified": False,
        "notes": "Sharded blockchain.",
    },
    "FIL": {
        "name": "Filecoin", "symbol": "FIL",
        "genesis_date": "2020-10-15", "genesis_time": "22:44:00",
        "tz_offset": 0, "lat": 0.0, "lon": 0.0,
        "source": "Mainnet launch block", "rectified": False,
        "notes": "Decentralized storage. Protocol Labs.",
    },
    "APT": {
        "name": "Aptos", "symbol": "APT",
        "genesis_date": "2022-10-12", "genesis_time": "00:00:00",
        "tz_offset": 0, "lat": 0.0, "lon": 0.0,
        "source": "Mainnet launch", "rectified": False,
        "notes": "Ex-Meta engineers. Move language.",
    },
    "SUI": {
        "name": "Sui", "symbol": "SUI",
        "genesis_date": "2023-05-03", "genesis_time": "00:00:00",
        "tz_offset": 0, "lat": 0.0, "lon": 0.0,
        "source": "Mainnet launch", "rectified": False,
        "notes": "Object-centric model.",
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════════════════════════════════

def get_genesis_data(symbol: str) -> Optional[dict]:
    """Get raw genesis data for a coin from the curated registry."""
    return GENESIS_REGISTRY.get(symbol.upper())


def list_supported_cryptos() -> List[str]:
    """Return sorted list of supported cryptocurrency symbols."""
    return sorted(GENESIS_REGISTRY.keys())


def list_registry_info() -> List[dict]:
    """Return summary info for all coins, sorted by genesis date."""
    return [
        {"symbol": k, "name": v["name"], "genesis_date": v["genesis_date"],
         "rectified": v["rectified"]}
        for k, v in sorted(GENESIS_REGISTRY.items(), key=lambda x: x[1]["genesis_date"])
    ]


def compute_crypto_chart(symbol: str = None, genesis_data: dict = None) -> dict:
    """
    Compute a FULL natal chart for a cryptocurrency using the Stellaris-13 engine.
    Same output as a human chart: all planets, minor bodies, aspects, angles, etc.

    Args:
        symbol: Look up from registry (e.g. "BTC")
        genesis_data: Or provide custom genesis data dict
    """
    from engine import compute_chart

    if symbol and not genesis_data:
        genesis_data = get_genesis_data(symbol)
        if not genesis_data:
            return {"error": f"Unknown symbol: {symbol}. Use list_supported_cryptos() or provide custom genesis_data."}

    if not genesis_data:
        return {"error": "Provide either a symbol or genesis_data dict."}

    date_parts = genesis_data["genesis_date"].split("-")
    time_parts = genesis_data.get("genesis_time", "00:00:00").split(":")

    year, month, day = int(date_parts[0]), int(date_parts[1]), int(date_parts[2])
    hour, minute = int(time_parts[0]), int(time_parts[1])
    second = int(float(time_parts[2])) if len(time_parts) > 2 else 0

    tz_offset = genesis_data.get("tz_offset", 0)
    lat = genesis_data.get("lat", 0.0)
    lon = genesis_data.get("lon", 0.0)
    name = genesis_data.get("name", genesis_data.get("symbol", "Unknown Coin"))

    chart = compute_chart(
        year=year, month=month, day=day,
        hour=hour, minute=minute, second=second,
        tz_offset=tz_offset, lat=lat, lon=lon,
        name=name
    )

    chart["crypto_meta"] = {
        "symbol": genesis_data.get("symbol", symbol or "CUSTOM"),
        "genesis_date": genesis_data["genesis_date"],
        "genesis_time": genesis_data.get("genesis_time", "00:00:00"),
        "source": genesis_data.get("source", "User provided"),
        "rectified": genesis_data.get("rectified", False),
        "notes": genesis_data.get("notes", ""),
        "location_note": "Null Island (0°N 0°E) — neutral house framework"
            if (lat == 0.0 and lon == 0.0) else f"Location: {lat}°N {lon}°E",
    }

    return chart


def compute_custom_crypto_chart(name: str, date: str, time: str = "00:00:00",
                                 tz_offset: float = 0, lat: float = 0.0,
                                 lon: float = 0.0, symbol: str = "CUSTOM") -> dict:
    """Convenience function for user-input custom coins."""
    genesis_data = {
        "name": name, "symbol": symbol.upper(),
        "genesis_date": date, "genesis_time": time,
        "tz_offset": tz_offset, "lat": lat, "lon": lon,
        "source": "User provided", "rectified": False,
    }
    return compute_crypto_chart(genesis_data=genesis_data)
