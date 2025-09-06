# Fambri Farms Backend - Fresh Start Development

## 🎯 **Current Status**

**State**: Backend fully operational with Electron place-order integration  
**Goal**: Complete WhatsApp-to-order processing system with manual selection UI  
**Focus**: Monday/Thursday orders → Tuesday/Wednesday/Friday delivery  
**Integration**: Electron desktop app for manual message selection and order creation  

---

## 🌾 **About Fambri Farms**

Fambri Farms is a family-owned farm in Hartbeespoort, South Africa, supplying fresh produce to restaurants. We're building a simple system to process WhatsApp orders efficiently.

### **Business Model**
- **Customers**: Restaurants order via WhatsApp
- **Processing**: Electron desktop app for manual message selection and order creation
- **Suppliers**: Multiple suppliers with sales rep management
- **Schedule**: Orders Monday/Thursday → Delivery Tuesday/Wednesday/Friday
- **Process**: WhatsApp → Electron App → Manual Selection → Order Creation → Procurement → Delivery

---

## 📅 **Order Schedule (CRITICAL)**

### **Order Days**
- **Monday**: Orders accepted for Tuesday/Wednesday delivery
- **Thursday**: Orders accepted for Friday delivery
- **Other days**: No orders accepted

### **Delivery Days**
- **Tuesday**: Monday orders delivered
- **Wednesday**: Monday orders delivered  
- **Friday**: Thursday orders delivered
- **Other days**: No deliveries

### **Processing Time**
- **Target**: WhatsApp message → PO sent to sales rep <2 hours
- **Maximum**: Order → delivery <72 hours

---

## 🏗️ **System Architecture to Build**

### **Core Components**
```
WhatsApp Messages → Electron App → Manual Selection → Order Creation → Procurement → Delivery
```

### **Django Apps Implemented**
1. **`orders/`** - Core order management with scheduling validation ✅
2. **`products/`** - Product catalog with inventory integration ✅
3. **`inventory/`** - Stock tracking and management ✅
4. **`accounts/`** - User and customer management ✅
5. **`suppliers/`** - Supplier and sales rep management ✅
6. **`procurement/`** - Purchase order and production management ✅
7. **`production/`** - Production planning and tracking ✅
8. **`invoices/`** - Invoice generation and management ✅

