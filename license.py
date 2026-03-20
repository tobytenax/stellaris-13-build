"""
Stellaris-13 License Validation & Machine Binding
====================================================
Anti-piracy system for one-time-purchase software.

Architecture:
  Layer 1 — License key validation against Payhip API
  Layer 2 — Machine fingerprint binding (CPU, MAC, disk serial)
  Layer 3 — Local encrypted activation cache (works offline after first activation)
  Layer 4 — Periodic re-validation (phone home every 7 days, grace period 30 days)

Flow:
  1. User enters license key on first launch
  2. App validates key against Payhip API
  3. App generates machine fingerprint
  4. App increments Payhip "uses" counter (tracks activations)
  5. App stores encrypted activation locally
  6. Subsequent launches check local activation + periodic re-validation
  7. If machine fingerprint changes → requires re-activation (new "use")

Integration:
  from license import LicenseManager
  
  lm = LicenseManager(config)
  status = lm.check_license()
  
  if status.tier == 'free':
      # Free features only
  elif status.tier == 'personal':
      # Personal features
  elif status.tier == 'professional':
      # Professional features
  elif status.tier == 'astrologer':
      # All features
  elif status.tier == 'invalid':
      # Show activation screen

Requires: cryptography (pip install cryptography)
"""

import os
import sys
import json
import hashlib
import platform
import uuid
import time
import logging
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import Optional

try:
    import requests
except ImportError:
    requests = None

try:
    from cryptography.fernet import Fernet
except ImportError:
    Fernet = None

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class LicenseConfig:
    """Configuration for the license system."""
    
    # Payhip product secret keys (one per tier, from Payhip product edit page)
    # These are NOT the API key — they're per-product secrets for license verification
    product_secrets: dict = None  # {'personal': 'xxx', 'professional': 'xxx', 'astrologer': 'xxx'}
    
    # Max activations per license key (machines)
    max_activations: int = 3
    
    # How often to re-validate online (seconds)
    revalidation_interval: int = 7 * 24 * 3600  # 7 days
    
    # Grace period if online validation fails (seconds)
    offline_grace_period: int = 30 * 24 * 3600  # 30 days
    
    # Where to store activation data
    activation_dir: str = None  # Set at runtime
    
    # App version (for activation records)
    app_version: str = '2.7.3'
    
    def __post_init__(self):
        if self.product_secrets is None:
            self.product_secrets = {}
        if self.activation_dir is None:
            # Platform-appropriate config directory
            if platform.system() == 'Windows':
                base = os.environ.get('APPDATA', os.path.expanduser('~'))
                self.activation_dir = os.path.join(base, 'Stellaris-13')
            elif platform.system() == 'Darwin':
                self.activation_dir = os.path.expanduser('~/Library/Application Support/Stellaris-13')
            else:
                self.activation_dir = os.path.expanduser('~/.config/stellaris-13')


# ═══════════════════════════════════════════════════════════════════════════════
# LICENSE STATUS
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class LicenseStatus:
    """Result of a license check."""
    valid: bool = False
    tier: str = 'free'  # 'free', 'personal', 'professional', 'astrologer', 'invalid'
    license_key: Optional[str] = None
    machine_id: Optional[str] = None
    activated_at: Optional[str] = None
    last_validated: Optional[str] = None
    expires_offline: Optional[str] = None
    activations_used: int = 0
    message: str = ''


# ═══════════════════════════════════════════════════════════════════════════════
# MACHINE FINGERPRINT
# ═══════════════════════════════════════════════════════════════════════════════

