"""
CRYPTO SYNASTRY — Person-to-Coin Compatibility via Stellaris Engine

Uses the same synastry engine as human-to-human charts. The coin's natal chart
is computed from genesis data, then compared to the person's chart using
engine.compute_synastry() for aspect calculation.
"""

from typing import Dict, List, Optional
from crypto_natal import compute_crypto_chart, get_genesis_data, list_supported_cryptos

# ═══════════════════════════════════════════════════════════════════════════════
# SYNASTRY INTERPRETATION LIBRARY
# ═══════════════════════════════════════════════════════════════════════════════

SYNASTRY_THEMES = {
    ("Sun", "Sun"): {"theme": "IDENTITY FUSION", "harmonious": "Core identity resonates with this coin's purpose.", "challenging": "Identity conflicts with what this coin represents."},
    ("Sun", "Jupiter"): {"theme": "EXPANSION ALIGNMENT", "harmonious": "This coin expands your sense of self. Growth feels natural.", "challenging": "Growth principle challenges your identity. Overextension risk."},
    ("Sun", "Saturn"): {"theme": "DISCIPLINE DYNAMIC", "harmonious": "This coin teaches you patience. Structured growth.", "challenging": "This coin restricts your expression."},
    ("Sun", "Uranus"): {"theme": "REVOLUTIONARY RESONANCE", "harmonious": "This coin liberates something in you.", "challenging": "This coin disrupts your sense of self. Expect volatility."},
    ("Moon", "Moon"): {"theme": "EMOTIONAL ATTUNEMENT", "harmonious": "You intuitively understand this coin's rhythms.", "challenging": "Your instincts and the coin's nature conflict."},
    ("Moon", "Jupiter"): {"theme": "INTUITIVE EXPANSION", "harmonious": "Your gut says grow with this coin.", "challenging": "Emotional overconfidence risk."},
    ("Jupiter", "Jupiter"): {"theme": "EXPANSION RESONANCE", "harmonious": "Your growth cycles align.", "challenging": "Growth mismatch."},
    ("Jupiter", "Saturn"): {"theme": "EXPANSION VS RESTRICTION", "harmonious": "Structured growth. Optimism meets discipline.", "challenging": "Growth impulse restricted. Frustration likely."},
    ("Venus", "Venus"): {"theme": "VALUE RESONANCE", "harmonious": "You value what this coin values.", "challenging": "Value mismatch. You'll misjudge its worth."},
    ("Venus", "Neptune"): {"theme": "VALUE-ILLUSION", "harmonious": "Visionary value perception.", "challenging": "You may be deceived about this coin's value."},
    ("Mars", "Mars"): {"theme": "ACTION ALIGNMENT", "harmonious": "Action style matches the coin's energy.", "challenging": "Likely to over-trade."},
    ("Uranus", "Uranus"): {"theme": "GENERATIONAL RESONANCE", "harmonious": "Same revolutionary frequency.", "challenging": "Misaligned innovation."},
    ("Pluto", "Sun"): {"theme": "TRANSFORMATIVE POWER", "harmonious": "This coin transforms your identity.", "challenging": "Power struggles with this coin."},
    ("Neptune", "Neptune"): {"theme": "COLLECTIVE DREAM", "harmonious": "Shared vision.", "challenging": "Mutual confusion."},
}

HARMONIOUS_ASPECTS = {"Trine", "Sextile"}
CHALLENGING_ASPECTS = {"Square", "Opposition"}


def get_theme(planet1: str, planet2: str, aspect: str) -> dict:
    """Get interpretation theme for a synastry aspect."""
    key = (planet1, planet2)
    if key not in SYNASTRY_THEMES:
        key = (planet2, planet1)

    if key in SYNASTRY_THEMES:
        data = SYNASTRY_THEMES[key]
        nature = "harmonious" if aspect in HARMONIOUS_ASPECTS else "challenging"
        if aspect == "Conjunction":
            nature = "harmonious" if planet1 in ("Jupiter", "Venus") or planet2 in ("Jupiter", "Venus") else "fused"
        return {
            "theme": data["theme"],
            "interpretation": data.get(nature, data.get("harmonious", "Significant connection.")),
            "nature": nature,
        }

    return {
        "theme": f"{planet1}-{planet2} CONNECTION",
        "interpretation": f"{planet1} and {planet2} are linked.",
        "nature": "harmonious" if aspect in HARMONIOUS_ASPECTS else "challenging",
    }


# ═══════════════════════════════════════════════════════════════════════════════
# CORE SYNASTRY — uses engine.compute_synastry
# ═══════════════════════════════════════════════════════════════════════════════

