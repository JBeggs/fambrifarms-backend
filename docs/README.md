# Fambri Farms Backend - Documentation

Welcome to the comprehensive documentation for the Fambri Farms Django backend system with AI-powered intelligent pricing.

## 📚 Documentation Structure

### 🚀 Getting Started
- **[Quick Start](getting-started/quick-start.md)** - Get the backend running in 5 minutes

### 🏗️ Architecture  
- **[System Overview](architecture/system-overview.md)** - Complete system architecture and Django apps
- **[Logic Decisions](architecture/logic-decisions.md)** - Backend vs frontend architectural decisions

### 💼 Business Logic
- **[WhatsApp Integration](business-logic/whatsapp-integration.md)** - Message processing workflow and business rules
- **[Intelligent Pricing System](business-logic/intelligent-pricing-system.md)** - AI-powered market volatility management and dynamic pricing
- **[WhatsApp Automation](business-logic/whatsapp-automation.md)** - Electron desktop implementation details
- **[Inventory Receiving Workflow](business-logic/inventory-receiving-workflow.md)** - Comprehensive inventory management workflow
- **[Pretoria Market Invoice Analysis](business-logic/pretoria-market-invoice-analysis.md)** - Market data processing structure

### 🛠️ Development
- **[Completed Intelligent Pricing Plan](development/completed-intelligent-pricing-plan.md)** - Historical development plan (completed)
- **[Legacy AI Parsing Approach](development/legacy-ai-parsing-approach.md)** - Previous AI-based approach
- **[Legacy Development Plan](development/legacy-development-plan.md)** - Previous development roadmap
- **[Legacy System Upgrade](development/legacy-system-upgrade.md)** - System evolution documentation

### 🚀 Deployment
- **[PythonAnywhere Deployment](deployment/pythonanywhere-deployment.md)** - Production deployment guide

## 🎯 Quick Navigation

**New to the project?** Start with [Quick Start](getting-started/quick-start.md)

**Want to understand the system?** Read [System Overview](architecture/system-overview.md)

**Interested in intelligent pricing?** Check [Intelligent Pricing System](business-logic/intelligent-pricing-system.md)

**Ready to deploy?** See [PythonAnywhere Deployment](deployment/pythonanywhere-deployment.md)

**Need API details?** Visit the interactive docs at `/api/docs/` when server is running

## 🔍 Current System Status

### ✅ What's Working Excellently
- **Complete Django Backend** - All 8 apps fully functional
- **Intelligent Pricing System** - AI-powered market volatility management and dynamic pricing
- **WhatsApp Integration** - Robust message processing pipeline
- **Order Management** - Full order lifecycle with Monday/Thursday validation
- **Market Intelligence** - Real-time price volatility tracking (handles 275%+ swings)
- **Customer Segmentation** - Dynamic pricing for Premium, Standard, Budget, Wholesale, Retail segments
- **Stock Analysis Engine** - Automated order vs inventory analysis with procurement suggestions
- **Business Intelligence** - Comprehensive weekly reports and analytics
- **API Documentation** - Interactive Swagger/ReDoc available at `/api/docs/`

### 📊 System Statistics
- **Django Apps**: 9 (accounts, products, orders, inventory, suppliers, procurement, production, invoices, whatsapp)
- **Database Tables**: 64 models across all apps (including intelligent pricing models)
- **API Endpoints**: 19 active ViewSets (8 for intelligent pricing) + additional endpoints
- **Migrations**: All up-to-date ✅ (includes 3 intelligent pricing migrations)
- **Dependencies**: Django 5.0.9, DRF 3.15.2, JWT authentication

### 🧠 Intelligent Pricing Capabilities
- **Market Volatility Management**: Handles extreme price swings (tested up to 275%)
- **Customer Segmentation**: 5 distinct pricing strategies
- **Automated Processing**: End-to-end automation from market data to customer pricing
- **Real-time Analysis**: Live price volatility monitoring
- **Business Intelligence**: Data-driven insights for strategic decisions

### 🔄 Integration Points
- **Flutter Desktop App** - Full API integration with intelligent pricing dashboard
- **WhatsApp Scraper** - Python Flask server integration
- **PythonAnywhere** - Production deployment ready
- **MySQL Database** - Production-ready database setup
- **Market Data Processing** - Invoice image analysis and price extraction

## 📞 Support

If you can't find what you're looking for in the documentation:
1. Check the interactive API docs at `/api/docs/` when server is running
2. Review Django admin interface for data inspection at `/admin/`
3. Check the logs for error messages
4. Review the [System Overview](architecture/system-overview.md) for architecture details

## 📝 Documentation Status

- ✅ **System Architecture**: Complete and up-to-date with intelligent pricing
- ✅ **Intelligent Pricing System**: Comprehensive documentation of all 3 phases
- ✅ **API Endpoints**: All documented with examples (19 active ViewSets + additional endpoints)
- ✅ **Installation**: Tested and verified
- ✅ **Business Logic**: Comprehensive workflow documentation
- ✅ **Deployment**: Production-ready guides
- ✅ **Market Intelligence**: Complete volatility management documentation

---

**Last Updated**: December 2024  
**Version**: 2.0.0 (with Intelligent Pricing System)  
**Django Version**: 5.0.9  
**Python Version**: 3.11+  
**Key Features**: AI-powered pricing, market volatility management, customer segmentation