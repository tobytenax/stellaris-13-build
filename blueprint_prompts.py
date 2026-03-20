"""
Stellaris-13 Celestial Blueprint — AI Prompt Templates v2
==========================================================
Expanded to match the depth of the Complete Celestial Blueprint.
9 chapters + preface + synthesis, each with detailed sub-section prompts.

Each prompt receives chart data and returns prose for that section.
The AI caller is responsible for splitting long chapters into sub-prompts
if the model's output limit is reached.
"""


# ═══════════════════════════════════════════════════════════════════════════════
# PERSONA
# ═══════════════════════════════════════════════════════════════════════════════

ASTROLOGER_PERSONA = """You are a master astrologer writing a professional natal chart reading.
Your voice is authoritative yet warm, poetic but precise. You blend astronomical accuracy with
psychological insight and esoteric depth. You understand both tropical and IAU 13-sign systems,
and you are writing for someone using the IAU astronomical system with actual constellation
boundaries. Ophiuchus is a real constellation the Sun transits.

Write in flowing prose with specific detail. Be specific to THIS person's chart — exact degrees,
orbs, Sabian symbols, decan rulers, dwad positions. Avoid generic astrology-speak. Make every
word count. When referencing aspects, always state the orb. When referencing placements, always
state the degree and house.

Use section headers (##) to organize sub-topics within each chapter. Include relevant mythology,
Sabian symbols, and fixed star lore where applicable."""


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER: Build comprehensive chart data summary
# ═══════════════════════════════════════════════════════════════════════════════

