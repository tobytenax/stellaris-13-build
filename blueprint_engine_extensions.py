"""
Stellaris-13 Engine Extensions for Blueprint v2
=================================================
Computes additional chart data needed for the full Celestial Blueprint:
  - Fixed star conjunctions
  - Arabic Parts (Hellenistic formulas)
  - Secondary Progressions (day-for-a-year)
  - Solar Arc Directions
  - Current transit aspects to natal

These functions take a computed chart dict and enrich it with additional data.
Call enrich_chart_for_blueprint(chart) before passing to the blueprint generator.

Requires: pyswisseph (swisseph)
"""

import swisseph as swe
from datetime import datetime, timedelta
import math
import logging

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# FIXED STARS
# ═══════════════════════════════════════════════════════════════════════════════

# Major fixed stars with ecliptic longitudes (approximate for J2000, precessing ~50"/yr)
# These are tropical longitudes for epoch 2000.0
FIXED_STARS_CATALOG = {
    # Royal Stars
    'Aldebaran':       {'lon_j2000': 69.87,  'mag': 0.85, 'nature': 'Mars', 'notes': 'Watcher of the East, Royal Star, Archangel Michael'},
    'Regulus':         {'lon_j2000': 149.83, 'mag': 1.35, 'nature': 'Mars/Jupiter', 'notes': 'Heart of the Lion, Royal Star'},
    'Antares':         {'lon_j2000': 249.79, 'mag': 1.09, 'nature': 'Mars/Jupiter', 'notes': 'Heart of the Scorpion, Royal Star, Rival of Mars'},
    'Fomalhaut':       {'lon_j2000': 333.87, 'mag': 1.16, 'nature': 'Venus/Mercury', 'notes': 'Watcher of the South, Royal Star'},
    
    # Bright stars
    'Sirius':          {'lon_j2000': 104.07, 'mag': -1.46, 'nature': 'Jupiter/Mars', 'notes': 'Brightest star, Dog Star, blazing power'},
    'Rigel':           {'lon_j2000': 78.63,  'mag': 0.13, 'nature': 'Jupiter/Mars', 'notes': 'Foot of Orion, teaching, knowledge'},
    'Betelgeuse':      {'lon_j2000': 88.79,  'mag': 0.50, 'nature': 'Mars/Mercury', 'notes': 'Shoulder of Orion, honors, fame'},
    'Spica':           {'lon_j2000': 203.84, 'mag': 1.04, 'nature': 'Venus/Mars', 'notes': 'Sheaf of wheat, gifts, brilliance'},
    'Altair':          {'lon_j2000': 301.82, 'mag': 0.77, 'nature': 'Mars/Jupiter', 'notes': 'The Eagle, boldness, courage'},
    'Vega':            {'lon_j2000': 275.17, 'mag': 0.03, 'nature': 'Venus/Mercury', 'notes': 'The Harp, charisma, artistic gifts'},
    'Capella':         {'lon_j2000': 81.51,  'mag': 0.08, 'nature': 'Mars/Mercury', 'notes': 'The She-Goat, honors, wealth'},
    'Procyon':         {'lon_j2000': 115.63, 'mag': 0.38, 'nature': 'Mars/Mercury', 'notes': 'Before the Dog, quick success'},
    'Pollux':          {'lon_j2000': 113.22, 'mag': 1.14, 'nature': 'Mars', 'notes': 'The Boxer, cruelty or subtlety'},
    'Castor':          {'lon_j2000': 110.08, 'mag': 1.58, 'nature': 'Mercury', 'notes': 'The Horseman, intellectual brilliance'},
    
    # Nebulae & clusters
    'Algol':           {'lon_j2000': 56.17,  'mag': 2.12, 'nature': 'Saturn/Jupiter', 'notes': 'The Ghoul, Medusa Head, intense transformation'},
    'Facies':          {'lon_j2000': 278.12, 'mag': 5.90, 'nature': 'Sun/Mars', 'notes': 'Eye of the Archer, piercing focus'},
    'Bellatrix':       {'lon_j2000': 80.93,  'mag': 1.64, 'nature': 'Mars/Mercury', 'notes': 'The Amazon, female warrior'},
    
    # Scales
    'Zubenelgenubi':   {'lon_j2000': 225.05, 'mag': 2.75, 'nature': 'Saturn/Mars', 'notes': 'Southern Scale, karmic justice'},
    'Zubeneschamali':  {'lon_j2000': 229.28, 'mag': 2.61, 'nature': 'Jupiter/Mercury', 'notes': 'Northern Scale, social reform'},
}

