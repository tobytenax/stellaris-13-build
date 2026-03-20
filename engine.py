"""
Stellaris-13 Ephemeris Engine v2.4
Dual-method 13-sign astronomical chart calculator.

FIXED IN v2.4:
- Unified calculation method between CLI and GUI (precession-corrected IAU boundaries)
- Both "Standard 13-Sign" and "IAU" methods now use consistent astronomy
- Standard method: Community date-table mapping (as before)
- IAU method: Now matches CLI with precession correction

Method 1 — Standard 13-Sign:
  Maps tropical longitude to constellation date ranges. This is the 
  community-accepted method that most 13-sign astrologers use.

Method 2 — IAU Astronomical (with precession correction):
  Uses J2000.0 IAU boundaries with precession correction applied.
  This matches the CLI ephemeris_13sign.py calculations exactly.
"""

import swisseph as swe
import math
from typing import Optional, Tuple, List, Dict
from datetime import datetime, timezone, timedelta

# ═══════════════════════════════════════════════════════════════
# METHOD 1: STANDARD 13-SIGN (COMMUNITY DATE TABLE)
# ═══════════════════════════════════════════════════════════════
# Tropical longitude boundaries derived from the 13-sign date table.

STANDARD_BOUNDARIES = [
    (28.75,  "Aries",        "Ari", "♈"),   # ~Apr 18 - May 13
    (53.02,  "Taurus",       "Tau", "♉"),   # ~May 13 - Jun 21
    (90.41,  "Gemini",       "Gem", "♊"),   # ~Jun 21 - Jul 20
    (118.06, "Cancer",       "Cnc", "♋"),   # ~Jul 20 - Aug 10
    (138.15, "Leo",          "Leo", "♌"),   # ~Aug 10 - Sep 16
    (173.92, "Virgo",        "Vir", "♍"),   # ~Sep 16 - Oct 30
    (217.37, "Libra",        "Lib", "♎"),   # ~Oct 30 - Nov 23
    (241.50, "Scorpio",      "Sco", "♏"),   # ~Nov 23 - Nov 29  (6 days!)
    (247.58, "Ophiuchus",    "Oph", "⛎"),   # ~Nov 29 - Dec 17
    (265.86, "Sagittarius",  "Sgr", "♐"),   # ~Dec 17 - Jan 20
    (299.73, "Capricorn",    "Cap", "♑"),   # ~Jan 20 - Feb 16
    (327.12, "Aquarius",     "Aqr", "♒"),   # ~Feb 16 - Mar 11
    (351.22, "Pisces",       "Psc", "♓"),   # ~Mar 11 - Apr 18
]


def get_standard_constellation(tropical_lon: float, jd: float) -> Tuple[str, str, str, float]:
    """
    Standard 13-sign method: map tropical longitude directly to the
    constellation boundaries derived from the 13-sign date table.
    """
    lon = tropical_lon % 360.0
    
    for i in range(len(STANDARD_BOUNDARIES)):
        start = STANDARD_BOUNDARIES[i][0]
        next_start = STANDARD_BOUNDARIES[(i + 1) % len(STANDARD_BOUNDARIES)][0]
        name = STANDARD_BOUNDARIES[i][1]
        abbr = STANDARD_BOUNDARIES[i][2]
        sym = STANDARD_BOUNDARIES[i][3]
        
        if next_start > start:
            if start <= lon < next_start:
                return name, abbr, sym, lon - start
        else:
            if lon >= start or lon < next_start:
                deg = lon - start if lon >= start else (360 - start) + lon
                return name, abbr, sym, deg
    
    return "Unknown", "???", "?", 0.0


# ═══════════════════════════════════════════════════════════════
# METHOD 2: IAU ASTRONOMICAL (PRECESSION-CORRECTED)
# ═══════════════════════════════════════════════════════════════
# J2000.0 IAU ecliptic longitude boundaries with precession correction.
# THIS NOW MATCHES THE CLI ephemeris_13sign.py EXACTLY.

IAU_BOUNDARIES_J2000 = [
    (28.69,   "Aries",        "Ari", "♈"),
    (53.47,   "Taurus",       "Tau", "♉"),
    (90.42,   "Gemini",       "Gem", "♊"),
    (118.10,  "Cancer",       "Cnc", "♋"),
    (138.17,  "Leo",          "Leo", "♌"),
    (174.13,  "Virgo",        "Vir", "♍"),
    (217.82,  "Libra",        "Lib", "♎"),
    (241.09,  "Scorpius",     "Sco", "♏"),
    (247.68,  "Ophiuchus",    "Oph", "⛎"),
    (266.60,  "Sagittarius",  "Sgr", "♐"),
    (299.69,  "Capricornus",  "Cap", "♑"),
    (327.76,  "Aquarius",     "Aqr", "♒"),
    (351.57,  "Pisces",       "Psc", "♓"),
]


