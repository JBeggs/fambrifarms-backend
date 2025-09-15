# Backend System Overview

Comprehensive overview of the Fambri Farms Django backend architecture and components.

## 🎯 System Purpose

The Django backend serves as the central data management and business logic layer for the Fambri Farms order processing system. It handles WhatsApp message processing, order management, inventory tracking, and procurement workflows.

## 🏗️ High-Level Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Flutter App    │───▶│  Django Backend │───▶│  MySQL Database │
│  (Desktop UI)   │    │  (REST API)     │    │  (Data Storage) │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │ Python Scraper  │
                       │ (WhatsApp Data) │
                       └─────────────────┘
```

## 🔧 Core Components

### Django Framework Stack
- **Django 5.0.9** - Main web framework
- **Django REST Framework 3.15.2** - API development
- **Django CORS Headers** - Cross-origin requests
- **SimpleJWT** - JWT authentication
- **drf-spectacular** - API documentation
- **python-decouple** - Environment configuration

### Database Layer
- **Development**: SQLite3 (db.sqlite3)
- **Production**: MySQL (PythonAnywhere)
- **ORM**: Django's built-in ORM with migrations
- **Admin Interface**: Django admin for data management

## 📱 Django Apps Architecture

### 1. **accounts/** - User & Customer Management
**Purpose**: Handle user authentication and customer profiles

**Models**:
- `User` (Custom user model)
- `RestaurantProfile` - Customer restaurant details
- User roles and permissions

**Key Features**:
- JWT authentication
- Customer management for restaurants
- User role-based access control
- Restaurant branch management

**API Endpoints**:
```
GET  /api/auth/customers/           # List customers
POST /api/auth/customers/           # Create customer
GET  /api/auth/customers/{id}/      # Customer details
```

### 2. **products/** - Product Catalog & Business Settings
**Purpose**: Manage product catalog and business configuration

**Models**:
- `Product` - Product catalog with inventory integration
- `Department` - Product categorization
- `BusinessSettings` - System configuration
- `Recipe` - Product recipes and components

**Key Features**:
- Product catalog with common names
- Department-based organization
- Business settings management
- Recipe and component tracking

**API Endpoints**:
```
GET  /api/products/products/        # List products with inventory
POST /api/products/products/        # Create product
GET  /api/products/departments/     # List departments
```

### 3. **orders/** - Order Management System
**Purpose**: Core order processing with business rule validation

**Models**:
- `Order` - Main order entity
- `OrderItem` - Individual order line items
- Order status tracking

**Key Features**:
- **Monday/Thursday validation** - Orders only accepted on specific days
- **Delivery date calculation** - Auto-assign Tue/Wed/Fri delivery
- Order status workflow
- WhatsApp message integration

**Business Rules**:
```python
# Order day validation (CRITICAL)
VALID_ORDER_DAYS = [0, 3]  # Monday=0, Thursday=3
DELIVERY_DAYS = {
    0: [1, 2],  # Monday orders → Tue/Wed delivery
    3: [4]      # Thursday orders → Friday delivery
}
```

**API Endpoints**:
```
GET  /api/orders/                   # List orders
POST /api/orders/                   # Create order
GET  /api/orders/{id}/              # Order details
PATCH /api/orders/{id}/             # Update order
```

### 4. **inventory/** - Stock Management & Intelligent Pricing System ⭐
**Purpose**: Track inventory levels, manage stock movements, and provide AI-powered pricing intelligence

**Core Models**:
- `FinishedInventory` - Finished goods stock levels
- `RawMaterialBatch` - Raw material tracking
- `PriceHistory` - Price validation and history
- `PriceValidationResult` - Automated price checking

**Intelligent Pricing Models**:
- `StockAnalysis` - Monday-Thursday order vs stock analysis
- `StockAnalysisItem` - Individual product analysis with procurement suggestions
- `MarketPrice` - Market pricing data from invoice processing
- `ProcurementRecommendation` - AI-generated procurement suggestions
- `PriceAlert` - Volatility alerts for significant price changes
- `PricingRule` - Customer segment-based pricing strategies
- `CustomerPriceList` - Generated customer pricing from market data
- `CustomerPriceListItem` - Individual product pricing with volatility tracking
- `WeeklyPriceReport` - Comprehensive business intelligence reports

**Key Features**:
- **Stock Analysis Engine** - Analyzes customer orders against available inventory
- **Market Intelligence** - Processes invoice data to track price volatility (handles 275%+ swings)
- **Dynamic Pricing Rules** - Customer segment-based pricing (Premium, Standard, Budget, Wholesale, Retail)
- **Automated Price Lists** - Generated customer pricing from market data
- **Volatility Management** - Real-time price change monitoring and alerts
- **Business Intelligence** - Comprehensive weekly reports and analytics
- **Procurement Intelligence** - Smart supplier recommendations based on market data

**API Endpoints**:
```
# Core Inventory
GET  /api/inventory/finished/                    # List finished inventory
POST /api/inventory/finished/                   # Create inventory record
PATCH /api/inventory/finished/{id}/             # Update stock levels

