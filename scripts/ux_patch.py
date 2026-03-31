#!/usr/bin/env python3
"""
Stellaris-13 UX Patch — Location Search + Auto UTC + API Save + Error Messages
Run from the stellaris-13-build directory:
    python3 scripts/ux_patch.py
"""
import sys, os

TARGET = os.path.join(os.path.dirname(__file__), '..', 'templates', 'index.html')
if not os.path.exists(TARGET):
    print(f"  ERROR: {TARGET} not found. Run from stellaris-13-build/")
    sys.exit(1)

with open(TARGET, 'r') as f:
    html = f.read()

patches = 0

# ═══════════════════════════════════════════════════════════════════════════════
# PATCH 1: Replace Lat/Lon/UTC fields with Location Search
# ═══════════════════════════════════════════════════════════════════════════════

old_location = '''        <div class="form-group">
          <label>Latitude</label>
          <input type="text" id="lat" placeholder="41.5868" value="">
        </div>
        <div class="form-group">
          <label>Longitude</label>
          <input type="text" id="lon" placeholder="-93.6250" value="">
        </div>
        <div class="form-group">
          <label>UTC Offset</label>
          <input type="text" id="tz" placeholder="-6" value="">
        </div>
        <div class="form-group" style="grid-column: 1 / -1;">
          <button type="button" class="btn-action map-toggle-btn" onclick="toggleMap('natal-map', 'lat', 'lon')">📍 Pick Location on Map</button>
          <div id="natal-map" class="map-container" style="display:none;"></div>
        </div>'''

new_location = '''        <div class="form-group" style="grid-column: 1 / -1; position: relative;">
          <label>Birth Location</label>
          <input type="text" id="location-search" placeholder="Type a city... e.g. Des Moines, IA" 
                 autocomplete="off"
                 style="width: 100%; padding-right: 40px;"
                 oninput="searchLocation(this.value)">
          <div id="location-results" style="display:none; position:absolute; top:100%; left:0; right:0; z-index:999; 
               background:var(--deep); border:1px solid var(--dust); border-radius:0 0 8px 8px; max-height:200px; overflow-y:auto;"></div>
          <input type="hidden" id="lat" value="">
          <input type="hidden" id="lon" value="">
          <input type="hidden" id="tz" value="">
          <div id="location-info" style="font-size:0.75rem; color:var(--star-dim); margin-top:4px;"></div>
        </div>
        <div class="form-group" style="grid-column: 1 / -1;">
          <button type="button" class="btn-action map-toggle-btn" onclick="toggleMap('natal-map', 'lat', 'lon')">📍 Or Pick on Map</button>
          <div id="natal-map" class="map-container" style="display:none;"></div>
        </div>'''

if old_location in html:
    html = html.replace(old_location, new_location)
    patches += 1
    print("  ok: Patch 1 — Location search field replaces lat/lon/tz inputs")
else:
    print("  SKIP: Patch 1 — could not find location fields (already patched?)")

# ═══════════════════════════════════════════════════════════════════════════════
# PATCH 2: Add geocoding JS + auto UTC + API key save + error handling
# Insert before the closing </script> of the main script block
# ═══════════════════════════════════════════════════════════════════════════════

