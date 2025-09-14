# Fambri Farms Backend - Documentation

Welcome to the comprehensive documentation for the Fambri Farms Django backend system.

## 📚 Documentation Structure

### 🚀 Getting Started
- [Installation Guide](getting-started/installation.md) - Complete setup instructions
- [Quick Start](getting-started/quick-start.md) - Get the backend running in 5 minutes
- [API Overview](getting-started/api-overview.md) - Introduction to the REST API
- [Troubleshooting](getting-started/troubleshooting.md) - Common issues and solutions

### 🏗️ Architecture
- [System Overview](architecture/system-overview.md) - High-level architecture and components
- [Django Apps](architecture/django-apps.md) - Detailed breakdown of each Django app
- [Database Models](architecture/database-models.md) - Model relationships and schema
- [API Design](architecture/api-design.md) - REST API structure and conventions

### 💼 Business Logic
- [Order Processing](business-logic/order-processing.md) - Order workflow and validation
- [WhatsApp Integration](business-logic/whatsapp-integration.md) - Message processing and classification
- [Inventory Management](business-logic/inventory-management.md) - Stock tracking and updates
- [Procurement System](business-logic/procurement-system.md) - Purchase orders and supplier management

### 🔧 Development
- [Development Guide](development/development-guide.md) - Setting up development environment
- [Testing Guide](development/testing.md) - Running tests and test coverage
- [Contributing](development/contributing.md) - How to contribute to the project
- [Code Standards](development/code-standards.md) - Coding conventions and best practices

### 🚀 Deployment
- [Production Deployment](deployment/production-deployment.md) - PythonAnywhere and production setup
- [Environment Configuration](deployment/environment-configuration.md) - Settings and environment variables
- [Database Setup](deployment/database-setup.md) - MySQL configuration and migrations

### 📖 API Reference
- [Authentication](api-reference/authentication.md) - JWT authentication and user management
- [Orders API](api-reference/orders.md) - Order management endpoints
- [Products API](api-reference/products.md) - Product catalog and inventory
- [WhatsApp API](api-reference/whatsapp.md) - Message processing endpoints
- [Customers API](api-reference/customers.md) - Customer management
- [Suppliers API](api-reference/suppliers.md) - Supplier and sales rep management

## 🎯 Quick Navigation

**New to the project?** Start with [Installation Guide](getting-started/installation.md)

**Want to understand the system?** Read [System Overview](architecture/system-overview.md)

**Setting up development?** Check [Development Guide](development/development-guide.md)

**Ready to deploy?** See [Production Deployment](deployment/production-deployment.md)

**Need API details?** Visit [API Overview](getting-started/api-overview.md)

**Having issues?** Check [Troubleshooting](getting-started/troubleshooting.md)

## 🔍 Current System Status

### ✅ What's Working
- **Complete Django Backend** - All 8 apps fully functional
- **WhatsApp Integration** - Message processing and order creation
- **Order Management** - Full order lifecycle with Monday/Thursday validation
- **Inventory System** - Stock tracking and management
- **Procurement** - Purchase orders and supplier management
- **API Documentation** - Interactive Swagger/ReDoc available at `/api/docs/`

### 📊 System Statistics
- **Django Apps**: 8 (accounts, products, orders, inventory, suppliers, procurement, production, invoices, whatsapp)
- **Database Tables**: 40+ models across all apps
- **API Endpoints**: 25+ REST endpoints
- **Migrations**: All up-to-date ✅
- **Dependencies**: Django 5.0.9, DRF 3.15.2, JWT authentication

### 🔄 Integration Points
- **Flutter Desktop App** - Full API integration for order processing
- **WhatsApp Scraper** - Python Flask server integration
- **PythonAnywhere** - Production deployment ready
- **MySQL Database** - Production-ready database setup

## 📞 Support

If you can't find what you're looking for in the documentation:
1. Check the [Troubleshooting Guide](getting-started/troubleshooting.md)
2. Review the interactive API docs at `/api/docs/` when server is running
3. Check Django admin interface for data inspection
4. Review the logs for error messages

## 📝 Documentation Status

- ✅ **System Architecture**: Complete and up-to-date
- ✅ **API Endpoints**: All documented with examples
- ✅ **Installation**: Tested and verified
- ✅ **Business Logic**: Comprehensive workflow documentation
- ✅ **Deployment**: Production-ready guides
- 🔄 **Advanced Features**: Some features still being documented

---

**Last Updated**: December 2024  
**Version**: 1.0.0  
**Django Version**: 5.0.9  
**Python Version**: 3.11+
