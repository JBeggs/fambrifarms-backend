# FambriFarms Django Deployment Guide - PythonAnywhere

This guide will walk you through deploying your FambriFarms Django backend to PythonAnywhere hosting.

## 📋 Prerequisites

- PythonAnywhere account (username: FambriDevOps)
- Django 5.0.9 project ready for deployment
- Repository access to push your code
- **Python 3.11** (3.10 has compatibility issues)

## 🚀 Step-by-Step Deployment

### 1. Prepare Your Local Project

Your project is already configured with:
- ✅ Django 5.0.9
- ✅ Production-ready settings
- ✅ Static/Media file configuration
- ✅ WSGI configuration for PythonAnywhere

### 2. Upload Your Project to PythonAnywhere

#### Option A: Using Git (Recommended)

1. **Open a Bash Console** on PythonAnywhere
2. **Clone your repository**:
   ```bash
   cd ~
   git clone https://github.com/JBeggs/fambrifarms-backend.git app
   cd app
   ```

#### Option B: Using File Upload

1. Zip your entire `backend/` folder (excluding `venv/`)
2. Upload via PythonAnywhere Files tab
3. Extract to `/home/FambriDevOps/app/`

### 3. Create Virtual Environment

In the PythonAnywhere Bash Console:

```bash
# Navigate to your app directory
cd ~/app

# Create virtual environment using Python 3.11
python3.11 -m venv venv

# Activate the virtual environment
source venv/bin/activate

# Verify Python version (should show 3.11.x)
python --version
```

### 4. Install Dependencies

```bash
# Make sure you're in the virtual environment (you should see (venv) in prompt)
pip install -r requirements.txt
```

### 5. Configure Environment Variables

1. **Create `.env` file**:
   ```bash
   cd ~/app
   cp production_env_template.txt .env
   nano .env
   ```

2. **Update the `.env` file** with your production settings:
   ```env
   SECRET_KEY=your-super-secret-production-key-here
   DEBUG=False
   PRODUCTION=True
   ALLOWED_HOSTS=fambridevops.pythonanywhere.com
   
   # MySQL Database Configuration
   DB_ENGINE=mysql
   DB_NAME=fambridevops$default
   DB_USER=fambridevops
   DB_PASSWORD=your-mysql-password-here
   DB_HOST=fambridevops.mysql.pythonanywhere-services.com
   DB_PORT=3306
   
   STATIC_ROOT=/home/FambriDevOps/app/static
   MEDIA_ROOT=/home/FambriDevOps/app/media
   
   # CORS/CSRF Configuration
   CORS_ALLOWED_ORIGINS=https://fambrifarms.vercel.app,http://localhost:3000,http://127.0.0.1:3000
   CSRF_TRUSTED_ORIGINS=https://fambrifarms.vercel.app,https://fambridevops.pythonanywhere.com,http://localhost:3000,http://127.0.0.1:3000
   ```

   **⚠️ Important**: Generate a new SECRET_KEY for production using:
   ```bash
   python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
   ```

### 6. Database Setup

```bash
# Run migrations
python manage.py migrate

# Create superuser for admin access
python manage.py createsuperuser

# Create static directory first (if collectstatic fails)
mkdir -p /home/fambridevops/app/static
mkdir -p /home/fambridevops/app/media

# Collect static files
python manage.py collectstatic --noinput

# Load your sample data (if these commands exist)
python manage.py setup_test_data
```

### 7. Configure Web App on PythonAnywhere

1. **Go to Web tab** in PythonAnywhere dashboard
2. **Click "Add a new web app"**
3. **Choose "Manual configuration"**
4. **Select "Python 3.11"**

### 8. Configure Virtual Environment

1. In the **Web tab**, find the **Virtualenv** section
2. Enter: `/home/FambriDevOps/app/venv`
3. Click the checkmark to save

### 9. Configure WSGI File

1. **Click the WSGI configuration file link** in the Web tab
2. **Delete all existing content**
3. **Replace with your production WSGI config**:
   ```python
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
   from django.contrib.staticfiles.handlers import StaticFilesHandler

   # Create the WSGI application
   django_application = get_wsgi_application()
   application = StaticFilesHandler(django_application)
   ```