ux_javascript = '''

// ═══════════════════════════════════════════════════════════════════════════════
// LOCATION SEARCH (Nominatim geocoding — free, no API key)
// ═══════════════════════════════════════════════════════════════════════════════
let _searchTimer = null;
function searchLocation(query) {
  clearTimeout(_searchTimer);
  const results = document.getElementById('location-results');
  if (!query || query.length < 3) { results.style.display = 'none'; return; }
  
  _searchTimer = setTimeout(async () => {
    try {
      const resp = await fetch(
        `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(query)}&format=json&limit=5&addressdetails=1`,
        { headers: { 'User-Agent': 'Stellaris-13/2.8' } }
      );
      const data = await resp.json();
      if (!data.length) {
        results.innerHTML = '<div style="padding:8px;color:var(--star-dim);">No results found</div>';
        results.style.display = 'block';
        return;
      }
      results.innerHTML = data.map(r => 
        `<div class="location-result" 
              style="padding:8px 12px;cursor:pointer;border-bottom:1px solid var(--dust);color:var(--star-bright);font-size:0.85rem;"
              onmouseover="this.style.background='var(--dust)'" 
              onmouseout="this.style.background='transparent'"
              onclick="selectLocation('${r.lat}','${r.lon}','${r.display_name.replace(/'/g, "\\'")}')">
          ${r.display_name}
        </div>`
      ).join('');
      results.style.display = 'block';
    } catch(e) {
      console.error('Geocoding error:', e);
      results.innerHTML = '<div style="padding:8px;color:#e74c3c;">Search failed — check internet connection</div>';
      results.style.display = 'block';
    }
  }, 400); // debounce 400ms
}

async function selectLocation(lat, lon, name) {
  document.getElementById('lat').value = lat;
  document.getElementById('lon').value = lon;
  document.getElementById('location-search').value = name;
  document.getElementById('location-results').style.display = 'none';
  
  // Auto-calculate UTC offset from coordinates + birth date
  const dateVal = document.getElementById('date').value;
  const timeVal = document.getElementById('time').value || '12:00:00';
  
  if (dateVal) {
    try {
      // Use TimeZoneDB or calculate from longitude as fallback
      const tzOffset = await getTimezoneOffset(lat, lon, dateVal, timeVal);
      document.getElementById('tz').value = tzOffset;
      document.getElementById('location-info').innerHTML = 
        `<span style="color:var(--gold-dim);">📍 ${parseFloat(lat).toFixed(4)}, ${parseFloat(lon).toFixed(4)} · UTC${tzOffset >= 0 ? '+' : ''}${tzOffset}</span>`;
    } catch(e) {
      // Fallback: estimate from longitude (rough but better than nothing)
      const roughTz = Math.round(parseFloat(lon) / 15);
      document.getElementById('tz').value = roughTz;
      document.getElementById('location-info').innerHTML = 
        `<span style="color:var(--gold-dim);">📍 ${parseFloat(lat).toFixed(4)}, ${parseFloat(lon).toFixed(4)} · UTC${roughTz >= 0 ? '+' : ''}${roughTz} (estimated)</span>`;
    }
  } else {
    const roughTz = Math.round(parseFloat(lon) / 15);
    document.getElementById('tz').value = roughTz;
    document.getElementById('location-info').innerHTML = 
      `<span style="color:var(--star-dim);">Set birth date for precise timezone</span>`;
  }
}

async function getTimezoneOffset(lat, lon, dateStr, timeStr) {
  // Try the backend timezone endpoint first
  try {
    const resp = await fetch(`/api/timezone?lat=${lat}&lon=${lon}&date=${dateStr}&time=${timeStr}`);
    if (resp.ok) {
      const data = await resp.json();
      return data.utc_offset;
    }
  } catch(e) {}
  
  // Fallback: use timeapi.io (free, no key)
  try {
    const resp = await fetch(`https://timeapi.io/api/timezone/coordinate?latitude=${lat}&longitude=${lon}`);
    if (resp.ok) {
      const data = await resp.json();
      // Parse the UTC offset from the timezone
      const offset = data.currentUtcOffset;
      if (offset) {
        const match = offset.match(/([+-]?)(\\d+):(\\d+)/);
        if (match) {
          const hours = parseInt(match[2]);
          const sign = match[1] === '-' ? -1 : 1;
          return sign * hours;
        }
      }
    }
  } catch(e) {}
  
  // Final fallback: longitude-based estimate
  return Math.round(parseFloat(lon) / 15);
}

// Close dropdown when clicking outside
document.addEventListener('click', function(e) {
  if (!e.target.closest('#location-search') && !e.target.closest('#location-results')) {
    document.getElementById('location-results').style.display = 'none';
  }
});

// ═══════════════════════════════════════════════════════════════════════════════
// API KEY AUTO-SAVE (localStorage — persists across sessions)
// ═══════════════════════════════════════════════════════════════════════════════
const API_KEY_FIELDS = [
  'mistral-api-key', 'claude-api-key', 'yi-api-key', 
  'fireworks-api-key', 'groq-api-key', 'openai-api-key', 'gemini-api-key'
];
const CHECKBOX_FIELDS = [
  'use-mistral', 'use-claude', 'use-ollama', 'use-yi', 
  'use-fireworks', 'use-groq', 'use-openai', 'use-gemini'
];

// Load saved keys on page load
function loadSavedApiKeys() {
  API_KEY_FIELDS.forEach(id => {
    const el = document.getElementById(id);
    if (el) {
      const saved = localStorage.getItem('stellaris_' + id);
      if (saved) el.value = saved;
    }
  });
  CHECKBOX_FIELDS.forEach(id => {
    const el = document.getElementById(id);
    if (el) {
      const saved = localStorage.getItem('stellaris_' + id);
      if (saved !== null) el.checked = saved === 'true';
    }
  });
}

// Auto-save on change
function setupApiKeyAutoSave() {
  API_KEY_FIELDS.forEach(id => {
    const el = document.getElementById(id);
    if (el) {
      el.addEventListener('change', () => {
        localStorage.setItem('stellaris_' + id, el.value);
        showSaveConfirmation();
      });
    }
  });
  CHECKBOX_FIELDS.forEach(id => {
    const el = document.getElementById(id);
    if (el) {
      el.addEventListener('change', () => {
        localStorage.setItem('stellaris_' + id, el.checked);
      });
    }
  });
}

function showSaveConfirmation() {
  const info = document.getElementById('api-save-status');
  if (info) {
    info.textContent = '✓ Saved';
    info.style.color = '#2ecc71';
    setTimeout(() => { info.textContent = ''; }, 2000);
  }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
  loadSavedApiKeys();
  setupApiKeyAutoSave();
  // Also load saved profile
  loadSavedProfile();
});

// ═══════════════════════════════════════════════════════════════════════════════
// AUTO-SAVE PROFILE (name, date, time, location)
// ═══════════════════════════════════════════════════════════════════════════════
function saveProfile() {
  const profile = {
    name: document.getElementById('name')?.value,
    date: document.getElementById('date')?.value,
    time: document.getElementById('time')?.value,
    lat: document.getElementById('lat')?.value,
    lon: document.getElementById('lon')?.value,
    tz: document.getElementById('tz')?.value,
    location_name: document.getElementById('location-search')?.value,
  };
  localStorage.setItem('stellaris_profile', JSON.stringify(profile));
}

function loadSavedProfile() {
  try {
    const saved = localStorage.getItem('stellaris_profile');
    if (!saved) return;
    const p = JSON.parse(saved);
    if (p.name) document.getElementById('name').value = p.name;
    if (p.date) document.getElementById('date').value = p.date;
    if (p.time) document.getElementById('time').value = p.time;
    if (p.lat) document.getElementById('lat').value = p.lat;
    if (p.lon) document.getElementById('lon').value = p.lon;
    if (p.tz) document.getElementById('tz').value = p.tz;
    if (p.location_name) {
      const search = document.getElementById('location-search');
      if (search) search.value = p.location_name;
    }
    if (p.lat && p.lon && p.tz) {
      const info = document.getElementById('location-info');
      if (info) info.innerHTML = `<span style="color:var(--gold-dim);">📍 ${parseFloat(p.lat).toFixed(4)}, ${parseFloat(p.lon).toFixed(4)} · UTC${parseFloat(p.tz) >= 0 ? '+' : ''}${p.tz}</span>`;
    }
  } catch(e) {}
}

// ═══════════════════════════════════════════════════════════════════════════════
// INTERPRETATION ERROR MESSAGES (no more silent failures)
// ═══════════════════════════════════════════════════════════════════════════════
// Monkey-patch the interpretation display to show errors
const _origDisplayInterpretations = typeof displayInterpretations === 'function' ? displayInterpretations : null;

// Override fetch to catch interpretation errors
const _origFetch = window.fetch;
window.fetch = async function(...args) {
  const resp = await _origFetch.apply(this, args);
  const url = typeof args[0] === 'string' ? args[0] : args[0]?.url || '';
  
  if (url.includes('/interpret') && resp.ok) {
    const clone = resp.clone();
    try {
      const data = await clone.json();
      if (data.interpretations && Object.keys(data.interpretations).length === 0) {
        // All providers failed silently — show error
        setTimeout(() => {
          const interpDiv = document.getElementById('interpretation-content');
          if (interpDiv && (!interpDiv.textContent || interpDiv.textContent.trim().length < 20)) {
            interpDiv.innerHTML = `
              <div style="padding:1.5rem;text-align:center;color:var(--star-dim);">
                <p style="font-size:1.1rem;color:#e74c3c;margin-bottom:0.5rem;">⚠ No interpretation received</p>
                <p style="font-size:0.85rem;">Check that you have selected a provider and entered a valid API key in the AI Interpretation section below.</p>
                <p style="font-size:0.8rem;margin-top:0.5rem;color:var(--star-dim);">
                  Free API keys: <a href="https://console.groq.com/keys" target="_blank" style="color:var(--gold-dim);">Groq</a> · 
                  <a href="https://console.mistral.ai/api-keys" target="_blank" style="color:var(--gold-dim);">Mistral</a> · 
                  <a href="https://aistudio.google.com/apikey" target="_blank" style="color:var(--gold-dim);">Gemini</a>
                </p>
              </div>`;
          }
        }, 1500);
      }
    } catch(e) {}
  }
  return resp;
};
'''

