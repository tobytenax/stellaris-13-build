/**
 * Stellaris-13 License Activation UI
 * ====================================
 * Drop-in activation dialog for the app frontend.
 * 
 * Shows current license status and allows activation/deactivation.
 * Add to index.html before </body>:
 *   <script src="/static/js/license_ui.js"></script>
 * 
 * Trigger with:
 *   <button onclick="showLicenseDialog()">Manage License</button>
 * 
 * Or auto-show on page load if no license is active:
 *   window.addEventListener('load', () => checkAndPromptLicense());
 */

(function() {
  'use strict';

  // ═══════════════════════════════════════════════════════════════════════════
  // STATE
  // ═══════════════════════════════════════════════════════════════════════════
  
  let currentTier = 'free';
  let dialogElement = null;

  // ═══════════════════════════════════════════════════════════════════════════
  // API CALLS
  // ═══════════════════════════════════════════════════════════════════════════

  async function getLicenseStatus() {
    try {
      const resp = await fetch('/api/license/status');
      return await resp.json();
    } catch (e) {
      return { valid: true, tier: 'free', message: 'Unable to check license status.' };
    }
  }

  async function activateLicense(key) {
    try {
      const resp = await fetch('/api/license/activate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ license_key: key })
      });
      return await resp.json();
    } catch (e) {
      return { valid: false, tier: 'invalid', message: 'Network error. Check your connection.' };
    }
  }

  async function deactivateLicense() {
    try {
      const resp = await fetch('/api/license/deactivate', { method: 'POST' });
      return await resp.json();
    } catch (e) {
      return { valid: true, tier: 'free', message: 'Error deactivating.' };
    }
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // TIER BADGE
  // ═══════════════════════════════════════════════════════════════════════════

  function getTierBadge(tier) {
    const badges = {
      'free':         { label: 'Seeker (Free)', color: '#888', bg: 'rgba(255,255,255,0.05)' },
      'personal':     { label: 'Personal',      color: '#c9a83b', bg: 'rgba(201,168,59,0.1)' },
      'professional': { label: 'Professional',  color: '#6c5ce7', bg: 'rgba(108,92,231,0.1)' },
      'astrologer':   { label: 'Astrologer',    color: '#e74c3c', bg: 'rgba(231,76,60,0.1)' },
      'invalid':      { label: 'Not Activated',  color: '#e74c3c', bg: 'rgba(231,76,60,0.1)' },
    };
    return badges[tier] || badges['free'];
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // DIALOG
  // ═══════════════════════════════════════════════════════════════════════════

  function createDialog() {
    const overlay = document.createElement('div');
    overlay.id = 'license-dialog-overlay';
    overlay.innerHTML = `
      <style>
        #license-dialog-overlay {
          position: fixed;
          top: 0; left: 0; right: 0; bottom: 0;
          background: rgba(0, 0, 0, 0.7);
          z-index: 50000;
          display: flex;
          align-items: center;
          justify-content: center;
          animation: fadeIn 0.2s ease-out;
        }
        @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
        
        #license-dialog {
          background: linear-gradient(135deg, #1a1a2e, #16213e);
          border: 1px solid #c9a83b;
          border-radius: 16px;
          padding: 32px;
          max-width: 480px;
          width: 90vw;
          box-shadow: 0 16px 64px rgba(0, 0, 0, 0.8);
          font-family: 'Georgia', serif;
          color: #d4cfc5;
        }
        
        #license-dialog h2 {
          color: #c9a83b;
          margin: 0 0 8px 0;
          font-size: 20px;
        }
        
        #license-dialog .tier-badge {
          display: inline-block;
          padding: 4px 12px;
          border-radius: 20px;
          font-size: 13px;
          font-weight: bold;
          margin-bottom: 20px;
        }
        
        #license-dialog input[type="text"] {
          width: 100%;
          padding: 12px 16px;
          background: rgba(255,255,255,0.05);
          border: 1px solid #444;
          border-radius: 8px;
          color: #e8e0d0;
          font-family: 'Courier New', monospace;
          font-size: 15px;
          letter-spacing: 2px;
          text-transform: uppercase;
          box-sizing: border-box;
          outline: none;
          transition: border-color 0.2s;
        }
        
        #license-dialog input[type="text"]:focus {
          border-color: #c9a83b;
        }
        
        #license-dialog input[type="text"]::placeholder {
          color: #555;
          letter-spacing: 1px;
          text-transform: none;
        }
        
        #license-dialog .btn-row {
          display: flex;
          gap: 10px;
          margin-top: 16px;
        }
        
        #license-dialog .btn {
          padding: 10px 20px;
          border-radius: 8px;
          border: none;
          font-size: 14px;
          font-weight: bold;
          cursor: pointer;
          transition: opacity 0.2s;
        }
        
        #license-dialog .btn:hover { opacity: 0.85; }
        #license-dialog .btn:disabled { opacity: 0.5; cursor: not-allowed; }
        
        #license-dialog .btn-primary {
          background: linear-gradient(135deg, #c9a83b, #a08520);
          color: #1a1a2e;
          flex: 1;
        }
        
        #license-dialog .btn-secondary {
          background: rgba(255,255,255,0.08);
          color: #a09686;
          border: 1px solid #444;
        }
        
        #license-dialog .btn-danger {
          background: rgba(231, 76, 60, 0.15);
          color: #e74c3c;
          border: 1px solid rgba(231, 76, 60, 0.3);
          font-size: 12px;
        }
        
        #license-dialog .status-msg {
          margin-top: 12px;
          padding: 10px 14px;
          border-radius: 8px;
          font-size: 13px;
          line-height: 1.4;
          display: none;
        }
        
        #license-dialog .status-msg.success {
          background: rgba(46, 204, 113, 0.1);
          border: 1px solid rgba(46, 204, 113, 0.3);
          color: #2ecc71;
          display: block;
        }
        
        #license-dialog .status-msg.error {
          background: rgba(231, 76, 60, 0.1);
          border: 1px solid rgba(231, 76, 60, 0.3);
          color: #e74c3c;
          display: block;
        }
        
        #license-dialog .upgrade-link {
          display: block;
          margin-top: 16px;
          text-align: center;
          color: #c9a83b;
          font-size: 13px;
          text-decoration: none;
        }
        
        #license-dialog .upgrade-link:hover {
          color: #e8d070;
          text-decoration: underline;
        }
        
        #license-dialog .close-btn {
          position: absolute;
          top: 16px;
          right: 20px;
          background: none;
          border: none;
          color: #666;
          font-size: 24px;
          cursor: pointer;
        }
      </style>
      
      <div id="license-dialog" style="position: relative;">
        <button class="close-btn" onclick="closeLicenseDialog()">&times;</button>
        <h2>✦ License Manager</h2>
        <div id="license-tier-badge" class="tier-badge"></div>
        
        <div id="license-activate-section">
          <p style="color: #a09686; font-size: 13px; margin-bottom: 12px;">
            Enter your license key to unlock paid features:
          </p>
          <input type="text" id="license-key-input" placeholder="XXXX-XXXX-XXXX-XXXX" 
                 maxlength="30" autocomplete="off" spellcheck="false" />
          <div class="btn-row">
            <button class="btn btn-primary" id="license-activate-btn" onclick="doActivate()">
              Activate
            </button>
            <button class="btn btn-secondary" onclick="closeLicenseDialog()">
              Cancel
            </button>
          </div>
        </div>
        
        <div id="license-active-section" style="display: none;">
          <p id="license-active-info" style="color: #a09686; font-size: 13px;"></p>
          <div class="btn-row">
            <button class="btn btn-secondary" onclick="closeLicenseDialog()">Close</button>
            <button class="btn btn-danger" onclick="doDeactivate()">
              Deactivate This Machine
            </button>
          </div>
        </div>
        
        <div id="license-status-msg" class="status-msg"></div>
        
        <a href="https://payhip.com/Stellaris13" target="_blank" class="upgrade-link">
          Don't have a license? Visit the Stellaris-13 store →
        </a>
      </div>
    `;
    
    document.body.appendChild(overlay);
    
    // Close on overlay click
    overlay.addEventListener('click', function(e) {
      if (e.target === overlay) closeLicenseDialog();
    });
    
    // Close on Escape
    document.addEventListener('keydown', function(e) {
      if (e.key === 'Escape') closeLicenseDialog();
    });
    
    return overlay;
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // DIALOG ACTIONS
  // ═══════════════════════════════════════════════════════════════════════════

  window.showLicenseDialog = async function() {
    if (dialogElement) dialogElement.remove();
    dialogElement = createDialog();
    
    // Get current status
    const status = await getLicenseStatus();
    currentTier = status.tier;
    
    // Update badge
    const badge = getTierBadge(status.tier);
    const badgeEl = document.getElementById('license-tier-badge');
    badgeEl.textContent = badge.label;
    badgeEl.style.color = badge.color;
    badgeEl.style.background = badge.bg;
    badgeEl.style.border = `1px solid ${badge.color}40`;
    
    // Show appropriate section
    if (status.tier !== 'free' && status.tier !== 'invalid') {
      document.getElementById('license-activate-section').style.display = 'none';
      document.getElementById('license-active-section').style.display = 'block';
      document.getElementById('license-active-info').textContent = status.message;
    } else {
      document.getElementById('license-activate-section').style.display = 'block';
      document.getElementById('license-active-section').style.display = 'none';
      // Focus the input
      setTimeout(() => document.getElementById('license-key-input').focus(), 100);
    }
  };

  window.closeLicenseDialog = function() {
    if (dialogElement) {
      dialogElement.remove();
      dialogElement = null;
    }
  };

  window.doActivate = async function() {
    const input = document.getElementById('license-key-input');
    const btn = document.getElementById('license-activate-btn');
    const msgEl = document.getElementById('license-status-msg');
    const key = input.value.trim();
    
    if (!key) {
      msgEl.className = 'status-msg error';
      msgEl.textContent = 'Please enter a license key.';
      return;
    }
    
    btn.disabled = true;
    btn.textContent = 'Validating...';
    msgEl.className = 'status-msg';
    msgEl.style.display = 'none';
    
    const result = await activateLicense(key);
    
    btn.disabled = false;
    btn.textContent = 'Activate';
    
    if (result.valid && result.tier !== 'free' && result.tier !== 'invalid') {
      msgEl.className = 'status-msg success';
      msgEl.textContent = result.message;
      currentTier = result.tier;
      
      // Update badge
      const badge = getTierBadge(result.tier);
      const badgeEl = document.getElementById('license-tier-badge');
      badgeEl.textContent = badge.label;
      badgeEl.style.color = badge.color;
      badgeEl.style.background = badge.bg;
      badgeEl.style.border = `1px solid ${badge.color}40`;
      
      // Switch to active view after a moment
      setTimeout(() => {
        document.getElementById('license-activate-section').style.display = 'none';
        document.getElementById('license-active-section').style.display = 'block';
        document.getElementById('license-active-info').textContent = result.message;
      }, 2000);
      
      // Notify the rest of the app
      window.dispatchEvent(new CustomEvent('license-changed', { detail: result }));
    } else {
      msgEl.className = 'status-msg error';
      msgEl.textContent = result.message;
    }
  };

  window.doDeactivate = async function() {
    if (!confirm('Deactivate your license on this machine? You can re-activate later.')) return;
    
    const result = await deactivateLicense();
    currentTier = 'free';
    
    // Refresh dialog
    await window.showLicenseDialog();
    
    const msgEl = document.getElementById('license-status-msg');
    msgEl.className = 'status-msg success';
    msgEl.textContent = result.message;
    
    // Notify the rest of the app
    window.dispatchEvent(new CustomEvent('license-changed', { detail: result }));
  };

  // ═══════════════════════════════════════════════════════════════════════════
  // AUTO-PROMPT (optional)
  // ═══════════════════════════════════════════════════════════════════════════

  window.checkAndPromptLicense = async function() {
    const status = await getLicenseStatus();
    currentTier = status.tier;
    
    // Update any tier badges in the main UI
    document.querySelectorAll('[data-tier-badge]').forEach(el => {
      const badge = getTierBadge(status.tier);
      el.textContent = badge.label;
      el.style.color = badge.color;
    });
    
    // Store tier globally for feature gating in the frontend
    window.stellarisTier = status.tier;
  };

  // ═══════════════════════════════════════════════════════════════════════════
  // EXPOSE TIER CHECK
  // ═══════════════════════════════════════════════════════════════════════════

  window.hasFeatureAccess = function(requiredTier) {
    const levels = { 'free': 0, 'personal': 1, 'professional': 2, 'astrologer': 3 };
    return (levels[currentTier] || 0) >= (levels[requiredTier] || 0);
  };

  // Auto-check on load
  if (document.readyState === 'complete') {
    checkAndPromptLicense();
  } else {
    window.addEventListener('load', checkAndPromptLicense);
  }

})();