def analyze_natal_synastry(person_chart: dict, crypto_symbol: str = None,
                           crypto_chart: dict = None) -> dict:
    """
    Analyze natal synastry between a person and a cryptocurrency.

    Args:
        person_chart: Person's full chart (from engine.compute_chart)
        crypto_symbol: Crypto symbol to look up and compute
        crypto_chart: Or provide a pre-computed crypto chart

    Both person_chart and crypto_chart should be full engine output dicts
    with 'placements' containing 'tropical_longitude' keys.

    Also accepts legacy format where person_chart is {planet: longitude} dict.
    """
    from engine import compute_synastry

    # Get or compute crypto chart
    if not crypto_chart:
        if not crypto_symbol:
            return {"error": "Provide either crypto_symbol or crypto_chart"}
        crypto_chart = compute_crypto_chart(crypto_symbol)
        if "error" in crypto_chart:
            return crypto_chart

    # Handle legacy format: person_chart might be {planet: longitude}
    if "placements" not in person_chart:
        # Convert flat {planet: lon} to engine format
        person_chart = _convert_legacy_planets(person_chart)

    # Use engine's synastry calculation
    raw_aspects = compute_synastry(person_chart, crypto_chart)

    # Enrich with interpretations
    aspects = []
    for a in raw_aspects:
        interp = get_theme(a["body1"], a["body2"], a["aspect"])
        aspects.append({
            "person_planet": a["body1"],
            "crypto_planet": a["body2"],
            "aspect": a["aspect"],
            "orb": a["orb"],
            "theme": interp["theme"],
            "interpretation": interp["interpretation"],
            "nature": interp["nature"],
        })

    # Categorize
    harmonious = [a for a in aspects if a["nature"] == "harmonious"]
    challenging = [a for a in aspects if a["nature"] == "challenging"]

    # Score
    score = 0
    for a in aspects:
        weight = (8 - a["orb"])
        if a["nature"] == "harmonious":
            score += weight * 2
        elif a["nature"] == "challenging":
            score -= weight * 1.5

    # Compatibility label
    crypto_name = crypto_chart.get("name", crypto_symbol or "coin")
    if score > 20:
        compatibility = "STRONG AFFINITY"
        summary = f"You and {crypto_name} are natally well-matched."
    elif score > 5:
        compatibility = "MODERATE AFFINITY"
        summary = f"Mixed signals with {crypto_name}. Some resonance, some friction."
    elif score > -10:
        compatibility = "NEUTRAL"
        summary = f"No strong pull either way with {crypto_name}."
    else:
        compatibility = "CHALLENGING"
        summary = f"Natal friction with {crypto_name}. This coin may test you."

    return {
        "crypto": crypto_symbol or crypto_chart.get("crypto_meta", {}).get("symbol", "CUSTOM"),
        "crypto_name": crypto_name,
        "compatibility": compatibility,
        "score": round(score, 1),
        "summary": summary,
        "all_aspects": aspects[:15],
        "harmonious": harmonious[:5],
        "challenging": challenging[:5],
        "key_aspect": aspects[0] if aspects else None,
    }


