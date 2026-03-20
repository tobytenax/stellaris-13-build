"""
CRYPTO TRANSITS — Transit Engine with Temporal Precision

Calculates current transits to any cryptocurrency natal chart,
including EXACT dates when transits perfect and separate.

Uses Swiss Ephemeris forward-search to find exactitude windows,
providing the AI interpreter with specific dates and durations.
"""

import swisseph as swe
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
from crypto_natal import get_genesis_data, compute_crypto_chart


# ═══════════════════════════════════════════════════════════════════════════════
# ASPECT DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════════

ASPECTS = {
    "Conjunction": {"angle": 0,   "orb": 8,  "nature": "fusion",      "weight": 10},
    "Opposition":  {"angle": 180, "orb": 8,  "nature": "tension",     "weight": 8},
    "Square":      {"angle": 90,  "orb": 6,  "nature": "friction",    "weight": 7},
    "Trine":       {"angle": 120, "orb": 6,  "nature": "flow",        "weight": 6},
    "Sextile":     {"angle": 60,  "orb": 5,  "nature": "opportunity", "weight": 4},
}

PLANET_IDS = {
    "Sun": swe.SUN, "Moon": swe.MOON, "Mercury": swe.MERCURY,
    "Venus": swe.VENUS, "Mars": swe.MARS, "Jupiter": swe.JUPITER,
    "Saturn": swe.SATURN, "Uranus": swe.URANUS, "Neptune": swe.NEPTUNE,
    "Pluto": swe.PLUTO,
}

# Average daily motion in degrees (for estimating search windows)
PLANET_SPEEDS = {
    "Sun": 0.986, "Moon": 13.176, "Mercury": 1.383, "Venus": 1.200,
    "Mars": 0.524, "Jupiter": 0.083, "Saturn": 0.034, "Uranus": 0.012,
    "Neptune": 0.006, "Pluto": 0.004,
}

# How long effects last by planet speed class (in days, approximate)
EFFECT_DURATION = {
    "Sun": 7, "Moon": 1, "Mercury": 5, "Venus": 7,
    "Mars": 14, "Jupiter": 60, "Saturn": 90,
    "Uranus": 180, "Neptune": 365, "Pluto": 365,
}


# ═══════════════════════════════════════════════════════════════════════════════
# CORE ASPECT CALCULATION
# ═══════════════════════════════════════════════════════════════════════════════

def angular_distance(lon1: float, lon2: float) -> float:
    """Shortest angular distance between two longitudes."""
    diff = abs(lon1 - lon2)
    return min(diff, 360 - diff)


def check_aspect(transit_lon: float, natal_lon: float) -> Optional[Tuple[str, float]]:
    """Check if two longitudes form a major aspect. Returns (aspect_name, orb) or None."""
    diff = angular_distance(transit_lon, natal_lon)

    for name, data in ASPECTS.items():
        angle = data["angle"]
        max_orb = data["orb"]

        if angle == 0:
            orb = diff
        elif name == "Square":
            orb = min(abs(diff - 90), abs(diff - 270))
        elif name == "Trine":
            orb = min(abs(diff - 120), abs(diff - 240))
        elif name == "Sextile":
            orb = min(abs(diff - 60), abs(diff - 300))
        else:
            orb = abs(diff - angle)

        if orb <= max_orb:
            return (name, round(orb, 3))

    return None


def get_planet_longitude(jd: float, planet_name: str) -> float:
    """Get tropical longitude for a planet at a given Julian Day."""
    body_id = PLANET_IDS.get(planet_name)
    if body_id is None:
        return 0.0
    result = swe.calc_ut(jd, body_id)
    return result[0][0]


# ═══════════════════════════════════════════════════════════════════════════════
# EXACT TRANSIT DATE FINDER
# ═══════════════════════════════════════════════════════════════════════════════