class MachineFingerprint:
    """
    Generate a stable machine fingerprint from hardware identifiers.
    
    Uses multiple signals so that minor changes (new USB device, network adapter)
    don't invalidate the fingerprint, but major changes (new motherboard, new CPU)
    do require re-activation.
    """
    
    @staticmethod
    def _get_cpu_id() -> str:
        """Get CPU identifier."""
        try:
            system = platform.system()
            if system == 'Linux':
                # Read from /proc/cpuinfo
                with open('/proc/cpuinfo', 'r') as f:
                    for line in f:
                        if 'model name' in line:
                            return line.split(':')[1].strip()
                # Fallback: machine id
                if os.path.exists('/etc/machine-id'):
                    with open('/etc/machine-id', 'r') as f:
                        return f.read().strip()
            elif system == 'Windows':
                result = subprocess.run(
                    ['wmic', 'cpu', 'get', 'processorid'],
                    capture_output=True, text=True, timeout=10
                )
                lines = [l.strip() for l in result.stdout.split('\n') if l.strip() and l.strip() != 'ProcessorId']
                if lines:
                    return lines[0]
            elif system == 'Darwin':
                result = subprocess.run(
                    ['sysctl', '-n', 'machdep.cpu.brand_string'],
                    capture_output=True, text=True, timeout=10
                )
                return result.stdout.strip()
        except Exception as e:
            logger.debug(f"CPU ID fallback: {e}")
        return platform.processor() or 'unknown_cpu'
    
    @staticmethod
    def _get_machine_id() -> str:
        """Get OS-level machine ID (most stable identifier)."""
        try:
            system = platform.system()
            if system == 'Linux':
                # /etc/machine-id is stable across reboots, generated at install
                for path in ['/etc/machine-id', '/var/lib/dbus/machine-id']:
                    if os.path.exists(path):
                        with open(path, 'r') as f:
                            mid = f.read().strip()
                            if mid:
                                return mid
            elif system == 'Windows':
                result = subprocess.run(
                    ['reg', 'query',
                     'HKLM\\SOFTWARE\\Microsoft\\Cryptography',
                     '/v', 'MachineGuid'],
                    capture_output=True, text=True, timeout=10
                )
                for line in result.stdout.split('\n'):
                    if 'MachineGuid' in line:
                        return line.split()[-1].strip()
            elif system == 'Darwin':
                result = subprocess.run(
                    ['ioreg', '-rd1', '-c', 'IOPlatformExpertDevice'],
                    capture_output=True, text=True, timeout=10
                )
                for line in result.stdout.split('\n'):
                    if 'IOPlatformUUID' in line:
                        return line.split('"')[-2]
        except Exception as e:
            logger.debug(f"Machine ID fallback: {e}")
        return str(uuid.getnode())  # MAC address as fallback
    
    @staticmethod
    def _get_disk_serial() -> str:
        """Get primary disk serial number."""
        try:
            system = platform.system()
            if system == 'Linux':
                # Try to get root filesystem disk serial
                result = subprocess.run(
                    ['lsblk', '-no', 'SERIAL', '/dev/sda'],
                    capture_output=True, text=True, timeout=10
                )
                serial = result.stdout.strip()
                if serial:
                    return serial
                # Fallback: filesystem UUID
                result = subprocess.run(
                    ['findmnt', '-no', 'UUID', '/'],
                    capture_output=True, text=True, timeout=10
                )
                return result.stdout.strip() or 'unknown_disk'
            elif system == 'Windows':
                result = subprocess.run(
                    ['wmic', 'diskdrive', 'get', 'serialnumber'],
                    capture_output=True, text=True, timeout=10
                )
                lines = [l.strip() for l in result.stdout.split('\n') if l.strip() and l.strip() != 'SerialNumber']
                if lines:
                    return lines[0]
            elif system == 'Darwin':
                result = subprocess.run(
                    ['system_profiler', 'SPSerialATADataType'],
                    capture_output=True, text=True, timeout=10
                )
                for line in result.stdout.split('\n'):
                    if 'Serial Number' in line:
                        return line.split(':')[-1].strip()
        except Exception as e:
            logger.debug(f"Disk serial fallback: {e}")
        return 'unknown_disk'
    
    @classmethod
    def generate(cls) -> str:
        """
        Generate a composite machine fingerprint.
        
        Uses machine_id as primary (most stable), with CPU and disk as salt.
        The fingerprint is a SHA-256 hash so no hardware info is stored in plain text.
        """
        components = [
            cls._get_machine_id(),
            cls._get_cpu_id(),
            cls._get_disk_serial(),
            platform.system(),
            platform.machine(),
        ]
        
        # Join and hash
        raw = '|'.join(components)
        fingerprint = hashlib.sha256(raw.encode('utf-8')).hexdigest()[:32]
        
        logger.debug(f"Machine fingerprint generated: {fingerprint[:8]}...")
        return fingerprint


