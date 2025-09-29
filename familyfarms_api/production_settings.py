"""
Production settings for PythonAnywhere deployment
Reads configuration from environment variables (.env file)
"""

from .settings import *
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

PYTHONANYWHERE_USERNAME = "fambridevops"

# Security settings from environment
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
PRODUCTION = os.getenv('PRODUCTION', 'True').lower() == 'true'
SECRET_KEY = os.getenv('SECRET_KEY', SECRET_KEY)

# Allowed hosts from environment
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '').split(',')

# Database configuration from environment
DB_ENGINE = os.getenv('DB_ENGINE', 'mysql')
if DB_ENGINE == 'mysql':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': os.getenv('DB_NAME'),
            'USER': os.getenv('DB_USER'),
            'PASSWORD': os.getenv('DB_PASSWORD'),
            'HOST': os.getenv('DB_HOST'),
            'PORT': os.getenv('DB_PORT', '3306'),
            'OPTIONS': {
                'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            },
        }
    }

# Static and Media files from environment
STATIC_ROOT = os.getenv('STATIC_ROOT', '/home/fambridevops/app/static')
STATIC_URL = '/static/'

MEDIA_ROOT = os.getenv('MEDIA_ROOT', '/home/fambridevops/app/media')
MEDIA_URL = '/media/'

# CORS configuration from environment
cors_origins = os.getenv('CORS_ALLOWED_ORIGINS', '')
if cors_origins:
    CORS_ALLOWED_ORIGINS = [origin.strip() for origin in cors_origins.split(',')]
else:
    CORS_ALLOWED_ORIGINS = [
        "http://localhost:3000",
        "http://localhost:8080",
    ]

# CSRF trusted origins from environment
csrf_origins = os.getenv('CSRF_TRUSTED_ORIGINS', '')
if csrf_origins:
    CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in csrf_origins.split(',')]

CORS_ALLOW_CREDENTIALS = True

# Security settings for production
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# Session configuration - Disabled SSL requirements for PythonAnywhere
# SESSION_COOKIE_SECURE = True  # Requires HTTPS
# CSRF_COOKIE_SECURE = True     # Requires HTTPS
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True

# Logging configuration - Use PythonAnywhere's default logging
# PythonAnywhere handles logging automatically, no custom configuration needed

# Email configuration (optional - for error reporting)
# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# EMAIL_HOST = 'smtp.gmail.com'
# EMAIL_PORT = 587
# EMAIL_USE_TLS = True
# EMAIL_HOST_USER = 'your-email@gmail.com'
# EMAIL_HOST_PASSWORD = 'your-app-password'
# DEFAULT_FROM_EMAIL = 'your-email@gmail.com'

# Cache configuration (optional - for better performance)
# CACHES = {
#     'default': {
#         'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
#         'LOCATION': 'cache_table',
#     }
# }

print(f"Production settings loaded for {PYTHONANYWHERE_USERNAME}.pythonanywhere.com")