# Precession rate: ~50.3 arcseconds per year = 0.01397 degrees per year
PRECESSION_RATE = 50.3 / 3600.0  # degrees per year


def compute_fixed_stars(chart: dict, orb: float = 2.0) -> list:
    """
    Find fixed star conjunctions within orb of natal planets and angles.
    Precesses star positions to the birth epoch.
    
    Returns list of {star, body, orb, magnitude, nature, notes}
    """
    placements = chart.get('placements', {})
    angles = chart.get('angles', {})
    
    # Get birth year for precession
    bd = chart.get('birth_data', {})
    birth_year = bd.get('year', 1985)
    epoch_offset = birth_year - 2000.0
    
    conjunctions = []
    
    # Collect all natal longitudes
    natal_points = {}
    for body, p in placements.items():
        lon = p.get('longitude')
        if lon is not None:
            natal_points[body] = float(lon)
    for angle, a in angles.items():
        lon = a.get('longitude')
        if lon is not None:
            natal_points[angle] = float(lon)
    
    # Check each fixed star
    for star_name, star_data in FIXED_STARS_CATALOG.items():
        # Precess to birth epoch
        star_lon = star_data['lon_j2000'] + (epoch_offset * PRECESSION_RATE)
        star_lon = star_lon % 360.0
        
        for body_name, body_lon in natal_points.items():
            diff = abs(star_lon - body_lon)
            if diff > 180:
                diff = 360 - diff
            
            if diff <= orb:
                conjunctions.append({
                    'star': star_name,
                    'body': body_name,
                    'orb': round(diff, 2),
                    'magnitude': star_data['mag'],
                    'nature': star_data['nature'],
                    'notes': star_data['notes'],
                    'star_longitude': round(star_lon, 2)
                })
    
    # Sort by orb (tightest first)
    conjunctions.sort(key=lambda x: x['orb'])
    return conjunctions


# ═══════════════════════════════════════════════════════════════════════════════
# ARABIC PARTS
# ═══════════════════════════════════════════════════════════════════════════════

def compute_arabic_parts(chart: dict) -> dict:
    """
    Compute Arabic/Hellenistic Lots using traditional formulas.
    Day chart formulas differ from night chart formulas for some parts.
    
    Returns dict of {part_name: {longitude, sign, degree, house}}
    """
    placements = chart.get('placements', {})
    angles = chart.get('angles', {})
    sect = chart.get('sect', 'Day')
    is_day = sect.lower() == 'day'
    
    def get_lon(body):
        p = placements.get(body, {})
        return float(p.get('longitude', 0))
    
    def get_angle_lon(angle):
        a = angles.get(angle, {})
        return float(a.get('longitude', 0))
    
    asc = get_angle_lon('Ascendant')
    mc = get_angle_lon('MC')
    sun = get_lon('Sun')
    moon = get_lon('Moon')
    mercury = get_lon('Mercury')
    venus = get_lon('Venus')
    mars = get_lon('Mars')
    jupiter = get_lon('Jupiter')
    saturn = get_lon('Saturn')
    
    def calc_part(a, b, c):
        """Part = Ascendant + B - C (mod 360)"""
        return (a + b - c) % 360.0
    
    # Define parts with day/night formulas
    # Format: (day_formula, night_formula) where each is (base, add, subtract)
    part_formulas = {
        'Fortune':    ((asc, moon, sun),      (asc, sun, moon)),
        'Spirit':     ((asc, sun, moon),      (asc, moon, sun)),
        'Courage':    ((asc, mars, moon) if is_day else (asc, moon, mars), None),
        'Victory':    ((asc, jupiter, venus) if is_day else (asc, venus, jupiter), None),
        'Wealth':     ((asc, jupiter, saturn) if is_day else (asc, saturn, jupiter), None),
        'Substance':  ((asc, venus, saturn) if is_day else (asc, saturn, venus), None),
        'Marriage':   ((asc, venus, saturn) if is_day else (asc, saturn, venus), None),
        'Illness':    ((asc, saturn, mars) if is_day else (asc, mars, saturn), None),
        'Debt':       ((asc, saturn, mercury) if is_day else (asc, mercury, saturn), None),
        'Father':     ((asc, saturn, sun) if is_day else (asc, sun, saturn), None),
        'Mother':     ((asc, moon, venus) if is_day else (asc, venus, moon), None),
        'Faith':      ((asc, saturn, mercury) if is_day else (asc, mercury, saturn), None),
    }
    
    parts = {}
    for name, formulas in part_formulas.items():
        if formulas[1] is not None:
            formula = formulas[0] if is_day else formulas[1]
        else:
            formula = formulas[0]
        
        lon = calc_part(*formula)
        
        # Convert longitude to sign + degree
        sign_index = int(lon / 30)
        degree = lon % 30
        signs = ['Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo',
                 'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces']
        sign = signs[sign_index % 12]
        
        # Determine house (whole sign)
        asc_sign_index = int(asc / 30)
        house = ((sign_index - asc_sign_index) % 12) + 1
        
        parts[name] = {
            'longitude': round(lon, 2),
            'sign': sign,
            'degree': round(degree, 2),
            'house': house
        }
    
    return parts


