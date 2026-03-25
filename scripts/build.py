#!/usr/bin/env python3
"""
Stellaris-13 Automated Build System v2
=======================================
Creates four distinct, secure builds by physically removing or replacing
code based on the target pricing tier.

TIER STRUCTURE:
  Free        ($0)    — Natal, transits, synastry, past life (unlimited)
  Personal    ($649)  — + Chart chat (AI conversation) + Celestial Blueprint
  Professional($1497) — + Birth time rectification
  Astrologer  ($2497) — + Crypto natal/transits/synastry + all tools

Each higher tier includes everything below it.
"""

import os
import re
import shutil
import zipfile
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────
# DIRECTORIES
# ─────────────────────────────────────────────────────────────────────
ROOT_DIR = Path(__file__).resolve().parent.parent
BUILD_DIR = ROOT_DIR / "builds"

# ─────────────────────────────────────────────────────────────────────
# CORE FILES included in ALL builds
# ─────────────────────────────────────────────────────────────────────
CORE_FILES = [
    "app.py", "config.py", "engine.py", "founder.py",
    "launch.sh", "requirements.txt", "Dockerfile", "docker-compose.yml",
    "README.md", "LICENSE", "LEGAL.md"
]
CORE_DIRS = ["static", "templates", "legal"]

# ─────────────────────────────────────────────────────────────────────
# TIER DEFINITIONS
# ─────────────────────────────────────────────────────────────────────
# "files"  = real modules included in this tier
# "dummy"  = modules replaced with stubs (prevents import errors)
# "locked_routes" = Flask routes that return 403 for this tier

TIERS = {
    "free": {
        "files": ["blueprint.py", "blueprint_prompts.py"],  # Blueprint available (behind $13 paywall in UI)
        "dummy": [
            "crypto_natal.py", "crypto_transits.py",
            "crypto_synastry.py", "crypto_prompts.py"
        ],
        "locked_routes": ["/chat", "/rectify",
                          "/crypto/analyze", "/crypto/interpret"],
        "locked_features": {
            "chart_chat": False,
            "blueprint": True,       # Available but $13 one-time in UI
            "blueprint_included": False,  # Not included — requires payment
            "past_life": False,
            "synastry_interp": False,  # Synastry computation is free; AI interpretation is Personal
            "rectification": False,
            "crypto": False,
        }
    },
    "personal": {
        "files": ["blueprint.py", "blueprint_prompts.py"],
        "dummy": [
            "crypto_natal.py", "crypto_transits.py",
            "crypto_synastry.py", "crypto_prompts.py"
        ],
        "locked_routes": ["/rectify", "/crypto/analyze", "/crypto/interpret"],
        "locked_features": {
            "chart_chat": True,       # ⭐ GOLD LINE FEATURE
            "blueprint": True,
            "blueprint_included": True,  # Included in tier
            "past_life": True,
            "synastry_interp": True,
            "rectification": False,
            "crypto": False,
        }
    },
    "professional": {
        "files": ["blueprint.py", "blueprint_prompts.py"],
        "dummy": [
            "crypto_natal.py", "crypto_transits.py",
            "crypto_synastry.py", "crypto_prompts.py"
        ],
        "locked_routes": ["/crypto/analyze", "/crypto/interpret"],
        "locked_features": {
            "chart_chat": True,
            "blueprint": True,
            "blueprint_included": True,
            "past_life": True,
            "synastry_interp": True,
            "rectification": True,   # ⭐ GOLD LINE FEATURE
            "crypto": False,
        }
    },
    "astrologer": {
        "files": [
            "blueprint.py", "blueprint_prompts.py",
            "crypto_natal.py", "crypto_transits.py",
            "crypto_synastry.py", "crypto_prompts.py"
        ],
        "dummy": [],
        "locked_routes": [],
        "locked_features": {
            "chart_chat": True,
            "blueprint": True,
            "blueprint_included": True,
            "past_life": True,
            "synastry_interp": True,
            "rectification": True,
            "crypto": True,          # ⭐ GOLD LINE FEATURE
        }
    }
}