# ═══════════════════════════════════════════════════════════════════════════════
# ACTIVATION STORAGE (encrypted local cache)
# ═══════════════════════════════════════════════════════════════════════════════

class ActivationStore:
    """
    Encrypted local storage for activation data.
    
    The encryption key is derived from the machine fingerprint,
    so the activation file is useless if copied to another machine.
    """
    
    def __init__(self, activation_dir: str, machine_id: str):
        self.activation_dir = activation_dir
        self.machine_id = machine_id
        self._fernet = None
        
        if Fernet is not None:
            # Derive encryption key from machine fingerprint
            key_material = hashlib.sha256(
                f"stellaris13:{machine_id}:activation".encode()
            ).digest()
            # Fernet needs url-safe base64 encoded 32-byte key
            import base64
            key = base64.urlsafe_b64encode(key_material)
            self._fernet = Fernet(key)
    
    @property
    def activation_file(self) -> str:
        return os.path.join(self.activation_dir, '.activation')
    
    def save(self, data: dict) -> bool:
        """Save activation data (encrypted)."""
        try:
            os.makedirs(self.activation_dir, exist_ok=True)
            
            payload = json.dumps(data).encode('utf-8')
            
            if self._fernet:
                payload = self._fernet.encrypt(payload)
            
            with open(self.activation_file, 'wb') as f:
                f.write(payload)
            
            # Set restrictive permissions on Linux/Mac
            if platform.system() != 'Windows':
                os.chmod(self.activation_file, 0o600)
            
            return True
        except Exception as e:
            logger.error(f"Failed to save activation: {e}")
            return False
    
    def load(self) -> Optional[dict]:
        """Load activation data (decrypted)."""
        try:
            if not os.path.exists(self.activation_file):
                return None
            
            with open(self.activation_file, 'rb') as f:
                payload = f.read()
            
            if self._fernet:
                try:
                    payload = self._fernet.decrypt(payload)
                except Exception:
                    # Decryption failed — file was copied from another machine
                    # or machine fingerprint changed
                    logger.warning("Activation file decryption failed — machine mismatch")
                    return None
            
            return json.loads(payload.decode('utf-8'))
        except Exception as e:
            logger.error(f"Failed to load activation: {e}")
            return None
    
    def clear(self) -> bool:
        """Remove activation data."""
        try:
            if os.path.exists(self.activation_file):
                os.remove(self.activation_file)
            return True
        except Exception as e:
            logger.error(f"Failed to clear activation: {e}")
            return False


# ═══════════════════════════════════════════════════════════════════════════════
# PAYHIP API CLIENT
# ═══════════════════════════════════════════════════════════════════════════════