def get_precession_correction(jd: float) -> float:
    """
    Compute precession correction in degrees from J2000.0.
    The IAU boundaries shift in tropical longitude by ~50.29"/year.
    """
    j2000 = 2451545.0  # Jan 1, 2000, 12:00 TT
    years_from_j2000 = (jd - j2000) / 365.25
    return years_from_j2000 * (50.29 / 3600.0)  # Convert arcsec to degrees


def get_iau_constellation(tropical_lon: float, tropical_lat: float, jd: float) -> Tuple[str, str, str, float]:
    """
    IAU astronomical method with precession correction.
    Now matches CLI ephemeris_13sign.py calculations exactly.
    
    Returns: (name, abbreviation, symbol, degree_within_constellation)
    """
    precession = get_precession_correction(jd)
    
    # Adjust boundaries for precession
    boundaries = []
    for start, name, abbr, sym in IAU_BOUNDARIES_J2000:
        adjusted = (start + precession) % 360
        boundaries.append((adjusted, name, abbr, sym))
    
    # Sort by adjusted longitude
    boundaries.sort(key=lambda x: x[0])
    
    lon = tropical_lon % 360.0
    
    for i in range(len(boundaries)):
        current_start = boundaries[i][0]
        next_start = boundaries[(i + 1) % len(boundaries)][0]
        
        if next_start > current_start:
            if current_start <= lon < next_start:
                deg_in = lon - current_start
                return boundaries[i][1], boundaries[i][2], boundaries[i][3], deg_in
        else:
            if lon >= current_start or lon < next_start:
                if lon >= current_start:
                    deg_in = lon - current_start
                else:
                    deg_in = (360 - current_start) + lon
                return boundaries[i][1], boundaries[i][2], boundaries[i][3], deg_in
    
    return "Unknown", "???", "?", 0.0


def get_iau_span(constellation: str) -> float:
    """Approximate ecliptic span in degrees for each IAU constellation."""
    spans = {
        "Aries": 25.0, "Taurus": 37.0, "Gemini": 28.0, "Cancer": 20.0,
        "Leo": 36.0, "Virgo": 44.0, "Libra": 21.0, "Scorpius": 7.0,
        "Ophiuchus": 18.5, "Sagittarius": 34.0, "Capricornus": 28.0,
        "Aquarius": 24.0, "Pisces": 37.0,
    }
    return spans.get(constellation, 30.0)


# ═══════════════════════════════════════════════════════════════
# SWISS EPHEMERIS PLANET COMPUTATION
# ═══════════════════════════════════════════════════════════════

PLANETS = {
    'Sun': swe.SUN, 'Moon': swe.MOON, 'Mercury': swe.MERCURY,
    'Venus': swe.VENUS, 'Mars': swe.MARS, 'Jupiter': swe.JUPITER,
    'Saturn': swe.SATURN, 'Uranus': swe.URANUS, 'Neptune': swe.NEPTUNE,
    'Pluto': swe.PLUTO,
}

MINOR_BODIES = {
    'Chiron': swe.CHIRON,
    'Ceres': swe.AST_OFFSET + 1,
    'Pallas': swe.AST_OFFSET + 2,
    'Juno': swe.AST_OFFSET + 3,
    'Vesta': swe.AST_OFFSET + 4,
}

TROPICAL_SIGNS = ['Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo',
                  'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces']

TROPICAL_SYMBOLS = ['♈', '♉', '♊', '♋', '♌', '♍', '♎', '♏', '♐', '♑', '♒', '♓']


def format_dms(deg: float) -> str:
    d = int(deg)
    m = int((deg - d) * 60)
    return f"{d}°{m:02d}'"


def get_tropical(lon: float) -> Tuple[str, str, float]:
    """Get tropical sign name, symbol, and degree within sign."""
    idx = int(lon / 30) % 12
    return TROPICAL_SIGNS[idx], TROPICAL_SYMBOLS[idx], lon - (idx * 30)


def is_retrograde(jd: float, body_id: int) -> bool:
    try:
        result = swe.calc_ut(jd, body_id, swe.FLG_SPEED)
        return result[0][3] < 0
    except:
        return False