# ─────────────────────────────────────────────────────────────────────
# DUMMY MODULE STUBS
# ─────────────────────────────────────────────────────────────────────

DUMMY_BLUEPRINT = '''"""Stellaris-13 — Blueprint module (requires Personal tier or higher)"""

def generate_blueprint(*args, **kwargs):
    raise Exception("Celestial Blueprint generation requires the Personal tier or higher.")

# Blueprint prompt stubs
CHAPTER_PROMPTS = {}
'''

DUMMY_BLUEPRINT_PROMPTS = '''"""Stellaris-13 — Blueprint prompts (requires Personal tier or higher)"""

ASTROLOGER_PERSONA = ""
CHAPTER_1_PROMPT = ""
CHAPTER_2_PROMPT = ""
CHAPTER_3_PROMPT = ""
CHAPTER_4_PROMPT = ""
CHAPTER_5_PROMPT = ""
CHAPTER_6_PROMPT = ""

def get_blueprint_chapters(*args, **kwargs):
    return []
'''

DUMMY_CRYPTO_NATAL = '''"""Stellaris-13 — Crypto natal module (requires Astrologer tier)"""

CRYPTO_REGISTRY = {}

def get_crypto_natal(symbol):
    return None

def list_supported_cryptos():
    return []

def get_natal_longitude(symbol, planet):
    return None
'''

DUMMY_CRYPTO_TRANSITS = '''"""Stellaris-13 — Crypto transits module (requires Astrologer tier)"""

def get_current_transits(symbol="BTC"):
    return []

def analyze_crypto_transits(*args, **kwargs):
    return {"error": "Crypto transit analysis requires the Astrologer tier."}

def compare_crypto_transits(*args, **kwargs):
    return {"error": "Crypto comparison requires the Astrologer tier."}
'''

DUMMY_CRYPTO_SYNASTRY = '''"""Stellaris-13 — Crypto synastry module (requires Astrologer tier)"""

def analyze_natal_synastry(person_planets, crypto_symbol="BTC"):
    return {"status": "locked", "message": "Crypto synastry requires the Astrologer tier.",
            "score": 0, "compatibility": "LOCKED", "all_aspects": []}

def analyze_transit_synastry(*args, **kwargs):
    return {"status": "locked", "message": "Crypto synastry requires the Astrologer tier."}

def full_synastry_report(*args, **kwargs):
    return {"status": "locked"}

def compare_synastry(*args, **kwargs):
    return {"status": "locked"}
'''

DUMMY_CRYPTO_PROMPTS = '''"""Stellaris-13 — Crypto prompts module (requires Astrologer tier)"""

CRYPTO_TRANSIT_PHILOSOPHY = ""

def get_transit_prompt(*args, **kwargs):
    return ""

def get_full_system_prompt(*args, **kwargs):
    return ""
'''

DUMMY_CONTENT = {
    "blueprint.py": DUMMY_BLUEPRINT,
    "blueprint_prompts.py": DUMMY_BLUEPRINT_PROMPTS,
    "crypto_natal.py": DUMMY_CRYPTO_NATAL,
    "crypto_transits.py": DUMMY_CRYPTO_TRANSITS,
    "crypto_synastry.py": DUMMY_CRYPTO_SYNASTRY,
    "crypto_prompts.py": DUMMY_CRYPTO_PROMPTS,
}

# ─────────────────────────────────────────────────────────────────────
# TIER GATING CODE — injected into app.py
# ─────────────────────────────────────────────────────────────────────