class PayhipLicenseAPI:
    """Client for Payhip's license verification API."""
    
    BASE_URL = 'https://payhip.com/api/v2'
    LEGACY_URL = 'https://payhip.com/api/v1'
    TIMEOUT = 15
    
    def __init__(self, product_secrets: dict):
        """
        Args:
            product_secrets: Dict mapping tier name to Payhip product secret key.
                             e.g. {'personal': 'abc123', 'professional': 'def456', ...}
        """
        self.product_secrets = product_secrets
    
    def verify(self, license_key: str) -> Optional[dict]:
        """
        Verify a license key against all product tiers.
        
        Returns dict with tier info if valid, None if invalid.
        Tries each product secret until one succeeds.
        """
        if requests is None:
            logger.error("requests library not available")
            return None
        
        for tier, secret in self.product_secrets.items():
            try:
                response = requests.get(
                    f"{self.BASE_URL}/license/verify",
                    params={'license_key': license_key},
                    headers={'product-secret-key': secret},
                    timeout=self.TIMEOUT
                )
                
                if response.status_code == 200:
                    data = response.json().get('data', {})
                    if data.get('enabled', False):
                        return {
                            'tier': tier,
                            'license_key': data.get('license_key'),
                            'buyer_email': data.get('buyer_email'),
                            'uses': data.get('uses', 0),
                            'date': data.get('date'),
                            'enabled': True
                        }
            except requests.RequestException as e:
                logger.warning(f"Payhip API error for tier {tier}: {e}")
                continue
            except Exception as e:
                logger.error(f"Unexpected error verifying {tier}: {e}")
                continue
        
        return None
    
    def increment_usage(self, license_key: str, tier: str) -> bool:
        """
        Increment the usage counter for a license key.
        Called on each new machine activation.
        """
        if requests is None:
            return False
        
        secret = self.product_secrets.get(tier)
        if not secret:
            return False
        
        try:
            response = requests.put(
                f"{self.LEGACY_URL}/license/usage",
                data={
                    'product_link': '',  # Not needed with v2 secret key approach
                    'license_key': license_key
                },
                headers={'product-secret-key': secret},
                timeout=self.TIMEOUT
            )
            
            if response.status_code == 200:
                data = response.json().get('data', {})
                return data.get('enabled', False)
        except Exception as e:
            logger.warning(f"Failed to increment usage: {e}")
        
        return False
    
    def disable(self, license_key: str, tier: str) -> bool:
        """Disable a license key (for abuse cases)."""
        if requests is None:
            return False
        
        secret = self.product_secrets.get(tier)
        if not secret:
            return False
        
        try:
            response = requests.put(
                f"{self.LEGACY_URL}/license/disable",
                data={'license_key': license_key},
                headers={'product-secret-key': secret},
                timeout=self.TIMEOUT
            )
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Failed to disable license: {e}")
        
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# LICENSE MANAGER (main interface)
# ═══════════════════════════════════════════════════════════════════════════════