def build_chart_summary(chart: dict) -> str:
    """
    Build a comprehensive text summary of all chart data for AI prompt injection.
    This is the master data block that every chapter prompt receives.
    """
    lines = []
    placements = chart.get('placements', {})
    angles = chart.get('angles', {})
    aspects = chart.get('aspects', [])
    syzygy = chart.get('syzygy', {})
    
    lines.append("=== CHART DATA ===")
    lines.append(f"Name: {chart.get('name', 'Subject')}")
    lines.append(f"Sect: {chart.get('sect', 'Day')} chart")
    
    # Birth data
    bd = chart.get('birth_data', {})
    if bd:
        lines.append(f"Born: {bd.get('date', 'Unknown')} at {bd.get('time', 'Unknown')}")
        lines.append(f"Location: {bd.get('location', 'Unknown')} ({bd.get('lat', '?')}N, {bd.get('lon', '?')}W)")
    
    lines.append("")
    lines.append("--- ANGLES ---")
    for angle_name in ['Ascendant', 'MC', 'Descendant', 'IC']:
        a = angles.get(angle_name, {})
        iau = a.get('iau_constellation', a.get('standard_constellation', '?'))
        deg = a.get('iau_degree', a.get('standard_degree', 0))
        std = a.get('standard_constellation', '?')
        std_deg = a.get('standard_degree', 0)
        lines.append(f"{angle_name}: {iau} {deg:.2f}° (tropical: {std} {std_deg:.2f}°)")
    
    lines.append("")
    lines.append("--- PLACEMENTS ---")
    body_order = [
        'Sun', 'Moon', 'Mercury', 'Venus', 'Mars', 'Jupiter', 'Saturn',
        'Uranus', 'Neptune', 'Pluto', 'North Node', 'South Node',
        'Chiron', 'Lilith', 'Ceres', 'Pallas', 'Juno', 'Vesta',
        'Vertex', 'Part of Fortune', 'Part of Spirit',
        'Eris', 'Sedna', 'Orcus', 'Quaoar', 'Haumea', 'Makemake',
        'Eros', 'Psyche', 'Nessus', 'Pholus',
        'Cupido', 'Hades', 'Zeus', 'Kronos', 'Apollon', 'Admetos', 'Vulkanus', 'Poseidon'
    ]
    for body in body_order:
        p = placements.get(body)
        if p:
            iau = p.get('iau_constellation', p.get('standard_constellation', '?'))
            deg = p.get('iau_degree', p.get('standard_degree', 0))
            std = p.get('standard_constellation', '?')
            std_deg = p.get('standard_degree', 0)
            house = p.get('house', '?')
            retro = ' R' if p.get('retrograde') else ''
            lon = p.get('longitude', 0)
            lines.append(
                f"{body}: {iau} {deg:.2f}° H{house}{retro} "
                f"(tropical: {std} {std_deg:.2f}°, ecliptic lon: {lon:.4f}°)"
            )
    
    # Fixed stars (if engine computes them)
    fixed_stars = chart.get('fixed_stars', [])
    if fixed_stars:
        lines.append("")
        lines.append("--- FIXED STAR CONJUNCTIONS ---")
        for fs in fixed_stars:
            lines.append(
                f"{fs.get('star', '?')} conjunct {fs.get('body', '?')} "
                f"(orb: {fs.get('orb', '?')}°) — {fs.get('magnitude', '?')}m"
            )
    
    # Arabic parts (if computed)
    arabic_parts = chart.get('arabic_parts', {})
    if arabic_parts:
        lines.append("")
        lines.append("--- ARABIC PARTS ---")
        for part_name, part_data in arabic_parts.items():
            sign = part_data.get('sign', '?')
            deg = part_data.get('degree', 0)
            house = part_data.get('house', '?')
            lines.append(f"Part of {part_name}: {sign} {deg:.2f}° H{house}")
    
    lines.append("")
    lines.append("--- ASPECTS ---")
    for asp in aspects:
        lines.append(
            f"{asp.get('body1', '?')} {asp.get('aspect', '?')} {asp.get('body2', '?')} "
            f"(orb: {asp.get('orb', '?')}°, {asp.get('quality', 'applying/separating')})"
        )
    
    if syzygy:
        lines.append("")
        lines.append("--- PRENATAL SYZYGY ---")
        lines.append(
            f"Type: {syzygy.get('type', '?')} at "
            f"{syzygy.get('iau_constellation', '?')} {syzygy.get('iau_degree', 0):.2f}° "
            f"(tropical: {syzygy.get('standard_constellation', '?')} {syzygy.get('standard_degree', 0):.2f}°)"
        )
    
    # Progressions (if computed)
    progressions = chart.get('progressions', {})
    if progressions:
        lines.append("")
        lines.append("--- SECONDARY PROGRESSIONS (current) ---")
        for body, data in progressions.items():
            lines.append(f"P.{body}: {data.get('sign', '?')} {data.get('degree', 0):.2f}°")
    
    # Solar arcs (if computed)
    solar_arcs = chart.get('solar_arcs', {})
    if solar_arcs:
        lines.append("")
        lines.append("--- SOLAR ARC DIRECTIONS (current) ---")
        lines.append(f"Solar Arc: {solar_arcs.get('arc_value', 0):.2f}°")
        for body, data in solar_arcs.get('positions', {}).items():
            lines.append(f"SA {body}: {data.get('sign', '?')} {data.get('degree', 0):.2f}°")
    
    # Current transits (if computed)
    transits = chart.get('current_transits', {})
    if transits:
        lines.append("")
        lines.append("--- CURRENT TRANSITS ---")
        for t in transits.get('aspects', []):
            lines.append(
                f"Tr.{t.get('transiting', '?')} {t.get('sign', '?')} {t.get('degree', 0):.2f}° "
                f"{t.get('aspect', '?')} natal {t.get('natal_body', '?')} (orb: {t.get('orb', '?')}°)"
            )
    
    return "\n".join(lines)


def build_aspect_table(aspects: list) -> str:
    """Format aspects as a readable table for prompt injection."""
    lines = ["Body 1 | Aspect | Body 2 | Orb | Quality"]
    lines.append("-" * 60)
    for asp in sorted(aspects, key=lambda a: abs(float(a.get('orb', 99)))):
        lines.append(
            f"{asp.get('body1', '?'):14} | {asp.get('aspect', '?'):12} | "
            f"{asp.get('body2', '?'):14} | {asp.get('orb', '?'):>6}° | "
            f"{asp.get('quality', '?')}"
        )
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# CHAPTER PROMPTS
# ═══════════════════════════════════════════════════════════════════════════════