def find_exact_transit_date(transit_planet: str, natal_lon: float, aspect_angle: float,
                            start_jd: float, search_days: int = 365,
                            direction: str = "forward") -> Optional[dict]:
    """
    Search forward (or backward) from start_jd to find when a transit planet
    reaches exact aspect to a natal longitude.

    Uses iterative refinement: coarse scan (1-day steps) then bisection.

    Returns dict with:
        exact_jd, exact_date (ISO string), orb_at_exact
    Or None if not found within search window.
    """
    body_id = PLANET_IDS.get(transit_planet)
    if body_id is None:
        return None

    step = 1.0 if direction == "forward" else -1.0
    best_jd = None
    best_orb = 999.0

    # Phase 1: coarse scan (1-day steps)
    jd = start_jd
    prev_diff = None
    for _ in range(search_days):
        lon = swe.calc_ut(jd, body_id)[0][0]
        diff = angular_distance(lon, natal_lon)

        # For non-conjunction aspects, measure distance from the target angle
        if aspect_angle == 0:
            orb = diff
        elif aspect_angle == 90:
            orb = min(abs(diff - 90), abs(diff - 270))
        elif aspect_angle == 120:
            orb = min(abs(diff - 120), abs(diff - 240))
        elif aspect_angle == 60:
            orb = min(abs(diff - 60), abs(diff - 300))
        else:
            orb = abs(diff - aspect_angle)

        if orb < best_orb:
            best_orb = orb
            best_jd = jd

        # Detect when we've passed through the minimum (orb starts increasing)
        if prev_diff is not None and orb > prev_diff + 0.5 and best_orb < 2.0:
            break

        prev_diff = orb
        jd += step

    if best_jd is None or best_orb > 10:
        return None

    # Phase 2: refine with bisection around best_jd (0.01-day precision ~ 15 min)
    lo = best_jd - 2
    hi = best_jd + 2
    for _ in range(20):
        mid = (lo + hi) / 2
        lon_lo = swe.calc_ut(lo, body_id)[0][0]
        lon_hi = swe.calc_ut(hi, body_id)[0][0]
        lon_mid = swe.calc_ut(mid, body_id)[0][0]

        if aspect_angle == 0:
            orb_lo = angular_distance(lon_lo, natal_lon)
            orb_hi = angular_distance(lon_hi, natal_lon)
            orb_mid = angular_distance(lon_mid, natal_lon)
        elif aspect_angle == 90:
            orb_lo = min(abs(angular_distance(lon_lo, natal_lon) - 90),
                        abs(angular_distance(lon_lo, natal_lon) - 270))
            orb_hi = min(abs(angular_distance(lon_hi, natal_lon) - 90),
                        abs(angular_distance(lon_hi, natal_lon) - 270))
            orb_mid = min(abs(angular_distance(lon_mid, natal_lon) - 90),
                         abs(angular_distance(lon_mid, natal_lon) - 270))
        elif aspect_angle == 120:
            orb_lo = min(abs(angular_distance(lon_lo, natal_lon) - 120),
                        abs(angular_distance(lon_lo, natal_lon) - 240))
            orb_hi = min(abs(angular_distance(lon_hi, natal_lon) - 120),
                        abs(angular_distance(lon_hi, natal_lon) - 240))
            orb_mid = min(abs(angular_distance(lon_mid, natal_lon) - 120),
                         abs(angular_distance(lon_mid, natal_lon) - 240))
        elif aspect_angle == 60:
            orb_lo = min(abs(angular_distance(lon_lo, natal_lon) - 60),
                        abs(angular_distance(lon_lo, natal_lon) - 300))
            orb_hi = min(abs(angular_distance(lon_hi, natal_lon) - 60),
                        abs(angular_distance(lon_hi, natal_lon) - 300))
            orb_mid = min(abs(angular_distance(lon_mid, natal_lon) - 60),
                         abs(angular_distance(lon_mid, natal_lon) - 300))
        else:
            orb_lo = abs(angular_distance(lon_lo, natal_lon) - aspect_angle)
            orb_hi = abs(angular_distance(lon_hi, natal_lon) - aspect_angle)
            orb_mid = abs(angular_distance(lon_mid, natal_lon) - aspect_angle)

        if orb_lo < orb_hi:
            hi = mid
        else:
            lo = mid

    exact_jd = (lo + hi) / 2
    exact_lon = swe.calc_ut(exact_jd, body_id)[0][0]

    if aspect_angle == 0:
        final_orb = angular_distance(exact_lon, natal_lon)
    elif aspect_angle == 90:
        final_orb = min(abs(angular_distance(exact_lon, natal_lon) - 90),
                       abs(angular_distance(exact_lon, natal_lon) - 270))
    elif aspect_angle == 120:
        final_orb = min(abs(angular_distance(exact_lon, natal_lon) - 120),
                       abs(angular_distance(exact_lon, natal_lon) - 240))
    elif aspect_angle == 60:
        final_orb = min(abs(angular_distance(exact_lon, natal_lon) - 60),
                       abs(angular_distance(exact_lon, natal_lon) - 300))
    else:
        final_orb = abs(angular_distance(exact_lon, natal_lon) - aspect_angle)

    # Convert JD to datetime
    year, month, day, hour_frac = swe.revjul(exact_jd)
    hour = int(hour_frac)
    minute = int((hour_frac - hour) * 60)
    exact_dt = datetime(year, month, day, hour, minute, tzinfo=timezone.utc)

    return {
        "exact_jd": exact_jd,
        "exact_date": exact_dt.strftime("%Y-%m-%d"),
        "exact_time": exact_dt.strftime("%H:%M UTC"),
        "exact_datetime_iso": exact_dt.isoformat(),
        "orb_at_exact": round(final_orb, 4),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN TRANSIT ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════

def get_current_transits(symbol: str = None, natal_chart: dict = None,
                         include_timing: bool = True) -> List[dict]:
    """
    Get current transits for a cryptocurrency with full temporal data.

    Args:
        symbol: Crypto symbol from registry (e.g. "BTC")
        natal_chart: Or provide a pre-computed natal chart
        include_timing: If True, search for exact dates (slower but richer)

    Returns:
        List of transit aspects with timing data
    """
    # Get or compute natal chart
    if not natal_chart:
        if not symbol:
            return []
        natal_chart = compute_crypto_chart(symbol)
        if "error" in natal_chart:
            return []

    # Current sky positions
    now = datetime.now(timezone.utc)
    now_jd = swe.julday(now.year, now.month, now.day,
                        now.hour + now.minute / 60.0)

    transit_positions = {}
    for planet_name, body_id in PLANET_IDS.items():
        result = swe.calc_ut(now_jd, body_id)
        transit_positions[planet_name] = result[0][0]

    # Extract natal longitudes
    natal_lons = {}
    for planet_name in PLANET_IDS:
        p = natal_chart.get("placements", {}).get(planet_name, {})
        lon = p.get("tropical_longitude")
        if lon is not None:
            natal_lons[planet_name] = lon

    # Find all aspects
    aspects = []
    for t_name, t_lon in transit_positions.items():
        for n_name, n_lon in natal_lons.items():
            result = check_aspect(t_lon, n_lon)
            if result:
                aspect_name, orb = result
                aspect_data = ASPECTS[aspect_name]
                significance = aspect_data["weight"] * (8 - orb)

                transit_info = {
                    "transiting": t_name,
                    "natal": n_name,
                    "aspect": aspect_name,
                    "orb": orb,
                    "nature": aspect_data["nature"],
                    "significance": round(significance, 1),
                    "applying": None,  # filled in below
                    "effect_duration_days": EFFECT_DURATION.get(t_name, 30),
                }

                # Determine if applying or separating
                # Check position 1 day ago
                yesterday_lon = get_planet_longitude(now_jd - 1, t_name)
                yesterday_orb = check_aspect(yesterday_lon, n_lon)
                if yesterday_orb:
                    transit_info["applying"] = yesterday_orb[1] > orb
                else:
                    transit_info["applying"] = True  # entering aspect

                # Find exact date and window
                if include_timing:
                    timing = compute_transit_timing(
                        t_name, n_lon, aspect_data["angle"], now_jd, orb
                    )
                    transit_info.update(timing)

                aspects.append(transit_info)

    # Sort by significance (tighter, heavier aspects first)
    aspects.sort(key=lambda x: -x["significance"])

    return aspects


def compute_transit_timing(transit_planet: str, natal_lon: float,
                           aspect_angle: float, now_jd: float,
                           current_orb: float) -> dict:
    """
    Compute the full timing window for a transit:
    - When it entered orb (became active)
    - When it goes exact (perfects)
    - When it separates (leaves orb)
    - Total duration of the transit window

    Returns dict of timing fields.
    """
    timing = {}
    max_orb = 8.0  # standard orb for activation

    # Search backward to find when it entered orb
    entered = find_exact_transit_date(
        transit_planet, natal_lon, aspect_angle,
        now_jd, search_days=365, direction="backward"
    )

    # Search forward to find next exact pass
    exact_forward = find_exact_transit_date(
        transit_planet, natal_lon, aspect_angle,
        now_jd, search_days=365, direction="forward"
    )

    # Also check if it was recently exact (search backward)
    exact_backward = find_exact_transit_date(
        transit_planet, natal_lon, aspect_angle,
        now_jd, search_days=180, direction="backward"
    )

    # Determine which exact date is most relevant
    if exact_backward and exact_forward:
        # Use whichever is closer to now
        back_dist = abs(now_jd - exact_backward["exact_jd"])
        fwd_dist = abs(exact_forward["exact_jd"] - now_jd)
        if back_dist < fwd_dist:
            timing["exact_date"] = exact_backward["exact_date"]
            timing["exact_time"] = exact_backward["exact_time"]
            timing["phase"] = "separating"
        else:
            timing["exact_date"] = exact_forward["exact_date"]
            timing["exact_time"] = exact_forward["exact_time"]
            timing["phase"] = "applying"
    elif exact_forward:
        timing["exact_date"] = exact_forward["exact_date"]
        timing["exact_time"] = exact_forward["exact_time"]
        timing["phase"] = "applying"
    elif exact_backward:
        timing["exact_date"] = exact_backward["exact_date"]
        timing["exact_time"] = exact_backward["exact_time"]
        timing["phase"] = "separating"
    else:
        timing["exact_date"] = "unknown"
        timing["exact_time"] = "unknown"
        timing["phase"] = "active"

    # Estimate window duration based on planet speed
    duration_days = EFFECT_DURATION.get(transit_planet, 30)
    timing["window_start"] = (
        datetime.now(timezone.utc) - timedelta(days=duration_days // 2)
    ).strftime("%Y-%m-%d")
    timing["window_end"] = (
        datetime.now(timezone.utc) + timedelta(days=duration_days // 2)
    ).strftime("%Y-%m-%d")
    timing["effect_duration_days"] = duration_days

    return timing


# ═══════════════════════════════════════════════════════════════════════════════
# COMPARISON & RANKING
# ═══════════════════════════════════════════════════════════════════════════════

def compare_crypto_transits(symbols: List[str]) -> dict:
    """
    Compare transit conditions across multiple coins.
    Returns ranked list with scores and timing.
    """
    results = {}
    rankings = []

    for symbol in symbols:
        transits = get_current_transits(symbol, include_timing=False)
        results[symbol] = transits

        score = 0
        for t in transits:
            weight = (8 - t["orb"])
            if t["nature"] in ("flow", "opportunity"):
                score += weight * 2
            elif t["nature"] in ("friction", "tension"):
                score -= weight * 1.5
            elif t["nature"] == "fusion":
                # Conjunction: depends on planet
                if t["transiting"] in ("Jupiter", "Venus", "Sun"):
                    score += weight * 2
                elif t["transiting"] in ("Saturn", "Pluto"):
                    score -= weight * 1.0
                # Uranus/Neptune are neutral magnitude

        rankings.append({
            "symbol": symbol,
            "score": round(score, 1),
            "transit_count": len(transits),
            "tightest": transits[0] if transits else None,
        })

    rankings.sort(key=lambda x: -x["score"])

    return {
        "analyses": results,
        "rankings": rankings,
        "recommendation": rankings[0]["symbol"] if rankings else None,
    }