# Find the last </script> and insert before it
if '</script>' in html:
    last_script = html.rindex('</script>')
    html = html[:last_script] + ux_javascript + '\n' + html[last_script:]
    patches += 1
    print("  ok: Patch 2 — Geocoding + auto UTC + API save + error messages JS")
else:
    print("  SKIP: Patch 2 — no </script> found")

# ═══════════════════════════════════════════════════════════════════════════════
# PATCH 3: Add save-status span near the Save API Keys button
# ═══════════════════════════════════════════════════════════════════════════════
old_save_btn = '''<button class="btn-action" onclick="saveAllApiKeys()" style="font-size: 0.75rem;">Save API Keys</button>'''
new_save_btn = '''<button class="btn-action" onclick="saveAllApiKeys()" style="font-size: 0.75rem;">Save API Keys</button>
            <span id="api-save-status" style="margin-left:8px;font-size:0.75rem;"></span>
            <span style="display:block;font-size:0.7rem;color:var(--star-dim);margin-top:4px;">Keys auto-save when you type them. Stored locally on your machine only.</span>'''

if old_save_btn in html:
    html = html.replace(old_save_btn, new_save_btn)
    patches += 1
    print("  ok: Patch 3 — API save status indicator")

# ═══════════════════════════════════════════════════════════════════════════════
# PATCH 4: Auto-save profile when computing chart
# ═══════════════════════════════════════════════════════════════════════════════
old_compute = "const resp = await fetch('/compute', {"
new_compute = "saveProfile(); // Auto-save birth data\n    const resp = await fetch('/compute', {"

if old_compute in html:
    html = html.replace(old_compute, new_compute, 1)
    patches += 1
    print("  ok: Patch 4 — Auto-save profile on chart compute")

# ═══════════════════════════════════════════════════════════════════════════════
# WRITE
# ═══════════════════════════════════════════════════════════════════════════════
with open(TARGET, 'w') as f:
    f.write(html)

print(f"\n  {patches} patches applied to templates/index.html")
if patches > 0:
    print("  Commit and push to trigger rebuild:")
    print("    git add templates/index.html")
    print('    git commit -m "UX: location search, auto UTC, API save, error messages"')
    print("    git push")