PREFACE_PROMPT = """Write a 400-600 word preface titled "The Correction" for this natal chart reading.

Explain that this reading uses IAU astronomical constellation boundaries — where the Sun, Moon,
and planets actually ARE in the sky — rather than tropical zodiac signs. Explain that for this
person, the difference is dramatic: their Sun falls in Ophiuchus, the 13th constellation that
mainstream astrology erased in the 2nd century CE.

Briefly explain: Ophiuchus = the Serpent-Bearer = Asclepius, the healer who could raise the dead,
struck down by Zeus for transgressing the mortal/divine boundary, placed among the stars. The Sun
transits Ophiuchus from approximately November 29 to December 17 each year.

Note that the IAU positions are used throughout as the PRIMARY system, with tropical positions
referenced for comparison. The whole sign house system is used.

{chart_summary}
"""


CHAPTER_1_PROMPT = """Write Chapter 1: THE NATAL CHART for this person's celestial blueprint.
This is the longest and most detailed chapter. It must cover ALL of the following sub-sections
with the same depth as a $500 professional reading. Write 3000-5000 words total.

## 1.1 The Angles
For each angle (Ascendant, MC, Descendant, IC), provide:
- The IAU constellation and degree
- The meaning of that angle in that constellation
- The Sabian Symbol for that degree (use the tropical degree for Sabian lookup)
- How this angle shapes the person's life
Also cover the Vertex if available.

## 1.2 The Stellium (if any)
Identify any stellium (3+ planets in one sign/house). For this chart, there is likely a major
Ophiuchus/Sagittarius stellium. Detail what a stellium of this size means — the concentration
of energy, the house it activates, the life theme it demands.

## 1.3 Each Planet in Detail
For EVERY planet (Sun through Pluto), provide:
- IAU constellation, degree, house, decan, dwad
- Sabian Symbol (use tropical degree)
- ALL aspects this planet makes to other planets (with exact orbs)
- The psychological and life-area meaning
- Any fixed star conjunctions within 2°
- Dignities/debilities

Cover in this order: Sun, Moon, Mercury, Venus, Mars, Jupiter, Saturn, Uranus, Neptune, Pluto.

## 1.4 The Nodal Axis
North Node and South Node — signs, houses, degrees, aspects. The soul's evolutionary direction.
Sabian Symbols for both nodes.

## 1.5 Chiron
Sign, house, degree, retrograde status. ALL aspects. The wound and the gift. Fixed star
conjunctions.

## 1.6 Black Moon Lilith
Sign, house, degree. The wild/exiled feminine. Ancestral wound.

## 1.7 Major Asteroids
Ceres, Pallas, Juno, Vesta — each with sign, house, aspects, meaning.

## 1.8 Uranian Hypothetical Planets (if data available)
Cupido, Hades, Zeus, Kronos, Apollon, Admetos, Vulkanus, Poseidon.

## 1.9 Fixed Star Conjunctions
List ALL fixed star conjunctions within 2° of planets or angles. Note Royal Stars especially
(Aldebaran, Antares, Regulus, Fomalhaut).

## 1.10 Aspect Pattern Summary
Identify major aspect patterns: stellium, T-squares, grand trines, yods, kites, mystic rectangles.
List the tightest aspects in order of exactness.

## 1.11 Ophiuchus
If the Sun (or other planets) fall in the IAU Ophiuchus boundaries, discuss the Ophiuchus
archetype in depth — the serpent-bearer, the healer, the transgressor of boundaries.

## 1.12 Astronomical Events at Birth
Research and include:
- Prenatal eclipse (type, sign, degree, date, and its chart implications)
- Any comets visible at the time (especially Halley's for 1985-86 births)
- Meteor showers active at birth date
- Moon phase at birth (New Moon, Full Moon, quarter, etc.)
- Any notable astronomical phenomena

## 1.13 Arabic Parts
If Arabic Part data is available, interpret each part: Fortune, Spirit, Courage, Victory, Wealth,
Substance, Marriage, Illness, Debt, Father, Mother, Faith. Sign, house, and meaning.

{chart_summary}

{aspect_table}
"""