class LicenseManager:
    """
    Main license management interface.
    
    Usage:
        config = LicenseConfig(
            product_secrets={
                'personal': 'your_payhip_product_secret',
                'professional': 'your_payhip_product_secret',
                'astrologer': 'your_payhip_product_secret',
            }
        )
        
        lm = LicenseManager(config)
        status = lm.check_license()
        
        if status.tier in ('personal', 'professional', 'astrologer'):
            # Paid features
        else:
            # Free tier
    """
    
    def __init__(self, config: LicenseConfig):
        self.config = config
        self.machine_id = MachineFingerprint.generate()
        self.store = ActivationStore(config.activation_dir, self.machine_id)
        self.api = PayhipLicenseAPI(config.product_secrets)
    
    def check_license(self) -> LicenseStatus:
        """
        Check license status. This is the main entry point.
        
        Logic:
          1. Check for local activation cache
          2. If cached and machine matches → check if re-validation needed
          3. If no cache → return free tier (user needs to activate)
          4. If cache exists but machine doesn't match → return invalid
        """
        # Load cached activation
        cached = self.store.load()
        
        if cached is None:
            # No activation found — free tier
            return LicenseStatus(
                valid=True,
                tier='free',
                machine_id=self.machine_id,
                message='No license activated. Running in free mode.'
            )
        
        # Verify machine fingerprint matches
        if cached.get('machine_id') != self.machine_id:
            # Machine changed — activation is invalid
            self.store.clear()
            return LicenseStatus(
                valid=False,
                tier='invalid',
                machine_id=self.machine_id,
                message='Machine fingerprint mismatch. Please re-activate your license.'
            )
        
        # Check if online re-validation is needed
        last_validated = cached.get('last_validated', 0)
        now = time.time()
        needs_revalidation = (now - last_validated) > self.config.revalidation_interval
        
        if needs_revalidation:
            # Try to re-validate online
            result = self.api.verify(cached.get('license_key', ''))
            
            if result and result['enabled']:
                # Still valid — update cache
                cached['last_validated'] = now
                cached['tier'] = result['tier']
                self.store.save(cached)
                
                return LicenseStatus(
                    valid=True,
                    tier=result['tier'],
                    license_key=cached.get('license_key'),
                    machine_id=self.machine_id,
                    activated_at=cached.get('activated_at'),
                    last_validated=datetime.fromtimestamp(now).isoformat(),
                    activations_used=result.get('uses', 0),
                    message=f'License valid. {result["tier"].title()} edition.'
                )
            elif result is None:
                # Network error — check grace period
                grace_deadline = last_validated + self.config.offline_grace_period
                
                if now < grace_deadline:
                    days_left = int((grace_deadline - now) / 86400)
                    return LicenseStatus(
                        valid=True,
                        tier=cached.get('tier', 'free'),
                        license_key=cached.get('license_key'),
                        machine_id=self.machine_id,
                        activated_at=cached.get('activated_at'),
                        last_validated=datetime.fromtimestamp(last_validated).isoformat(),
                        message=f'Offline mode. {days_left} days until re-validation required.'
                    )
                else:
                    # Grace period expired
                    return LicenseStatus(
                        valid=False,
                        tier='invalid',
                        machine_id=self.machine_id,
                        message='License re-validation required. Please connect to the internet.'
                    )
            else:
                # License was disabled/revoked
                self.store.clear()
                return LicenseStatus(
                    valid=False,
                    tier='invalid',
                    machine_id=self.machine_id,
                    message='License has been revoked or disabled.'
                )
        
        # Cached and still within re-validation window
        return LicenseStatus(
            valid=True,
            tier=cached.get('tier', 'free'),
            license_key=cached.get('license_key'),
            machine_id=self.machine_id,
            activated_at=cached.get('activated_at'),
            last_validated=datetime.fromtimestamp(last_validated).isoformat(),
            message=f'{cached.get("tier", "free").title()} edition active.'
        )
    
    def activate(self, license_key: str) -> LicenseStatus:
        """
        Activate a license key on this machine.
        
        Flow:
          1. Validate key against Payhip API
          2. Check activation count against max_activations
          3. Increment usage counter
          4. Store encrypted activation locally
        """
        license_key = license_key.strip().upper()
        
        if not license_key:
            return LicenseStatus(
                valid=False,
                tier='invalid',
                message='No license key provided.'
            )
        
        # Validate against Payhip
        result = self.api.verify(license_key)
        
        if result is None:
            return LicenseStatus(
                valid=False,
                tier='invalid',
                message='Invalid license key, or unable to reach the license server. Check your internet connection and try again.'
            )
        
        if not result.get('enabled', False):
            return LicenseStatus(
                valid=False,
                tier='invalid',
                message='This license key has been disabled.'
            )
        
        # Check activation limit
        current_uses = result.get('uses', 0)
        if current_uses >= self.config.max_activations:
            return LicenseStatus(
                valid=False,
                tier='invalid',
                activations_used=current_uses,
                message=f'Activation limit reached ({current_uses}/{self.config.max_activations} machines). '
                        f'Contact support to reset activations.'
            )
        
        # Check if this machine is already activated with this key
        cached = self.store.load()
        if cached and cached.get('license_key') == license_key and cached.get('machine_id') == self.machine_id:
            # Already activated on this machine — just re-validate
            cached['last_validated'] = time.time()
            cached['tier'] = result['tier']
            self.store.save(cached)
            
            return LicenseStatus(
                valid=True,
                tier=result['tier'],
                license_key=license_key,
                machine_id=self.machine_id,
                activated_at=cached.get('activated_at'),
                last_validated=datetime.now().isoformat(),
                activations_used=current_uses,
                message=f'License already active on this machine. {result["tier"].title()} edition.'
            )
        
        # New activation — increment usage counter
        self.api.increment_usage(license_key, result['tier'])
        
        # Store activation
        now = time.time()
        activation_data = {
            'license_key': license_key,
            'tier': result['tier'],
            'machine_id': self.machine_id,
            'activated_at': datetime.now().isoformat(),
            'last_validated': now,
            'buyer_email': result.get('buyer_email', ''),
            'app_version': self.config.app_version,
        }
        
        if self.store.save(activation_data):
            return LicenseStatus(
                valid=True,
                tier=result['tier'],
                license_key=license_key,
                machine_id=self.machine_id,
                activated_at=activation_data['activated_at'],
                last_validated=datetime.now().isoformat(),
                activations_used=current_uses + 1,
                message=f'Activation successful! {result["tier"].title()} edition unlocked. '
                        f'({current_uses + 1}/{self.config.max_activations} machines used.)'
            )
        else:
            return LicenseStatus(
                valid=False,
                tier='invalid',
                message='License is valid but activation could not be saved locally. Check file permissions.'
            )
    
    def deactivate(self) -> LicenseStatus:
        """
        Deactivate this machine (free up an activation slot).
        Does NOT revoke the key — just removes local activation.
        """
        # Note: Payhip doesn't have a "decrease usage" endpoint in the new API,
        # so we can only clear the local activation. The uses counter stays.
        # For a manual reset, the seller (you) can manage this from the Payhip dashboard.
        
        self.store.clear()
        
        return LicenseStatus(
            valid=True,
            tier='free',
            machine_id=self.machine_id,
            message='License deactivated on this machine. You can re-activate on another machine.'
        )
    
    def get_tier(self) -> str:
        """Quick check — returns just the tier string."""
        return self.check_license().tier