def compute_chart(year, month, day, hour, minute, second, tz_offset, lat, lon, name="Chart"):
    """
    Compute a full chart with both 13-sign methods.
    """
    # Convert to UTC
    hour_utc = hour + minute / 60.0 + second / 3600.0 - tz_offset
    day_adj = day
    if hour_utc >= 24:
        hour_utc -= 24
        day_adj += 1
    elif hour_utc < 0:
        hour_utc += 24
        day_adj -= 1
    
    jd = swe.julday(year, month, day_adj, hour_utc)
    
    # Get ayanamsa for display
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    ayanamsa = swe.get_ayanamsa_ut(jd)
    
    # Compute houses
    cusps, ascmc = swe.houses(jd, lat, lon, b'W')
    asc_lon = ascmc[0]
    mc_lon = ascmc[1]
    
    # Determine sect (day/night)
    sun_result = swe.calc_ut(jd, swe.SUN)
    sun_lon = sun_result[0][0]
    asc_sign = int(asc_lon / 30)
    sun_sign = int(sun_lon / 30)
    sun_house = ((sun_sign - asc_sign) % 12) + 1
    is_day = sun_house >= 7
    
    # Compute all bodies
    placements = {}
    all_bodies = {**PLANETS, **MINOR_BODIES, 'North Node': swe.TRUE_NODE}
    
    for body_name, body_id in all_bodies.items():
        try:
            result = swe.calc_ut(jd, body_id)
            trop_lon = result[0][0]
            trop_lat = result[0][1]
            retro = is_retrograde(jd, body_id)
            
            trop_sign, trop_sym, trop_deg = get_tropical(trop_lon)
            
            # Standard 13-sign (community method)
            std_name, std_abbr, std_sym, std_deg = get_standard_constellation(trop_lon, jd)
            
            # IAU astronomical (precession-corrected - matches CLI)
            iau_name, iau_abbr, iau_sym, iau_deg = get_iau_constellation(trop_lon, trop_lat, jd)
            
            # House
            body_sign = int(trop_lon / 30)
            house = ((body_sign - asc_sign) % 12) + 1
            
            placements[body_name] = {
                'tropical_longitude': trop_lon,
                'tropical_sign': trop_sign,
                'tropical_symbol': trop_sym,
                'tropical_degree': trop_deg,
                'standard_constellation': std_name,
                'standard_abbr': std_abbr,
                'standard_symbol': std_sym,
                'standard_degree': std_deg,
                'iau_constellation': iau_name,
                'iau_abbr': iau_abbr,
                'iau_symbol': iau_sym,
                'iau_degree': iau_deg,
                'house': house,
                'retrograde': retro,
            }
        except Exception as e:
            pass
    
    # South Node
    if 'North Node' in placements:
        nn = placements['North Node']
        sn_lon = (nn['tropical_longitude'] + 180) % 360
        sn_lat = -nn.get('tropical_lat', 0)
        trop_sign, trop_sym, trop_deg = get_tropical(sn_lon)
        std_name, std_abbr, std_sym, std_deg = get_standard_constellation(sn_lon, jd)
        iau_name, iau_abbr, iau_sym, iau_deg = get_iau_constellation(sn_lon, 0, jd)
        body_sign = int(sn_lon / 30)
        house = ((body_sign - asc_sign) % 12) + 1
        placements['South Node'] = {
            'tropical_longitude': sn_lon,
            'tropical_sign': trop_sign,
            'tropical_symbol': trop_sym,
            'tropical_degree': trop_deg,
            'standard_constellation': std_name,
            'standard_abbr': std_abbr,
            'standard_symbol': std_sym,
            'standard_degree': std_deg,
            'iau_constellation': iau_name,
            'iau_abbr': iau_abbr,
            'iau_symbol': iau_sym,
            'iau_degree': iau_deg,
            'house': house,
            'retrograde': False,
        }
    
    # Computed points: Lilith, Pars Fortuna, Part of Spirit, East Point
    moon_lon = placements['Moon']['tropical_longitude'] if 'Moon' in placements else 0
    
    extra_points = {}
    
    # Lilith (Mean Apogee)
    try:
        lil = swe.calc_ut(jd, swe.MEAN_APOG)
        extra_points['Lilith'] = lil[0][0]
    except:
        pass
    
    # Pars Fortuna
    if is_day:
        pf = (asc_lon + moon_lon - sun_lon) % 360
    else:
        pf = (asc_lon + sun_lon - moon_lon) % 360
    extra_points['Pars Fortuna'] = pf
    
    # Part of Spirit
    if is_day:
        ps = (asc_lon + sun_lon - moon_lon) % 360
    else:
        ps = (asc_lon + moon_lon - sun_lon) % 360
    extra_points['Part of Spirit'] = ps
    
    # East Point
    try:
        ep_cusps, ep_ascmc = swe.houses(jd, 0.0, lon, b'W')
        extra_points['East Point'] = ep_ascmc[0]
    except:
        pass
    
    for point_name, point_lon in extra_points.items():
        trop_sign, trop_sym, trop_deg = get_tropical(point_lon)
        std_name, std_abbr, std_sym, std_deg = get_standard_constellation(point_lon, jd)
        iau_name, iau_abbr, iau_sym, iau_deg = get_iau_constellation(point_lon, 0, jd)
        body_sign = int(point_lon / 30)
        house = ((body_sign - asc_sign) % 12) + 1
        placements[point_name] = {
            'tropical_longitude': point_lon,
            'tropical_sign': trop_sign,
            'tropical_symbol': trop_sym,
            'tropical_degree': trop_deg,
            'standard_constellation': std_name,
            'standard_abbr': std_abbr,
            'standard_symbol': std_sym,
            'standard_degree': std_deg,
            'iau_constellation': iau_name,
            'iau_abbr': iau_abbr,
            'iau_symbol': iau_sym,
            'iau_degree': iau_deg,
            'house': house,
            'retrograde': False,
        }
    
    # Angles
    angles = {}
    for angle_name, angle_lon in [('Ascendant', asc_lon), ('MC', mc_lon),
                                    ('Descendant', (asc_lon+180)%360),
                                    ('IC', (mc_lon+180)%360)]:
        trop_sign, trop_sym, trop_deg = get_tropical(angle_lon)
        std_name, std_abbr, std_sym, std_deg = get_standard_constellation(angle_lon, jd)
        iau_name, iau_abbr, iau_sym, iau_deg = get_iau_constellation(angle_lon, 0, jd)
        angles[angle_name] = {
            'tropical_longitude': angle_lon,
            'tropical_sign': trop_sign,
            'tropical_symbol': trop_sym,
            'tropical_degree': trop_deg,
            'standard_constellation': std_name,
            'standard_abbr': std_abbr,
            'standard_symbol': std_sym,
            'standard_degree': std_deg,
            'iau_constellation': iau_name,
            'iau_abbr': iau_abbr,
            'iau_symbol': iau_sym,
            'iau_degree': iau_deg,
        }
    
    # Compute aspects
    aspects = compute_aspects(placements)
    
    # Compute syzygy
    syzygy = compute_syzygy(jd, lat, lon)
    
    return {
        'name': name,
        'birth_data': {
            'year': year, 'month': month, 'day': day,
            'hour': hour, 'minute': minute, 'second': second,
            'tz_offset': tz_offset, 'lat': lat, 'lon': lon,
            'julian_day': jd, 'ayanamsa': round(ayanamsa, 4),
        },
        'sect': 'Day' if is_day else 'Night',
        'placements': placements,
        'angles': angles,
        'aspects': aspects,
        'syzygy': syzygy,
    }