TIER_GATE_IMPORT = """
# ═══ TIER GATING (injected by build system) ═══
from functools import wraps

TIER = '{tier}'
TIER_FEATURES = {features}

def require_feature(feature_name):
    \"\"\"Decorator to gate routes by tier feature.\"\"\"
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if not TIER_FEATURES.get(feature_name, False):
                tier_needed = {{
                    'chart_chat': 'Personal',
                    'blueprint': 'Free ($13 one-time)',
                    'past_life': 'Personal',
                    'synastry_interp': 'Personal',
                    'rectification': 'Professional',
                    'crypto': 'Astrologer',
                }}.get(feature_name, 'a higher')
                return jsonify({{
                    'status': 'error',
                    'message': f'This feature requires the {{tier_needed}} tier or higher.',
                    'tier_required': tier_needed,
                    'current_tier': TIER
                }}), 403
            return f(*args, **kwargs)
        return wrapped
    return decorator
# ═══ END TIER GATING ═══
"""

# Route patterns and their required feature
ROUTE_FEATURE_MAP = {
    "def chat()": "chart_chat",
    "def rectify()": "rectification",
    "def crypto_analyze()": "crypto",
    "def crypto_interpret()": "crypto",
    # Note: /blueprint route is always available (paywall handled in UI for free tier)
    # Note: /interpret route handles past_life gating internally via query_type
    # Note: /synastry computation is free; AI interpretation gating is in /interpret
}


# ─────────────────────────────────────────────────────────────────────
# BUILD FUNCTIONS
# ─────────────────────────────────────────────────────────────────────

def clean_build_dir():
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
    os.makedirs(BUILD_DIR)


def inject_tier_gating(target_dir: Path, tier: str):
    """
    Inject tier gating into app.py:
    1. Add TIER constant and require_feature decorator
    2. Add @require_feature decorators to locked routes
    3. Inject TIER_FEATURES into config.py
    """
    features = TIERS[tier]["locked_features"]

    # ── Patch app.py ──
    app_path = target_dir / "app.py"
    with open(app_path, "r") as f:
        content = f.read()

    # Insert tier gating code after initial imports
    gate_code = TIER_GATE_IMPORT.format(tier=tier, features=features)

    # Find the right insertion point — after the last top-level import block
    # We'll insert just before the first Flask app creation
    insert_marker = "app = Flask(__name__"
    if insert_marker in content:
        content = content.replace(
            insert_marker,
            gate_code + "\n" + insert_marker
        )

    # Add @require_feature decorators to gated routes
    for func_sig, feature in ROUTE_FEATURE_MAP.items():
        if not features.get(feature, False):
            # Find the @app.route line above this function and add decorator
            pattern = r'(@app\.route\([^)]+\)\n(?:@[^\n]+\n)*)def ' + re.escape(func_sig.replace('def ', ''))
            match = re.search(pattern, content)
            if match:
                # Insert @require_feature between @app.route and def
                route_line = match.group(0)
                decorator_line = f"@require_feature('{feature}')\n"
                new_route = route_line.replace(
                    f"def {func_sig.replace('def ', '')}",
                    f"{decorator_line}def {func_sig.replace('def ', '')}"
                )
                content = content.replace(route_line, new_route)

    with open(app_path, "w") as f:
        f.write(content)

    # ── Patch config.py ──
    config_path = target_dir / "config.py"
    if config_path.exists():
        with open(config_path, "r") as f:
            cfg_content = f.read()

        # Add tier info at end
        cfg_content += f"\n\n# Build tier (injected by build system)\nTIER = '{tier}'\n"
        cfg_content += f"TIER_FEATURES = {features}\n"

        # Update version
        cfg_content = re.sub(
            r'APP_VERSION\s*=\s*"[^"]*"',
            f'APP_VERSION = "2.7.1-{tier}"',
            cfg_content
        )

        with open(config_path, "w") as f:
            f.write(cfg_content)


