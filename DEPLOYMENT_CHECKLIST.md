# 🚀 PythonAnywhere Deployment Checklist

## ✅ **Pre-Deployment (Completed)**

- [x] Environment variables configured in `.env`
- [x] MySQL database credentials set up
- [x] Production settings updated to read from `.env`
- [x] WSGI configuration updated for your paths
- [x] Requirements.txt includes `python-dotenv`
- [x] Static/Media paths configured
- [x] CORS origins configured for Vercel

## 📋 **Deployment Steps**

### 1. Upload Files
- [ ] Upload entire backend folder to `/home/fambridevops/app/`
- [ ] Verify `.env` file is in place at `/home/fambridevops/.env`

### 2. Install Dependencies
```bash
cd /home/fambridevops/app
pip3.10 install --user -r requirements.txt
```
- [ ] All packages installed successfully

### 3. Database Migration
```bash
python3.10 manage.py migrate --settings=familyfarms_api.production_settings
```
- [ ] Migrations completed without errors

### 4. Seed Database
```bash
python3.10 manage.py seed_production_database --settings=familyfarms_api.production_settings
```
- [ ] Database seeded with all data

### 5. Static Files
```bash
python3.10 manage.py collectstatic --noinput --settings=familyfarms_api.production_settings
```
- [ ] Static files collected to `/home/fambridevops/app/static`

### 6. WSGI Configuration
- [ ] Copy WSGI content to `/var/www/fambridevops_pythonanywhere_com_wsgi.py`
- [ ] Reload web app in PythonAnywhere Web tab

### 7. Test Deployment
- [ ] API endpoints respond: `/api/products/`
- [ ] Admin panel accessible: `/admin/`
- [ ] Authentication working: `/api/auth/login/`

## 🔧 **Post-Deployment**

### Update Flutter App
- [x] Updated default API base URL to: `https://fambridevops.pythonanywhere.com/api`
- [x] Created production environment configuration
- [ ] Test Flutter app with production backend
- [ ] Verify all features working

### Flutter Environment Setup
Use production configuration:
```bash
# Copy production environment
cp environment.production .env

# Or run with environment variables
flutter run --dart-define=DJANGO_URL=https://fambridevops.pythonanywhere.com/api
```

### Admin Access
- [ ] Test admin login: `admin@fambrifarms.co.za` / `defaultpassword123`
- [ ] Or create new superuser if needed

## 🎯 **Success Criteria**

- [ ] Backend API responds correctly
- [ ] Database contains all seeded data
- [ ] Flutter app connects successfully
- [ ] All CRUD operations work
- [ ] Authentication flows properly
- [ ] WhatsApp message processing works
- [ ] Procurement system functional

## 📞 **Support**

If any step fails:
1. Check PythonAnywhere error logs
2. Verify file paths and permissions
3. Test individual components
4. Check environment variables

**Ready to deploy!** 🚀
