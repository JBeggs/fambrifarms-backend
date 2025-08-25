# Fambri Farms Backend API

A Django REST API backend for Fambri Farms - a farm-to-restaurant supply chain platform connecting fresh produce suppliers with restaurant customers.

## 🌾 About Fambri Farms

Fambri Farms is a family-owned farm located in Hartbeespoort, South Africa, specializing in growing fresh herbs and vegetables for restaurants. The farm supplies premium produce including:

- Fresh herbs (coriander/cilantro, chives)
- Premium lettuce varieties (Red/Green Batavia, Red/Green Oak, Multi Green, Butter, Green Cos)
- Seasonal vegetables grown with sustainable practices

## 🏗️ System Architecture

This Django backend serves as the API for a comprehensive farm-to-restaurant B2B platform that manages the complete supply chain:

### 🏢 Restaurant Customer Management (`accounts/`)
- Custom user authentication with email-based login
- Restaurant profiles with business details and payment terms
- JWT-based secure authentication
- Multi-role system: restaurants, staff (CEO, Manager, Stocktaker, Production Lead, Sales), admin
- Support for multiple users per restaurant (chef, manager, owner)

### 🥬 Product Catalog & CMS (`products/`)
- Product management with color-coded department categorization
- Per-kilogram pricing model with supplier integration
- Comprehensive CMS: company info, FAQs, testimonials, business hours, team members
- Content management for public-facing pages

### 📋 Advanced Order Management (`orders/`)
- **Scheduled ordering**: Orders only accepted on Mondays and Thursdays
- Enhanced order lifecycle: pending → confirmed → processing → ready → delivered
- **Multi-fulfillment sources**: Supplier procurement + internal production
- Automatic supplier assignment based on cost and availability
- Order item tracking with supplier and pricing details
- Automatic order number generation (FB + date + random digits)

### 🏭 Production Management (`production/`)
- **Production batch tracking**: Complete traceability from raw materials to finished products
- **Production reservations**: Automatic stock reservation for internal fulfillment
- Recipe-based production with yield tracking
- Batch lifecycle management with actual vs planned quantities
- Integration with order fulfillment workflow

### 📦 Comprehensive Inventory System (`inventory/`)
- **Dual supply chain**: Raw materials and finished products
- **Batch tracking**: Complete traceability with expiry management
- **Automated stock movements**: Integration with orders and production
- **Alert system**: Low stock, expiry warnings, production needed alerts
- **Cost tracking**: FIFO/weighted average costing methods
- **Multi-location support**: Raw material and finished inventory separation

### 🛒 Procurement System (`procurement/`)
- **Automated PO generation**: Group order items by supplier
- **Purchase order management**: Draft → Sent → Confirmed → Received workflow
- **Partial receiving**: Support for incomplete deliveries
- **Supplier performance tracking**: Lead times, quality ratings, cost analysis
- **Integration with inventory**: Automatic stock updates on receipt

### 🚚 Advanced Supplier Management (`suppliers/`)
- **Supplier classification**: Raw materials, finished products, or mixed
- **Dual product relationships**: Separate models for raw materials vs finished products
- **Quality management**: Ratings, certifications, business terms
- **Purchase order integration**: Complete PO lifecycle management
- **Performance analytics**: Delivery tracking, cost optimization

### 🧾 Enhanced Invoice System (`invoices/`)
- Automatic invoice generation from completed orders
- South African VAT calculation (15%)
- 30-day payment terms with due date tracking
- Sequential invoice numbering (INV-YYYYMM-XXXX)
- Integration with multi-supplier cost calculations

### ❤️ Wishlist Feature (`wishlist/`)
- Save products for quick future ordering
- Quantity tracking and order notes
- One-click order conversion from wishlist

## ⚙️ Technical Stack

- **Framework**: Django 5.0.9 + Django REST Framework 3.15.2
- **Authentication**: JWT tokens (djangorestframework-simplejwt 5.3.0)
- **Database**: SQLite (development), MySQL (production ready)
- **CORS**: Configured for frontend at localhost:3000 (django-cors-headers 4.4.0)
- **Image Processing**: Pillow 10.4.0 for product images
- **Configuration**: python-decouple 3.8 for environment management
- **Timezone**: Africa/Johannesburg

## 🚀 Getting Started

### Prerequisites
- Python 3.11+
- Virtual environment support

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/JBeggs/fambrifarms-backend.git
   cd fambrifarms-backend
   ```

2. **Create and activate virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run database migrations**
   ```bash
   python manage.py migrate
   ```

5. **Create superuser (optional)**
   ```bash
   python manage.py createsuperuser
   ```

6. **Populate sample content**
   ```bash
   python manage.py populate_fambri_content
   ```

7. **Start development server**
   ```bash
   python manage.py runserver
   ```

The API will be available at `http://127.0.0.1:8000/`