def compute_aspects(placements: dict) -> list:
    """Compute all inter-body aspects."""
    ASPECT_DEFS = [
        ("Conjunction",     "CON", 0,    8.0),
        ("Opposition",      "OPP", 180,  8.0),
        ("Trine",          "TRI", 120,  8.0),
        ("Square",         "SQR", 90,   8.0),
        ("Sextile",        "SEX", 60,   6.0),
        ("Quincunx",       "QUI", 150,  5.0),
        ("Semisextile",    "SSX", 30,   3.0),
        ("Semisquare",     "SSQ", 45,   3.0),
        ("Sesquiquadrate", "SQQ", 135,  3.0),
    ]
    
    bodies = list(placements.keys())
    aspects = []
    
    for i in range(len(bodies)):
        for j in range(i + 1, len(bodies)):
            lon1 = placements[bodies[i]]['tropical_longitude']
            lon2 = placements[bodies[j]]['tropical_longitude']
            diff = abs(lon1 - lon2)
            if diff > 180:
                diff = 360 - diff
            
            for asp_name, asp_abbr, asp_angle, max_orb in ASPECT_DEFS:
                orb = abs(diff - asp_angle)
                if orb <= max_orb:
                    aspects.append({
                        'body1': bodies[i],
                        'body2': bodies[j],
                        'aspect': asp_name,
                        'abbr': asp_abbr,
                        'orb': round(orb, 2),
                    })
                    break
    
    # Filter: North Node opposing South Node is a mathematical identity, not an aspect
    aspects = [a for a in aspects
               if not (frozenset({a['body1'], a['body2']}) == frozenset({'North Node', 'South Node'}))]
    
    aspects.sort(key=lambda x: x['orb'])
    return aspects


