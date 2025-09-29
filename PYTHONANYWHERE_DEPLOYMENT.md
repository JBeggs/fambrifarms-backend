# PythonAnywhere Deployment Guide

## Pre-Deployment Checklist

### 1. Backend Finalization ✅
- [x] Fixed buffer_quantity API error in procurement recommendations
- [x] Business settings system implemented and working
- [x] Authentication system working with JWT
- [x] All API endpoints tested and functional
- [x] Database migrations up to date

### 2. Database Seeding ✅
- [x] Updated seeding scripts with current data
- [x] Production database seeding command ready
- [x] All models properly seeded (Users, Products, Customers, etc.)

### 3. Settings Configuration
- [ ] Update `ALLOWED_HOSTS` for PythonAnywhere domain
- [ ] Configure static files for production
- [ ] Set up environment variables
- [ ] Update CORS settings for Flutter app

## Deployment Steps

### Step 1: Upload Code to PythonAnywhere
```bash
# On PythonAnywhere console
git clone https://github.com/your-repo/fambrifarms_after_meeting.git
cd fambrifarms_after_meeting/backend
```

### Step 2: Install Dependencies
```bash
pip3.11 install --user -r requirements.txt
```

### Step 3: Configure Settings
Create `backend/familyfarms_api/production_settings.py`:
```python
from .settings import *

# Production settings
DEBUG = False
ALLOWED_HOSTS = ['yourusername.pythonanywhere.com', 'localhost', '127.0.0.1']

# Database (PythonAnywhere MySQL)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'yourusername$fambrifarms',
        'USER': 'yourusername',
        'PASSWORD': 'your-db-password',
        'HOST': 'yourusername.mysql.pythonanywhere-services.com',
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}

# Static files
STATIC_ROOT = '/home/yourusername/fambrifarms_after_meeting/backend/staticfiles'
STATIC_URL = '/static/'

# CORS for Flutter app
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",  # Flutter web dev
    "https://your-flutter-app-domain.com",  # Production Flutter
]
```

### Step 4: Database Setup
```bash
# Run migrations
python manage.py migrate --settings=familyfarms_api.production_settings

# Seed production database
python manage.py seed_production_database --settings=familyfarms_api.production_settings

# Create superuser
python manage.py createsuperuser --settings=familyfarms_api.production_settings

# Collect static files
python manage.py collectstatic --noinput --settings=familyfarms_api.production_settings
```

### Step 5: Configure WSGI
Create `/var/www/yourusername_pythonanywhere_com_wsgi.py`:
```python
import os
import sys

# Add your project directory to the sys.path
path = '/home/yourusername/fambrifarms_after_meeting/backend'
if path not in sys.path:
    sys.path.insert(0, path)

os.environ['DJANGO_SETTINGS_MODULE'] = 'familyfarms_api.production_settings'

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

### Step 6: Configure Static Files
In PythonAnywhere Web tab:
- Static files URL: `/static/`
- Static files directory: `/home/yourusername/fambrifarms_after_meeting/backend/staticfiles`

## Flutter App Configuration

### Update API Base URL
In `place-order-final/lib/services/api_service.dart`:
```dart
// Change from localhost to PythonAnywhere URL
static const String _baseUrl = 'https://yourusername.pythonanywhere.com/api';
```

### Build and Deploy Flutter
```bash
# For web deployment
flutter build web

# For mobile app stores
flutter build apk --release  # Android
flutter build ios --release  # iOS
```

## Testing Checklist

### Backend API Tests
- [ ] Authentication endpoints working
- [ ] Product management APIs
- [ ] Order processing APIs
- [ ] Procurement intelligence APIs
- [ ] WhatsApp message processing
- [ ] Business settings APIs

### Flutter App Tests
- [ ] Login/authentication working
- [ ] Product management
- [ ] Order creation and editing
- [ ] Customer management
- [ ] Procurement intelligence
- [ ] WhatsApp message processing

## Environment Variables

Create `.env` file on PythonAnywhere:
```
SECRET_KEY=your-secret-key-here
DEBUG=False
PRODUCTION=True
ALLOWED_HOSTS=yourusername.pythonanywhere.com,localhost,127.0.0.1
DATABASE_URL=mysql://username:password@host/database
```

## Monitoring and Maintenance

### Log Files
- Django logs: `/home/yourusername/logs/`
- Error logs: PythonAnywhere error log tab
- Access logs: PythonAnywhere access log tab

### Regular Tasks
- [ ] Database backups
- [ ] Static file updates
- [ ] Dependency updates
- [ ] Security patches

## Troubleshooting

### Common Issues
1. **Static files not loading**: Check STATIC_ROOT and run collectstatic
2. **Database connection errors**: Verify database credentials
3. **CORS errors**: Update CORS_ALLOWED_ORIGINS
4. **Import errors**: Check Python path in WSGI file

### Debug Commands
```bash
# Check Django configuration
python manage.py check --settings=familyfarms_api.production_settings

# Test database connection
python manage.py dbshell --settings=familyfarms_api.production_settings

# View migrations status
python manage.py showmigrations --settings=familyfarms_api.production_settings
```

## Post-Deployment

### 1. Update Flutter App
- Change API base URL to PythonAnywhere domain
- Test all functionality
- Deploy to app stores or web hosting

### 2. DNS Configuration (if using custom domain)
- Point domain to PythonAnywhere
- Update ALLOWED_HOSTS
- Configure SSL certificate

### 3. Monitoring Setup
- Set up error monitoring
- Configure backup schedules
- Monitor performance metrics