## 📊 Business Rules

### Order Schedule
- **Order Days**: Monday and Thursday only
- **Business Hours**: 
  - Monday-Friday: 7:00 AM - 5:00 PM
  - Saturday: 8:00 AM - 2:00 PM  
  - Sunday: Closed

### Payment Terms
- **Invoice Terms**: Net 30 days
- **VAT Rate**: 15% (South African standard)

### User Types
- **Restaurant**: Customer accounts for placing orders
- **Admin**: Full system access and order management
- **Staff**: Limited administrative access

## 🔗 API Endpoints

### Authentication
- `POST /api/auth/login/` - User login with role-based routing
- `POST /api/auth/register/` - Restaurant registration
- `POST /api/auth/token/refresh/` - Refresh JWT token
- `GET /api/auth/profile/` - Current user profile with roles

### Products & CMS
- `GET /api/products/` - List all active products with filtering
- `GET /api/products/{id}/` - Product details with supplier information
- `GET /api/products/departments/` - Product departments with color coding
- `GET /api/products/company-info/` - Company information for CMS
- `GET /api/products/page-content/{page}/` - Dynamic page content
- `GET /api/products/business-hours/` - Operating hours
- `GET /api/products/team-members/` - Team information
- `GET /api/products/faqs/` - Frequently asked questions
- `GET /api/products/testimonials/` - Customer testimonials

### Orders & Fulfillment
- `GET /api/orders/` - User's orders (or all for admin) with supplier grouping
- `GET /api/orders/{id}/` - Order details with fulfillment sources
- `POST /api/orders/` - Create order from wishlist with auto-supplier assignment
- `PATCH /api/orders/{id}/status/` - Update order status (admin only)

### Procurement System
- `GET /api/procurement/purchase-orders/` - List purchase orders
- `POST /api/procurement/purchase-orders/generate/` - Generate POs from order
- `GET /api/procurement/purchase-orders/{id}/` - PO details
- `PATCH /api/procurement/purchase-orders/{id}/` - Update PO status/notes
- `POST /api/procurement/purchase-orders/{id}/receive/` - Receive PO items

### Production Management
- `GET /api/production/batches/` - Production batch list
- `POST /api/production/batches/` - Create production batch
- `GET /api/production/batches/{id}/` - Batch details with yield tracking
- `PATCH /api/production/batches/{id}/complete/` - Complete production batch
- `GET /api/production/reservations/` - Production reservations for orders
- `POST /api/production/reservations/` - Create production reservation

### Inventory System
- `GET /api/inventory/raw-materials/` - Raw material inventory
- `GET /api/inventory/finished-inventory/` - Finished product inventory
- `GET /api/inventory/stock-movements/` - Stock movement history
- `GET /api/inventory/alerts/` - Active inventory alerts
- `POST /api/inventory/stock-movements/` - Record manual stock adjustment

### Supplier Management
- `GET /api/suppliers/` - List suppliers with classification
- `GET /api/suppliers/{id}/` - Supplier details with performance metrics
- `GET /api/suppliers/supplier-products/` - Supplier product catalog
- `GET /api/suppliers/supplier-raw-materials/` - Supplier raw materials
- `POST /api/suppliers/supplier-products/` - Add supplier product relationship

### Invoices
- `GET /api/invoices/` - User's invoices
- `GET /api/invoices/{id}/` - Invoice details with VAT breakdown
- `POST /api/invoices/generate/` - Generate invoice from completed order

### Wishlist
- `GET /api/wishlist/` - User's wishlist with availability
- `POST /api/wishlist/add/` - Add item to wishlist
- `DELETE /api/wishlist/remove/{id}/` - Remove wishlist item
- `POST /api/wishlist/convert-to-order/` - Convert wishlist to order

## 🚀 Development Status & Next Steps

### ✅ **Production Ready**
- User authentication and role management
- Product catalog with CMS
- Order lifecycle management
- Invoice generation with VAT
- Wishlist functionality
- Database models for inventory, production, procurement

### 🚧 **In Development** 
- Procurement system automation
- Production reservation workflows  
- Advanced role-based permissions
- Audit trail system
- Email notification system

### 📋 **Planned Features**
- Swagger/OpenAPI documentation
- Comprehensive test suite
- Advanced reporting APIs
- Mobile-optimized endpoints
- Real-time inventory updates

**📖 See [DEVELOPMENT-ROADMAP.md](DEVELOPMENT-ROADMAP.md) for detailed implementation plan**

## 🏢 Company Information

- **Location**: BR1601, Hartbeeshoek Road, Broederstroom, 0260, South Africa
- **Phone**: +27 (0)84 504 8586
- **Email**: info@fambrifarms.co.za
- **Region**: Magaliesburg, Hartbeespoort

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

This is a private business application. For questions or issues, contact the development team.