def compute_syzygy(jd: float, lat: float, lon: float) -> dict:
    """Compute the prenatal syzygy (most recent New Moon or Full Moon before birth)."""
    search_jd = jd
    
    for _ in range(60):
        search_jd -= 0.5
        s = swe.calc_ut(search_jd, swe.SUN)[0][0]
        m = swe.calc_ut(search_jd, swe.MOON)[0][0]
        diff = (m - s) % 360
        
        if diff < 5 or diff > 355:
            found_type = 'New Moon'
            break
        if 175 < diff < 185:
            found_type = 'Full Moon'
            break
    else:
        return None
    
    # Refine
    low_jd = search_jd
    high_jd = search_jd + 0.5
    
    for _ in range(20):
        mid_jd = (low_jd + high_jd) / 2
        s = swe.calc_ut(mid_jd, swe.SUN)[0][0]
        m = swe.calc_ut(mid_jd, swe.MOON)[0][0]
        d = (m - s) % 360
        
        if found_type == 'New Moon':
            if d > 180:
                high_jd = mid_jd
            else:
                low_jd = mid_jd
        else:
            if d > 180:
                low_jd = mid_jd
            else:
                high_jd = mid_jd
    
    syzygy_jd = (low_jd + high_jd) / 2
    s_lon = swe.calc_ut(syzygy_jd, swe.SUN)[0][0]
    m_lon = swe.calc_ut(syzygy_jd, swe.MOON)[0][0]
    syz_lon = s_lon
    
    year, month, day, hour = swe.revjul(syzygy_jd)
    trop_sign, trop_sym, trop_deg = get_tropical(syz_lon)
    std_name, std_abbr, std_sym, std_deg = get_standard_constellation(syz_lon, syzygy_jd)
    iau_name, iau_abbr, iau_sym, iau_deg = get_iau_constellation(syz_lon, 0, syzygy_jd)
    
    return {
        'type': found_type,
        'julian_day': syzygy_jd,
        'year': year, 'month': month, 'day': int(day), 'hour': hour,
        'sun_longitude': s_lon, 'moon_longitude': m_lon,
        'tropical_sign': trop_sign, 'tropical_symbol': trop_sym, 'tropical_degree': trop_deg,
        'standard_constellation': std_name, 'standard_symbol': std_sym, 'standard_degree': std_deg,
        'iau_constellation': iau_name, 'iau_symbol': iau_sym, 'iau_degree': iau_deg,
    }


def compute_synastry(chart1: dict, chart2: dict) -> list:
    """Compute synastry aspects between two charts."""
    ASPECT_DEFS = [
        ("Conjunction", "CON", 0, 8.0),
        ("Opposition", "OPP", 180, 8.0),
        ("Trine", "TRI", 120, 8.0),
        ("Square", "SQR", 90, 8.0),
        ("Sextile", "SEX", 60, 6.0),
        ("Quincunx", "QUI", 150, 5.0),
    ]
    
    aspects = []
    
    for b1, p1 in chart1.get('placements', {}).items():
        for b2, p2 in chart2.get('placements', {}).items():
            lon1 = p1['tropical_longitude']
            lon2 = p2['tropical_longitude']
            diff = abs(lon1 - lon2)
            if diff > 180:
                diff = 360 - diff
            
            for asp_name, asp_abbr, asp_angle, max_orb in ASPECT_DEFS:
                orb = abs(diff - asp_angle)
                if orb <= max_orb:
                    aspects.append({
                        'body1': b1,
                        'body2': b2,
                        'chart1': chart1.get('name', 'A'),
                        'chart2': chart2.get('name', 'B'),
                        'aspect': asp_name,
                        'abbr': asp_abbr,
                        'orb': round(orb, 2),
                    })
                    break
    
    aspects.sort(key=lambda x: x['orb'])
    # Filter trivial: same-person North/South Node opposition is mathematical, not synastric
    aspects = [a for a in aspects
               if not (a['body1'] in ('North Node','South Node') and a['body2'] in ('North Node','South Node')
                       and a['aspect'] == 'Opposition')]
    return aspects