### **Electron Integration**
- **place-order/** - Desktop application for manual WhatsApp message selection
- **Real-time WhatsApp reading** - Selenium-based message extraction
- **Manual order creation** - Human-in-the-loop for 100% accuracy
- **Product validation** - Real-time inventory and pricing checks
- **Customer management** - Create and manage restaurant customers

---

## 🚀 **Getting Started**

### **Prerequisites**
- **Python 3.11+** (Python 3.10 has compatibility issues)
- Virtual environment support
- MySQL database (configured for PythonAnywhere)

### **Installation**

1. **Clone the repository**
   ```bash
   git clone https://github.com/JBeggs/fambrifarms-backend.git
   cd fambrifarms-backend
   ```

2. **Create and activate virtual environment**
   ```bash
   python3.11 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   cp production_env_template.txt .env
   # Edit .env with your settings
   ```

5. **Run database migrations**
   ```bash
   python manage.py migrate
   ```

6. **Create superuser**
   ```bash
   python manage.py createsuperuser
   ```

7. **Start development server**
   ```bash
   python manage.py runserver
   ```

---

## 🛠️ **Development Status**

### **✅ Phase 1: Core Order System (COMPLETED)**
- Order model with Monday/Thursday validation ✅
- Delivery date auto-calculation (Tue/Wed/Fri) ✅
- Order status tracking ✅
- Customer management ✅

### **✅ Phase 2: Electron Integration (COMPLETED)**
- Electron desktop application ✅
- Real-time WhatsApp message reading ✅
- Manual message selection interface ✅
- Order creation from selected messages ✅

### **✅ Phase 3: Stock Management (COMPLETED)**
- Inventory tracking with finished goods ✅
- Product catalog integration ✅
- Stock level validation ✅
- Manual stock adjustments ✅

### **✅ Phase 4: Procurement System (COMPLETED)**
- Purchase order generation ✅
- Production order support ✅
- Supplier and sales rep management ✅
- Inventory integration ✅

### **🔄 Phase 5: System Optimization (IN PROGRESS)**
- Performance improvements
- Enhanced error handling
- Comprehensive documentation ✅
- Testing and validation

---

## 🤖 **Message Processing Strategy**

### **Manual Selection Approach (Current)**
1. **Electron Desktop App** - Real-time WhatsApp message display
2. **Manual Selection** - Human selects relevant messages by clicking
3. **Smart Parsing** - Regex-based item extraction from selected messages
4. **100% Accuracy** - Human intelligence eliminates parsing errors

### **Processing Flow**
```
WhatsApp Messages → Electron App Display → Manual Selection → Item Parsing → Order Creation
```

### **Benefits of Manual Approach**
- **Zero parsing errors** - Human verification ensures accuracy
- **No AI costs** - Completely free message processing
- **Flexible handling** - Can process any message format
- **Real-time processing** - Immediate order creation capability

---

## 📊 **API Endpoints Implemented**

### **Order Management** ✅
```
POST /api/orders/orders/                    # Create new order
GET /api/orders/orders/                     # List orders
GET /api/orders/orders/{id}/                # Get order details
PATCH /api/orders/orders/{id}/              # Update order
```

### **Product Management** ✅
```
GET /api/products/products/                 # List products with inventory
POST /api/products/products/                # Create product (with inventory)
PATCH /api/products/products/{id}/          # Update product/add stock
GET /api/products/departments/              # List departments
```

### **Customer Management** ✅
```
GET /api/accounts/customers/                # List customers
POST /api/accounts/customers/               # Create customer
GET /api/accounts/customers/{id}/           # Get customer details
```

### **Procurement Management** ✅
```
POST /api/procurement/purchase-orders/create/  # Create purchase/production order
GET /api/suppliers/suppliers/               # List suppliers
GET /api/suppliers/sales-reps/              # List sales reps
```

### **Inventory Management** ✅
```
GET /api/inventory/finished/                # List finished inventory
POST /api/inventory/finished/               # Create inventory record
PATCH /api/inventory/finished/{id}/         # Update inventory levels
```

### **Electron Integration** ✅
- **Real-time API calls** from Electron app to Django backend
- **Cross-platform compatibility** (Mac development, Windows deployment)
- **Manual message selection** for 100% accuracy
- **Live inventory validation** during order creation

---

## 🗄️ **Database Models to Implement**

### **Order Model**
```python
class Order(models.Model):
    restaurant = models.ForeignKey(User, on_delete=models.CASCADE)
    order_number = models.CharField(max_length=20, unique=True)
    
    # Scheduling (CRITICAL)
    order_date = models.DateField()      # Must be Monday or Thursday
    delivery_date = models.DateField()   # Must be Tue/Wed/Fri
    
    # WhatsApp integration
    whatsapp_message_id = models.CharField(max_length=100, null=True)
    original_message = models.TextField(blank=True)
    
    # Status tracking
    STATUS_CHOICES = [
        ('received', 'Received via WhatsApp'),
        ('parsed', 'AI Parsed'),
        ('confirmed', 'Manager Confirmed'),
        ('po_sent', 'PO Sent to Sales Rep'),
        ('po_confirmed', 'Sales Rep Confirmed'),
        ('delivered', 'Delivered'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
```

### **WhatsApp Message Model**
```python
class WhatsAppMessage(models.Model):
    sender_phone = models.CharField(max_length=20)
    sender_name = models.CharField(max_length=100)
    message_text = models.TextField()
    
    # AI parsing results
    parsed_items = models.JSONField(null=True, blank=True)
    parsing_confidence = models.FloatField(default=0.0)
    
    # Processing status
    processed = models.BooleanField(default=False)
    order = models.ForeignKey(Order, null=True, on_delete=models.SET_NULL)
```

---

## 🎯 **Success Metrics**

### **Business Goals**
- **Schedule Compliance**: 100% orders on correct days only
- **Processing Speed**: WhatsApp → PO sent <2 hours
- **Delivery Time**: Order → delivery <72 hours
- **Manager Efficiency**: <30 minutes/day order processing

### **Technical Goals**
- **Parsing Accuracy**: 90%+ correct product identification
- **System Uptime**: 99%+ availability
- **Cost Control**: Minimal AI costs during development
- **User Experience**: Simple, reliable workflows

---

## 🚀 **Deployment**

### **PythonAnywhere Setup**
- **URL**: https://fambridevops.pythonanywhere.com
- **Database**: MySQL (fambridevops$default)
- **Python**: 3.11 (not 3.10 - compatibility issues)
- **Environment**: Production settings in .env file

### **CORS Configuration**
```env
CORS_ALLOWED_ORIGINS=https://fambrifarms.vercel.app,http://localhost:3000,http://127.0.0.1:3000
```

---

## 📝 **Development Notes**

### **Key Principles**
1. **Simple First**: Build basic functionality before adding complexity
2. **Manager Control**: All AI parsing requires manager confirmation
3. **Schedule Validation**: Enforce Monday/Thursday → Tue/Wed/Fri strictly
4. **Cost Control**: Use free alternatives during development
5. **Backend Logic**: 80% logic in Django, 20% in frontend

### **No Wishlist Complexity**
- Customers place orders directly (no saving for later)
- Simple flow: WhatsApp → Order → Process → Deliver
- Remove all wishlist-related code and concepts

---

## 📞 **Support & Documentation**

### **Backend Documentation**
- **Development Plan**: See `DEVELOPMENT_PLAN.md`
- **Message Processing**: See `AI_PARSING_FREE.md`
- **Deployment**: See `PYTHONANYWHERE-DEPLOYMENT.md`
- **Logic Decisions**: See `LOGIC-DECISIONS.md`

### **Electron App Documentation**
- **User Guide**: See `../place-order/USER_GUIDE.md`
- **Technical Docs**: See `../place-order/TECHNICAL.md`
- **Deployment**: See `../place-order/DEPLOYMENT.md`
- **README**: See `../place-order/README.md`

### **API Documentation**
- **Interactive Docs**: Visit `/api/docs/` when server is running
- **ReDoc Interface**: Visit `/api/redoc/` for alternative documentation
- **OpenAPI Schema**: Available at `/api/schema/`

---

**🎯 Achievement**: Built a complete WhatsApp-to-order processing system with Electron desktop integration, manual message selection for 100% accuracy, comprehensive inventory management, and full procurement workflow. The system maintains the Monday/Thursday → Tuesday/Wednesday/Friday schedule while providing real-time order processing capabilities.**
