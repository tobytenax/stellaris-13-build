# Stellaris-13 Production Configuration

import os
from datetime import timedelta

class Config:
    """Base configuration."""
    
    # Application
    APP_NAME = "Stellaris-13"
    APP_VERSION = "2.8.0"
    
    # Security
    SECRET_KEY = os.environ.get('SECRET_KEY') or os.urandom(32).hex()
    
    # Session
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    
    # Rate Limiting
    RATELIMIT_ENABLED = True
    RATELIMIT_DEFAULT = "100 per minute"
    RATELIMIT_STORAGE_URL = "memory://"
    
    # CORS (adjust for your domains)
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*').split(',')
    
    # AI Providers (optional server-side keys)
    MISTRAL_API_KEY = os.environ.get('MISTRAL_API_KEY')
    ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
    
    # Payhip License Secrets
    PAYHIP_SECRET_PERSONAL = os.environ.get('PAYHIP_SECRET_PERSONAL', 'prod_sk_uFaVf_b133ad83c84192f7487c7f1e5a3a1754e49c3334')
    PAYHIP_SECRET_PROFESSIONAL = os.environ.get('PAYHIP_SECRET_PROFESSIONAL', 'prod_sk_1HALp_11d9d60b538b21f9f370a82386914ab6de63b212')
    PAYHIP_SECRET_ASTROLOGER = os.environ.get('PAYHIP_SECRET_ASTROLOGER', 'prod_sk_gQZWH_42e8879e6d3d63458764debcaa74e7a88399d89b')
    
    # Timeouts
    AI_REQUEST_TIMEOUT = 120  # seconds
    
    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    SESSION_COOKIE_SECURE = False
    RATELIMIT_ENABLED = False


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    
    # Enforce HTTPS
    PREFERRED_URL_SCHEME = 'https'
    
    # Stricter rate limits
    RATELIMIT_DEFAULT = "60 per minute"
    
    # Security headers (applied via middleware)
    SECURITY_HEADERS = {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'SAMEORIGIN',
        'X-XSS-Protection': '1; mode=block',
        'Referrer-Policy': 'strict-origin-when-cross-origin',
        'Permissions-Policy': 'geolocation=(), microphone=(), camera=()',
        'Content-Security-Policy': (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://unpkg.com https://cdnjs.cloudflare.com; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: https://*.tile.openstreetmap.org; "
            "connect-src 'self' https://api.mistral.ai https://api.anthropic.com https://api.01.ai https://api.fireworks.ai https://api.groq.com http://localhost:11434; "
        )
    }


class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    DEBUG = True
    RATELIMIT_ENABLED = False


# Config selector
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


def get_config():
    """Get configuration based on environment."""
    env = os.environ.get('FLASK_ENV', 'development')
    return config.get(env, config['default'])

TIER = 'astrologer'