def compute_transits(year: int, month: int, day: int, hour: int, minute: int, 
                     second: int, tz_offset: float, natal_chart: dict) -> dict:
    """Compute current planetary positions and aspects to natal chart."""
    hour_utc = hour + minute / 60.0 + second / 3600.0 - tz_offset
    day_adj = day
    if hour_utc >= 24:
        hour_utc -= 24
        day_adj += 1
    elif hour_utc < 0:
        hour_utc += 24
        day_adj -= 1
    
    jd = swe.julday(year, month, day_adj, hour_utc)
    
    # Get current planetary positions
    placements = {}
    for body_name, body_id in PLANETS.items():
        try:
            result = swe.calc_ut(jd, body_id)
            trop_lon = result[0][0]
            trop_lat = result[0][1]
            retro = is_retrograde(jd, body_id)
            
            trop_sign, trop_sym, trop_deg = get_tropical(trop_lon)
            std_name, std_abbr, std_sym, std_deg = get_standard_constellation(trop_lon, jd)
            iau_name, iau_abbr, iau_sym, iau_deg = get_iau_constellation(trop_lon, trop_lat, jd)
            
            placements[body_name] = {
                'tropical_longitude': trop_lon,
                'tropical_sign': trop_sign,
                'tropical_symbol': trop_sym,
                'tropical_degree': trop_deg,
                'standard_constellation': std_name,
                'standard_symbol': std_sym,
                'standard_degree': std_deg,
                'iau_constellation': iau_name,
                'iau_symbol': iau_sym,
                'iau_degree': iau_deg,
                'retrograde': retro,
            }
        except:
            pass
    
    # Compute aspects to natal
    ASPECT_DEFS = [
        ("Conjunction", "CON", 0, 8.0),
        ("Opposition", "OPP", 180, 8.0),
        ("Trine", "TRI", 120, 8.0),
        ("Square", "SQR", 90, 8.0),
        ("Sextile", "SEX", 60, 5.0),
        ("Quincunx", "QUI", 150, 4.0),
    ]
    
    aspects = []
    natal_bodies = {**natal_chart.get('placements', {}), **natal_chart.get('angles', {})}
    
    for t_name, t_data in placements.items():
        for n_name, n_data in natal_bodies.items():
            t_lon = t_data['tropical_longitude']
            n_lon = n_data['tropical_longitude']
            diff = abs(t_lon - n_lon)
            if diff > 180:
                diff = 360 - diff
            
            for asp_name, asp_abbr, asp_angle, max_orb in ASPECT_DEFS:
                orb = abs(diff - asp_angle)
                if orb <= max_orb:
                    aspects.append({
                        'transit_body': t_name,
                        'natal_body': n_name,
                        'aspect': asp_name,
                        'abbr': asp_abbr,
                        'orb': round(orb, 2),
                    })
                    break
    
    aspects.sort(key=lambda x: x['orb'])
    
    return {
        'transit_time': {'year': year, 'month': month, 'day': day, 'hour': hour, 'minute': minute},
        'placements': placements,
        'aspects_to_natal': aspects,
    }


def rectify_birth_time(birth_date: tuple, lat: float, lon: float, tz: float, 
                       time_range: tuple, events: list, resolution_minutes: int = 4) -> list:
    """Test candidate birth times and return top 10 ranked by score."""
    candidates = []
    start_hour, end_hour = time_range
    if end_hour <= start_hour:
        end_hour += 24
    
    current = start_hour
    while current < end_hour:
        result = score_rectification_candidate(current % 24, birth_date, lat, lon, tz, events)
        if result['chart']:
            candidates.append(result)
        current += resolution_minutes / 60.0
    
    candidates.sort(key=lambda x: x['total_score'], reverse=True)
    
    top = []
    for c in candidates[:10]:
        h, m = int(c['time']), int((c['time'] % 1) * 60)
        ampm = 'AM' if h < 12 else 'PM'
        h12 = h if 1 <= h <= 12 else (h - 12 if h > 12 else 12)
        top.append({
            'time': c['time'],
            'time_formatted': f"{h12}:{m:02d} {ampm}",
            'score': c['total_score'],
            'event_scores': c['event_scores']
        })
    return top


