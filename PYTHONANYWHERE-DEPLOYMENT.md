# FambriFarms Django Deployment Guide - PythonAnywhere

This guide will walk you through deploying your FambriFarms Django backend to PythonAnywhere hosting.

## 📋 Prerequisites

- PythonAnywhere account (username: FamdriDevOps)
- Django 5.0.9 project ready for deployment
- Repository access to push your code

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
3. Extract to `/home/FamdriDevOps/app/`

### 3. Create Virtual Environment

In the PythonAnywhere Bash Console:

```bash
# Create virtual environment
mkvirtualenv fambrifarms --python=/usr/bin/python3.10

# If command not found, install virtualenvwrapper first:
pip3.10 install --user virtualenvwrapper
echo "source ~/.local/bin/virtualenvwrapper.sh" >> ~/.bashrc
source ~/.bashrc
mkvirtualenv fambrifarms --python=/usr/bin/python3.10

# Activate the environment (should happen automatically)
workon fambrifarms

# Navigate to your app directory
cd ~/app
```

### 4. Install Dependencies

```bash
# Make sure you're in the virtual environment (you should see (fambrifarms) in prompt)
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
   ALLOWED_HOSTS=famdridevops.pythonanywhere.com
   STATIC_ROOT=/home/FamdriDevOps/app/static
   MEDIA_ROOT=/home/FamdriDevOps/app/media
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

# Collect static files
python manage.py collectstatic --noinput

# Load your sample data
python manage.py populate_fambri_content
python manage.py populate_shallome_stock
```

### 7. Configure Web App on PythonAnywhere

1. **Go to Web tab** in PythonAnywhere dashboard
2. **Click "Add a new web app"**
3. **Choose "Manual configuration"**
4. **Select "Python 3.10"**

### 8. Configure Virtual Environment

1. In the **Web tab**, find the **Virtualenv** section
2. Enter: `/home/FamdriDevOps/.virtualenvs/fambrifarms`
3. Click the checkmark to save

### 9. Configure WSGI File

1. **Click the WSGI configuration file link** in the Web tab
2. **Delete all existing content**
3. **Replace with your production WSGI config**:
   ```python
   import os
   import sys

   # Add your project directory to Python's path
   path = '/home/FamdriDevOps/app'
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
   | `/static/` | `/home/FamdriDevOps/app/static/` |
   | `/media/` | `/home/FamdriDevOps/app/media/` |

3. **Click the checkmarks** to save both mappings

### 11. Reload and Test

1. **Click the "Reload" button** in the Web tab
2. **Visit your site**: `https://famdridevops.pythonanywhere.com`
3. **Test API endpoints**:
   - Main API: `https://famdridevops.pythonanywhere.com/api/`
   - Products: `https://famdridevops.pythonanywhere.com/api/products/products/`
   - Admin: `https://famdridevops.pythonanywhere.com/admin/`

## 🔧 Troubleshooting

### Common Issues:

1. **DisallowedHost Error**
   - Check `ALLOWED_HOSTS` in your `.env` file
   - Make sure it includes `famdridevops.pythonanywhere.com`

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
   workon fambrifarms
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
NEXT_PUBLIC_API_URL=https://famdridevops.pythonanywhere.com/api
```

## 📞 Support

- **PythonAnywhere Help**: [help.pythonanywhere.com](https://help.pythonanywhere.com/pages/FollowingTheDjangoTutorial)
- **Django Documentation**: [docs.djangoproject.com](https://docs.djangoproject.com/)

---

**🎉 Your FambriFarms Django backend is now live on PythonAnywhere!**

**Live URLs:**
- **Main Site**: https://famdridevops.pythonanywhere.com
- **API Root**: https://famdridevops.pythonanywhere.com/api/
- **Admin Panel**: https://famdridevops.pythonanywhere.com/admin/
