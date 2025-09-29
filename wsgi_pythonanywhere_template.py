"""
WSGI configuration for PythonAnywhere deployment

This file should be copied to:
/var/www/fambridevops_pythonanywhere_com_wsgi.py
"""

import os
import sys

# PythonAnywhere username
PYTHONANYWHERE_USERNAME = 'fambridevops'

# Add your project directory to the sys.path
project_path = f'/home/{PYTHONANYWHERE_USERNAME}/app'
if project_path not in sys.path:
    sys.path.insert(0, project_path)

# Set the Django settings module
os.environ['DJANGO_SETTINGS_MODULE'] = 'familyfarms_api.production_settings'

# Import Django WSGI application
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

print(f"WSGI application loaded for {PYTHONANYWHERE_USERNAME}")
