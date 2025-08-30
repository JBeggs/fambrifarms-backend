# Fambri Farms Backend Development Plan

## 🎯 **Current State: Fresh Start**

**Status**: Backend deployed to PythonAnywhere but logic needs complete rebuild  
**Goal**: Simple WhatsApp-integrated order processing system  
**Timeline**: 4-6 weeks development  

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

### **Core Django Apps Needed**

#### **1. `orders/` - Order Management (Priority 1)**
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

#### **2. `whatsapp/` - WhatsApp Integration (Priority 2)**
```python
class WhatsAppMessage(models.Model):
    message_id = models.CharField(max_length=100, unique=True)
    sender_phone = models.CharField(max_length=20)
    sender_name = models.CharField(max_length=100)
    message_text = models.TextField()
    
    # Processing status
    processed = models.BooleanField(default=False)
    processing_error = models.TextField(blank=True)
    
    # AI parsing results
    parsed_items = models.JSONField(null=True, blank=True)
    parsing_confidence = models.FloatField(default=0.0)
    
    # Links to created order
    order = models.ForeignKey(Order, null=True, on_delete=models.SET_NULL)
    
    created_at = models.DateTimeField(auto_now_add=True)

class SalesRep(models.Model):
    name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=20)
    whatsapp_number = models.CharField(max_length=20)
    is_active = models.BooleanField(default=True)
    
    # Performance tracking
    average_response_time = models.DurationField(null=True)
    total_orders_handled = models.IntegerField(default=0)
```

#### **3. `products/` - Simple Product Catalog (Priority 3)**
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

#### **4. `inventory/` - Basic Stock Tracking (Priority 4)**
```python
class StockLevel(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    current_quantity = models.DecimalField(max_digits=10, decimal_places=2)
    last_updated = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE)

class StockMovement(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    movement_type = models.CharField(max_length=20)  # 'receipt', 'sale', 'adjustment'
    quantity_change = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.TextField()
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
```

---

## 🤖 **AI Message Parsing - Cost Analysis**

### **OpenAI API Costs (Expensive)**
```
GPT-3.5-turbo: $0.0015 per 1K input tokens, $0.002 per 1K output tokens
GPT-4: $0.03 per 1K input tokens, $0.06 per 1K output tokens

Example cost per message:
- Input: ~100 tokens ("1 x onions, 2 x tomatoes please")
- Output: ~200 tokens (JSON response)
- Cost per message: ~$0.0006 (GPT-3.5) or ~$0.015 (GPT-4)
- 100 messages/day = $0.06 - $1.50 per day
```

### **FREE Alternative: Claude/Assistant Integration**
```python
# Development approach using Claude API (you + scripts)
def parse_message_with_claude(message_text):
    """
    Use Claude API during development (free tier)
    Or create manual parsing rules for common patterns
    """
    # Pattern matching for common orders
    patterns = {
        r'(\d+)\s*x?\s*onions?': {'product': 'Red Onions', 'unit': 'kg'},
        r'(\d+)\s*x?\s*tomatoes?': {'product': 'Tomatoes', 'unit': 'kg'},
        r'(\d+)\s*kg\s*(\w+)': {'extract_product': True},
    }
    
    # Manual parsing logic here
    # Much cheaper than OpenAI for simple cases
```

### **Hybrid Approach (Recommended)**
1. **Development**: Use Claude API (free) + manual patterns
2. **Production**: Start with manual parsing, add AI only for complex cases
3. **Cost Control**: Set daily limits, fallback to manual review

---

## 🚀 **Development Phases**

### **Phase 1: Core Order System (Week 1-2)**
```python
# Backend endpoints to build
POST /api/orders/create-from-whatsapp/
GET /api/orders/
GET /api/orders/{id}/
PATCH /api/orders/{id}/status/

# Manager interface endpoints
GET /api/manager/pending-orders/
POST /api/manager/confirm-order/
POST /api/manager/send-po-to-sales-rep/
```

**Deliverables:**
- Order model with proper scheduling validation
- WhatsApp message storage
- Basic order status tracking
- Manager approval workflow

### **Phase 2: Message Processing (Week 3-4)**
```python
# Message parsing endpoints
POST /api/whatsapp/receive-message/
GET /api/whatsapp/unparsed-messages/
POST /api/whatsapp/parse-message/
POST /api/whatsapp/confirm-parsing/

# Sales rep communication
POST /api/sales-rep/send-po/
POST /api/sales-rep/receive-confirmation/
```

**Deliverables:**
- WhatsApp message ingestion
- AI/manual parsing system
- Sales rep PO generation
- Confirmation tracking

### **Phase 3: Stock Management (Week 5-6)**
```python
# Stock endpoints
GET /api/inventory/stock-levels/
POST /api/inventory/receive-stock/
POST /api/inventory/adjust-stock/
GET /api/inventory/movements/
```

**Deliverables:**
- Basic inventory tracking
- Stock receipt workflow
- Movement history
- Low stock alerts

### **Phase 4: Reporting & Polish (Week 7-8)**
```python
# Reporting endpoints
GET /api/reports/daily-summary/
GET /api/reports/order-processing-stats/
GET /api/reports/stock-movements/
GET /api/reports/sales-rep-performance/
```

**Deliverables:**
- Manager dashboard data
- Performance metrics
- Error handling improvements
- System optimization

---

## 📱 **WhatsApp Integration Strategy**

### **Development Approach (No Selenium Initially)**
```python
# Manual WhatsApp integration for development
class WhatsAppHandler:
    def manual_message_entry(self, message_data):
        """Manager manually enters WhatsApp messages during development"""
        pass
    
    def generate_po_message(self, order):
        """Generate formatted PO message for copy/paste to WhatsApp"""
        pass
    
    def manual_confirmation_entry(self, po_id, confirmation_text):
        """Manager enters sales rep confirmations manually"""
        pass
```

### **Production Approach (Later)**
- **Option 1**: WhatsApp Business API (official, costs money)
- **Option 2**: Selenium automation (free, but complex)
- **Option 3**: Manual process with good UX (simple, reliable)

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