# ═══════════════════════════════════════════════════════════════════════════════
# SECONDARY PROGRESSIONS
# ═══════════════════════════════════════════════════════════════════════════════

def compute_progressions(chart: dict, target_date: datetime = None) -> dict:
    """
    Compute secondary progressions (day-for-a-year method).
    
    For age N, the progressed chart = natal chart + N days.
    Only progresses Sun, Moon, Mercury, Venus, Mars (outer planets move negligibly).
    
    Returns dict of {body: {sign, degree, longitude, natal_sign, natal_degree}}
    """
    if target_date is None:
        target_date = datetime.now()
    
    bd = chart.get('birth_data', {})
    birth_year = bd.get('year', 1985)
    birth_month = bd.get('month', 12)
    birth_day = bd.get('day', 12)
    birth_hour = bd.get('hour', 10)
    birth_minute = bd.get('minute', 47)
    tz_offset = bd.get('tz_offset', -6)
    
    try:
        birth_dt = datetime(birth_year, birth_month, birth_day, birth_hour, birth_minute)
    except:
        return {}
    
    # Age in years (fractional)
    age_days = (target_date - birth_dt).days
    age_years = age_days / 365.25
    
    # Progressed date = birth + age_years days
    progressed_dt = birth_dt + timedelta(days=age_years)
    
    # Calculate Julian Day for progressed date
    prog_year = progressed_dt.year
    prog_month = progressed_dt.month
    prog_day = progressed_dt.day + (progressed_dt.hour + progressed_dt.minute / 60.0 - tz_offset) / 24.0
    
    jd_prog = swe.julday(prog_year, prog_month, prog_day)
    
    signs = ['Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo',
             'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces']
    
    bodies_to_progress = {
        'Sun': swe.SUN,
        'Moon': swe.MOON,
        'Mercury': swe.MERCURY,
        'Venus': swe.VENUS,
        'Mars': swe.MARS,
    }
    
    placements = chart.get('placements', {})
    progressions = {}
    
    for body_name, swe_id in bodies_to_progress.items():
        try:
            result = swe.calc_ut(jd_prog, swe_id)
            lon = result[0][0]  # ecliptic longitude
            
            sign_index = int(lon / 30) % 12
            degree = lon % 30
            
            natal_p = placements.get(body_name, {})
            natal_sign = natal_p.get('standard_constellation', '?')
            natal_degree = natal_p.get('standard_degree', 0)
            
            progressions[body_name] = {
                'sign': signs[sign_index],
                'degree': round(degree, 2),
                'longitude': round(lon, 4),
                'natal_sign': natal_sign,
                'natal_degree': round(natal_degree, 2) if isinstance(natal_degree, (int, float)) else natal_degree
            }
        except Exception as e:
            logger.warning(f"Failed to compute progression for {body_name}: {e}")
    
    # Add progressed lunar phase
    if 'Sun' in progressions and 'Moon' in progressions:
        sun_lon = progressions['Sun']['longitude']
        moon_lon = progressions['Moon']['longitude']
        angle = (moon_lon - sun_lon) % 360
        
        phase_names = [
            (0, 45, 'New Moon'),
            (45, 90, 'Crescent'),
            (90, 135, 'First Quarter'),
            (135, 180, 'Gibbous'),
            (180, 225, 'Full Moon'),
            (225, 270, 'Disseminating'),
            (270, 315, 'Third Quarter'),
            (315, 360, 'Balsamic'),
        ]
        
        phase = 'Unknown'
        for start, end, name in phase_names:
            if start <= angle < end:
                phase = name
                break
        
        progressions['_lunar_phase'] = {
            'phase': phase,
            'angle': round(angle, 2),
            'age_years': round(age_years, 2)
        }
    
    return progressions