# Stock Analysis Engine
GET  /api/inventory/stock-analysis/             # List stock analyses
POST /api/inventory/stock-analysis/analyze_current_period/  # Run analysis

# Market Intelligence
GET  /api/inventory/market-prices/              # List market prices
POST /api/inventory/market-prices/bulk_import/  # Import from invoices
GET  /api/inventory/market-prices/price_trends/ # Price trend analysis
GET  /api/inventory/enhanced-market-prices/volatility_dashboard/  # Volatility dashboard

# Procurement Intelligence
GET  /api/inventory/procurement-recommendations/ # List recommendations
POST /api/inventory/procurement-recommendations/generate_from_analysis/  # Generate from analysis

# Dynamic Pricing
GET  /api/inventory/pricing-rules/              # List pricing rules
POST /api/inventory/pricing-rules/              # Create pricing rule
POST /api/inventory/pricing-rules/{id}/test_markup/  # Test markup calculation

# Customer Price Lists
GET  /api/inventory/customer-price-lists/       # List customer price lists
POST /api/inventory/customer-price-lists/generate_from_market_data/  # Generate from market data
POST /api/inventory/customer-price-lists/{id}/activate/  # Activate price list
POST /api/inventory/customer-price-lists/{id}/send_to_customer/  # Send to customer

# Business Intelligence
GET  /api/inventory/weekly-reports/             # List weekly reports
POST /api/inventory/weekly-reports/generate_current_week/  # Generate current week report

# Price Alerts
GET  /api/inventory/price-alerts/               # List price alerts
POST /api/inventory/price-alerts/acknowledge_all/  # Acknowledge all alerts
```

### 5. **suppliers/** - Supplier Management
**Purpose**: Manage suppliers and sales representatives

**Models**:
- `Supplier` - Supplier company details
- `SalesRep` - Sales representative contacts
- `PriceList` - Supplier pricing information

**Key Features**:
- Supplier contact management
- Sales rep assignment and tracking
- Price list management
- Supplier performance tracking

**API Endpoints**:
```
GET  /api/suppliers/suppliers/      # List suppliers
GET  /api/suppliers/sales-reps/     # List sales reps
```

### 6. **procurement/** - Purchase Order System
**Purpose**: Generate and manage purchase orders

**Models**:
- `PurchaseOrder` - Purchase order entity
- `PurchaseOrderItem` - PO line items
- Order-to-PO relationship tracking

**Key Features**:
- Automated PO generation from orders
- Sales rep assignment
- PO status tracking
- Integration with production planning

**API Endpoints**:
```
POST /api/procurement/purchase-orders/create/  # Create PO
GET  /api/procurement/purchase-orders/         # List POs
```

### 7. **production/** - Production Planning
**Purpose**: Manage production batches and reservations

**Models**:
- `ProductionBatch` - Production run tracking
- `ProductionReservation` - Order item reservations
- Production scheduling

**Key Features**:
- Production batch management
- Order item reservation system
- Production scheduling
- Yield tracking and reporting

### 8. **invoices/** - Invoice Management
**Purpose**: Generate invoices and manage billing

**Models**:
- `Invoice` - Invoice generation
- `InvoiceItem` - Invoice line items
- `CreditNote` - Credit note management

**Key Features**:
- Automated invoice generation
- Credit note processing
- Invoice status tracking
- Integration with order fulfillment

### 9. **whatsapp/** - Message Processing ⭐
**Purpose**: Process WhatsApp messages and convert to orders

**Models**:
- `WhatsAppMessage` - Scraped message storage
- Message classification and parsing
- Company extraction and assignment

**Key Features**:
- **Message Classification** - Auto-classify as order/stock/instruction
- **Company Extraction** - Identify customer companies from messages
- **Order Creation** - Convert messages to structured orders
- **Media Support** - Handle images, voice messages, documents
- **Soft Delete** - Mark messages as deleted without removing

**Message Types**:
```python
MESSAGE_TYPES = [
    ('order', 'Customer Order'),
    ('stock', 'Stock Update'),
    ('instruction', 'Instruction/Note'),
    ('demarcation', 'Order Day Demarcation'),
    ('image', 'Image Message'),
    ('voice', 'Voice Message'),
    ('other', 'Other'),
]
```

**API Endpoints**:
```
POST /api/whatsapp/receive-messages/     # Receive scraped messages
GET  /api/whatsapp/messages/             # Get processed messages
POST /api/whatsapp/messages/edit/        # Edit message content
POST /api/whatsapp/messages/process/     # Create orders from messages
GET  /api/whatsapp/companies/            # List extracted companies
```

## 🔄 Data Flow Architecture

### Message Processing Workflow
```
1. Python Scraper → POST /api/whatsapp/receive-messages/
   ├── Store raw WhatsApp messages
   ├── Auto-classify message types
   └── Extract company information

