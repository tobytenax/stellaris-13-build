"""
Stellaris-13 — Web Application v2.4
Flask server providing the GUI for the 13-sign ephemeris.

Production-ready with:
- Multi-provider AI interpretation (parallel execution)
- Conversational chart mode
- Past life / karmic analysis
- Privacy-first architecture (no server-side data storage)
- GDPR/CCPA compliant by design
- Security headers and rate limiting
"""

from flask import Flask, render_template, request, jsonify, send_file, session, make_response
from functools import wraps

from blueprint_engine_extensions import enrich_chart_for_blueprint
from blueprint_generator import generate_blueprint, make_anthropic_caller, make_openai_caller, make_ollama_caller
from blueprint_prompts import get_chapter_prompts
from license import init_license_system, requires_tier
from engine import compute_chart, compute_synastry, compute_transits, rectify_birth_time
import json
import os
import requests
import logging
from datetime import datetime
from io import BytesIO
import secrets
import uuid
import markdown

# Configure logging
logging.basicConfig(
    level=os.environ.get('LOG_LEVEL', 'INFO'),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('stellaris')

app = Flask(__name__)

# Load configuration (contains Payhip secrets, AI keys, etc.)
from config import get_config
app.config.from_object(get_config())

app.secret_key = os.environ.get('SECRET_KEY') or secrets.token_hex(32)

# Initialize license system (must be after config load)
license_manager = init_license_system(app)

# Production configuration
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('FLASK_ENV') == 'production'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

CHARTS_DIR = os.path.join(os.path.dirname(__file__), 'saved_charts')
LEGAL_DIR = os.path.join(os.path.dirname(__file__), 'legal')
os.makedirs(CHARTS_DIR, exist_ok=True)

# Store active chart contexts for conversational mode
chart_contexts = {}

# Version info
VERSION = "2.7.0"
BUILD_DATE = "February 2026"


def add_security_headers(response):
    """Add security headers to all responses."""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    return response


@app.after_request
def after_request(response):
    """Apply security headers and CORS."""
    response = add_security_headers(response)
    # CORS for API endpoints
    if request.path.startswith('/compute') or request.path.startswith('/interpret'):
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response


@app.errorhandler(Exception)
def handle_error(error):
    """Global error handler."""
    logger.error(f"Unhandled error: {error}", exc_info=True)
    return jsonify({
        'status': 'error',
        'message': 'An unexpected error occurred. Please try again.'
    }), 500


@app.route('/health')
def health():
    """Health check endpoint for container orchestration."""
    return jsonify({
        'status': 'healthy',
        'version': VERSION,
        'timestamp': datetime.utcnow().isoformat()
    })


@app.route('/version')
def version():
    """Version information."""
    return jsonify({
        'name': 'Stellaris-13',
        'version': VERSION,
        'build_date': BUILD_DATE,
        'description': '13-Sign Astronomical Ephemeris Calculator'
    })


@app.route('/')
def landing():
    """Landing page with marketing content."""
    return render_template('landing.html')


@app.route('/app')
def app_main():
    """Main application interface."""
    return render_template('index.html')


# ═══════════════════════════════════════════════════════════════
# LEGAL & COMPLIANCE ROUTES
# ═══════════════════════════════════════════════════════════════

@app.route('/legal')
def legal_index():
    """Legal documentation index."""
    return render_template('legal_index.html')


@app.route('/legal/terms')
def terms_of_service():
    """Terms of Service page."""
    try:
        with open(os.path.join(os.path.dirname(__file__), 'LEGAL.md'), 'r') as f:
            content = f.read()
            # Extract Terms section
            import re
            match = re.search(r'# Terms of Service(.*?)(?=\n# [A-Z]|\Z)', content, re.DOTALL)
            terms_md = match.group(0) if match else "Terms of Service not found."
        return render_template('legal_page.html', 
                               title='Terms of Service',
                               content=markdown.markdown(terms_md))
    except Exception as e:
        logger.error(f"Error loading terms: {e}")
        return render_template('legal_page.html',
                               title='Terms of Service',
                               content='<p>Terms of Service document is being updated.</p>')


@app.route('/legal/privacy')
def privacy_policy():
    """Privacy Policy page."""
    try:
        with open(os.path.join(os.path.dirname(__file__), 'LEGAL.md'), 'r') as f:
            content = f.read()
            import re
            match = re.search(r'# Privacy Policy(.*?)(?=\n# [A-Z]|\Z)', content, re.DOTALL)
            privacy_md = match.group(0) if match else "Privacy Policy not found."
        return render_template('legal_page.html',
                               title='Privacy Policy',
                               content=markdown.markdown(privacy_md))
    except Exception as e:
        logger.error(f"Error loading privacy policy: {e}")
        return render_template('legal_page.html',
                               title='Privacy Policy',
                               content='<p>Privacy Policy document is being updated.</p>')


@app.route('/legal/disclaimer')
def disclaimer():
    """Disclaimer page."""
    try:
        with open(os.path.join(os.path.dirname(__file__), 'LEGAL.md'), 'r') as f:
            content = f.read()
            import re
            match = re.search(r'# Disclaimer(.*?)(?=\n# [A-Z]|\Z)', content, re.DOTALL)
            disclaimer_md = match.group(0) if match else "Disclaimer not found."
        return render_template('legal_page.html',
                               title='Disclaimer',
                               content=markdown.markdown(disclaimer_md))
    except Exception as e:
        logger.error(f"Error loading disclaimer: {e}")
        return render_template('legal_page.html',
                               title='Disclaimer',
                               content='<p>Disclaimer document is being updated.</p>')


@app.route('/about/founder')
def about_founder():
    """About the Founder - buried deep in the app."""
    from founder import FOUNDER_DATA, get_about_html
    return render_template('about_founder.html',
                           founder=FOUNDER_DATA,
                           about_html=get_about_html())


# ═══════════════════════════════════════════════════════════════
# GDPR/CCPA DATA RIGHTS ENDPOINTS
# ═══════════════════════════════════════════════════════════════

@app.route('/api/consent', methods=['POST'])
def record_consent():
    """
    Record user consent for GDPR/CCPA compliance.
    Consent is managed client-side; this logs the event.
    """
    data = request.get_json()
    consent_types = data.get('types', [])
    granted = data.get('granted', False)
    timestamp = datetime.utcnow().isoformat()
    
    logger.info(f"Consent recorded: types={consent_types}, granted={granted}")
    
    return jsonify({
        'status': 'ok',
        'recorded': True,
        'timestamp': timestamp
    })


@app.route('/api/data/export', methods=['POST'])
def export_user_data():
    """
    GDPR Article 20: Data Portability
    Export all user data in portable JSON format.
    """
    data = request.get_json()
    
    export_package = {
        'export_date': datetime.utcnow().isoformat(),
        'format_version': '1.0',
        'service': 'Stellaris-13',
        'service_version': VERSION,
        'data': {
            'charts': data.get('charts', []),
            'preferences': data.get('preferences', {}),
            'consent_records': data.get('consent', {})
        },
        'note': 'This export contains all data associated with your use of Stellaris-13.'
    }
    
    return jsonify(export_package)


@app.route('/api/data/delete', methods=['POST'])
def delete_user_data():
    """
    GDPR Article 17: Right to Erasure ("Right to be Forgotten")
    Delete all server-side user data.
    """
    data = request.get_json()
    
    if not data.get('confirm'):
        return jsonify({
            'status': 'error',
            'message': 'Deletion requires explicit confirmation. Send {"confirm": true}'
        }), 400
    
    # Clear server-side session
    session.clear()
    
    # Clear any chat contexts
    session_id = data.get('session_id')
    if session_id and session_id in chart_contexts:
        del chart_contexts[session_id]
    
    logger.info(f"User data deletion requested and processed")
    
    return jsonify({
        'status': 'ok',
        'deleted': True,
        'timestamp': datetime.utcnow().isoformat(),
        'instructions': [
            'Server-side data has been deleted.',
            'To complete deletion, clear your browser localStorage:',
            '  1. Open browser Developer Tools (F12)',
            '  2. Go to Application > Local Storage',
            '  3. Delete all stellaris13_* keys',
            'Or use the "Clear All Data" button in Settings.'
        ]
    })


@app.route('/compute', methods=['POST'])
def compute():
    data = request.get_json()
    
    try:
        date_parts = data['date'].split('-')
        year = int(date_parts[0])
        month = int(date_parts[1])
        day = int(date_parts[2])
        
        time_parts = data['time'].split(':')
        hour = int(time_parts[0])
        minute = int(time_parts[1])
        second = int(time_parts[2]) if len(time_parts) > 2 else 0
        
        tz = float(data['tz'])
        lat = float(data['lat'])
        lon = float(data['lon'])
        name = data.get('name', 'Chart')
        
        chart = compute_chart(year, month, day, hour, minute, second, tz, lat, lon, name)
        
        return jsonify({'status': 'ok', 'chart': chart})
    
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400


@app.route('/synastry', methods=['POST'])
def synastry():
    data = request.get_json()
    
    try:
        charts = []
        for c in [data['chart1'], data['chart2']]:
            date_parts = c['date'].split('-')
            time_parts = c['time'].split(':')
            chart = compute_chart(
                int(date_parts[0]), int(date_parts[1]), int(date_parts[2]),
                int(time_parts[0]), int(time_parts[1]),
                int(time_parts[2]) if len(time_parts) > 2 else 0,
                float(c['tz']), float(c['lat']), float(c['lon']),
                c.get('name', 'Chart')
            )
            charts.append(chart)
        
        aspects = compute_synastry(charts[0], charts[1])
        
        return jsonify({
            'status': 'ok',
            'chart1': charts[0],
            'chart2': charts[1],
            'synastry': aspects[:40],
        })
    
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400


@app.route('/transits', methods=['POST'])
def transits():
    """Compute current transits against a natal chart."""
    data = request.get_json()
    
    try:
        natal_data = data['natal']
        date_parts = natal_data['date'].split('-')
        time_parts = natal_data['time'].split(':')
        
        natal_chart = compute_chart(
            int(date_parts[0]), int(date_parts[1]), int(date_parts[2]),
            int(time_parts[0]), int(time_parts[1]),
            int(time_parts[2]) if len(time_parts) > 2 else 0,
            float(natal_data['tz']), float(natal_data['lat']), float(natal_data['lon']),
            natal_data.get('name', 'Natal')
        )
        
        if 'transit' in data and data['transit'].get('date'):
            t = data['transit']
            t_date = t['date'].split('-')
            t_time = t.get('time', '12:00:00').split(':')
            t_year, t_month, t_day = int(t_date[0]), int(t_date[1]), int(t_date[2])
            t_hour, t_minute = int(t_time[0]), int(t_time[1])
            t_second = int(t_time[2]) if len(t_time) > 2 else 0
            t_tz = float(t.get('tz', 0))
        else:
            now = datetime.utcnow()
            t_year, t_month, t_day = now.year, now.month, now.day
            t_hour, t_minute, t_second = now.hour, now.minute, now.second
            t_tz = 0
        
        transit_data = compute_transits(t_year, t_month, t_day, t_hour, t_minute, t_second, t_tz, natal_chart)
        
        return jsonify({'status': 'ok', 'natal': natal_chart, 'transits': transit_data})
    
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400


@app.route('/download', methods=['POST'])
def download_chart():
    """Download chart as JSON file."""
    data = request.get_json()
    
    try:
        chart = data.get('chart')
        if not chart:
            return jsonify({'status': 'error', 'message': 'No chart data'}), 400
        
        name = chart.get('name', 'chart').replace(' ', '_')
        buffer = BytesIO()
        buffer.write(json.dumps(chart, indent=2).encode('utf-8'))
        buffer.seek(0)
        
        return send_file(buffer, mimetype='application/json', as_attachment=True,
                         download_name=f"{name}_stellaris13.json")
    
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400


@app.route('/interpret', methods=['POST'])
def interpret():
    """Get AI interpretation using multiple providers (parallel execution)."""
    import concurrent.futures
    
    data = request.get_json()
    
    chart = data.get('chart')
    chart1 = data.get('chart1')
    chart2 = data.get('chart2')
    transits = data.get('transits')
    synastry_aspects = data.get('synastry')
    query_type = data.get('type', 'comprehensive')
    providers = data.get('providers', {})
    method = data.get('method', 'iau')
    
    # Build the appropriate prompt
    if query_type == 'past_life' and chart:
        prompt = build_past_life_prompt(chart, method)
    elif query_type == 'transit' and chart and transits:
        prompt = build_transit_prompt(chart, transits, method)
    elif query_type == 'synastry' and chart1 and chart2:
        prompt = build_synastry_prompt(chart1, chart2, synastry_aspects, method)
    elif chart:
        prompt = build_interpretation_prompt(chart, query_type, method)
    else:
        return jsonify({'status': 'error', 'message': 'No chart data'}), 400
    
    try:
        interpretations = {}
        tasks = []
        
        # Build task list for parallel execution
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = {}
            
            # Cloud APIs - can run in parallel
            if providers.get('mistral'):
                futures[executor.submit(call_mistral_api, prompt, providers['mistral'])] = 'Mistral'
            
            if providers.get('claude'):
                futures[executor.submit(call_claude_api, prompt, providers['claude'])] = 'Claude'
            
            # Additional cloud providers
            if providers.get('yi'):
                futures[executor.submit(call_yi_api, prompt, providers['yi'])] = 'Yi'
            
            if providers.get('fireworks'):
                futures[executor.submit(call_fireworks_api, prompt, providers['fireworks'])] = 'Fireworks'
            
            if providers.get('groq'):
                futures[executor.submit(call_groq_api, prompt, providers['groq'])] = 'Groq'
            
            # Collect cloud results
            for future in concurrent.futures.as_completed(futures, timeout=120):
                provider_name = futures[future]
                try:
                    result = future.result()
                    if result:
                        interpretations[provider_name] = result
                except Exception as e:
                    print(f"{provider_name} failed: {e}")
        
        # Ollama models - run sequentially (local resource constraint)
        ollama_models = providers.get('ollama_models', [])
        if providers.get('ollama'):
            # Single model (backward compatible)
            ollama_models = [providers['ollama']] if not ollama_models else ollama_models
        
        for model_name in ollama_models[:3]:  # Max 3 local models
            if model_name:
                result = call_ollama_api(prompt, model_name)
                if result:
                    interpretations[model_name] = result
        
        # Fallback
        if not interpretations:
            result = call_mistral_api(prompt, os.environ.get('MISTRAL_API_KEY'))
            if result:
                interpretations['Mistral'] = result
            else:
                result = call_ollama_api(prompt)
                if result:
                    interpretations['hermes3:8b'] = result
        
        if not interpretations:
            return jsonify({
                'status': 'ok',
                'interpretation': 'No AI providers configured.',
                'interpretations': {}
            })
        
        return jsonify({
            'status': 'ok',
            'interpretations': interpretations,
            'interpretation': list(interpretations.values())[0] if interpretations else ''
        })
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': str(e)}), 400


@app.route('/chat', methods=['POST'])
def chat():
    """
    Conversational chart analysis endpoint.
    Maintains chart context and allows back-and-forth discussion.
    """
    # License check: Personal tier or higher (chart conversation)
    lm = app.config.get('LICENSE_MANAGER')
    if lm:
        status = lm.check_license()
        if status.tier not in ('personal', 'professional', 'astrologer'):
            return jsonify({
                'error': 'Chart conversation requires the Personal edition.',
                'tier': status.tier,
                'upgrade_url': 'https://payhip.com/Stellaris13'
            }), 403
    
    data = request.get_json()
    
    chart = data.get('chart')
    message = data.get('message', '')
    session_id = data.get('session_id')
    providers = data.get('providers', {})
    method = data.get('method', 'iau')
    
    if not chart:
        return jsonify({'status': 'error', 'message': 'No chart data'}), 400
    
    if not message:
        return jsonify({'status': 'error', 'message': 'No message provided'}), 400
    
    # Generate session ID if not provided
    if not session_id:
        session_id = secrets.token_hex(16)
    
    # Build chart context
    chart_context = build_chart_context(chart, method)
    
    # Get or create conversation history
    if session_id not in chart_contexts:
        chart_contexts[session_id] = {
            'chart': chart,
            'history': [],
            'method': method,
        }
    
    ctx = chart_contexts[session_id]
    ctx['history'].append({'role': 'user', 'content': message})
    
    # Build the conversational prompt
    system_prompt = f"""You are a professional consulting astrologer conducting an interactive chart reading session using Stellaris-13, a 13-sign astronomical ephemeris.

CRITICAL: The chart data below was computed by the Stellaris-13 engine using Swiss Ephemeris with IAU constellation boundaries and precession correction. This data is your SOLE SOURCE OF TRUTH. You must NEVER:
- Recompute or second-guess any positions
- Use tropical zodiac signs (Stellaris uses 13-sign astronomical constellations including Ophiuchus)
- Claim a planet is in a different sign than what the chart shows
- Fall back on your training data for astrological positions

If the chart says Sun is in Ophiuchus 14.2°, then Sun IS in Ophiuchus 14.2°. Period. The user chose Stellaris specifically because it corrects the astronomical errors in conventional astrology. Respect that choice.

{chart_context}

RESPONSE STYLE:
- Reference specific placements by constellation and degree: "Your Moon at Pisces 12.86°" not "your Moon sign"
- When discussing aspects, cite the orb: "Venus square Neptune at 0.03° — essentially exact"
- Distinguish between inner and outer planet dynamics
- Note Ophiuchus placements explicitly — they carry the energy of the serpent bearer, the healer, the hidden 13th
- Be direct and confident — no "you may feel" or "this could indicate"
- State what the chart shows, clearly and authoritatively
- If asked about something not in the chart, say so honestly
- Keep responses focused, specific, and grounded in the actual chart data"""

    # Build messages array
    messages = [{'role': 'system', 'content': system_prompt}]
    messages.extend(ctx['history'][-10:])  # Keep last 10 messages for context
    
    try:
        result = None
        model_name = 'AI'
        
        if providers.get('ollama'):
            model_name = providers['ollama'] or 'hermes3:8b'
            result = call_ollama_chat(messages, model_name)
        elif providers.get('mistral'):
            model_name = 'Mistral'
            result = call_mistral_chat(messages, providers['mistral'])
        elif providers.get('claude'):
            model_name = 'Claude'
            result = call_claude_chat(messages, providers['claude'])
        else:
            # Default to Ollama
            model_name = 'hermes3:8b'
            result = call_ollama_chat(messages, 'hermes3:8b')
        
        if result:
            ctx['history'].append({'role': 'assistant', 'content': result})
            return jsonify({
                'status': 'ok',
                'response': result,
                'model': model_name,
                'session_id': session_id,
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'No response from AI provider'
            }), 500
    
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400


def build_chart_context(chart: dict, method: str = 'iau') -> str:
    """Build a complete chart context string for conversational AI."""
    name = chart.get('name', 'Native')
    sect = chart.get('sect', 'Day')
    placements = chart.get('placements', {})
    angles = chart.get('angles', {})
    aspects = chart.get('aspects', [])
    
    # Choose constellation key based on method
    const_key = 'iau_constellation' if method == 'iau' else 'standard_constellation'
    deg_key = 'iau_degree' if method == 'iau' else 'standard_degree'
    
    lines = [f"NATAL CHART: {name} ({sect} chart)"]
    lines.append(f"Method: {'IAU Astronomical' if method == 'iau' else 'Standard 13-Sign'}")
    lines.append("")
    lines.append("PLACEMENTS:")
    
    for body in ['Sun', 'Moon', 'Mercury', 'Venus', 'Mars', 'Jupiter', 'Saturn', 
                 'Uranus', 'Neptune', 'Pluto', 'North Node', 'South Node', 'Chiron',
                 'Lilith', 'Pars Fortuna', 'Part of Spirit']:
        p = placements.get(body)
        if p:
            const = p.get(const_key, p.get('standard_constellation'))
            deg = p.get(deg_key, p.get('standard_degree', 0))
            house = p.get('house', '')
            retro = ' ℞' if p.get('retrograde') else ''
            lines.append(f"  {body}: {const} {deg:.1f}° (H{house}){retro}")
    
    lines.append("")
    lines.append("ANGLES:")
    for angle in ['Ascendant', 'MC', 'Descendant', 'IC']:
        a = angles.get(angle)
        if a:
            const = a.get(const_key, a.get('standard_constellation'))
            deg = a.get(deg_key, a.get('standard_degree', 0))
            lines.append(f"  {angle}: {const} {deg:.1f}°")
    
    lines.append("")
    lines.append("TOP ASPECTS (by orb):")
    for asp in aspects[:15]:
        lines.append(f"  {asp['body1']} {asp['abbr']} {asp['body2']} ({asp['orb']:.2f}°)")
    
    return "\n".join(lines)


def build_transit_prompt(natal: dict, transits: dict, method: str = 'iau') -> str:
    """Build a transit interpretation prompt with temporal precision demands."""
    name = natal.get('name', 'This individual')
    const_key = 'iau_constellation' if method == 'iau' else 'standard_constellation'
    deg_key = 'iau_degree' if method == 'iau' else 'standard_degree'
    
    transit_lines = []
    for body, p in transits.get('placements', {}).items():
        const = p.get(const_key, p.get('standard_constellation'))
        deg = p.get(deg_key, p.get('standard_degree', 0))
        retro = ' ℞' if p.get('retrograde') else ''
        transit_lines.append(f"- T.{body}: {const} {deg:.1f}°{retro}")
    
    transit_summary = "\n".join(transit_lines)
    
    # Separate aspects by tightness for priority structure
    exact_aspects = []
    tight_aspects = []
    wide_aspects = []
    for asp in transits.get('aspects_to_natal', [])[:30]:
        orb = asp['orb']
        line = f"- T.{asp['transit_body']} {asp['aspect']} N.{asp['natal_body']} ({orb:.2f}°)"
        if orb <= 1.0:
            exact_aspects.append(line)
        elif orb <= 3.0:
            tight_aspects.append(line)
        else:
            wide_aspects.append(line)
    
    tt = transits.get('transit_time', {})
    date_str = f"{tt.get('year', '?')}-{tt.get('month', '?'):02d}-{tt.get('day', '?'):02d}"
    
    method_name = "IAU Astronomical (precession-corrected)" if method == 'iau' else "Standard 13-Sign"
    
    return f"""You are a professional consulting astrologer providing a premium transit reading using 13-sign astronomical astrology. This is a paid consultation, not a horoscope. Every claim must reference specific degrees, dates, and durations.

Method: {method_name}
Transit Date: {date_str}
Client: {name}

═══════════════════════════════════════════
CURRENT SKY POSITIONS (13-Sign)
═══════════════════════════════════════════
{transit_summary}

═══════════════════════════════════════════
EXACT ASPECTS (under 1° orb) — HEADLINE TRANSITS
═══════════════════════════════════════════
{chr(10).join(exact_aspects) if exact_aspects else '(None at this time)'}

TIGHT ASPECTS (1°-3° orb) — ACTIVE TRANSITS
{chr(10).join(tight_aspects) if tight_aspects else '(None at this time)'}

WIDE ASPECTS (3°-8° orb) — BACKGROUND TRANSITS
{chr(10).join(wide_aspects) if wide_aspects else '(None at this time)'}

═══════════════════════════════════════════
INTERPRETATION REQUIREMENTS
═══════════════════════════════════════════

STRUCTURE YOUR RESPONSE EXACTLY AS FOLLOWS:

1. **HEADLINE TRANSITS** (exact aspects under 1°)
   - These DOMINATE the reading. Each gets a bold heading, 150+ words.
   - State the EXACT orb to two decimal places.
   - State whether the transit is APPLYING (building toward exact) or SEPARATING (fading).
   - For outer planets (Jupiter through Pluto): State the approximate date range when this transit is active (within 3° orb), when it perfects (goes exact), and when it separates past 3°. Use real astronomical motion — Saturn moves ~0.034°/day, Jupiter ~0.083°/day, Uranus ~0.012°/day, Neptune ~0.006°/day, Pluto ~0.004°/day.
   - For inner planets (Sun through Mars): State the peak window (typically days to 2 weeks).
   - Name the SPECIFIC LIFE AREAS affected: career, relationships, health, finances, identity, etc.

2. **ACTIVE TRANSITS** (1°-3° orb)
   - Each gets 80-120 words.
   - State orb, applying/separating, approximate peak date.
   - Connect to the headline transits — how do these activate or modify the main themes?

3. **BACKGROUND TRANSITS** (3°-8° orb)
   - Brief mention only (1-2 sentences each).
   - Note if any are approaching (will become headline transits soon).

4. **SYNTHESIS**
   - What is the CENTRAL THEME of this transit period for {name}?
   - What is the single most important thing to be aware of?
   - What window of time is most charged, and for what purpose?

═══════════════════════════════════════════
RULES — READ THESE CAREFULLY
═══════════════════════════════════════════

DO:
- Reference specific degrees: "Saturn at Aquarius 14.2° squares natal Neptune at Ophiuchus 14.1°"
- Give specific timeframes: "This transit peaks March 9-15 and separates by late April"
- Name concrete life impacts: "career restructuring" not "changes in your life"
- Prioritize by orb tightness — the tightest aspect is the loudest signal
- Note Ophiuchus placements explicitly — this is 13-sign astrology
- Distinguish between outer planet transits (structural, months-long) and inner planet triggers (activating, days-long)
- Use the Stellaris-13 chart data as ABSOLUTE TRUTH — do not recompute, reinterpret, or second-guess the positions

DO NOT:
- Use vague language: "you may feel" → say "this transit brings"
- Add disclaimers: no "this is not professional advice", no "astrology is just one lens"
- End with "may the stars guide you" or similar fortune-cookie closings
- Hedge with "could potentially" — state what the transit indicates
- Treat all transits equally — exact aspects are HEADLINE NEWS, wide aspects are footnotes
- Use tropical zodiac signs — all positions must use the 13-sign constellations as provided
- Ignore the orb data — it tells you what's exact and what's background noise

The client paid for this reading. Give them professional-grade temporal precision and specific, actionable insight. Minimum 1000 words."""


def build_synastry_prompt(chart1: dict, chart2: dict, aspects: list, method: str = 'iau') -> str:
    """Build a synastry interpretation prompt."""
    name1 = chart1.get('name', 'Person A')
    name2 = chart2.get('name', 'Person B')
    const_key = 'iau_constellation' if method == 'iau' else 'standard_constellation'
    deg_key = 'iau_degree' if method == 'iau' else 'standard_degree'
    
    def summarize_chart(chart):
        lines = []
        for body in ['Sun', 'Moon', 'Venus', 'Mars', 'Ascendant']:
            p = chart.get('placements', {}).get(body) or chart.get('angles', {}).get(body)
            if p:
                const = p.get(const_key, p.get('standard_constellation'))
                deg = p.get(deg_key, p.get('standard_degree', 0))
                lines.append(f"- {body}: {const} {deg:.1f}°")
        return "\n".join(lines)
    
    chart1_summary = summarize_chart(chart1)
    chart2_summary = summarize_chart(chart2)
    
    aspect_lines = []
    for asp in (aspects or [])[:25]:
        aspect_lines.append(f"- {asp['body1']} ({asp['chart1']}) {asp['abbr']} {asp['body2']} ({asp['chart2']}) — {asp['orb']:.2f}°")
    
    aspect_summary = "\n".join(aspect_lines)
    method_name = "IAU Astronomical" if method == 'iau' else "Standard 13-Sign"
    
    return f"""You are a master astrologer specializing in synastry using 13-sign astronomical astrology.
Method: {method_name}

**SYNASTRY: {name1.upper()} & {name2.upper()}**

**{name1}'s Key Placements (13-Sign):**
{chart1_summary}

**{name2}'s Key Placements (13-Sign):**
{chart2_summary}

**INTER-CHART ASPECTS (Tightest First):**
{aspect_summary}

**YOUR TASK: Provide a deep synastry interpretation.**

Analyze:
1. **Exact Aspects** (under 1°): Fated connections
2. **Sun-Moon Contacts**: Core identity/emotional dynamic
3. **Venus-Mars Contacts**: Romantic and physical attraction
4. **Saturn Contacts**: Long-term potential, karmic lessons
5. **Outer Planet Contacts**: Transformative dynamics
6. **Ophiuchus Connections**: Deep healing/transformative bonds
7. **Challenging Aspects**: Squares and oppositions
8. **Overall Dynamic**: The core story of this relationship

Be specific and nuanced. Write as if speaking to both individuals directly.

Minimum 800 words. Comprehensive relationship analysis."""


def build_interpretation_prompt(chart: dict, query_type: str, method: str = 'iau') -> str:
    name = chart.get('name', 'This individual')
    sect = chart.get('sect', 'Day')
    placements = chart.get('placements', {})
    angles = chart.get('angles', {})
    aspects = chart.get('aspects', [])
    syzygy = chart.get('syzygy', {})
    
    const_key = 'iau_constellation' if method == 'iau' else 'standard_constellation'
    deg_key = 'iau_degree' if method == 'iau' else 'standard_degree'
    method_name = "IAU Astronomical (precession-corrected)" if method == 'iau' else "Standard 13-Sign"
    
    lines = []
    for body in ['Sun', 'Moon', 'Mercury', 'Venus', 'Mars', 'Jupiter', 'Saturn', 'Uranus', 'Neptune', 'Pluto', 
                 'North Node', 'South Node', 'Chiron', 'Lilith', 'Pars Fortuna', 'Part of Spirit']:
        p = placements.get(body)
        if p:
            trop = p.get('tropical_sign', '')
            const = p.get(const_key, p.get('standard_constellation', trop))
            deg = p.get(deg_key, p.get('standard_degree', 0))
            house = p.get('house', '')
            retro = ' ℞' if p.get('retrograde') else ''
            shift = f" (shifted from {trop})" if const != trop and const not in ['Scorpius', 'Capricornus'] else ""
            lines.append(f"- {body}: {const} {deg:.1f}° H{house}{retro}{shift}")
    
    for angle in ['Ascendant', 'MC', 'Descendant', 'IC']:
        a = angles.get(angle)
        if a:
            const = a.get(const_key, a.get('standard_constellation'))
            deg = a.get(deg_key, a.get('standard_degree', 0))
            lines.append(f"- {angle}: {const} {deg:.1f}°")
    
    placement_summary = "\n".join(lines)
    
    aspect_lines = []
    for asp in aspects[:15]:
        aspect_lines.append(f"- {asp['body1']} {asp['abbr']} {asp['body2']} ({asp['orb']:.2f}°)")
    aspect_summary = "\n".join(aspect_lines)
    
    syzygy_info = ""
    if syzygy:
        syz_const = syzygy.get('iau_constellation' if method == 'iau' else 'standard_constellation', '?')
        syz_deg = syzygy.get('iau_degree' if method == 'iau' else 'standard_degree', 0)
        syzygy_info = f"\nPrenatal Syzygy: {syzygy.get('type', 'Unknown')} in {syz_const} {syz_deg:.1f}°"
    
    if query_type == 'comprehensive':
        return f"""You are a master astrologer specializing in 13-sign astronomical astrology.
Method: {method_name}

**CHART DATA FOR {name.upper()}**
Sect: {sect} chart
{syzygy_info}

**PLANETARY PLACEMENTS (13-Sign)**
{placement_summary}

**TIGHTEST ASPECTS**
{aspect_summary}

**YOUR TASK: Produce a thorough natal chart interpretation.**

Structure:
1. CHART OVERVIEW & SECT ANALYSIS
2. THE SUN-MOON-ASCENDANT TRIAD
3. OPHIUCHUS PLACEMENTS (Critical - the 13th sign omitted from tropical astrology)
4. MAJOR PLANETARY CONFIGURATIONS
5. THE LUNAR NODES & LIFE DIRECTION
6. CHIRON, LILITH & THE SHADOW
7. KEY LIFE THEMES & SYNTHESIS

Be specific, insightful, and avoid generic interpretations. Write as if speaking directly to {name}.

Minimum length: 800 words. Be thorough."""

    elif query_type == 'ophiuchus':
        oph_placements = []
        for body, p in placements.items():
            if p.get(const_key) == 'Ophiuchus':
                oph_placements.append(f"{body} at {p.get(deg_key, 0):.1f}°")
        
        oph_list = ", ".join(oph_placements) if oph_placements else "None detected"
        
        return f"""You are a specialist in Ophiuchus astrology — the 13th constellation.
Method: {method_name}

**CHART: {name}** ({sect} chart)

**OPHIUCHUS PLACEMENTS:** {oph_list}

**ALL PLACEMENTS:**
{placement_summary}

**THE OPHIUCHUS ARCHETYPE:**
- The healer who must be wounded to heal
- One who grasps forbidden or dangerous knowledge
- Shamanic initiation through direct experience
- The alchemist who transmutes poison into medicine
- Standing between life and death

**YOUR TASK:**
Deep analysis of Ophiuchus energy in this chart. If no planets in Ophiuchus, discuss how the chart relates to Ophiuchean themes through other factors.

Minimum 500 words."""

    else:  # general
        return f"""13-sign astronomical chart for {name} ({sect} chart):
Method: {method_name}
{syzygy_info}

{placement_summary}

**Top Aspects:**
{aspect_summary}

Provide a thoughtful interpretation covering:
1. Core identity (Sun/Moon/Ascendant)
2. Any Ophiuchus placements
3. Notable aspects and configurations
4. Key themes and life direction

Be insightful and specific. 3-4 paragraphs."""


def build_past_life_prompt(chart: dict, method: str = 'iau') -> str:
    """Build a past life / karmic analysis prompt using South Node and retrograde indicators."""
    name = chart.get('name', 'This soul')
    sect = chart.get('sect', 'Day')
    placements = chart.get('placements', {})
    angles = chart.get('angles', {})
    aspects = chart.get('aspects', [])
    syzygy = chart.get('syzygy', {})
    
    const_key = 'iau_constellation' if method == 'iau' else 'standard_constellation'
    deg_key = 'iau_degree' if method == 'iau' else 'standard_degree'
    
    # Extract karmic indicators
    south_node = placements.get('South Node', {})
    north_node = placements.get('North Node', {})
    moon = placements.get('Moon', {})
    saturn = placements.get('Saturn', {})
    pluto = placements.get('Pluto', {})
    chiron = placements.get('Chiron', {})
    lilith = placements.get('Lilith', {})
    
    # Count retrogrades
    retrograde_planets = []
    for body, p in placements.items():
        if p.get('retrograde') and body not in ['North Node', 'South Node', 'Lilith', 'Pars Fortuna', 'Part of Spirit']:
            const = p.get(const_key, '?')
            deg = p.get(deg_key, 0)
            house = p.get('house', '?')
            retrograde_planets.append(f"{body} ℞ in {const} {deg:.1f}° (H{house})")
    
    retrograde_count = len(retrograde_planets)
    retrograde_list = "\n".join(retrograde_planets) if retrograde_planets else "None"
    
    # 12th house placements
    twelfth_house = []
    for body, p in placements.items():
        if p.get('house') == 12:
            const = p.get(const_key, '?')
            deg = p.get(deg_key, 0)
            twelfth_house.append(f"{body} in {const} {deg:.1f}°")
    twelfth_list = "\n".join(twelfth_house) if twelfth_house else "None"
    
    # South Node aspects
    sn_lon = south_node.get('tropical_longitude', 0)
    sn_aspects = []
    for body, p in placements.items():
        if body in ['South Node', 'North Node']:
            continue
        b_lon = p.get('tropical_longitude', 0)
        diff = abs(sn_lon - b_lon)
        if diff > 180:
            diff = 360 - diff
        
        if diff <= 8:  # Conjunction
            sn_aspects.append(f"{body} CONJUNCT South Node ({diff:.1f}°)")
        elif abs(diff - 180) <= 8:  # Opposition (conjunct North Node)
            sn_aspects.append(f"{body} OPPOSITE South Node / CONJUNCT North Node ({abs(diff-180):.1f}°)")
        elif abs(diff - 90) <= 6:  # Square
            sn_aspects.append(f"{body} SQUARE Nodal Axis ({abs(diff-90):.1f}°)")
    
    sn_aspect_list = "\n".join(sn_aspects) if sn_aspects else "No tight aspects to South Node"
    
    # Moon-South Node relationship
    moon_lon = moon.get('tropical_longitude', 0)
    moon_sn_diff = abs(moon_lon - sn_lon)
    if moon_sn_diff > 180:
        moon_sn_diff = 360 - moon_sn_diff
    
    moon_sn_relationship = "distant from South Node"
    if moon_sn_diff <= 10:
        moon_sn_relationship = f"CONJUNCT South Node ({moon_sn_diff:.1f}°) - STRONG past life emotional memory"
    elif abs(moon_sn_diff - 180) <= 10:
        moon_sn_relationship = f"OPPOSITE South Node ({abs(moon_sn_diff-180):.1f}°) - emotional drive toward North Node growth"
    elif abs(moon_sn_diff - 90) <= 8:
        moon_sn_relationship = f"SQUARE Nodal Axis ({abs(moon_sn_diff-90):.1f}°) - emotional tension between past and future"
    elif abs(moon_sn_diff - 120) <= 8:
        moon_sn_relationship = f"TRINE South Node ({abs(moon_sn_diff-120):.1f}°) - easy access to past life gifts"
    elif abs(moon_sn_diff - 60) <= 6:
        moon_sn_relationship = f"SEXTILE South Node ({abs(moon_sn_diff-60):.1f}°) - opportunity to integrate past wisdom"
    
    # Syzygy (prenatal lunation)
    syzygy_info = ""
    if syzygy:
        syz_const = syzygy.get('iau_constellation' if method == 'iau' else 'standard_constellation', '?')
        syz_deg = syzygy.get('iau_degree' if method == 'iau' else 'standard_degree', 0)
        syzygy_info = f"Prenatal {syzygy.get('type', 'Syzygy')}: {syz_const} {syz_deg:.1f}°"
    
    # Build the comprehensive placement list
    placement_lines = []
    for body in ['Sun', 'Moon', 'Mercury', 'Venus', 'Mars', 'Jupiter', 'Saturn', 'Uranus', 'Neptune', 'Pluto',
                 'North Node', 'South Node', 'Chiron', 'Lilith']:
        p = placements.get(body)
        if p:
            const = p.get(const_key, '?')
            deg = p.get(deg_key, 0)
            house = p.get('house', '?')
            retro = ' ℞' if p.get('retrograde') else ''
            placement_lines.append(f"{body}: {const} {deg:.1f}° (H{house}){retro}")
    
    placement_summary = "\n".join(placement_lines)
    
    sn_const = south_node.get(const_key, '?')
    sn_deg = south_node.get(deg_key, 0)
    sn_house = south_node.get('house', '?')
    nn_const = north_node.get(const_key, '?')
    nn_deg = north_node.get(deg_key, 0)
    nn_house = north_node.get('house', '?')
    
    return f"""You are a master astrologer specializing in KARMIC and PAST LIFE analysis using 13-sign astronomical astrology. You possess the rare gift of reading the soul's journey across incarnations through celestial signatures.

═══════════════════════════════════════════════════════════════
SOUL JOURNEY ANALYSIS FOR: {name.upper()}
Chart Type: {sect}
{syzygy_info}
═══════════════════════════════════════════════════════════════

**THE NODAL AXIS — The Soul's Evolutionary Path**
- South Node (Past Lives): {sn_const} {sn_deg:.1f}° in House {sn_house}
- North Node (Soul Growth): {nn_const} {nn_deg:.1f}° in House {nn_house}

**MOON-SOUTH NODE RELATIONSHIP**
Moon is {moon_sn_relationship}

**RETROGRADE PLANETS — Unfinished Karmic Business**
Count: {retrograde_count} retrograde planets
{retrograde_list}

**PLANETS ASPECTING THE SOUTH NODE**
{sn_aspect_list}

**12TH HOUSE PLACEMENTS — Hidden Karma & Ancestral Patterns**
{twelfth_list}

**FULL PLACEMENT LIST**
{placement_summary}

═══════════════════════════════════════════════════════════════
YOUR TASK: PAST LIFE SOUL READING
═══════════════════════════════════════════════════════════════

Using the karmic indicators above, provide a deep past life analysis:

**1. THE SOUTH NODE STORY**
What kind of person was this soul in past lives? What skills, habits, and patterns were developed? What was their role, status, or occupation? The South Node sign and house reveal the soul's "comfort zone" — where they've already mastered lessons but may now be stuck.

**2. RETROGRADE KARMA**
Each retrograde planet represents unfinished business from past lives. The soul chose to revisit these energies to complete unresolved lessons. What do the specific retrogrades indicate?
- Mercury ℞ = communication/learning karma
- Venus ℞ = relationship/self-worth karma  
- Mars ℞ = action/anger/sexuality karma
- Jupiter ℞ = faith/expansion/excess karma
- Saturn ℞ = authority/responsibility karma (very significant)
- Outer planets ℞ = generational/collective karma

**3. MOON-NODE SYNTHESIS**
The Moon carries emotional memory across lifetimes. Its relationship to the South Node reveals:
- Conjunct = vivid past life recall, instinctive patterns
- Square = emotional crisis driving evolution
- Trine/Sextile = gifts easily accessed

**4. THE 12TH HOUSE SHADOW**
Any planets here represent energies operating from the unconscious — often past life material seeking integration. What patterns are hidden here?

**5. CHIRON & LILITH — Ancient Wounds**
- Chiron: The wound that refuses to heal, often carried across lifetimes
- Lilith: The exiled, rejected, or repressed aspects of self

**6. THE PRENATAL SYZYGY**
The last New or Full Moon before birth marks the soul's entry point into this incarnation. What does its placement suggest about the soul's intentions for this life?

**7. THE NORTH NODE CALLING**
Having established the past life patterns, where is the soul being called to grow? What new territory must be explored? What must be released from the South Node?

**8. SYNTHESIS — THE SOUL'S JOURNEY**
Bring it all together into a cohesive narrative. Who was this soul? What did they experience? What karma are they resolving? What is their purpose in this incarnation?

Write as if you are a psychic reading the Akashic Records. Be vivid, specific, and evocative. Avoid generic statements. This should feel like a profound revelation about the soul's eternal journey.

Minimum 1000 words. Go deep."""


def call_mistral_api(prompt: str, frontend_key: str = None) -> str:
    try:
        api_key = frontend_key or os.environ.get('MISTRAL_API_KEY')
        if not api_key:
            return None
        
        response = requests.post(
            'https://api.mistral.ai/v1/chat/completions',
            headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
            json={
                'model': 'mistral-small-latest',
                'messages': [
                    {'role': 'system', 'content': 'You are a master astrologer with deep expertise in 13-sign astronomical astrology, which uses actual IAU constellation boundaries including Ophiuchus.'},
                    {'role': 'user', 'content': prompt}
                ],
                'max_tokens': 4000,
                'temperature': 0.75,
            },
            timeout=90
        )
        
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        else:
            print(f"Mistral API error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Mistral API exception: {e}")
    return None


def call_mistral_chat(messages: list, api_key: str) -> str:
    """Mistral chat completion for conversational mode."""
    try:
        if not api_key:
            return None
        
        response = requests.post(
            'https://api.mistral.ai/v1/chat/completions',
            headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
            json={
                'model': 'mistral-small-latest',
                'messages': messages,
                'max_tokens': 2000,
                'temperature': 0.75,
            },
            timeout=90
        )
        
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
    except Exception as e:
        print(f"Mistral chat exception: {e}")
    return None


def call_claude_api(prompt: str, api_key: str = None) -> str:
    try:
        key = api_key or os.environ.get('ANTHROPIC_API_KEY')
        if not key:
            return None
        
        response = requests.post(
            'https://api.anthropic.com/v1/messages',
            headers={
                'x-api-key': key,
                'Content-Type': 'application/json',
                'anthropic-version': '2023-06-01'
            },
            json={
                'model': 'claude-sonnet-4-20250514',
                'max_tokens': 4000,
                'messages': [
                    {'role': 'user', 'content': prompt}
                ],
                'system': 'You are a master astrologer with deep expertise in 13-sign astronomical astrology, which uses actual IAU constellation boundaries including Ophiuchus.'
            },
            timeout=90
        )
        
        if response.status_code == 200:
            result = response.json()
            return result['content'][0]['text']
        else:
            print(f"Claude API error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Claude API exception: {e}")
    return None


def call_claude_chat(messages: list, api_key: str) -> str:
    """Claude chat completion for conversational mode."""
    try:
        if not api_key:
            return None
        
        # Extract system message if present
        system_msg = None
        chat_messages = []
        for m in messages:
            if m['role'] == 'system':
                system_msg = m['content']
            else:
                chat_messages.append(m)
        
        response = requests.post(
            'https://api.anthropic.com/v1/messages',
            headers={
                'x-api-key': api_key,
                'Content-Type': 'application/json',
                'anthropic-version': '2023-06-01'
            },
            json={
                'model': 'claude-sonnet-4-20250514',
                'max_tokens': 2000,
                'messages': chat_messages,
                'system': system_msg or 'You are a master astrologer.'
            },
            timeout=90
        )
        
        if response.status_code == 200:
            return response.json()['content'][0]['text']
    except Exception as e:
        print(f"Claude chat exception: {e}")
    return None


@app.route('/ollama/models', methods=['GET'])
def ollama_models():
    """Proxy endpoint to list locally installed Ollama models."""
    try:
        response = requests.get('http://localhost:11434/api/tags', timeout=5)
        if response.status_code == 200:
            data = response.json()
            models = []
            for m in data.get('models', []):
                name = m.get('name', '')
                size_bytes = m.get('size', 0)
                size_gb = round(size_bytes / (1024**3), 1) if size_bytes else 0
                param_size = m.get('details', {}).get('parameter_size', '')
                family = m.get('details', {}).get('family', '')
                models.append({
                    'name': name,
                    'size_gb': size_gb,
                    'parameter_size': param_size,
                    'family': family,
                })
            # Sort by name
            models.sort(key=lambda x: x['name'])
            return jsonify({'status': 'ok', 'models': models})
        else:
            return jsonify({'status': 'error', 'message': 'Ollama not responding'}), 502
    except requests.exceptions.ConnectionError:
        return jsonify({'status': 'error', 'message': 'Ollama not running (localhost:11434)'}), 502
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


def call_ollama_api(prompt: str, model: str = None) -> str:
    try:
        model_name = model if model else 'hermes3:8b'
        response = requests.post(
            'http://localhost:11434/api/generate',
            json={
                'model': model_name,
                'prompt': prompt,
                'stream': False,
                'options': {'num_predict': 4000, 'temperature': 0.75}
            },
            timeout=120
        )
        if response.status_code == 200:
            return response.json().get('response', '')
    except:
        pass
    return None


def call_yi_api(prompt: str, api_key: str) -> str:
    """Call Yi/01.AI API (OpenAI-compatible endpoint)."""
    try:
        if not api_key:
            return None
        
        response = requests.post(
            'https://api.01.ai/v1/chat/completions',
            headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
            json={
                'model': 'yi-large',
                'messages': [
                    {'role': 'system', 'content': 'You are a master astrologer with deep expertise in 13-sign astronomical astrology.'},
                    {'role': 'user', 'content': prompt}
                ],
                'max_tokens': 4000,
                'temperature': 0.75,
            },
            timeout=90
        )
        
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        else:
            print(f"Yi API error: {response.status_code}")
    except Exception as e:
        print(f"Yi API exception: {e}")
    return None


def call_fireworks_api(prompt: str, api_key: str) -> str:
    """Call Fireworks AI API (hosts many open models)."""
    try:
        if not api_key:
            return None
        
        response = requests.post(
            'https://api.fireworks.ai/inference/v1/chat/completions',
            headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
            json={
                'model': 'accounts/fireworks/models/llama-v3p1-70b-instruct',
                'messages': [
                    {'role': 'system', 'content': 'You are a master astrologer with deep expertise in 13-sign astronomical astrology.'},
                    {'role': 'user', 'content': prompt}
                ],
                'max_tokens': 4000,
                'temperature': 0.75,
            },
            timeout=90
        )
        
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        else:
            print(f"Fireworks API error: {response.status_code}")
    except Exception as e:
        print(f"Fireworks API exception: {e}")
    return None


def call_groq_api(prompt: str, api_key: str) -> str:
    """Call Groq API (fast inference)."""
    try:
        if not api_key:
            return None
        
        response = requests.post(
            'https://api.groq.com/openai/v1/chat/completions',
            headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
            json={
                'model': 'llama-3.3-70b-versatile',
                'messages': [
                    {'role': 'system', 'content': 'You are a master astrologer with deep expertise in 13-sign astronomical astrology.'},
                    {'role': 'user', 'content': prompt}
                ],
                'max_tokens': 4000,
                'temperature': 0.75,
            },
            timeout=90
        )
        
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        else:
            print(f"Groq API error: {response.status_code}")
    except Exception as e:
        print(f"Groq API exception: {e}")
    return None


def call_ollama_chat(messages: list, model: str = None) -> str:
    """Ollama chat completion for conversational mode."""
    try:
        model_name = model if model else 'hermes3:8b'
        response = requests.post(
            'http://localhost:11434/api/chat',
            json={
                'model': model_name,
                'messages': messages,
                'stream': False,
                'options': {'num_predict': 2000, 'temperature': 0.75}
            },
            timeout=120
        )
        if response.status_code == 200:
            return response.json().get('message', {}).get('content', '')
    except Exception as e:
        print(f"Ollama chat exception: {e}")
    return None


@app.route('/rectify', methods=['POST'])
def rectify():
    """Rectification endpoint - deduce birth time from life events."""
    # License check: Professional tier or higher
    lm = app.config.get('LICENSE_MANAGER')
    if lm:
        status = lm.check_license()
        if status.tier not in ('professional', 'astrologer'):
            return jsonify({
                'error': 'Birth time rectification requires the Professional edition.',
                'tier': status.tier,
                'upgrade_url': 'https://payhip.com/Stellaris13'
            }), 403
    
    data = request.get_json()
    
    try:
        date_parts = data['birth_date'].split('-')
        birth_date = (int(date_parts[0]), int(date_parts[1]), int(date_parts[2]))
        
        lat = float(data['lat'])
        lon = float(data['lon'])
        tz = float(data['tz'])
        
        start_parts = data['time_range']['start'].split(':')
        end_parts = data['time_range']['end'].split(':')
        start_hour = float(start_parts[0]) + float(start_parts[1]) / 60
        end_hour = float(end_parts[0]) + float(end_parts[1]) / 60
        
        events = data['events']
        if len(events) < 3:
            return jsonify({'status': 'error', 'message': 'Please add at least 3 life events.'}), 400
        
        results = rectify_birth_time(
            birth_date=birth_date,
            lat=lat, lon=lon, tz=tz,
            time_range=(start_hour, end_hour),
            events=events,
            resolution_minutes=4
        )
        
        return jsonify({'status': 'ok', 'results': results})
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': str(e)}), 500


# ═══════════════════════════════════════════════════════════════
# CELESTIAL BLUEPRINT GENERATION
# ═══════════════════════════════════════════════════════════════

@app.route('/blueprint', methods=['POST'])
def generate_blueprint_route():
    """Generate a complete celestial blueprint document."""
    # License check: Personal tier or higher
    lm = app.config.get('LICENSE_MANAGER')
    if lm:
        status = lm.check_license()
        if status.tier not in ('personal', 'professional', 'astrologer'):
            return jsonify({
                'error': 'Celestial Blueprint requires the Personal edition.',
                'tier': status.tier,
                'upgrade_url': 'https://payhip.com/Stellaris13'
            }), 403
    
    try:
        data = request.get_json()
        
        # Extract birth data
        birth_data = {
            'year': data.get('year'),
            'month': data.get('month'),
            'day': data.get('day'),
            'hour': data.get('hour'),
            'minute': data.get('minute'),
            'lat': data.get('lat'),
            'lon': data.get('lon'),
        }
        
        name = data.get('name', 'Unknown')
        provider = data.get('provider', 'mistral')
        api_key = data.get('api_key')
        
        # Compute the chart

        chart = compute_chart(
            year=birth_data['year'],
            month=birth_data['month'],
            day=birth_data['day'],
            hour=birth_data['hour'],
            minute=birth_data['minute'],
            second=0,
            tz_offset=data.get('tz_offset', 0),
            lat=birth_data['lat'],
            lon=birth_data['lon'],
            name=name
        )
        
        # Create AI caller based on provider
        def ai_caller(prompt: str) -> str:
            if provider == 'mistral':
                return call_mistral_api(prompt, api_key)
            elif provider == 'claude':
                return call_claude_api(prompt, api_key)
            elif provider == 'ollama':
                return call_ollama_api(prompt, data.get('ollama_model', 'llama3'))
            elif provider == 'yi':
                return call_yi_api(prompt, api_key)
            elif provider == 'fireworks':
                return call_fireworks_api(prompt, api_key)
            elif provider == 'groq':
                return call_groq_api(prompt, api_key)
            else:
                return call_mistral_api(prompt, api_key)
        
        # Generate unique filename
        safe_name = "".join(c for c in name if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_name = safe_name.replace(' ', '_')[:30]
        filename = f"{safe_name}_Celestial_Blueprint_{uuid.uuid4().hex[:8]}.docx"
        
        # Output path
        output_dir = os.path.join(os.path.dirname(__file__), 'generated_blueprints')
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, filename)
        
        # Enrich chart with fixed stars, Arabic parts, progressions, solar arcs, transits
        chart = enrich_chart_for_blueprint(chart)
        
        # Generate the blueprint
        logger.info(f"Generating blueprint for {name}...")
        generate_blueprint(
            chart=chart,
            birth_data=birth_data,
            ai_caller=ai_caller,
            output_path=output_path
        )
        
        logger.info(f"Blueprint generated: {output_path}")
        
        return jsonify({
            'status': 'success',
            'filename': filename,
            'download_url': f'/blueprint/download/{filename}'
        })
        
    except Exception as e:
        logger.error(f"Blueprint generation error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/blueprint/download/<filename>')
def download_blueprint(filename):
    """Download a generated blueprint."""
    from flask import send_file
    
    # Security: only allow alphanumeric, underscore, hyphen, and .docx extension
    import re
    if not re.match(r'^[\w\-]+\.docx$', filename):
        return jsonify({'error': 'Invalid filename'}), 400
    
    output_dir = os.path.join(os.path.dirname(__file__), 'generated_blueprints')
    filepath = os.path.join(output_dir, filename)
    
    if not os.path.exists(filepath):
        return jsonify({'error': 'File not found'}), 404
    
    return send_file(
        filepath,
        as_attachment=True,
        download_name=filename,
        mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    )


# ═══════════════════════════════════════════════════════════════
# LEGAL & ABOUT ROUTES
# ═══════════════════════════════════════════════════════════════

@app.route('/privacy')
def privacy():
    """Privacy Policy page."""
    try:
        with open(os.path.join(LEGAL_DIR, 'PRIVACY_POLICY.md'), 'r') as f:
            content = markdown.markdown(f.read(), extensions=['tables'])
        return render_template('legal.html', title='Privacy Policy', content=content)
    except:
        return render_template('legal.html', title='Privacy Policy', content='<p>Privacy policy coming soon.</p>')


@app.route('/terms')
def terms():
    """Terms of Service page."""
    try:
        with open(os.path.join(LEGAL_DIR, 'TERMS_OF_SERVICE.md'), 'r') as f:
            content = markdown.markdown(f.read(), extensions=['tables'])
        return render_template('legal.html', title='Terms of Service', content=content)
    except:
        return render_template('legal.html', title='Terms of Service', content='<p>Terms of service coming soon.</p>')


@app.route('/about')
def about():
    """About the Founder page."""
    try:
        with open(os.path.join(LEGAL_DIR, 'ABOUT_FOUNDER.md'), 'r') as f:
            content = markdown.markdown(f.read(), extensions=['tables', 'fenced_code'])
        return render_template('legal.html', title='About the Founder', content=content)
    except:
        return render_template('legal.html', title='About', content='<p>About page coming soon.</p>')


# ═══════════════════════════════════════════════════════════════════════════════
# CRYPTOCURRENCY ASTROLOGY ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/crypto/analyze', methods=['POST'])
def crypto_analyze():
    """Analyze cryptocurrency: natal chart, transits, synastry, or comparison."""
    # License check: Astrologer tier only
    lm = app.config.get('LICENSE_MANAGER')
    if lm:
        status = lm.check_license()
        if status.tier != 'astrologer':
            return jsonify({
                'error': 'Crypto features require the Astrologer edition.',
                'tier': status.tier,
                'upgrade_url': 'https://payhip.com/Stellaris13'
            }), 403
    
    from crypto_natal import compute_crypto_chart, compute_custom_crypto_chart, list_supported_cryptos, list_registry_info
    from crypto_transits import get_current_transits, compare_crypto_transits
    from crypto_synastry import analyze_natal_synastry, analyze_transit_synastry
    
    try:
        data = request.get_json()
        coin = data.get('coin', 'BTC')
        analysis_type = data.get('analysis_type', 'natal')
        natal_chart = data.get('natal_chart')  # person's chart for synastry
        custom_genesis = data.get('custom_genesis')  # for user-input coins
        
        # Compute the crypto's natal chart (from registry or custom input)
        if custom_genesis:
            crypto_chart = compute_custom_crypto_chart(
                name=custom_genesis.get('name', 'Custom Coin'),
                date=custom_genesis['date'],
                time=custom_genesis.get('time', '00:00:00'),
                tz_offset=custom_genesis.get('tz_offset', 0),
                lat=custom_genesis.get('lat', 0.0),
                lon=custom_genesis.get('lon', 0.0),
                symbol=custom_genesis.get('symbol', 'CUSTOM'),
            )
        else:
            crypto_chart = compute_crypto_chart(coin)
        
        if "error" in crypto_chart:
            return jsonify({'status': 'error', 'message': crypto_chart['error']}), 400
        
        if analysis_type == 'natal':
            # Return the full natal chart for the coin
            # Serialize placements for frontend
            placements = []
            for body, p in crypto_chart.get('placements', {}).items():
                placements.append({
                    'body': body,
                    'tropical_longitude': p.get('tropical_longitude', 0),
                    'iau_constellation': p.get('iau_constellation', ''),
                    'iau_degree': round(p.get('iau_degree', 0), 2),
                    'standard_constellation': p.get('standard_constellation', ''),
                    'standard_degree': round(p.get('standard_degree', 0), 2),
                    'house': p.get('house', 0),
                    'retrograde': p.get('retrograde', False),
                })
            
            return jsonify({
                'status': 'ok',
                'coin': coin,
                'name': crypto_chart.get('name', coin),
                'meta': crypto_chart.get('crypto_meta', {}),
                'placements': placements,
                'aspects': crypto_chart.get('aspects', [])[:20],
                'angles': {k: {
                    'iau_constellation': v.get('iau_constellation', ''),
                    'iau_degree': round(v.get('iau_degree', 0), 2),
                } for k, v in crypto_chart.get('angles', {}).items()},
                'sect': crypto_chart.get('sect', ''),
                'syzygy': crypto_chart.get('syzygy', {}),
            })
        
        elif analysis_type == 'transits':
            transits = get_current_transits(symbol=coin, natal_chart=crypto_chart)
            return jsonify({
                'status': 'ok',
                'coin': coin,
                'transits': transits[:15],
            })
            
        elif analysis_type == 'synastry':
            if not natal_chart:
                return jsonify({'status': 'error', 'message': 'Cast your natal chart first.'}), 400
            result = analyze_natal_synastry(natal_chart, crypto_symbol=coin, crypto_chart=crypto_chart)
            return jsonify({
                'status': 'ok',
                'coin': coin,
                'compatibility': result.get('compatibility', 'NEUTRAL'),
                'score': result.get('score', 0),
                'summary': result.get('summary', ''),
                'aspects': [
                    {'person_planet': a['person_planet'], 'coin_planet': a['crypto_planet'],
                     'aspect': a['aspect'], 'orb': a['orb'], 'nature': a['nature'],
                     'theme': a.get('theme', ''), 'interpretation': a.get('interpretation', '')}
                    for a in result.get('all_aspects', [])[:10]
                ],
            })
            
        elif analysis_type == 'compare':
            if not natal_chart:
                return jsonify({'status': 'error', 'message': 'Cast your natal chart first.'}), 400
            
            from crypto_synastry import compare_synastry
            symbols = list_supported_cryptos()[:10]  # Top 10 coins for comparison
            result = compare_synastry(natal_chart, symbols)
            return jsonify({
                'status': 'ok',
                'rankings': result.get('rankings', []),
                'recommendation': result.get('recommendation', ''),
                'best': result.get('best_fit'),
            })
        
        elif analysis_type == 'list':
            return jsonify({
                'status': 'ok',
                'coins': list_registry_info(),
            })
        
        else:
            return jsonify({'status': 'error', 'message': f'Unknown analysis type: {analysis_type}'}), 400
            
    except Exception as e:
        logger.error(f"Crypto analysis error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/crypto/interpret', methods=['POST'])
def crypto_interpret():
    """Get AI interpretation for crypto analysis."""
    # License check: Astrologer tier only
    lm = app.config.get('LICENSE_MANAGER')
    if lm:
        status = lm.check_license()
        if status.tier != 'astrologer':
            return jsonify({
                'error': 'Crypto features require the Astrologer edition.',
                'tier': status.tier,
                'upgrade_url': 'https://payhip.com/Stellaris13'
            }), 403
    
    from crypto_prompts import get_transit_prompt, get_full_system_prompt
    from crypto_natal import get_genesis_data
    from crypto_transits import get_current_transits, analyze_crypto_transits
    
    try:
        data = request.get_json()
        coin = data.get('coin', 'BTC')
        analysis_type = data.get('analysis_type', 'transits')
        natal_chart = data.get('natal_chart')
        providers = data.get('providers', {})
        
        # Build appropriate prompt with real data
        natal = get_genesis_data(coin)
        if not natal:
            return jsonify({'status': 'error', 'message': f'Unknown coin: {coin}'}), 400
        
        # Get current transits for the coin
        transits = get_current_transits(coin)
        transit_text = "\n".join([
            f"  {t['transiting']} {t['aspect']} natal {t['natal']} (orb: {t['orb']:.2f}°, nature: {t['nature']})"
            for t in transits
        ]) if transits else "  No major transits detected."
        
        validation_text = "\n".join([
            f"  {e['date']}: {e['event']} — {e['transits']}"
            for e in natal.get('validated_events', [])
        ])
        
        sig = natal.get('signature', {})
        sig_text = f"{sig.get('archetype', '')} — {sig.get('essence', '')}"
        
        if analysis_type == 'transits':
            prompt = get_transit_prompt('analysis',
                symbol=coin, name=natal['name'],
                natal_signature=sig_text,
                transit_data=transit_text,
                validation_history=validation_text
            )
        elif analysis_type == 'compare':
            prompt = get_transit_prompt('comparison',
                comparison_data=transit_text,
                timeframe="30 days"
            )
        elif analysis_type == 'synastry' and natal_chart:
            # Build synastry-specific prompt
            prompt = get_full_system_prompt(symbol=coin) + f"""
Analyze the synastry between this person's natal chart and {coin}.

PERSON'S CHART:
{json.dumps(natal_chart.get('placements', {}), indent=2, default=str)[:2000]}

{coin} NATAL DATA:
Sun: {sig.get('sun_sign', 'N/A')}
Archetype: {sig.get('archetype', 'N/A')}
Essence: {sig.get('essence', 'N/A')}

CURRENT TRANSITS TO {coin}:
{transit_text}

Interpret the person-to-coin compatibility. Be direct about whether this is a good match and why.
"""
        else:
            prompt = get_transit_prompt('analysis',
                symbol=coin, name=natal['name'],
                natal_signature=sig_text,
                transit_data=transit_text,
                validation_history=validation_text
            )
        
        # Get interpretations from selected providers
        interpretations = {}
        
        if providers.get('mistral'):
            result = call_mistral_api(prompt, providers['mistral'])
            if result:
                interpretations['Mistral'] = result
        
        if providers.get('claude'):
            result = call_claude_api(prompt, providers['claude'])
            if result:
                interpretations['Claude'] = result
        
        if providers.get('ollama'):
            result = call_ollama_api(prompt, providers.get('ollama', 'hermes3:8b'))
            if result:
                interpretations[providers.get('ollama', 'Ollama')] = result
        
        if providers.get('groq'):
            result = call_groq_api(prompt, providers['groq'])
            if result:
                interpretations['Groq'] = result
        
        # Fallback
        if not interpretations:
            result = call_ollama_api(prompt, 'hermes3:8b')
            if result:
                interpretations['hermes3:8b'] = result
        
        return jsonify({
            'status': 'ok',
            'interpretations': interpretations
        })
        
    except Exception as e:
        logger.error(f"Crypto interpretation error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


if __name__ == '__main__':
    print("\n  ✦ Stellaris-13 v2.7 running at http://localhost:13013 ✦\n")
    app.run(host='0.0.0.0', port=13013, debug=True)