# ═══════════════════════════════════════════════════════════════════════════════
# SOLAR ARC DIRECTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def compute_solar_arcs(chart: dict, target_date: datetime = None) -> dict:
    """
    Compute solar arc directions.
    Solar arc = progressed Sun longitude - natal Sun longitude.
    All natal positions advance by this arc.
    
    Returns dict with arc_value and positions.
    """
    if target_date is None:
        target_date = datetime.now()
    
    progressions = compute_progressions(chart, target_date)
    if 'Sun' not in progressions:
        return {}
    
    placements = chart.get('placements', {})
    natal_sun = float(placements.get('Sun', {}).get('longitude', 0))
    prog_sun = progressions['Sun']['longitude']
    
    arc = (prog_sun - natal_sun) % 360
    if arc > 180:
        arc = arc - 360  # shouldn't happen for reasonable ages but safety check
    
    signs = ['Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo',
             'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces']
    
    sa_positions = {}
    for body, p in placements.items():
        lon = p.get('longitude')
        if lon is not None:
            sa_lon = (float(lon) + arc) % 360
            sign_index = int(sa_lon / 30) % 12
            degree = sa_lon % 30
            
            sa_positions[body] = {
                'sign': signs[sign_index],
                'degree': round(degree, 2),
                'longitude': round(sa_lon, 4)
            }
    
    return {
        'arc_value': round(arc, 2),
        'positions': sa_positions
    }


# ═══════════════════════════════════════════════════════════════════════════════
# CURRENT TRANSITS
# ═══════════════════════════════════════════════════════════════════════════════