def patch_frontend(target_dir: Path, tier: str):
    """
    Modify the frontend template to hide/lock UI elements for gated features.
    """
    features = TIERS[tier]["locked_features"]
    index_path = target_dir / "templates" / "index.html"

    if not index_path.exists():
        return

    with open(index_path, "r") as f:
        content = f.read()

    # Crypto tab: ALWAYS visible (teaser/upsell), but functionality locked for non-Astrologer
    if not features.get("crypto", False):
        # Replace the action buttons with upgrade prompts instead of hiding the tab
        content = content.replace(
            'onclick="castCryptoChart()"',
            'onclick="alert(\'🪙 Crypto Astrology is available in the Astrologer tier.\\n\\nCast natal charts for 24+ cryptocurrencies, track real-time transits with exact dates, and discover your personal synastry with any coin.\\n\\nUpgrade to unlock.\'); return;"'
        )
        content = content.replace(
            'onclick="runCryptoAnalysis()"',
            'onclick="alert(\'🪙 Crypto analysis requires the Astrologer tier.\\n\\nUpgrade to access transit analysis, person-to-coin synastry, and multi-coin comparison.\'); return;"'
        )
        content = content.replace(
            'onclick="requestCryptoInterpretation()"',
            'onclick="alert(\'🪙 Crypto AI interpretation requires the Astrologer tier.\'); return;"'
        )
        # Add a subtle lock badge to the tab button
        content = content.replace(
            '>🪙 Crypto</button>',
            '>🪙 Crypto <span style="font-size:0.6rem;opacity:0.5;">🔒</span></button>'
        )

    # Lock chat section if not in tier
    if not features.get("chart_chat", False):
        content = content.replace(
            'id="chart-chat-section"',
            'id="chart-chat-section" data-locked="true"'
        )

    # Rectification tab: visible but locked for lower tiers (upsell)
    if not features.get("rectification", False):
        content = content.replace(
            '<button class="tab" data-tab="rectify"',
            '<button class="tab" data-tab="rectify" title="Birth time rectification — available in Professional tier"'
        )
        # Add lock icon to tab
        content = content.replace(
            '>⚕ Rectify Time</button>',
            '>⚕ Rectify Time <span style="font-size:0.6rem;opacity:0.5;">🔒</span></button>'
        )

    # Lock past life button in free tier
    if not features.get("past_life", False):
        content = content.replace(
            "setInterpType('past_life'",
            "alert('Past Life reading requires the Personal tier or higher.'); return; // setInterpType('past_life'"
        )

    # Lock synastry AI interpretation in free tier (computation stays free)
    if not features.get("synastry_interp", False):
        content = content.replace(
            'onclick="requestSynastryInterpretation()"',
            'onclick="alert(\'Synastry AI interpretation requires the Personal tier or higher.\')"'
        )

    # Blueprint: available to all tiers, but show $13 price for free tier
    if not features.get("blueprint_included", False):
        content = content.replace(
            'onclick="generateBlueprint()"',
            'onclick="if(!confirm(\'Celestial Blueprint is a one-time purchase of $13. Proceed to payment?\')) return; generateBlueprint()"'
        )

    # Inject tier badge into footer
    tier_badge = f"""
    <div style="text-align:center;padding:0.5rem;font-size:0.7rem;color:var(--star-dim);opacity:0.6;">
      Stellaris-13 v2.7.3 — {tier.capitalize()} Edition
    </div>
    """
    content = content.replace("</body>", f"{tier_badge}\n</body>")

    with open(index_path, "w") as f:
        f.write(content)


