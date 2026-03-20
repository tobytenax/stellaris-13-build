/**
 * Stellaris-13 — Version Notification System
 * ============================================
 * Lightweight client-side version checker.
 * 
 * How it works:
 *   1. On page load, fetches /version.json (a static file you update with each release)
 *   2. Compares against the version baked into the current build
 *   3. If a newer version exists, shows a non-intrusive toast notification
 *   4. User can dismiss or click to learn more (changelog URL)
 *   5. Dismissed versions are remembered in localStorage so they don't nag
 * 
 * Integration:
 *   - Add <script src="/static/js/version_notify.js"></script> before </body>
 *   - Deploy version.json to your static root (Cloudflare Pages or Flask static/)
 *   - Update version.json each time you push a new release
 */

(function() {
  'use strict';

  // ═══════════════════════════════════════════════════════════════════════════
  // CONFIG — update CURRENT_VERSION with each build
  // ═══════════════════════════════════════════════════════════════════════════
  
  const CURRENT_VERSION = '2.8.0';  // Baked into this build by build.py
  const VERSION_CHECK_URL = '/version.json';  // Relative to app root
  const CHECK_INTERVAL_MS = 4 * 60 * 60 * 1000;  // Check every 4 hours
  const DISMISSED_KEY = 'stellaris13_dismissed_version';
  const LAST_CHECK_KEY = 'stellaris13_last_version_check';

  // ═══════════════════════════════════════════════════════════════════════════
  // VERSION COMPARISON
  // ═══════════════════════════════════════════════════════════════════════════
  
  function compareVersions(a, b) {
    // Returns: 1 if a > b, -1 if a < b, 0 if equal
    const partsA = a.split('.').map(Number);
    const partsB = b.split('.').map(Number);
    const len = Math.max(partsA.length, partsB.length);
    
    for (let i = 0; i < len; i++) {
      const numA = partsA[i] || 0;
      const numB = partsB[i] || 0;
      if (numA > numB) return 1;
      if (numA < numB) return -1;
    }
    return 0;
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // TOAST UI
  // ═══════════════════════════════════════════════════════════════════════════
  
  function showUpdateToast(latestVersion, changelog, releaseNotes) {
    // Don't show if already dismissed this version
    const dismissed = localStorage.getItem(DISMISSED_KEY);
    if (dismissed === latestVersion) return;

    // Create toast container
    const toast = document.createElement('div');
    toast.id = 'stellaris-update-toast';
    toast.innerHTML = `
      <div style="
        position: fixed;
        bottom: 24px;
        right: 24px;
        background: linear-gradient(135deg, #1a1a2e, #2d1a35);
        border: 1px solid #c9a83b;
        border-radius: 12px;
        padding: 16px 20px;
        max-width: 360px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.6);
        z-index: 10000;
        font-family: 'Georgia', serif;
        animation: slideInUp 0.4s ease-out;
      ">
        <style>
          @keyframes slideInUp {
            from { transform: translateY(100px); opacity: 0; }
            to { transform: translateY(0); opacity: 1; }
          }
          #stellaris-update-toast a {
            color: #c9a83b;
            text-decoration: underline;
          }
          #stellaris-update-toast a:hover {
            color: #e8d070;
          }
        </style>
        
        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
          <div style="color: #c9a83b; font-weight: bold; font-size: 14px;">
            ✦ Stellaris-13 v${latestVersion} Available
          </div>
          <button id="stellaris-toast-dismiss" style="
            background: none;
            border: none;
            color: #666;
            font-size: 18px;
            cursor: pointer;
            padding: 0 0 0 12px;
            line-height: 1;
          ">&times;</button>
        </div>
        
        <div style="color: #a09686; font-size: 12px; margin-top: 6px;">
          You're on v${CURRENT_VERSION}
        </div>
        
        ${releaseNotes ? `
          <div style="color: #d4cfc5; font-size: 13px; margin-top: 10px; line-height: 1.4;">
            ${releaseNotes}
          </div>
        ` : ''}
        
        <div style="margin-top: 12px; display: flex; gap: 10px;">
          ${changelog ? `
            <a href="${changelog}" target="_blank" style="
              display: inline-block;
              background: linear-gradient(135deg, #c9a83b, #a08520);
              color: #1a1a2e;
              padding: 6px 14px;
              border-radius: 6px;
              font-size: 12px;
              font-weight: bold;
              text-decoration: none;
            ">View Update</a>
          ` : ''}
          <button id="stellaris-toast-later" style="
            background: rgba(255,255,255,0.08);
            border: 1px solid #444;
            color: #a09686;
            padding: 6px 14px;
            border-radius: 6px;
            font-size: 12px;
            cursor: pointer;
          ">Dismiss</button>
        </div>
      </div>
    `;

    document.body.appendChild(toast);

    // Dismiss handlers
    const dismissBtn = document.getElementById('stellaris-toast-dismiss');
    const laterBtn = document.getElementById('stellaris-toast-later');
    
    function dismiss() {
      localStorage.setItem(DISMISSED_KEY, latestVersion);
      toast.remove();
    }

    if (dismissBtn) dismissBtn.addEventListener('click', dismiss);
    if (laterBtn) laterBtn.addEventListener('click', dismiss);
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // VERSION CHECK
  // ═══════════════════════════════════════════════════════════════════════════

  async function checkForUpdates() {
    try {
      // Throttle checks
      const lastCheck = localStorage.getItem(LAST_CHECK_KEY);
      if (lastCheck && (Date.now() - parseInt(lastCheck)) < CHECK_INTERVAL_MS) {
        return;
      }

      const response = await fetch(VERSION_CHECK_URL, {
        cache: 'no-store',  // Always get fresh version info
        headers: { 'Accept': 'application/json' }
      });

      if (!response.ok) return;  // Silently fail — version check is non-critical

      const data = await response.json();
      localStorage.setItem(LAST_CHECK_KEY, Date.now().toString());

      if (data.version && compareVersions(data.version, CURRENT_VERSION) > 0) {
        showUpdateToast(
          data.version,
          data.changelog_url || null,
          data.release_notes || null
        );
      }
    } catch (e) {
      // Silently fail — network issues shouldn't affect the app
      console.debug('Stellaris version check skipped:', e.message);
    }
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // INIT — run after page loads
  // ═══════════════════════════════════════════════════════════════════════════
  
  if (document.readyState === 'complete') {
    setTimeout(checkForUpdates, 3000);  // Delay so it doesn't compete with app load
  } else {
    window.addEventListener('load', function() {
      setTimeout(checkForUpdates, 3000);
    });
  }

})();
