# Fambri Farms Backend - Django REST API

A comprehensive Django backend system for WhatsApp order processing, inventory management, and restaurant customer management.

## 📚 Documentation

**Complete documentation is available in the [`docs/`](docs/) folder.**

### Quick Links
- 🚀 **[Quick Start](docs/getting-started/quick-start.md)** - Get running in 5 minutes
- 🏗️ **[System Overview](docs/architecture/system-overview.md)** - Architecture and components
- 📱 **[WhatsApp Integration](docs/business-logic/whatsapp-integration.md)** - Message processing workflow
- 🚨 **[Troubleshooting](docs/getting-started/troubleshooting.md)** - Common issues and solutions

### Documentation Structure
- **[Getting Started](docs/getting-started/)** - Installation, quick start, API overview
- **[Architecture](docs/architecture/)** - System design and Django apps
- **[Business Logic](docs/business-logic/)** - Order processing and WhatsApp integration
- **[Development](docs/development/)** - Development guides and testing
- **[Deployment](docs/deployment/)** - Production deployment instructions

---

## ⚡ Quick Start

### 5-Minute Setup
```bash
# 1. Setup Environment
cd backend/
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Database Setup
cp production_env_template.txt .env
python manage.py migrate
python manage.py createsuperuser

# 3. Start Server
python manage.py runserver
# Visit http://localhost:8000/api/docs/ for API documentation
```

## 🏗️ System Components

### Django Apps (8 Total) ✅
- **accounts/** - User and customer management
- **products/** - Product catalog with business settings  
- **orders/** - Order management with Monday/Thursday validation
- **inventory/** - Stock tracking and finished goods
- **suppliers/** - Supplier and sales rep management
- **procurement/** - Purchase orders and production planning
- **production/** - Production batches and reservations
- **invoices/** - Invoice generation and credit notes
- **whatsapp/** - Message processing and classification

### Key Features
- ✅ **WhatsApp Integration** - Process messages from Flutter desktop app
- ✅ **Order Validation** - Strict Monday/Thursday business rules enforced
- ✅ **Inventory Tracking** - Real-time stock levels and management
- ✅ **Procurement System** - Automated purchase order generation
- ✅ **API Documentation** - Interactive Swagger UI at `/api/docs/`
- ✅ **Admin Interface** - Full Django admin at `/admin/`

## 💻 System Requirements

- **Python**: 3.11+ (3.10 has compatibility issues)
- **Database**: SQLite (dev) / MySQL (production)
- **Dependencies**: Django 5.0.9, DRF 3.15.2, JWT authentication

## 📊 Migration Status

All Django migrations are up-to-date ✅

```bash
# Check migration status
python manage.py showmigrations

# All apps have current migrations:
# accounts: 5 migrations ✅
# inventory: 7 migrations ✅  
# orders: 2 migrations ✅
# whatsapp: 4 migrations ✅
# All other apps: Current ✅
```

## 🔗 Integration Points

### Flutter Desktop App
- **Message Processing**: Receives WhatsApp messages via `/api/whatsapp/receive-messages/`
- **Order Creation**: Converts messages to orders via `/api/whatsapp/messages/process/`
- **Product Catalog**: Accesses products via `/api/products/products/`
- **Customer Management**: Manages customers via `/api/auth/customers/`

### Python WhatsApp Scraper
- **Message Submission**: Sends scraped messages to Django backend
- **Health Checks**: Monitors system status via `/api/whatsapp/health/`

### Production Deployment
- **PythonAnywhere**: Production-ready deployment configuration
- **MySQL Database**: Production database setup
- **Environment Configuration**: Secure settings management

## 📝 Current Status

### What's Working ✅
- Complete Django backend with 8 functional apps
- WhatsApp message processing and order creation
- Order management with Monday/Thursday validation
- Inventory tracking and stock management
- Procurement system with purchase orders
- Interactive API documentation
- Production deployment ready

### System Statistics
- **API Endpoints**: 25+ REST endpoints
- **Database Models**: 40+ models across all apps
- **Migration Status**: All up-to-date
- **Test Coverage**: Core functionality tested
- **Documentation**: Comprehensive guides available

## 🚨 Need Help?

- **Installation Issues**: See [Quick Start Guide](docs/getting-started/quick-start.md)
- **API Questions**: Visit interactive docs at `/api/docs/` when server is running
- **System Details**: Read [System Overview](docs/architecture/system-overview.md)
- **WhatsApp Integration**: Check [WhatsApp Integration Guide](docs/business-logic/whatsapp-integration.md)

---

**For complete documentation, visit the [`docs/`](docs/) folder.**