def build_tier(tier: str):
    print(f"\n{'═' * 60}")
    print(f"  Building {tier.upper()} tier...")
    print(f"{'═' * 60}")

    tier_dir = BUILD_DIR / f"stellaris-{tier}"
    os.makedirs(tier_dir)

    # 1. Copy core files
    for filename in CORE_FILES:
        src = ROOT_DIR / filename
        if src.exists():
            shutil.copy2(src, tier_dir / filename)
        else:
            print(f"  ⚠ Missing core file: {filename}")

    # 2. Copy core directories
    for dirname in CORE_DIRS:
        src = ROOT_DIR / dirname
        if src.exists():
            shutil.copytree(src, tier_dir / dirname)
        else:
            print(f"  ⚠ Missing core dir: {dirname}")

    # 3. Create user data directories
    os.makedirs(tier_dir / "saved_charts", exist_ok=True)
    os.makedirs(tier_dir / "generated_blueprints", exist_ok=True)

    # 4. Copy real premium modules for this tier
    for filename in TIERS[tier]["files"]:
        src = ROOT_DIR / filename
        if src.exists():
            shutil.copy2(src, tier_dir / filename)
            print(f"  ✓ Included: {filename}")
        else:
            print(f"  ⚠ Missing premium file: {filename}")

    # 5. Create dummy stubs for locked modules
    for filename in TIERS[tier]["dummy"]:
        with open(tier_dir / filename, "w") as f:
            f.write(DUMMY_CONTENT.get(filename, f'"""Stub for {filename}"""\n'))
        print(f"  ✗ Stubbed:  {filename}")

    # 6. Inject tier gating into app.py and config.py
    inject_tier_gating(tier_dir, tier)
    print(f"  ⚙ Tier gating injected (TIER='{tier}')")

    # 7. Patch frontend to hide/lock UI for gated features
    patch_frontend(tier_dir, tier)
    print(f"  🎨 Frontend patched for {tier} tier")

    # 8. Create zip
    zip_path = BUILD_DIR / f"stellaris-{tier}.zip"
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(tier_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, BUILD_DIR)
                zf.write(file_path, arcname)

    zip_size = zip_path.stat().st_size / (1024 * 1024)
    print(f"  📦 Created {zip_path.name} ({zip_size:.1f} MB)")


def print_tier_summary():
    print("\n" + "═" * 60)
    print("  TIER SUMMARY")
    print("═" * 60)
    print()
    print("  FREE ($0)")
    print("    ✓ Natal charts (all 3 zodiacs, unlimited)")
    print("    ✓ Transits (unlimited)")
    print("    ✓ Celestial Blueprint ($13 one-time purchase)")
    print("    ✗ Chart chat (AI conversation)")
    print("    ✗ Past life reading")
    print("    ✗ Synastry AI interpretation")
    print("    ✗ Rectification")
    print("    ✗ Crypto charts")
    print()
    print("  PERSONAL ($649)")
    print("    ✓ Everything in Free")
    print("    ★ Chart chat — AI conversation with YOUR chart")
    print("    ★ Past life reading")
    print("    ★ Synastry AI interpretation")
    print("    ✓ Celestial Blueprint (included)")
    print("    ✗ Rectification")
    print("    ✗ Crypto charts")
    print()
    print("  PROFESSIONAL ($1,497)")
    print("    ✓ Everything in Personal")
    print("    ★ Birth time rectification (monetizable)")
    print("    ✗ Crypto charts")
    print()
    print("  ASTROLOGER ($2,497)")
    print("    ✓ Everything in Professional")
    print("    ★ Crypto natal charts (24+ coins + custom)")
    print("    ★ Crypto transit analysis (with exact dates)")
    print("    ★ Person-to-coin synastry")
    print("    ★ Multi-coin comparison")
    print()


def main():
    print()
    print("  ╔══════════════════════════════════════════╗")
    print("  ║  Stellaris-13 Automated Build System v2  ║")
    print("  ╚══════════════════════════════════════════╝")
    print()
    print(f"  Source:      {ROOT_DIR}")
    print(f"  Destination: {BUILD_DIR}")

    print_tier_summary()

    clean_build_dir()

    for tier in TIERS:
        build_tier(tier)

    print("\n" + "═" * 60)
    print("  ✅ All builds completed successfully!")
    print(f"  Builds: {BUILD_DIR}")
    print("═" * 60)

    # List output
    print()
    for f in sorted(BUILD_DIR.glob("*.zip")):
        size = f.stat().st_size / (1024 * 1024)
        print(f"  {f.name:30s} {size:.1f} MB")
    print()


if __name__ == "__main__":
    main()
