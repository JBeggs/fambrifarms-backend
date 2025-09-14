# Backend Quick Start Guide

Get the Fambri Farms Django backend running in 5 minutes.

## ⚡ 5-Minute Setup

### Step 1: Environment Setup (2 minutes)
```bash
cd backend/
python3.11 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Step 2: Database Setup (2 minutes)
```bash
# Copy environment template
cp production_env_template.txt .env

# Run migrations (all are up-to-date ✅)
python manage.py migrate

# Create superuser
python manage.py createsuperuser
```

### Step 3: Start Server (1 minute)
```bash
python manage.py runserver
# Server runs on http://localhost:8000
```

## 🎯 Verify Installation

### Test API Endpoints
```bash
# Health check
curl http://localhost:8000/api/

# WhatsApp health
curl http://localhost:8000/api/whatsapp/health/

# API documentation
open http://localhost:8000/api/docs/
```

### Check Django Admin
```bash
# Visit admin interface
open http://localhost:8000/admin/

# Login with superuser credentials
# Verify all apps are visible:
# - Accounts, Products, Orders, Inventory
# - Suppliers, Procurement, Production, Invoices, WhatsApp
```

## 🏗️ System Overview

### Django Apps (8 Total)
```
✅ accounts/     - User and customer management
✅ products/     - Product catalog with business settings
✅ orders/       - Order management with Monday/Thursday validation
✅ inventory/    - Stock tracking and finished goods
✅ suppliers/    - Supplier and sales rep management
✅ procurement/  - Purchase orders and production planning
✅ production/   - Production batches and reservations
✅ invoices/     - Invoice generation and credit notes
✅ whatsapp/     - Message processing and classification
```

### Key Features Working
- **WhatsApp Integration** - Message processing from Flutter app
- **Order Validation** - Monday/Thursday order days enforced
- **Inventory Tracking** - Real-time stock levels
- **Procurement System** - Automated purchase order generation
- **Customer Management** - Restaurant customer profiles
- **API Documentation** - Interactive Swagger UI

## 🔄 Integration Points

### Flutter Desktop App Integration
```python
# API endpoints used by Flutter app:
POST /api/whatsapp/receive-messages/    # Receive scraped messages
GET  /api/whatsapp/messages/            # Get processed messages
POST /api/whatsapp/messages/process/    # Create orders from messages
GET  /api/orders/                       # List orders
POST /api/orders/                       # Create orders
GET  /api/products/products/            # Product catalog
GET  /api/accounts/customers/           # Customer list
```

### Database Status
```bash
# All migrations applied ✅
python manage.py showmigrations

# Key tables created:
# - whatsapp_whatsappmessage (message processing)
# - orders_order (order management)
# - products_product (product catalog)
# - inventory_finishedinventory (stock levels)
# - accounts_user (customers and users)
```

## 🚨 Quick Troubleshooting

### Common Issues

**Django not found**
```bash
# Ensure virtual environment is activated
source venv/bin/activate
pip install -r requirements.txt
```

**Database errors**
```bash
# Reset database if needed
rm db.sqlite3
python manage.py migrate
python manage.py createsuperuser
```

**Port already in use**
```bash
# Use different port
python manage.py runserver 8001

# Or kill existing process
lsof -ti:8000 | xargs kill -9
```

**CORS errors from Flutter**
```bash
# Verify CORS settings in settings.py
CORS_ALLOW_ALL_ORIGINS = True  # Development only
```

## 📊 System Health Check

### Verify All Components
```bash
# 1. Django server running
curl http://localhost:8000/api/

# 2. Database accessible
python manage.py shell -c "from django.contrib.auth.models import User; print(f'Users: {User.objects.count()}')"

# 3. WhatsApp app working
curl http://localhost:8000/api/whatsapp/health/

# 4. All migrations applied
python manage.py showmigrations | grep "\[ \]" | wc -l  # Should be 0

# 5. Admin interface accessible
open http://localhost:8000/admin/
```

## 🎯 Next Steps

Once the backend is running:

1. **Test API Integration**: Use the interactive docs at `/api/docs/`
2. **Connect Flutter App**: Ensure Flutter app can reach `localhost:8000`
3. **Load Sample Data**: Create test customers and products via admin
4. **Test WhatsApp Flow**: Process messages through the WhatsApp endpoints
5. **Monitor Logs**: Check console output for any errors

## 📚 Further Reading

- **[System Overview](../architecture/system-overview.md)** - Understand the architecture
- **[API Overview](api-overview.md)** - Learn about the REST API
- **[WhatsApp Integration](../business-logic/whatsapp-integration.md)** - Message processing workflow
- **[Troubleshooting](troubleshooting.md)** - Detailed problem solving

---

**Tip**: Keep the Django development server running while developing. It auto-reloads on code changes and provides detailed error messages in the console.
