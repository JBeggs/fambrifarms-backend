"""
WSGI configuration for FambriFarms on PythonAnywhere.

This module contains the WSGI application used by Django's development server
and any production WSGI deployments on PythonAnywhere.

Usage on PythonAnywhere:
1. Upload your project to: /home/FambriDevOps/app/
2. Set this as your WSGI file in the Web tab
3. Configure virtualenv: /home/FambriDevOps/.virtualenvs/fambrifarms
"""

import os
import sys

# Add your project directory to Python's path
path = '/home/FambriDevOps/app'
if path not in sys.path:
    sys.path.insert(0, path)

# Set the Django settings module
os.environ['DJANGO_SETTINGS_MODULE'] = 'familyfarms_api.settings'

# Import Django WSGI application
from django.core.wsgi import get_wsgi_application

# For serving static files in production (PythonAnywhere specific)
from django.contrib.staticfiles.handlers import StaticFilesHandler

# Create the WSGI application
django_application = get_wsgi_application()

# Wrap with StaticFilesHandler for serving static files
# Note: For production, you should configure static files through PythonAnywhere's web interface
application = StaticFilesHandler(django_application)
