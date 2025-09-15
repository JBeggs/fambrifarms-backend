# Fambri Farms Backend Development Plan

## 🎯 **Current State: System Complete**

**Status**: Backend fully operational with Electron integration  
**Goal**: Complete WhatsApp-to-order processing system ✅  
**Timeline**: Development completed - now in optimization phase  
**Integration**: Electron desktop app provides manual message selection for 100% accuracy  

---

## 📅 **Corrected Business Rules**

### **Order Schedule (CRITICAL)**
- **Order Days**: Monday and Thursday ONLY
- **Delivery Days**: Tuesday, Wednesday, and Friday ONLY
- **Processing Time**: Orders placed Monday → delivered Tuesday/Wednesday
- **Processing Time**: Orders placed Thursday → delivered Friday/next week

### **No Wishlist Complexity**
- **Simple Orders**: Customers place orders directly (no wishlist saving)
- **WhatsApp Primary**: Orders come via WhatsApp, eventually migrate to app
- **One-Step Process**: Order → Process → Deliver (no intermediate wishlist)

---

## 🏗️ **Backend Architecture to Build**

### **Core Django Apps Implemented**

#### **✅ 1. `orders/` - Order Management (COMPLETED)**
```python
# Models to implement
class Order(models.Model):
    restaurant = models.ForeignKey(User, on_delete=models.CASCADE)
    order_number = models.CharField(max_length=20, unique=True)
    
    # Order scheduling
    order_date = models.DateField()  # Must be Monday or Thursday
    delivery_date = models.DateField()  # Must be Tue/Wed/Fri
    
    # WhatsApp integration
    whatsapp_message_id = models.CharField(max_length=100, null=True)
    original_message = models.TextField(blank=True)
    parsed_by_ai = models.BooleanField(default=False)
    
    # Status tracking
    STATUS_CHOICES = [
        ('received', 'Received via WhatsApp'),
        ('parsed', 'AI Parsed'),
        ('confirmed', 'Manager Confirmed'),
        ('po_sent', 'PO Sent to Sales Rep'),
        ('po_confirmed', 'Sales Rep Confirmed'),
        ('delivered', 'Delivered to Customer'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    
    created_at = models.DateTimeField(auto_now_add=True)

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=8, decimal_places=2)
    unit = models.CharField(max_length=20)  # kg, bunch, etc.
    
    # AI parsing tracking
    original_text = models.CharField(max_length=200)  # "1 x onions"
    confidence_score = models.FloatField(default=0.0)
    manually_corrected = models.BooleanField(default=False)
```

#### **✅ 2. `suppliers/` - Supplier Management (COMPLETED)**
```python
class Supplier(models.Model):
    name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

class SalesRep(models.Model):
    name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=20)
    whatsapp_number = models.CharField(max_length=20)
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    
    # Performance tracking
    average_response_time = models.DurationField(null=True)
    total_orders_handled = models.IntegerField(default=0)

class SupplierProduct(models.Model):
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE)
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE)
    supplier_price = models.DecimalField(max_digits=10, decimal_places=2)
    is_available = models.BooleanField(default=True)
```

#### **✅ 3. `products/` - Product Catalog (COMPLETED)**
```python
class Product(models.Model):
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=100)  # Vegetables, Herbs, etc.
    unit = models.CharField(max_length=20, default='kg')
    price_per_unit = models.DecimalField(max_digits=10, decimal_places=2)
    
    # AI parsing helpers
    common_names = models.JSONField(default=list)  # ["onions", "red onions", "onion"]
    
    is_active = models.BooleanField(default=True)
```

#### **✅ 4. `inventory/` - Stock Tracking (COMPLETED)**
```python
class FinishedInventory(models.Model):
    product = models.OneToOneField('products.Product', on_delete=models.CASCADE)
    available_quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    reserved_quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    minimum_level = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    reorder_level = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    average_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    last_updated = models.DateTimeField(auto_now=True)

class RawMaterial(models.Model):
    name = models.CharField(max_length=200)
    unit = models.CharField(max_length=20)
    current_stock = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    minimum_level = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    supplier = models.ForeignKey('suppliers.Supplier', on_delete=models.SET_NULL, null=True)
```

#### **✅ 5. `procurement/` - Purchase Order Management (COMPLETED)**
```python
class PurchaseOrder(models.Model):
    po_number = models.CharField(max_length=50, unique=True)
    supplier = models.ForeignKey('suppliers.Supplier', on_delete=models.CASCADE, null=True, blank=True)
    sales_rep = models.ForeignKey('suppliers.SalesRep', on_delete=models.SET_NULL, null=True)
    order = models.ForeignKey('orders.Order', on_delete=models.CASCADE, null=True, blank=True)
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent to Supplier'),
        ('confirmed', 'Confirmed by Supplier'),
        ('received', 'Received'),
        ('cancelled', 'Cancelled'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Production vs Purchase distinction
    is_production = models.BooleanField(default=False)
    priority = models.CharField(max_length=20, default='normal')
    
    created_at = models.DateTimeField(auto_now_add=True)
    expected_delivery = models.DateField(null=True, blank=True)

class PurchaseOrderItem(models.Model):
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
```

