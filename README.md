# Fambri Farms Backend - Fresh Start Development

## 🎯 **Current Status**

**State**: Backend deployed to PythonAnywhere but needs complete rebuild  
**Goal**: Simple WhatsApp-integrated order processing system  
**Focus**: Monday/Thursday orders → Tuesday/Wednesday/Friday delivery  

---

## 🌾 **About Fambri Farms**

Fambri Farms is a family-owned farm in Hartbeespoort, South Africa, supplying fresh produce to restaurants. We're building a simple system to process WhatsApp orders efficiently.

### **Business Model**
- **Customers**: Restaurants order via WhatsApp
- **Supplier**: Single supplier (Pretoria Market) with 2 sales reps
- **Schedule**: Orders Monday/Thursday → Delivery Tuesday/Wednesday/Friday
- **Process**: WhatsApp → Manager → Sales Rep → Delivery

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
WhatsApp Messages → Manager Review → Order Creation → PO to Sales Rep → Delivery
```

### **Django Apps Needed**
1. **`orders/`** - Core order management with scheduling validation
2. **`whatsapp/`** - Message processing and sales rep communication  
3. **`products/`** - Simple product catalog
4. **`inventory/`** - Basic stock tracking
5. **`accounts/`** - User management (Manager, Restaurants)

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

## 🛠️ **Development Plan**

### **Phase 1: Core Order System (Week 1-2)**
- Order model with Monday/Thursday validation
- Delivery date auto-calculation (Tue/Wed/Fri)
- Basic order status tracking
- Manager approval workflow

### **Phase 2: WhatsApp Integration (Week 3-4)**
- Message parsing (manual patterns + Claude API)
- Manager review interface
- Sales rep PO generation
- Confirmation tracking

### **Phase 3: Stock Management (Week 5-6)**
- Basic inventory tracking
- Stock receipt workflow
- Movement history
- Low stock alerts

### **Phase 4: Reporting (Week 7-8)**
- Manager dashboard
- Order processing metrics
- Performance analytics
- System optimization

---

## 🤖 **AI Message Parsing Strategy**

### **Cost-Effective Approach**
1. **Manual Patterns** (Free) - Handle 80% of common orders
2. **Claude API** (Free tier) - Complex messages during development
3. **Manager Review** - Always confirm AI parsing results
4. **No OpenAI** - Too expensive for development phase

### **Example Parsing**
```
Input: "2 x onions, 5kg tomatoes please"
Output: 
- Red Onions: 5kg (interpreted from "2 x onions")
- Tomatoes: 5kg (exact match)
Confidence: 85%
```

---

## 📊 **API Endpoints to Build**

### **Order Management**
```
POST /api/orders/create-from-whatsapp/
GET /api/orders/
GET /api/orders/{id}/
PATCH /api/orders/{id}/status/
```

### **WhatsApp Processing**
```
POST /api/whatsapp/receive-message/
GET /api/whatsapp/unparsed-messages/
POST /api/whatsapp/parse-message/
POST /api/whatsapp/confirm-parsing/
```

### **Manager Interface**
```
GET /api/manager/pending-orders/
POST /api/manager/confirm-order/
POST /api/manager/send-po-to-sales-rep/
GET /api/manager/dashboard-stats/
```

### **Stock Management**
```
GET /api/inventory/stock-levels/
POST /api/inventory/receive-stock/
POST /api/inventory/adjust-stock/
GET /api/inventory/movements/
```

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

- **Development Plan**: See `DEVELOPMENT_PLAN.md`
- **AI Parsing**: See `AI_PARSING_FREE.md`
- **Deployment**: See `PYTHONANYWHERE-DEPLOYMENT.md`

---

**🎯 Goal**: Build a simple, reliable system that processes WhatsApp orders efficiently while maintaining the Monday/Thursday → Tuesday/Wednesday/Friday schedule. Focus on backend logic, keep frontend simple, and control costs during development.**