def analyze_transit_synastry(person_chart: dict, crypto_symbol: str,
                             transit_positions: dict = None) -> dict:
    """
    Analyze how current transits activate the person-crypto relationship.

    Args:
        person_chart: Person's chart (full or legacy {planet: lon})
        crypto_symbol: Crypto symbol
        transit_positions: Current sky positions {planet: lon} (computed if None)
    """
    import swisseph as swe
    from datetime import datetime, timezone

    crypto_chart = compute_crypto_chart(crypto_symbol)
    if "error" in crypto_chart:
        return crypto_chart

    # Get current sky if not provided
    if not transit_positions:
        now = datetime.now(timezone.utc)
        now_jd = swe.julday(now.year, now.month, now.day,
                            now.hour + now.minute / 60.0)
        transit_positions = {}
        planet_ids = {
            "Sun": swe.SUN, "Moon": swe.MOON, "Mercury": swe.MERCURY,
            "Venus": swe.VENUS, "Mars": swe.MARS, "Jupiter": swe.JUPITER,
            "Saturn": swe.SATURN, "Uranus": swe.URANUS, "Neptune": swe.NEPTUNE,
            "Pluto": swe.PLUTO,
        }
        for name, body_id in planet_ids.items():
            transit_positions[name] = swe.calc_ut(now_jd, body_id)[0][0]

    # Extract person's natal longitudes
    person_lons = _extract_longitudes(person_chart)
    crypto_lons = _extract_longitudes(crypto_chart)

    from crypto_transits import check_aspect

    # Transits to person
    person_transits = []
    for tr_name, tr_lon in transit_positions.items():
        for p_name, p_lon in person_lons.items():
            result = check_aspect(tr_lon, p_lon)
            if result and result[1] <= 5:  # tighter orb for transit synastry
                person_transits.append({
                    "transit": tr_name, "natal": p_name,
                    "aspect": result[0], "orb": result[1],
                    "nature": "beneficial" if result[0] in HARMONIOUS_ASPECTS
                             else ("challenging" if result[0] in CHALLENGING_ASPECTS
                                   else "activating"),
                })

    # Transits to crypto
    crypto_transits = []
    for tr_name, tr_lon in transit_positions.items():
        for c_name, c_lon in crypto_lons.items():
            result = check_aspect(tr_lon, c_lon)
            if result and result[1] <= 5:
                crypto_transits.append({
                    "transit": tr_name, "natal": c_name,
                    "aspect": result[0], "orb": result[1],
                    "nature": "beneficial" if result[0] in HARMONIOUS_ASPECTS
                             else ("challenging" if result[0] in CHALLENGING_ASPECTS
                                   else "activating"),
                })

    person_transits.sort(key=lambda x: x["orb"])
    crypto_transits.sort(key=lambda x: x["orb"])

    p_beneficial = [t for t in person_transits if t["nature"] == "beneficial"]
    p_challenging = [t for t in person_transits if t["nature"] == "challenging"]
    c_beneficial = [t for t in crypto_transits if t["nature"] == "beneficial"]
    c_challenging = [t for t in crypto_transits if t["nature"] == "challenging"]

    p_score = len(p_beneficial) * 2 - len(p_challenging) * 1.5
    c_score = len(c_beneficial) * 2 - len(c_challenging) * 1.5

    if p_score > 2 and c_score > 2:
        alignment = "DOUBLE ACTIVATION"
        message = f"Your window AND {crypto_symbol}'s window are BOTH active. Green light."
    elif p_score > 2 and c_score < -2:
        alignment = "MISMATCH — YOU'RE HOT, COIN'S NOT"
        message = f"You feel expansive, but {crypto_symbol} is under pressure."
    elif p_score < -2 and c_score > 2:
        alignment = "MISMATCH — COIN'S HOT, YOU'RE NOT"
        message = f"{crypto_symbol} is in a good window, but your timing is off."
    elif p_score < -2 and c_score < -2:
        alignment = "DOUBLE CHALLENGE"
        message = f"Both you AND {crypto_symbol} are under challenging transits. Not the time."
    else:
        alignment = "NEUTRAL"
        message = "Mixed signals. No strong push either direction."

    return {
        "crypto": crypto_symbol,
        "alignment": alignment,
        "message": message,
        "person_transits": {"all": person_transits[:8], "beneficial": p_beneficial[:4],
                            "challenging": p_challenging[:4], "score": p_score},
        "crypto_transits": {"all": crypto_transits[:8], "beneficial": c_beneficial[:4],
                            "challenging": c_challenging[:4], "score": c_score},
    }


def compare_synastry(person_chart: dict, crypto_symbols: List[str],
                     transit_positions: dict = None) -> dict:
    """Compare synastry across multiple cryptos for one person."""
    rankings = []
    for symbol in crypto_symbols:
        natal = analyze_natal_synastry(person_chart, symbol)
        transit = analyze_transit_synastry(person_chart, symbol, transit_positions)
        combined = natal.get("score", 0) * 0.3 + (
            transit.get("person_transits", {}).get("score", 0) +
            transit.get("crypto_transits", {}).get("score", 0)
        ) * 0.7
        rankings.append({
            "symbol": symbol, "natal_score": natal.get("score", 0),
            "transit_score": transit.get("person_transits", {}).get("score", 0) +
                            transit.get("crypto_transits", {}).get("score", 0),
            "combined_score": round(combined, 1),
            "compatibility": natal.get("compatibility", "NEUTRAL"),
            "alignment": transit.get("alignment", "NEUTRAL"),
        })

    rankings.sort(key=lambda x: -x["combined_score"])
    best = rankings[0] if rankings else None

    return {
        "rankings": rankings,
        "recommendation": f"{best['symbol']} — Clear synastry advantage."
            if best and best["combined_score"] > 5
            else "No coin shows strong advantage. Consider waiting.",
        "best_fit": best["symbol"] if best else None,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _extract_longitudes(chart: dict) -> dict:
    """Extract {planet: longitude} from either engine chart or flat dict."""
    if "placements" in chart:
        result = {}
        for planet in ["Sun", "Moon", "Mercury", "Venus", "Mars",
                       "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"]:
            p = chart["placements"].get(planet, {})
            lon = p.get("tropical_longitude")
            if lon is not None:
                result[planet] = lon
        return result
    else:
        # Already flat {planet: lon}
        return chart


def _convert_legacy_planets(flat_dict: dict) -> dict:
    """Convert {planet: longitude} to engine-compatible chart structure."""
    placements = {}
    for planet, lon in flat_dict.items():
        placements[planet] = {"tropical_longitude": lon}
    return {"placements": placements, "name": "Person"}