#### **✅ 6. `accounts/` - Customer Management (COMPLETED)**
```python
class RestaurantProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    restaurant_name = models.CharField(max_length=200)
    phone_number = models.CharField(max_length=20)
    whatsapp_number = models.CharField(max_length=20, blank=True)
    branch_name = models.CharField(max_length=100, blank=True)
    address = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
```

### **🖥️ Electron Integration (COMPLETED)**

#### **place-order/ Desktop Application**
```javascript
// Key Features Implemented:
- Real-time WhatsApp message reading via Selenium
- Manual message selection interface (click to select)
- Smart item parsing with regex patterns
- Live inventory validation and product creation
- Customer management (create/select customers)
- Order creation with procurement integration
- Cross-platform compatibility (Mac dev → Windows deploy)
```

---

## 🤖 **Message Processing - Manual Selection Approach**

### **Current Implementation: Zero AI Costs**
```
Manual Selection Process:
1. Electron app displays all WhatsApp messages in real-time
2. User clicks to select relevant order messages
3. Smart regex parsing extracts items from selected messages
4. Human verification ensures 100% accuracy
5. Order creation with live inventory validation

Cost: $0 - No AI APIs required
Accuracy: 100% - Human intelligence eliminates parsing errors
```

### **Smart Parsing Without AI**
```javascript
// Regex patterns for common order formats
const ITEM_PATTERNS = [
    /(\d+(?:\.\d+)?)\s*x\s*(.+)/i,           // "2 x onions"
    /(\d+(?:\.\d+)?)\s*kg\s*(.+)/i,          // "5kg tomatoes"  
    /(\d+(?:\.\d+)?)\s*bunch(?:es)?\s*(.+)/i, // "3 bunches lettuce"
    /(\d+(?:\.\d+)?)\s*(.+)/i                 // "10 potatoes"
];

// Product name standardization
const PRODUCT_ALIASES = {
    'onions': 'Red Onions',
    'tomatoes': 'Tomatoes',
    'potatoes': 'Potatoes'
};
```

### **Benefits of Manual Approach**
1. **Zero Costs**: No AI API fees or usage limits
2. **Perfect Accuracy**: Human verification prevents all parsing errors
3. **Flexible Processing**: Can handle any message format or language
4. **Real-time Operation**: Immediate processing without API delays
5. **Full Control**: Complete oversight of order creation process

---

## 🚀 **Development Phases - COMPLETED**

### **✅ Phase 1: Core Order System (COMPLETED)**
```python
# Backend endpoints implemented
POST /api/orders/orders/                    # ✅ Create orders
GET /api/orders/orders/                     # ✅ List orders
GET /api/orders/orders/{id}/                # ✅ Get order details
PATCH /api/orders/orders/{id}/              # ✅ Update orders

# Customer management endpoints
GET /api/accounts/customers/                # ✅ List customers
POST /api/accounts/customers/               # ✅ Create customers
```

**✅ Deliverables Completed:**
- Order model with scheduling validation ✅
- Customer management system ✅
- Order status tracking ✅
- RESTful API endpoints ✅

### **✅ Phase 2: Electron Integration (COMPLETED)**
```javascript
// Electron app features implemented
- Real-time WhatsApp message reading ✅
- Manual message selection interface ✅
- Smart regex-based item parsing ✅
- Live inventory validation ✅
- Customer creation and selection ✅
- Order creation workflow ✅
```

**✅ Deliverables Completed:**
- Electron desktop application ✅
- WhatsApp automation with Selenium ✅
- Manual selection for 100% accuracy ✅
- Cross-platform compatibility ✅

### **✅ Phase 3: Stock Management (COMPLETED)**
```python
# Inventory endpoints implemented
GET /api/products/products/                 # ✅ Products with inventory
POST /api/products/products/                # ✅ Create products + inventory
PATCH /api/products/products/{id}/          # ✅ Update stock levels
GET /api/inventory/finished/                # ✅ Inventory management
```

**✅ Deliverables Completed:**
- Comprehensive inventory tracking ✅
- Product catalog integration ✅
- Stock level validation ✅
- Manual stock adjustments ✅

