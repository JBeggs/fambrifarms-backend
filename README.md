# Fambri Farms Backend API

A Django REST API backend for Fambri Farms - a farm-to-restaurant supply chain platform connecting fresh produce suppliers with restaurant customers.

## 🌾 About Fambri Farms

Fambri Farms is a family-owned farm located in Hartbeespoort, South Africa, specializing in growing fresh herbs and vegetables for restaurants. The farm supplies premium produce including:

- Fresh herbs (coriander/cilantro, chives)
- Premium lettuce varieties (Red/Green Batavia, Red/Green Oak, Multi Green, Butter, Green Cos)
- Seasonal vegetables grown with sustainable practices

## 🏗️ System Architecture

This Django backend serves as the API for a B2B platform that manages:

### 🏢 Restaurant Customer Management (`accounts/`)
- Custom user authentication with email-based login
- Restaurant profiles with business details and payment terms
- JWT-based secure authentication
- User types: restaurants (customers), admin, staff

### 🥬 Product Catalog (`products/`)
- Product management with department categorization
- Color-coded product departments
- Per-kilogram pricing model
- Comprehensive CMS for content management (company info, FAQs, testimonials)

### 📋 Order Management (`orders/`)
- **Scheduled ordering**: Orders only accepted on Tuesdays and Fridays
- Order lifecycle: pending → confirmed → processing → ready → delivered
- Automatic order number generation (FB + date + random digits)

### 🧾 Invoice System (`invoices/`)
- Automatic invoice generation from completed orders
- South African VAT calculation (15%)
- 30-day payment terms
- Sequential invoice numbering (INV-YYYYMM-XXXX)

### ❤️ Wishlist Feature (`wishlist/`)
- Save products for quick future ordering
- Quantity tracking and order notes

### 🚚 Supplier Management (`suppliers/`)
- Basic supplier information and contact details
- Supplier-specific product pricing
- Limited stock quantity tracking (manual updates only)

## ⚙️ Technical Stack

- **Framework**: Django 4.2.7 + Django REST Framework 3.14.0
- **Authentication**: JWT tokens (djangorestframework-simplejwt)
- **Database**: SQLite (development)
- **CORS**: Configured for frontend at localhost:3000
- **Timezone**: Africa/Johannesburg

## 🚀 Getting Started

### Prerequisites
- Python 3.11+
- Virtual environment support

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/JBeggs/famdrifarms-backend.git
   cd famdrifarms-backend
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
- **Order Days**: Tuesday and Friday only
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
- `POST /api/auth/login/` - User login
- `POST /api/auth/register/` - Restaurant registration
- `POST /api/auth/token/refresh/` - Refresh JWT token

### Products
- `GET /api/products/` - List all active products
- `GET /api/products/{id}/` - Product details
- `GET /api/products/departments/` - Product departments

### Orders
- `GET /api/orders/` - User's orders (or all for admin)
- `GET /api/orders/{id}/` - Order details
- `PATCH /api/orders/{id}/status/` - Update order status (admin only)

### Wishlist
- `GET /api/wishlist/` - User's wishlist
- `POST /api/wishlist/add/` - Add item to wishlist
- `DELETE /api/wishlist/remove/{id}/` - Remove wishlist item

## 🏢 Company Information

- **Location**: BR1601, Hartbeeshoek Road, Broederstroom, 0260, South Africa
- **Phone**: +27 (0)84 504 8586
- **Email**: info@fambrifarms.co.za
- **Region**: Magaliesburg, Hartbeespoort

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

This is a private business application. For questions or issues, contact the development team.
