#!/usr/bin/env python3
"""Stellaris-13 Build System v3 — Corrected tier structure."""
import os, re, shutil, zipfile
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
ROOT_DIR = _BASE if (_BASE / "app.py").exists() else _BASE / "stellaris-13-v2.7 (4).3/stellaris-13-v2.4"
BUILD_DIR = _BASE / "builds"
VERSION = "2.8.0"

CORE_FILES = [
    "app.py","config.py","engine.py","founder.py","license.py","launch.sh",
    "requirements.txt","version.json","Dockerfile","docker-compose.yml",
    "README.md","LICENSE","LEGAL.md",
    "Stellaris-13.bat","Stellaris-13.command","Stellaris-13.sh",
]
CORE_DIRS = ["static","templates","legal"]

TIERS = {
    "free":         {"real":[], "dummy":["blueprint.py","blueprint_prompts.py","blueprint_generator.py","blueprint_engine_extensions.py","crypto_natal.py","crypto_transits.py","crypto_synastry.py","crypto_prompts.py"]},
    "personal":     {"real":["blueprint.py","blueprint_prompts.py","blueprint_generator.py","blueprint_engine_extensions.py"], "dummy":["crypto_natal.py","crypto_transits.py","crypto_synastry.py","crypto_prompts.py"]},
    "professional": {"real":["blueprint.py","blueprint_prompts.py","blueprint_generator.py","blueprint_engine_extensions.py"], "dummy":["crypto_natal.py","crypto_transits.py","crypto_synastry.py","crypto_prompts.py"]},
    "astrologer":   {"real":["blueprint.py","blueprint_prompts.py","blueprint_generator.py","blueprint_engine_extensions.py","crypto_natal.py","crypto_transits.py","crypto_synastry.py","crypto_prompts.py"], "dummy":[]},
}

DUMMIES = {
    "blueprint.py": 'def generate_blueprint(*a,**k): raise PermissionError("Requires Personal edition")',
    "blueprint_prompts.py": 'ASTROLOGER_PERSONA=""\ndef build_chart_summary(c): return ""\ndef build_aspect_table(a): return ""\ndef get_chapter_prompts(c): return []\ndef get_title_page_content(c,b): return {}',
    "blueprint_generator.py": 'def generate_blueprint(*a,**k): raise PermissionError("Requires Personal edition")\ndef make_anthropic_caller(*a,**k): return None\ndef make_openai_caller(*a,**k): return None\ndef make_ollama_caller(*a,**k): return None',
    "blueprint_engine_extensions.py": 'def enrich_chart_for_blueprint(chart,target_date=None): return chart',
    "crypto_natal.py": 'CRYPTO_REGISTRY={}\ndef get_crypto_chart(s="BTC"): raise PermissionError("Requires Astrologer edition")',
    "crypto_transits.py": 'def get_current_transits(s="BTC",d=None): raise PermissionError("Requires Astrologer edition")\ndef analyze_crypto_transits(*a,**k): raise PermissionError("Requires Astrologer edition")',
    "crypto_synastry.py": 'def analyze_natal_synastry(p,s="BTC"): raise PermissionError("Requires Astrologer edition")\ndef analyze_transit_synastry(*a,**k): raise PermissionError("Requires Astrologer edition")',
    "crypto_prompts.py": 'def get_transit_prompt(*a,**k): return ""\ndef get_synastry_prompt(*a,**k): return ""\ndef get_comparison_prompt(*a,**k): return ""\ndef get_full_system_prompt(*a,**k): return ""',
}

def build_tier(tier):
    print(f"\n  Building {tier.upper()}...")
    td = BUILD_DIR / f"stellaris-{tier}"
    if td.exists(): shutil.rmtree(td)
    os.makedirs(td)
    for f in CORE_FILES:
        s = ROOT_DIR / f
        if s.exists(): shutil.copy2(s, td / f)
    for d in CORE_DIRS:
        s = ROOT_DIR / d
        if s.exists(): shutil.copytree(s, td / d)
    os.makedirs(td / "saved_charts", exist_ok=True)
    os.makedirs(td / "generated_blueprints", exist_ok=True)
    for f in TIERS[tier]["real"]:
        s = ROOT_DIR / f
        if s.exists(): shutil.copy2(s, td / f)
    for f in TIERS[tier]["dummy"]:
        if not (td / f).exists():
            (td / f).write_text(DUMMIES.get(f, ''))
    # Stamp tier + version in config
    cp = td / "config.py"
    if cp.exists():
        c = cp.read_text()
        if "TIER =" in c: c = re.sub(r"TIER\s*=\s*['\"].*?['\"]", f"TIER = '{tier}'", c)
        else: c += f"\nTIER = '{tier}'\n"
        c = re.sub(r'APP_VERSION\s*=\s*["\'].*?["\']', f'APP_VERSION = "{VERSION}"', c)
        cp.write_text(c)
    # Stamp version in JS
    vjs = td / "static" / "js" / "version_notify.js"
    if vjs.exists():
        c = vjs.read_text()
        c = re.sub(r"const CURRENT_VERSION = '[^']+';", f"const CURRENT_VERSION = '{VERSION}';", c)
        vjs.write_text(c)

    # Automatically write the launcher script for PyInstaller
    launcher_code = """import sys, os, threading, webbrowser, time, signal
if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
    os.chdir(BASE_DIR)
    DATA_DIR = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'Stellaris-13')
    os.makedirs(DATA_DIR, exist_ok=True)
    os.environ['STELLARIS_DATA_DIR'] = DATA_DIR
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    os.chdir(BASE_DIR)

def open_browser():
    time.sleep(3)
    webbrowser.open('http://localhost:13013')

signal.signal(signal.SIGINT, lambda s,f: sys.exit(0))

if __name__ == '__main__':
    print('\\n  Stellaris-13 is starting...')
    print('  Your browser will open automatically.\\n')
    threading.Thread(target=open_browser, daemon=True).start()
    from app import app
    app.run(host='127.0.0.1', port=13013, debug=False, use_reloader=False)
"""
    (td / "stellaris_launcher.py").write_text(launcher_code)

    # Make scripts executable
    for s in ['Stellaris-13.command','Stellaris-13.sh','launch.sh']:
        sp = td / s
        if sp.exists(): os.chmod(sp, 0o755)
    # Zip
    zp = BUILD_DIR / f"stellaris-{tier}.zip"
    with zipfile.ZipFile(zp, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root,dirs,files in os.walk(td):
            dirs[:] = [d for d in dirs if d != '__pycache__']
            for f in files:
                fp = os.path.join(root, f)
                zf.write(fp, os.path.relpath(fp, BUILD_DIR))
    sz = os.path.getsize(zp)/1024
    print(f"    → {zp.name} ({sz:.0f} KB)")

if __name__ == "__main__":
    print("  Stellaris-13 Build System v3")
    print(f"  Source: {ROOT_DIR}")
    if BUILD_DIR.exists(): shutil.rmtree(BUILD_DIR)
    os.makedirs(BUILD_DIR)
    for t in ["free","personal","professional","astrologer"]:
        build_tier(t)
    print(f"\n  ✅ All builds in {BUILD_DIR}")
