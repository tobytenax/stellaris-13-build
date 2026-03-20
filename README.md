# Stellaris-13 v2.4

## Astronomical 13-Sign Ephemeris Calculator
### Production-Ready for Worldwide Commercial Release

---

## What's New in v2.4

### 🔧 Bug Fixes
1. **Ollama Model Name Display** - Shows actual model name instead of generic "Ollama"
2. **CLI/GUI Calculation Alignment** - Both use consistent IAU+precession method
3. **Method-Aware AI Prompts** - Respects IAU vs Standard selection

### ✨ New Features
1. **Multi-Provider AI** - Parallel execution for cloud APIs (Mistral, Claude, Yi, Fireworks, Groq)
2. **Multiple Ollama Models** - Comma-separated list, runs sequentially
3. **Conversational Chart Mode** - Back-and-forth discussion with chart as context
4. **Past Life Soul Reading** - Karmic analysis using South Node, retrogrades, 12th house
5. **About the Founder** - Hidden page at `/about/founder`

### 🔒 Compliance & Legal (Production-Ready)
- **GDPR Compliant** - Consent banner, data export, right to erasure
- **CCPA Compliant** - Do not sell, data access rights
- **Terms of Service** - Full legal documentation
- **Privacy Policy** - Transparent data handling
- **Disclaimer** - Entertainment/spiritual use only
- **Accessibility** - WCAG 2.1 Level AA target

---

## Installation

```bash
tar -xf stellaris-13-v2.4.tar.xz
cd stellaris-13-v2.4
pip install -r requirements.txt
python app.py
```

Open http://localhost:13013

### Production Deployment

```bash
# With gunicorn
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:13013 app:app

# Environment variables
export FLASK_ENV=production
export SECRET_KEY=your-secret-key-here
export LOG_LEVEL=WARNING
```

---

## Legal Documents

All legal documentation is in `LEGAL.md` and served at:
- `/legal/terms` - Terms of Service
- `/legal/privacy` - Privacy Policy  
- `/legal/disclaimer` - Disclaimer

**Before commercial release, update:**
- Contact email addresses
- Business name and address
- DPO contact (if required)
- Jurisdiction-specific requirements

---

## Swiss Ephemeris License

Stellaris-13 uses the Swiss Ephemeris library (pyswisseph), which is GPL-licensed.

**Options:**
1. **Open Source Release** - GPL-compatible license, source code available
2. **Commercial License** - Contact Astrodienst AG for commercial licensing

See: https://www.astro.com/swisseph/swephinfo_e.htm

---

## Data Architecture (Privacy-First)

```
┌─────────────────────────────────────────────────────────────┐
│                    CLIENT (Browser)                          │
├─────────────────────────────────────────────────────────────┤
│  localStorage:                                               │
│    - stellaris13_consent (consent record)                   │
│    - stellaris13_profiles (saved charts)                    │
│    - stellaris13_*_key (API keys - never sent to server)   │
│    - stellaris13_preferences (UI settings)                  │
└──────────────────────────┬──────────────────────────────────┘
                           │
                    HTTPS only
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                    SERVER (Stateless)                        │
├─────────────────────────────────────────────────────────────┤
│  - No user data stored on server                            │
│  - Session cookies (httponly, secure, samesite)             │
│  - Temporary chat contexts (memory only, cleared on restart)│
│  - Logs: IP addresses retained 90 days (configurable)       │
└──────────────────────────┬──────────────────────────────────┘
                           │
                    Direct API calls
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                 AI PROVIDERS (External)                      │
├─────────────────────────────────────────────────────────────┤
│  When AI interpretation requested:                          │
│    - Chart data sent to selected provider(s)                │
│    - Subject to provider's privacy policy                   │
│    - User explicitly consents via consent banner            │
└─────────────────────────────────────────────────────────────┘
```

---

## API Endpoints

### Core Functionality
- `POST /compute` - Calculate natal chart
- `POST /synastry` - Calculate synastry
- `POST /transits` - Calculate transits
- `POST /interpret` - AI interpretation (multi-provider)
- `POST /chat` - Conversational chart mode
- `POST /rectify` - Birth time rectification

### Compliance
- `POST /api/consent` - Record consent
- `POST /api/data/export` - GDPR data export
- `POST /api/data/delete` - GDPR right to erasure

### Info
- `GET /health` - Health check
- `GET /version` - Version info

---

## Internationalization Notes

For worldwide release, consider:
- [ ] Multi-language UI support
- [ ] RTL language support (Arabic, Hebrew)
- [ ] Date format localization
- [ ] Timezone auto-detection
- [ ] Currency formatting (if monetizing)
- [ ] Regional privacy law compliance (LGPD Brazil, POPIA South Africa, etc.)

---

## Security Headers

All responses include:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: SAMEORIGIN`
- `X-XSS-Protection: 1; mode=block`
- `Referrer-Policy: strict-origin-when-cross-origin`

Session cookies are:
- `HttpOnly` - No JavaScript access
- `Secure` - HTTPS only in production
- `SameSite=Lax` - CSRF protection

---

Built for the Forge — TAO  
⛎ The Serpent-Bearer