# ═══════════════════════════════════════════════════════════════════════════════
# FEATURE GATING DECORATOR
# ═══════════════════════════════════════════════════════════════════════════════

# Tier hierarchy: free < personal < professional < astrologer
TIER_LEVELS = {
    'free': 0,
    'personal': 1,
    'professional': 2,
    'astrologer': 3,
    'invalid': -1,
}


def requires_tier(minimum_tier: str, license_manager: 'LicenseManager' = None):
    """
    Decorator to gate features by tier.
    
    Usage:
        @requires_tier('personal')
        def generate_blueprint(chart):
            ...
        
        @requires_tier('professional')
        def rectify_birth_time(chart, events):
            ...
        
        @requires_tier('astrologer')
        def crypto_natal_chart(coin):
            ...
    """
    min_level = TIER_LEVELS.get(minimum_tier, 0)
    
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Get license manager from global or parameter
            lm = license_manager or kwargs.pop('_license_manager', None)
            if lm is None:
                # Try to get from Flask app context
                try:
                    from flask import current_app
                    lm = current_app.config.get('LICENSE_MANAGER')
                except:
                    pass
            
            if lm is None:
                raise RuntimeError("License manager not configured")
            
            status = lm.check_license()
            current_level = TIER_LEVELS.get(status.tier, -1)
            
            if current_level < min_level:
                tier_names = {
                    'personal': 'Personal ($649)',
                    'professional': 'Professional ($1,497)',
                    'astrologer': 'Astrologer ($2,497)',
                }
                required_name = tier_names.get(minimum_tier, minimum_tier)
                raise PermissionError(
                    f"This feature requires the {required_name} edition. "
                    f"Current license: {status.tier.title()}. "
                    f"Upgrade at https://payhip.com/Stellaris13"
                )
            
            return func(*args, **kwargs)
        
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        wrapper._required_tier = minimum_tier
        return wrapper
    
    return decorator