CHAPTER_2_PROMPT = """Write Chapter 2: CURRENT & UPCOMING TRANSITS for this person's celestial blueprint.
Write 2000-3000 words.

## 2.1 The Heavyweight Transits Active NOW
Identify the 5-8 most significant transits currently affecting this chart. For each:
- Transit planet, sign, degree
- Aspect type and orb to natal point
- What this transit means psychologically and practically
- Duration — when it started, when it peaks, when it ends
- How it interacts with other active transits

Pay special attention to:
- Outer planet transits (Pluto, Neptune, Uranus to natal points)
- Saturn transits
- Eclipse activations
- The Pluto square (if person is ~38-44 years old)
- Uranus opposition (if approaching)

## 2.2 Transit Summary Table
Present a table of ALL significant current transits with: transit planet/sign/degree, aspect,
natal point, orb, and a one-line quality description.

## 2.3 Major Transit Windows (next 2-3 years)
Season by season, describe the major astrological weather ahead:
- What enters which houses
- Key aspect dates
- Eclipse seasons and their chart impacts
- Saturn and Jupiter ingresses
- When current heavy transits perfect and separate

Be specific with timing. "Spring 2026" not "soon."

{chart_summary}
"""


CHAPTER_3_PROMPT = """Write Chapter 3: SECONDARY PROGRESSIONS for this person's celestial blueprint.
Write 1500-2500 words.

## 3.1 Current Progressed Positions
Using the "day for a year" method, calculate approximate progressed positions for Sun, Moon,
Mercury, Venus, and Mars. Present as a table: Progressed Position vs Natal Position with notes
on sign changes.

## 3.2 Key Progressed Aspects
Identify the most significant progressed aspects currently active or approaching:
- Progressed Sun aspects to natal or progressed points
- Progressed Moon aspects (current house transit, upcoming conjunctions)
- Progressed planets crossing angles (ASC, MC)
- Progressed planets changing signs

For each, describe the psychological and life meaning.

## 3.3 Progressed Lunar Phase
Calculate the progressed Sun-Moon angle and determine the progressed lunar phase
(New, Crescent, First Quarter, Gibbous, Full, Disseminating, Third Quarter, Balsamic).
Describe what this phase means for where the person is in their ~30-year progressed cycle.

{chart_summary}
"""


CHAPTER_4_PROMPT = """Write Chapter 4: SOLAR ARC DIRECTIONS for this person's celestial blueprint.
Write 1200-2000 words.

Calculate the solar arc (approximately 1° per year of life) and identify the most significant
solar arc contacts currently active or within 1° of exact.

## 4.1 Critical Solar Arc Contacts — NOW
For each significant solar arc direction:
- SA planet reaching natal planet/angle
- The orb (note anything under 0.5° as especially potent)
- The life meaning of this direction
- Whether this is a once-in-a-lifetime contact

Pay special attention to:
- SA planets crossing angles (ASC, MC)
- SA outer planets reaching natal inner planets
- SA Moon contacts (extremely significant, moves ~13° per year by arc)

## 4.2 Upcoming Solar Arc Events
Note any major SA contacts approaching in the next 2-5 years.

{chart_summary}
"""


CHAPTER_5_PROMPT = """Write Chapter 5: SYNASTRY & RELATIONSHIP ARCHETYPES for this person's celestial blueprint.
Write 1500-2500 words.

This is NOT a comparison with a specific partner — it's an analysis of the person's
relationship patterns encoded in their natal chart.

## 5.1 What You Attract
Analyze:
- Descendant sign and ruler — the partner archetype
- Venus sign, house, aspects — what is valued in love
- Mars sign, house, aspects — desire and attraction style
- Juno sign, house — the marriage partner archetype
- Eros (if available) — erotic nature
- Psyche (if available) — the soul's deepest love-need

## 5.2 Relationship Patterns from the Chart
Identify recurring relationship dynamics encoded in:
- Venus-Chiron aspects (wounded lover pattern)
- Moon-Neptune aspects (idealization/fusion)
- 7th/8th house placements
- Nodal axis through relationship houses
- Lilith's relationship implications

## 5.3 The Healing Edge
What does this person need to learn in partnership? What patterns need to break?
How does the North Node inform relationship growth?

{chart_summary}
"""