def compute_current_transits(chart: dict, target_date: datetime = None, orb: float = 3.0) -> dict:
    """
    Compute current transit aspects to natal positions.
    
    Returns dict with current planet positions and aspects to natal.
    """
    if target_date is None:
        target_date = datetime.now()
    
    # Julian Day for now
    jd = swe.julday(
        target_date.year, target_date.month,
        target_date.day + target_date.hour / 24.0
    )
    
    signs = ['Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo',
             'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces']
    
    transit_bodies = {
        'Sun': swe.SUN, 'Moon': swe.MOON, 'Mercury': swe.MERCURY,
        'Venus': swe.VENUS, 'Mars': swe.MARS, 'Jupiter': swe.JUPITER,
        'Saturn': swe.SATURN, 'Uranus': swe.URANUS, 'Neptune': swe.NEPTUNE,
        'Pluto': swe.PLUTO
    }
    
    # Get current positions
    current_positions = {}
    for name, swe_id in transit_bodies.items():
        try:
            result = swe.calc_ut(jd, swe_id)
            lon = result[0][0]
            sign_index = int(lon / 30) % 12
            degree = lon % 30
            current_positions[name] = {
                'longitude': lon,
                'sign': signs[sign_index],
                'degree': round(degree, 2)
            }
        except:
            pass
    
    # Aspect definitions
    aspect_angles = {
        'conjunction': 0, 'opposition': 180, 'trine': 120,
        'square': 90, 'sextile': 60, 'quincunx': 150,
        'semi-sextile': 30, 'semi-square': 45, 'sesquiquadrate': 135
    }
    
    # Find aspects to natal
    placements = chart.get('placements', {})
    transit_aspects = []
    
    for tr_name, tr_data in current_positions.items():
        tr_lon = tr_data['longitude']
        
        for natal_name, natal_data in placements.items():
            natal_lon = natal_data.get('longitude')
            if natal_lon is None:
                continue
            natal_lon = float(natal_lon)
            
            diff = abs(tr_lon - natal_lon)
            if diff > 180:
                diff = 360 - diff
            
            for aspect_name, aspect_angle in aspect_angles.items():
                aspect_orb = abs(diff - aspect_angle)
                
                # Tighter orbs for minor aspects
                max_orb = orb
                if aspect_angle in (30, 45, 135, 150):
                    max_orb = orb * 0.5
                
                if aspect_orb <= max_orb:
                    transit_aspects.append({
                        'transiting': tr_name,
                        'sign': tr_data['sign'],
                        'degree': tr_data['degree'],
                        'aspect': aspect_name,
                        'natal_body': natal_name,
                        'orb': round(aspect_orb, 2)
                    })
    
    # Sort by orb
    transit_aspects.sort(key=lambda x: x['orb'])
    
    return {
        'date': target_date.strftime('%Y-%m-%d'),
        'positions': current_positions,
        'aspects': transit_aspects
    }


# ═══════════════════════════════════════════════════════════════════════════════
# MASTER ENRICHMENT FUNCTION
# ═══════════════════════════════════════════════════════════════════════════════

def enrich_chart_for_blueprint(chart: dict, target_date: datetime = None) -> dict:
    """
    Enrich a computed chart with all additional data needed for the blueprint.
    Call this BEFORE passing the chart to generate_blueprint().
    
    Adds:
      - chart['fixed_stars']: list of fixed star conjunctions
      - chart['arabic_parts']: dict of Arabic Parts
      - chart['progressions']: dict of secondary progressions
      - chart['solar_arcs']: dict of solar arc directions
      - chart['current_transits']: dict of current transit aspects
    
    Usage:
        chart = compute_chart(...)
        enriched = enrich_chart_for_blueprint(chart)
        generate_blueprint(enriched, birth_data, ai_caller, output_path)
    """
    if target_date is None:
        target_date = datetime.now()
    
    logger.info("Enriching chart for blueprint generation...")
    
    try:
        chart['fixed_stars'] = compute_fixed_stars(chart)
        logger.info(f"  Fixed stars: {len(chart['fixed_stars'])} conjunctions found")
    except Exception as e:
        logger.warning(f"  Fixed stars failed: {e}")
        chart['fixed_stars'] = []
    
    try:
        chart['arabic_parts'] = compute_arabic_parts(chart)
        logger.info(f"  Arabic Parts: {len(chart['arabic_parts'])} parts computed")
    except Exception as e:
        logger.warning(f"  Arabic Parts failed: {e}")
        chart['arabic_parts'] = {}
    
    try:
        chart['progressions'] = compute_progressions(chart, target_date)
        logger.info(f"  Progressions: {len(chart['progressions'])} bodies progressed")
    except Exception as e:
        logger.warning(f"  Progressions failed: {e}")
        chart['progressions'] = {}
    
    try:
        chart['solar_arcs'] = compute_solar_arcs(chart, target_date)
        arc = chart['solar_arcs'].get('arc_value', 0)
        logger.info(f"  Solar arcs: {arc:.2f}° arc computed")
    except Exception as e:
        logger.warning(f"  Solar arcs failed: {e}")
        chart['solar_arcs'] = {}
    
    try:
        chart['current_transits'] = compute_current_transits(chart, target_date)
        n = len(chart['current_transits'].get('aspects', []))
        logger.info(f"  Current transits: {n} aspects found")
    except Exception as e:
        logger.warning(f"  Current transits failed: {e}")
        chart['current_transits'] = {}
    
    logger.info("Chart enrichment complete.")
    return chart