EVENT_SIGNATURES = {
    'marriage': ['Venus', 'Jupiter', 'Descendant', 'Sun', 'Moon'],
    'divorce': ['Saturn', 'Uranus', 'Pluto', 'Venus', 'Descendant'],
    'career_change': ['Saturn', 'Uranus', 'Jupiter', 'Pluto', 'MC'],
    'job_loss': ['Saturn', 'Neptune', 'Pluto', 'MC'],
    'promotion': ['Jupiter', 'Sun', 'Pluto', 'MC'],
    'accident': ['Mars', 'Uranus', 'Ascendant'],
    'surgery': ['Mars', 'Pluto', 'Chiron'],
    'death_parent': ['Saturn', 'Pluto', 'IC', 'MC'],
    'death_sibling': [
        ('Saturn', 'angle', 10),
        ('Pluto', 'angle', 10),
        ('Saturn', 'Moon', 8),
        ('Pluto', 'Moon', 8),
        ('Uranus', 'angle', 7),
        ('Saturn', 'Mercury', 6),
        ('Pluto', 'Mercury', 6),
        ('Neptune', 'Moon', 5),
    ],
    'child_born': ['Jupiter', 'Moon', 'Venus'],
    'death_sibling': [
        ('Saturn', 'angle', 10),
        ('Pluto', 'angle', 10),
        ('Saturn', 'Moon', 8),
        ('Pluto', 'Moon', 8),
        ('Uranus', 'angle', 7),
        ('Saturn', 'Mercury', 6),
        ('Pluto', 'Mercury', 6),
        ('Neptune', 'Moon', 5),
    ],
    'relocation': ['Uranus', 'Moon', 'Jupiter', 'IC'],
    'windfall': ['Jupiter', 'Uranus', 'Pluto'],
    'health_crisis': ['Saturn', 'Neptune', 'Mars', 'Chiron'],
}


def _angular_separation(lon1: float, lon2: float) -> float:
    """Shortest angle between two longitudes."""
    delta = abs(lon1 - lon2)
    return min(delta, 360 - delta)


def compute_progressions(natal_chart: dict, event_date: tuple) -> dict:
    """Compute secondary progressed chart."""
    bd = natal_chart['birth_data']
    natal_jd = bd['julian_day']
    lat, lon = bd['lat'], bd['lon']
    
    event_jd = swe.julday(event_date[0], event_date[1], event_date[2], 12.0)
    days_of_life = event_jd - natal_jd
    progressed_jd = natal_jd + (days_of_life / 365.2422)
    
    jd_int = int(progressed_jd)
    jd_frac = progressed_jd - jd_int
    l = jd_int + 68569
    n = 4 * l // 146097
    l = l - (146097 * n + 3) // 4
    i = 4000 * (l + 1) // 1461001
    l = l - 1461 * i // 4 + 31
    j = 80 * l // 2447
    day = l - 2447 * j // 80
    l = j // 11
    month = j + 2 - 12 * l
    year = 100 * (n - 49) + i + l
    hour_dec = jd_frac * 24
    hour = int(hour_dec)
    minute = int((hour_dec - hour) * 60)
    
    try:
        return compute_chart(year, month, day, hour, minute, 0, 0, lat, lon, "Progressed")
    except:
        return None


def compute_solar_arcs(natal_chart: dict, event_date: tuple) -> dict:
    """Compute solar arc directions."""
    bd = natal_chart['birth_data']
    natal_jd = bd['julian_day']
    event_jd = swe.julday(event_date[0], event_date[1], event_date[2], 12.0)
    years = (event_jd - natal_jd) / 365.2422
    progressed_jd = natal_jd + years
    natal_sun = natal_chart['placements']['Sun']['tropical_longitude']
    prog_sun = swe.calc_ut(progressed_jd, swe.SUN)[0][0]
    arc = prog_sun - natal_sun
    
    sa_placements = {name: {'tropical_longitude': (d['tropical_longitude'] + arc) % 360, 'name': name}
                     for name, d in natal_chart['placements'].items()}
    sa_angles = {name: {'tropical_longitude': (d['tropical_longitude'] + arc) % 360, 'name': name}
                 for name, d in natal_chart['angles'].items()}
    return {'placements': sa_placements, 'angles': sa_angles, 'arc': arc}