CHAPTER_6_PROMPT = """Write Chapter 6: PAST LIVES & KARMIC ANALYSIS for this person's celestial blueprint.
Write 2000-3000 words.

## 6.1 The South Node Story
The South Node sign and house tell the story of past-life patterns. Describe:
- What role the soul played in previous incarnations
- Specific past-life scenarios that fit the placements
- The karmic residue — habits, fears, comfort zones carried forward
- Any planets conjunct the South Node amplify this story

## 6.2 The North Node Path
What the soul is growing toward in this lifetime. Be specific and practical.

## 6.3 Saturn: Karmic Lessons
Saturn's sign, house, and aspects as indicators of karmic debts and required disciplines.

## 6.4 Pluto: Evolutionary Intent
Using Jeffrey Wolf Green's evolutionary astrology framework, describe:
- Pluto's evolutionary stage (consensus, individuated, or spiritual)
- The evolutionary intent based on Pluto's sign/house/aspects
- The polarity point (opposite Pluto) as the direction of growth

## 6.5 12th House: Karmic Residue
Any planets in the 12th house as past-life carryover. What was left unfinished?

## 6.6 Retrograde Planets: Karmic Signatures
Any retrograde planets (excluding nodes) represent past-life business needing review.

{chart_summary}
"""


CHAPTER_7_PROMPT = """Write Chapter 7: PSYCHOLOGICAL PROFILE for this person's celestial blueprint.
Write 2000-3000 words.

## 7.1 Core Psychology
The fundamental psychological makeup: how do the major placements interact to create
the person's inner world? What are the central tensions and gifts?

## 7.2 Shadow Work
Using Pluto, Lilith, 8th house, and 12th house placements, identify:
- The primary shadow material — what is repressed or projected
- Where power dynamics play out unconsciously
- The exile patterns (Lilith) — what was rejected about the self
- Dissolution patterns (Neptune/12th) — how the person loses themselves

## 7.3 Emotional Patterns
Moon sign, house, aspects. How emotions are experienced, processed, expressed.
What triggers emotional reactions. What provides emotional security.

## 7.4 Mental Patterns
Mercury sign, house, aspects. How the mind works — fast/slow, analytical/intuitive,
verbal/visual. Intellectual strengths and blind spots.

## 7.5 Drive and Aggression
Mars sign, house, aspects. How anger and desire are channeled. The aggression style.
What motivates action.

## 7.6 Defense Mechanisms
Based on the chart, identify 3-5 primary defense mechanisms the person likely uses
when threatened or overwhelmed. Name them specifically (intellectualization, projection,
flight, dissolution, denial, etc.) and link each to specific chart placements.

End with the antidote: what the chart suggests as the healthy alternative to each defense.

{chart_summary}
"""


CHAPTER_8_PROMPT = """Write Chapter 8: PREDICTIVE TIMING & VOCATIONAL DESTINY for this person's celestial blueprint.
Write 2500-3500 words.

## 8.1 The Midheaven and Career Destiny
MC sign, degree, ruler, aspects. What is the person's public calling? What career
archetype is encoded? How do MC conjunctions (especially with Mercury, Saturn, or
other planets) shape the vocational path?

Also consider the 10th house (whole sign) and any planets there.

## 8.2 The North Node Path and Life Mission
Synthesize the North Node direction with the MC to describe the life mission.
Be concrete: not just "your mission is growth" but specific vocational/life directions.

## 8.3 Timing Windows
Based on the transit, progression, and solar arc data, identify the KEY timing windows
for the next 5-10 years:
- Launch windows (favorable for starting new projects)
- Crisis/transformation periods
- Breakthrough windows
- Consolidation periods
- The second Saturn return (if approaching)

Be specific: "Summer 2027" not "eventually."

## 8.4 Vesta and Vocational Dedication
Vesta's sign and house as indicator of what the person is devoted to serving.
The sacred flame they tend.

## 8.5 Pallas: Strategic Intelligence
Pallas sign, house, aspects. How does the person strategize? What kind of intelligence
do they bring to their work?

{chart_summary}
"""