4. **Save the file**

### 10. Configure Static and Media Files

1. **In the Web tab**, scroll to **Static files** section
2. **Add the following mappings**:

   | URL | Directory |
   |-----|-----------|
   | `/static/` | `/home/fambridevops/app/static/` |
   | `/media/` | `/home/fambridevops/app/media/` |

3. **Click the checkmarks** to save both mappings

### 11. Reload and Test

1. **Click the "Reload" button** in the Web tab
2. **Visit your site**: `https://fambridevops.pythonanywhere.com`
3. **Test API endpoints**:
   - Main API: `https://fambridevops.pythonanywhere.com/api/`
   - Products: `https://fambridevops.pythonanywhere.com/api/products/products/`
   - Admin: `https://fambridevops.pythonanywhere.com/admin/`

## 🔧 Troubleshooting

### Common Issues:

1. **DisallowedHost Error**
   - Check `ALLOWED_HOSTS` in your `.env` file
   - Make sure it includes `fambridevops.pythonanywhere.com`

2. **Static Files Not Loading**
   - Ensure static file mappings are correct in Web tab
   - Run `python manage.py collectstatic` again

3. **Database Errors**
   - Check database file permissions
   - Make sure migrations are applied

4. **Import Errors**
   - Verify virtual environment is activated
   - Check all dependencies are installed

### Viewing Logs:

- **Error Log**: Available in Web tab → Logs section
- **Server Log**: Available in Web tab → Logs section

## 📝 Post-Deployment Tasks

1. **Test all API endpoints**
2. **Verify inventory data is accessible**
3. **Test authentication functionality**  
4. **Configure CORS for frontend integration**
5. **Set up automated backups**
6. **Configure custom domain** (if needed)

## 🔄 Updates and Maintenance

When you make changes to your code:

1. **Update code on server**:
   ```bash
   cd ~/app
   git pull origin main  # if using git
   ```

2. **Install any new requirements**:
   ```bash
   cd ~/app
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Apply migrations** (if any):
   ```bash
   python manage.py migrate
   ```

4. **Collect static files** (if changed):
   ```bash
   python manage.py collectstatic --noinput
   ```

5. **Reload your web app** via Web tab

## 🌐 Frontend Integration

Update your Next.js frontend to point to:
```env
NEXT_PUBLIC_API_URL=https://fambridevops.pythonanywhere.com/api
```

## 🔧 Troubleshooting

### collectstatic Error (Permission/Path Issues)

If you get an error like:
```
os.makedirs(directory, exist_ok=True)
File "<frozen os>", line 225, in makedirs
```

**Solution:**
```bash
# 1. Create directories manually with correct permissions
mkdir -p /home/fambridevops/app/static
mkdir -p /home/fambridevops/app/media

# 2. Set proper permissions
chmod 755 /home/fambridevops/app/static
chmod 755 /home/fambridevops/app/media

# 3. Try collectstatic again
python manage.py collectstatic --noinput --clear
```

### Static Files Not Loading

1. **Check Web tab Static files mappings**:
   - `/static/` → `/home/fambridevops/app/static/`
   - `/media/` → `/home/fambridevops/app/media/`

2. **Verify .env file has correct paths**:
   ```
   STATIC_ROOT=/home/fambridevops/app/static
   MEDIA_ROOT=/home/fambridevops/app/media
   ```

3. **Reload your web app** after making changes

### Database Connection Issues

1. **Check MySQL credentials** in .env file
2. **Test connection** in console:
   ```bash
   python manage.py dbshell
   ```

## 📞 Support

- **PythonAnywhere Help**: [help.pythonanywhere.com](https://help.pythonanywhere.com/pages/FollowingTheDjangoTutorial)
- **Django Documentation**: [docs.djangoproject.com](https://docs.djangoproject.com/)

---

**🎉 Your FambriFarms Django backend is now live on PythonAnywhere!**

**Live URLs:**
- **Main Site**: https://fambridevops.pythonanywhere.com
- **API Root**: https://fambridevops.pythonanywhere.com/api/
- **Admin Panel**: https://fambridevops.pythonanywhere.com/admin/