# ═══════════════════════════════════════════════════════════════════════════════
# FLASK INTEGRATION
# ═══════════════════════════════════════════════════════════════════════════════

def init_license_system(app):
    """
    Initialize the license system with a Flask app.
    
    Call this in app.py after creating the Flask app:
    
        from license import init_license_system
        init_license_system(app)
    
    Then use in routes:
    
        from license import requires_tier
        
        @app.route('/api/blueprint', methods=['POST'])
        @requires_tier('personal')
        def api_blueprint():
            ...
    """
    config = LicenseConfig(
        product_secrets={
            'personal': app.config.get('PAYHIP_SECRET_PERSONAL', ''),
            'professional': app.config.get('PAYHIP_SECRET_PROFESSIONAL', ''),
            'astrologer': app.config.get('PAYHIP_SECRET_ASTROLOGER', ''),
        },
        max_activations=app.config.get('MAX_ACTIVATIONS', 3),
        app_version=app.config.get('VERSION', '2.7.3'),
    )
    
    lm = LicenseManager(config)
    app.config['LICENSE_MANAGER'] = lm
    
    # Add license check route
    @app.route('/api/license/status')
    def license_status():
        status = lm.check_license()
        return {
            'valid': status.valid,
            'tier': status.tier,
            'message': status.message,
            'activated_at': status.activated_at,
            'activations_used': status.activations_used,
        }
    
    @app.route('/api/license/activate', methods=['POST'])
    def license_activate():
        from flask import request
        data = request.get_json()
        key = data.get('license_key', '')
        status = lm.activate(key)
        return {
            'valid': status.valid,
            'tier': status.tier,
            'message': status.message,
            'activations_used': status.activations_used,
        }
    
    @app.route('/api/license/deactivate', methods=['POST'])
    def license_deactivate():
        status = lm.deactivate()
        return {
            'valid': status.valid,
            'tier': status.tier,
            'message': status.message,
        }
    
    logger.info(f"License system initialized. Machine ID: {lm.machine_id[:8]}...")
    return lm


# ═══════════════════════════════════════════════════════════════════════════════
# CLI TESTING
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    import argparse
    
    logging.basicConfig(level=logging.DEBUG)
    
    parser = argparse.ArgumentParser(description='Stellaris-13 License Manager')
    parser.add_argument('command', choices=['status', 'activate', 'deactivate', 'fingerprint'],
                       help='Command to run')
    parser.add_argument('--key', help='License key for activation')
    parser.add_argument('--secrets', help='JSON file with product secrets')
    
    args = parser.parse_args()
    
    # Load secrets
    secrets = {}
    if args.secrets and os.path.exists(args.secrets):
        with open(args.secrets, 'r') as f:
            secrets = json.load(f)
    
    config = LicenseConfig(product_secrets=secrets)
    lm = LicenseManager(config)
    
    if args.command == 'fingerprint':
        print(f"Machine fingerprint: {lm.machine_id}")
        print(f"Platform: {platform.system()} {platform.machine()}")
        print(f"Activation dir: {config.activation_dir}")
    
    elif args.command == 'status':
        status = lm.check_license()
        print(f"Valid: {status.valid}")
        print(f"Tier: {status.tier}")
        print(f"Message: {status.message}")
        if status.license_key:
            print(f"Key: {status.license_key[:8]}...")
        if status.activated_at:
            print(f"Activated: {status.activated_at}")
    
    elif args.command == 'activate':
        if not args.key:
            print("ERROR: --key required for activation")
            sys.exit(1)
        status = lm.activate(args.key)
        print(f"Valid: {status.valid}")
        print(f"Tier: {status.tier}")
        print(f"Message: {status.message}")
        print(f"Activations used: {status.activations_used}")
    
    elif args.command == 'deactivate':
        status = lm.deactivate()
        print(f"Tier: {status.tier}")
        print(f"Message: {status.message}")