### **✅ Phase 4: Procurement System (COMPLETED)**
```python
# Procurement endpoints implemented
POST /api/procurement/purchase-orders/create/  # ✅ Create POs/production orders
GET /api/suppliers/suppliers/               # ✅ Supplier management
GET /api/suppliers/sales-reps/              # ✅ Sales rep management
```

**✅ Deliverables Completed:**
- Purchase order generation ✅
- Production order support ✅
- Supplier and sales rep management ✅
- Procurement workflow integration ✅

### **🔄 Phase 5: System Optimization (IN PROGRESS)**
**Current Focus:**
- Performance improvements
- Enhanced error handling
- Comprehensive documentation ✅
- Testing and validation
- Production deployment optimization

---

## 📱 **WhatsApp Integration - Electron Implementation**

### **Current Implementation (Selenium-based)**
```javascript
// Electron app with Selenium WebDriver
class WhatsAppReader {
    async initializeDriver() {
        // Chrome WebDriver with persistent session
        const options = new chrome.Options();
        options.addArguments('--user-data-dir=./whatsapp-session');
        this.driver = new webdriver.Builder()
            .forBrowser('chrome')
            .setChromeOptions(options)
            .build();
    }
    
    async readMessages() {
        // Real-time message extraction from WhatsApp Web
        const messages = await this.driver.findElements(
            By.css('[data-testid="msg-container"]')
        );
        return this.parseMessages(messages);
    }
}
```

### **Production Benefits**
- **Real-time Processing**: Live message reading without manual entry
- **Session Persistence**: Maintains WhatsApp Web login across restarts
- **Cross-platform**: Works on both Mac (development) and Windows (deployment)
- **No API Costs**: Uses WhatsApp Web interface, no Business API required
- **Manual Oversight**: Human selects which messages to process for 100% accuracy

---

## 🎯 **Backend Logic Priority**

### **Business Logic in Django (80%)**
```python
# Order validation
def validate_order_date(order_date):
    """Ensure order is placed on Monday or Thursday"""
    
def calculate_delivery_date(order_date):
    """Auto-assign delivery date based on order date"""
    
def validate_delivery_schedule():
    """Ensure delivery is Tue/Wed/Fri only"""

# Message parsing
def parse_order_message(message_text):
    """Convert "1 x onions" to structured order items"""
    
def suggest_products(text_fragment):
    """AI/pattern matching to suggest products"""
    
def calculate_confidence_score(parsing_result):
    """Rate how confident we are in the parsing"""

# Stock management
def check_stock_availability(order_items):
    """Verify if we have enough stock"""
    
def reserve_stock_for_order(order):
    """Reserve stock when order is confirmed"""
    
def update_stock_levels(movements):
    """Update inventory after receipts/sales"""
```

### **Frontend Logic (20%)**
```typescript
// Simple UI interactions only
interface ManagerDashboard {
  displayOrders(): void;
  confirmParsing(): void;
  sendPOToSalesRep(): void;
}

interface RestaurantPortal {
  browseProducts(): void;
  createOrder(): void;
  trackOrderStatus(): void;
}
```

---

## 📊 **Success Metrics (Corrected)**

### **Order Processing**
- **Schedule Compliance**: 100% orders on Mon/Thu only
- **Delivery Compliance**: 100% deliveries on Tue/Wed/Fri only
- **Processing Speed**: WhatsApp message → PO sent <2 hours
- **Delivery Time**: Order placed → delivered <72 hours max

### **System Efficiency**
- **Parsing Accuracy**: 90%+ correct product identification
- **Manager Workload**: <30 minutes/day for order processing
- **Customer Satisfaction**: Clear delivery expectations
- **Cost Control**: Minimal AI costs during development

---

## 🔧 **Technical Implementation Notes**

### **Django Settings Updates Needed**
```python
# Add to INSTALLED_APPS
INSTALLED_APPS = [
    # ... existing apps
    'orders',
    'whatsapp',
    'inventory',
    # Remove complex apps not needed initially
]

# Business rules validation
ORDER_DAYS = [0, 3]  # Monday=0, Thursday=3
DELIVERY_DAYS = [1, 2, 4]  # Tuesday=1, Wednesday=2, Friday=4
```

### **API Design Principles**
1. **Manager-Centric**: Most endpoints require manager permission
2. **Simple Data**: Avoid complex nested relationships initially
3. **Clear Status**: Every order has clear status progression
4. **Audit Trail**: Log all important actions
5. **Error Handling**: Graceful failures with clear messages

---

This development plan focuses on building a **simple, working system** that handles the core business need: processing WhatsApp orders efficiently with proper scheduling. The backend will handle all business logic, making the frontend simple and reliable.

**Next Step**: Start with Phase 1 - build the core order system with proper Monday/Thursday → Tuesday/Wednesday/Friday scheduling logic.