CHAPTER_9_PROMPT = """Write Chapter 9: SPECIAL TOPICS for this person's celestial blueprint.
Write 2000-3000 words.

## 9.1 The Galactic Center Connection
If any natal points (especially Moon or Sun) are within 5° of the Galactic Center (~27° Sag
tropical / in the Ophiuchus-Sagittarius IAU boundary), describe the significance: cosmic
downloads, sensitivity to galactic-scale information, feeling "tuned in" to something beyond
the solar system.

## 9.2 Prenatal Eclipse
Describe the solar/lunar eclipse immediately preceding birth. Its sign, degree, and
implications for the incarnation theme.

## 9.3 The Decan System
What decan is the Sun in? What is its sub-ruler? What Tarot card corresponds?
Describe how this refines the solar identity.

## 9.4 Heliocentric Earth Position
In a heliocentric (Sun-centered) chart, Earth sits opposite the geocentric Sun.
Calculate the approximate position and describe what it means — the physical incarnation
point as distinct from the solar identity.

## 9.5 Asteroid Interpretations
For any minor bodies available in the chart data (Eros, Psyche, Nessus, Pholus, Sedna,
Eris, Orcus, Quaoar, Icarus, etc.), provide brief interpretations with sign, house, and
aspects to major bodies.

## 9.6 Synthesis: Who You Are and Why You're Here
A 500-800 word synthesis pulling ALL threads together — natal, progressions, solar arcs,
transits, karmic, psychological — into a single unified narrative of this person's soul story.
This should be the most powerful passage in the entire reading.

End with the chart's core message: the single sentence the cosmos encoded at this person's birth.

{chart_summary}
"""


# ═══════════════════════════════════════════════════════════════════════════════
# CHAPTER LIST BUILDER
# ═══════════════════════════════════════════════════════════════════════════════

def get_chapter_prompts(chart: dict) -> list:
    """
    Build the ordered list of (title, prompt) tuples for blueprint generation.
    Each prompt is fully populated with chart data.
    
    Returns:
        List of (chapter_title: str, filled_prompt: str) tuples
    """
    summary = build_chart_summary(chart)
    aspects = chart.get('aspects', [])
    aspect_table = build_aspect_table(aspects) if aspects else "(Aspect data not available — compute from positions)"
    
    chapters = [
        (
            "Preface: The Correction",
            PREFACE_PROMPT.format(chart_summary=summary)
        ),
        (
            "Chapter 1: The Natal Chart",
            CHAPTER_1_PROMPT.format(chart_summary=summary, aspect_table=aspect_table)
        ),
        (
            "Chapter 2: Current & Upcoming Transits",
            CHAPTER_2_PROMPT.format(chart_summary=summary)
        ),
        (
            "Chapter 3: Secondary Progressions",
            CHAPTER_3_PROMPT.format(chart_summary=summary)
        ),
        (
            "Chapter 4: Solar Arc Directions",
            CHAPTER_4_PROMPT.format(chart_summary=summary)
        ),
        (
            "Chapter 5: Synastry & Relationship Archetypes",
            CHAPTER_5_PROMPT.format(chart_summary=summary)
        ),
        (
            "Chapter 6: Past Lives & Karmic Analysis",
            CHAPTER_6_PROMPT.format(chart_summary=summary)
        ),
        (
            "Chapter 7: Psychological Profile",
            CHAPTER_7_PROMPT.format(chart_summary=summary)
        ),
        (
            "Chapter 8: Predictive Timing & Vocational Destiny",
            CHAPTER_8_PROMPT.format(chart_summary=summary)
        ),
        (
            "Chapter 9: Special Topics & Synthesis",
            CHAPTER_9_PROMPT.format(chart_summary=summary)
        ),
    ]
    
    return chapters


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORT FOR TITLE PAGE
# ═══════════════════════════════════════════════════════════════════════════════

def get_title_page_content(chart: dict, birth_data: dict) -> dict:
    """
    Return data for the title page.
    """
    placements = chart.get('placements', {})
    sun = placements.get('Sun', {})
    moon = placements.get('Moon', {})
    asc = chart.get('angles', {}).get('Ascendant', {})
    
    return {
        'name': chart.get('name', 'Subject'),
        'date': birth_data.get('date', 'Unknown'),
        'time': birth_data.get('time', 'Unknown'),
        'location': birth_data.get('location', 'Unknown'),
        'sun_sign': sun.get('iau_constellation', sun.get('standard_constellation', '?')),
        'moon_sign': moon.get('iau_constellation', moon.get('standard_constellation', '?')),
        'rising_sign': asc.get('iau_constellation', asc.get('standard_constellation', '?')),
        'sect': chart.get('sect', 'Day'),
    }
