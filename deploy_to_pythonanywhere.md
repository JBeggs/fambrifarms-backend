# Deploy to PythonAnywhere - Step by Step Guide

## 🚀 **Your Setup is Ready!**

Based on your `.env` file, here's how to deploy to your existing PythonAnywhere setup:

### 📁 **1. Upload Backend Files**

Upload these files to `/home/fambridevops/app/`:

```bash
# Core Django files
familyfarms_api/
accounts/
inventory/
invoices/
orders/
procurement/
production/
products/
suppliers/
whatsapp/
manage.py
requirements.txt
```

### 🔧 **2. Install Dependencies**

In your PythonAnywhere console:

```bash
cd /home/fambridevops/app
pip3.10 install --user -r requirements.txt
```

### 🗄️ **3. Database Setup**

Your database is already configured! Run migrations:

```bash
cd /home/fambridevops/app
python3.10 manage.py migrate --settings=familyfarms_api.production_settings
```

### 🌱 **4. Seed Production Database**

```bash
# Seed the production database with all your data
python3.10 manage.py seed_production_database --settings=familyfarms_api.production_settings
```

### 📊 **5. Collect Static Files**

```bash
python3.10 manage.py collectstatic --noinput --settings=familyfarms_api.production_settings
```

### 🌐 **6. Update WSGI Configuration**

Copy the content from `wsgi_pythonanywhere_template.py` to your WSGI file:
`/var/www/fambridevops_pythonanywhere_com_wsgi.py`

```python
"""
WSGI configuration for PythonAnywhere deployment
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
```

### ✅ **7. Test the Deployment**

1. **Reload your web app** in the PythonAnywhere Web tab
2. **Test API endpoints**:
   - `https://fambridevops.pythonanywhere.com/api/products/`
   - `https://fambridevops.pythonanywhere.com/api/auth/login/`
   - `https://fambridevops.pythonanywhere.com/admin/`

### 🔐 **8. Admin Access**

Create a superuser for production:

```bash
python3.10 manage.py createsuperuser --settings=familyfarms_api.production_settings
```

Or use the seeded admin account:
- **Email**: `admin@fambrifarms.co.za`
- **Password**: `defaultpassword123`

### 📱 **9. Update Flutter App**

Update your Flutter app's API base URL to:
```dart
static const String baseUrl = 'https://fambridevops.pythonanywhere.com/api';
```

## 🎯 **Your Configuration Summary**

✅ **Database**: MySQL configured with your credentials  
✅ **Static Files**: `/home/fambridevops/app/static`  
✅ **Media Files**: `/home/fambridevops/app/media`  
✅ **CORS**: Configured for Vercel and localhost  
✅ **CSRF**: Trusted origins configured  
✅ **Environment**: Production-ready with `.env` support  

## 🚨 **Important Notes**

1. **Your `.env` file** is already perfect - no changes needed!
2. **Database name**: `fambridevops$default` (matches your setup)
3. **Static/Media paths**: Match your existing structure
4. **CORS origins**: Include your Vercel app domain

## 🔄 **Future Updates**

To update the backend:
1. Upload changed files to `/home/fambridevops/app/`
2. Run migrations if models changed
3. Collect static files if needed
4. Reload the web app

## 🆘 **Troubleshooting**

If you get errors:
1. Check the error logs in PythonAnywhere
2. Verify all files uploaded correctly
3. Ensure virtual environment has all packages
4. Check WSGI file configuration

**You're all set for deployment!** 🎉