def score_rectification_candidate(candidate_hour: float, birth_date: tuple, 
                                  lat: float, lon: float, tz: float, events: list) -> dict:
    """Score how well a candidate birth time aligns with life events."""
    year, month, day = birth_date
    hour = int(candidate_hour)
    minute = int((candidate_hour % 1) * 60)
    
    try:
        natal_chart = compute_chart(year, month, day, hour, minute, 0, tz, lat, lon, "Candidate")
    except:
        return {'time': candidate_hour, 'total_score': 0, 'event_scores': [], 'chart': None}
    
    total_score = 0
    event_scores = []
    PLANET_WEIGHT = {'Saturn': 10, 'Uranus': 10, 'Neptune': 10, 'Pluto': 10, 
                     'Jupiter': 7, 'Sun': 5, 'Moon': 8, 'Mars': 4, 'Venus': 4, 
                     'Mercury': 2, 'Chiron': 5}
    ASPECT_WEIGHT = {'conjunction': 1.0, 'opposition': 0.9, 'square': 0.8}
    ORB_WEIGHT = [(0.5, 1.0), (1.0, 0.9), (2.0, 0.7), (3.0, 0.4)]
    
    for event in events:
        evt_score = 0
        evt_hits = []
        evt_date = tuple(map(int, event['date'].split('-')))
        signatures = EVENT_SIGNATURES.get(event['type'], [])
        
        try:
            transit_jd = swe.julday(evt_date[0], evt_date[1], evt_date[2], 12.0)
            transit_planets = {pname: swe.calc_ut(transit_jd, pid)[0][0] 
                for pid, pname in [(swe.SUN,'Sun'), (swe.MOON,'Moon'), (swe.MERCURY,'Mercury'),
                                   (swe.VENUS,'Venus'), (swe.MARS,'Mars'), (swe.JUPITER,'Jupiter'),
                                   (swe.SATURN,'Saturn'), (swe.URANUS,'Uranus'), 
                                   (swe.NEPTUNE,'Neptune'), (swe.PLUTO,'Pluto')]}
        except:
            continue
        
        prog_chart = compute_progressions(natal_chart, evt_date)
        sa_data = compute_solar_arcs(natal_chart, evt_date)
        
        natal_points = [(n, d['tropical_longitude'], 'planet') 
                        for n, d in natal_chart['placements'].items()]
        natal_points += [(n, d['tropical_longitude'], 'angle') 
                         for n, d in natal_chart['angles'].items()]
        
        for t_name, t_lon in transit_planets.items():
            if t_name not in signatures:
                continue
            for n_name, n_lon, n_type in natal_points:
                if n_name not in signatures and n_type != 'angle':
                    continue
                orb = _angular_separation(t_lon, n_lon)
                for asp_name, asp_angle in [('conjunction',0), ('opposition',180), ('square',90)]:
                    asp_orb = orb if asp_name == 'conjunction' else abs(orb - asp_angle)
                    if asp_orb <= 3.0:
                        base = PLANET_WEIGHT.get(t_name, 1) * (1.5 if n_type == 'angle' else 1)
                        orb_mult = next((m for o, m in ORB_WEIGHT if asp_orb <= o), 0)
                        hit_score = base * ASPECT_WEIGHT.get(asp_name, 0.5) * orb_mult
                        evt_score += hit_score
                        evt_hits.append(f"Tr.{t_name} {asp_name[:3]} N.{n_name} ({asp_orb:.2f}°)")
                        break
        
        if prog_chart:
            prog_moon = prog_chart['placements'].get('Moon', {}).get('tropical_longitude')
            if prog_moon:
                for n_name, n_lon, n_type in natal_points:
                    if n_type == 'angle':
                        orb = _angular_separation(prog_moon, n_lon)
                        if orb <= 2.0:
                            evt_score += 8 * (1 - orb/3)
                            evt_hits.append(f"Pr.Moon conj N.{n_name} ({orb:.2f}°)")
        
        if sa_data:
            for sa_name in ['Ascendant', 'MC']:
                sa_lon = sa_data['angles'].get(sa_name, {}).get('tropical_longitude')
                if sa_lon:
                    for n_name, n_lon, n_type in natal_points:
                        if n_name in signatures and n_type == 'planet':
                            orb = _angular_separation(sa_lon, n_lon)
                            if orb <= 2.0:
                                evt_score += 6 * (1 - orb/3)
                                evt_hits.append(f"SA.{sa_name} conj N.{n_name} ({orb:.2f}°)")
        
        total_score += evt_score
        event_scores.append({
            'event': f"{event['type']} ({event['date']})",
            'score': round(evt_score, 2),
            'hits': evt_hits[:10]
        })
    
    return {
        'time': candidate_hour,
        'total_score': round(total_score, 2),
        'event_scores': event_scores,
        'chart': natal_chart
    }