2. Flutter App → GET /api/whatsapp/messages/
   ├── Fetch processed messages
   ├── Display for user editing
   └── Allow message classification changes

3. Flutter App → POST /api/whatsapp/messages/process/
   ├── Convert selected messages to orders
   ├── Validate order day (Monday/Thursday)
   ├── Create order items from message content
   └── Update inventory levels
```

### Order Processing Workflow
```
1. Order Creation
   ├── Validate order day (Monday/Thursday only)
   ├── Calculate delivery date (Tue/Wed/Fri)
   ├── Create order items
   └── Check inventory availability

2. Procurement Generation
   ├── Analyze order requirements
   ├── Generate purchase orders
   ├── Assign to sales reps
   └── Track PO status

3. Production Planning
   ├── Reserve inventory for orders
   ├── Schedule production batches
   ├── Track production progress
   └── Update inventory levels
```

## 🔐 Security & Authentication

### JWT Authentication
```python
# JWT configuration
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
}
```

### CORS Configuration
```python
# Development CORS settings
CORS_ALLOW_ALL_ORIGINS = True  # Development only
CORS_ALLOWED_ORIGINS = [
    "https://fambrifarms.vercel.app",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
```

### Permissions
- **Admin Interface** - Full access to all models
- **API Authentication** - JWT-based API access
- **User Roles** - Role-based access control

## 📊 Database Schema Overview

### Key Relationships
```
User (Customer) ──┐
                  ├── Order ──── OrderItem ──── Product
                  │               │
                  │               └── FinishedInventory
                  │
WhatsAppMessage ──┘

Order ──── PurchaseOrder ──── Supplier
  │              │
  └── Invoice    └── SalesRep

Product ──── Recipe ──── Department
   │
   └── ProductionBatch ──── ProductionReservation
```

### Migration Status ✅
All migrations are up-to-date across all apps:
- **accounts**: 5 migrations applied
- **inventory**: 10 migrations applied (includes intelligent pricing system)
- **orders**: 2 migrations applied
- **whatsapp**: 4 migrations applied
- **All other apps**: Migrations current

**Latest Migrations**:
- `0008_stockanalysis_stockanalysisitem` - Stock Analysis Engine
- `0009_marketprice_pricealert_procurementrecommendation` - Market Intelligence
- `0010_pricingrule_customerpricelist_weeklypricereport_and_more` - Dynamic Pricing System

## 🚀 Performance Characteristics

### API Performance
- **Average Response Time**: <200ms for most endpoints
- **Database Queries**: Optimized with select_related/prefetch_related
- **Pagination**: Implemented for large datasets
- **Caching**: Django's built-in caching for static data

### Scalability Considerations
- **Database**: MySQL production-ready
- **File Storage**: Django's file handling for media
- **API Rate Limiting**: Can be implemented as needed
- **Background Tasks**: Ready for Celery integration

## 🔧 Development Tools

### API Documentation
- **Swagger UI**: Available at `/api/docs/`
- **ReDoc**: Available at `/api/redoc/`
- **OpenAPI Schema**: Available at `/api/schema/`

### Admin Interface
- **Django Admin**: Full CRUD operations at `/admin/`
- **Model Registration**: All models accessible
- **Custom Admin Views**: Enhanced for business workflows

### Development Server
- **Auto-reload**: Automatic restart on code changes
- **Debug Mode**: Detailed error pages and logging
- **SQL Logging**: Database query debugging

## 🎯 System Strengths

### ✅ What's Working Excellently
- **Complete Business Logic** - All 9 Django apps fully functional
- **Intelligent Pricing System** - AI-powered market volatility management and dynamic pricing
- **WhatsApp Integration** - Robust message processing pipeline
- **Order Validation** - Strict Monday/Thursday business rules
- **Market Intelligence** - Real-time price volatility tracking (handles 275%+ swings)
- **Customer Segmentation** - Dynamic pricing for Premium, Standard, Budget, Wholesale, Retail
- **Business Intelligence** - Comprehensive weekly reports and analytics
- **API Design** - RESTful, well-documented endpoints (8 intelligent pricing ViewSets)
- **Database Design** - Normalized schema with proper relationships
- **Admin Interface** - Full data management capabilities with intelligent pricing controls

### 🔧 Areas for Enhancement
- **Background Tasks** - Could benefit from Celery for heavy processing
- **API Rate Limiting** - Not currently implemented
- **Caching Strategy** - Basic caching, could be enhanced
- **Monitoring** - Could add health check endpoints
- **Testing Coverage** - Could expand automated test suite

---

This Django backend represents a mature, production-ready system that successfully handles the complex business requirements of restaurant order processing while maintaining clean architecture and comprehensive functionality.
