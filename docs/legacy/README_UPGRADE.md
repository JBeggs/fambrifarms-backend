# Fambri Farms System Upgrade - Simplified WhatsApp-First Architecture

## 🎯 **New System Vision**

**From**: Complex multi-supplier B2B system  
**To**: Streamlined single-supplier system with WhatsApp integration and granular stock management

---

## 🏗️ **Simplified Architecture Overview**

### **Core Entities**
1. **Single Supplier** (Pretoria Market) with **2 Sales Reps**
2. **Restaurant Customers** (order via WhatsApp → eventually migrate to app)
3. **Manager** (central control for all stock and order processing)
4. **WhatsApp Groups** (primary communication channel)

### **Key Workflows**

```
Restaurant → WhatsApp Order → Manager Processing → Sales Rep → Market → Stock Receipt → Delivery
     ↓              ↓               ↓              ↓         ↓           ↓            ↓
  Wishlist    AI Processing    Purchase Order   WhatsApp   Weighing   Adjustments  Invoice
```

---

## 🔄 **Major System Changes**

### **1. Supplier Simplification**
- **Before**: Multiple suppliers with complex routing
- **After**: Single supplier (Pretoria Market) with 2 sales reps
- **Implementation**: 
  - Keep supplier model but mark only one as active
  - Add `sales_rep` field to track which rep handles each order
  - Sales reps are contacts, not separate user accounts (for now)

### **2. WhatsApp-First Ordering**
- **Primary Channel**: WhatsApp group for restaurant orders
- **AI Processing**: Backend script parses vague orders ("1 x onions" → specific product)
- **Gradual Migration**: Restaurants eventually move to app interface
- **Fallback**: WhatsApp remains for convenience even after app adoption

### **3. Manager-Controlled Stock Management**
- **Granular Control**: Every stock movement tracked and recorded
- **Weighing Process**: Only manager can receive stock after physical weighing
- **Adjustments**: Manager handles shortages, losses, and corrections
- **Audit Trail**: Complete history of every stock transaction for reporting

### **4. Sales Rep Integration**
- **Current**: WhatsApp communication with 2 sales reps
- **Future**: Sales reps get app access for order management
- **PO Process**: Manager sends purchase orders to sales reps via WhatsApp
- **Confirmation**: Sales reps confirm orders back through WhatsApp

---

## 📱 **WhatsApp Integration Architecture**

### **WhatsApp Automation Script** (`whatsapp_manager.py`)
```python
# Core Functions:
- monitor_restaurant_orders()     # Listen to restaurant WhatsApp group
- parse_order_message()          # AI parsing of vague orders
- send_po_to_sales_rep()         # Send PO to appropriate sales rep
- process_confirmation()         # Handle sales rep confirmations
- update_order_status()          # Sync with Django backend
```

### **Message Processing Pipeline**
1. **Receive**: Restaurant sends "1 x onions, 2 x tomatoes"
2. **Parse**: AI converts to specific products with quantities
3. **Create**: Generate purchase order in system
4. **Route**: Send to appropriate sales rep via WhatsApp
5. **Confirm**: Sales rep confirms availability and pricing
6. **Update**: System reflects confirmed order status

---

## 👥 **User Role Definitions**

### **Manager (Central Control)**
- **Stock Management**: Receive, weigh, adjust all inventory
- **Order Processing**: Convert WhatsApp orders to purchase orders
- **Sales Rep Communication**: Send POs, receive confirmations
- **Reporting**: Access all system data and audit trails
- **Quality Control**: Final approval on all stock movements

### **Restaurant Owners**
- **Current**: Send orders via WhatsApp group
- **Future**: Manage wishlists → convert to orders in app
- **Stock Visibility**: See available stock (our inventory)
- **Order History**: Track their order status and history

### **Sales Reps (External)**
- **Current**: Receive POs via WhatsApp, send confirmations
- **Future**: App access for order management and inventory updates
- **Market Liaison**: Interface between farm and Pretoria Market
- **Pricing**: Provide real-time market pricing

---

## 🗄️ **Enhanced Data Model Changes**

### **New/Modified Models**

#### **SalesRep Model**
```python
class SalesRep(models.Model):
    name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=20)
    whatsapp_number = models.CharField(max_length=20)
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    specialties = models.JSONField(default=list)  # Product categories they handle
```

#### **WhatsAppMessage Model**
```python
class WhatsAppMessage(models.Model):
    message_id = models.CharField(max_length=100, unique=True)
    sender_phone = models.CharField(max_length=20)
    sender_name = models.CharField(max_length=100)
    message_text = models.TextField()
    parsed_order = models.JSONField(null=True, blank=True)
    order = models.ForeignKey(Order, null=True, blank=True, on_delete=models.SET_NULL)
    processed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
```

#### **StockMovement Model (Enhanced)**
```python
class StockMovement(models.Model):
    MOVEMENT_TYPES = [
        ('receipt', 'Stock Receipt'),
        ('adjustment', 'Manager Adjustment'),
        ('loss', 'Stock Loss/Damage'),
        ('sale', 'Sale to Customer'),
        ('transfer', 'Internal Transfer'),
    ]
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    movement_type = models.CharField(max_length=20, choices=MOVEMENT_TYPES)
    quantity_before = models.DecimalField(max_digits=10, decimal_places=2)
    quantity_change = models.DecimalField(max_digits=10, decimal_places=2)
    quantity_after = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Weighing and Quality Control
    weighed_by = models.ForeignKey(User, on_delete=models.CASCADE)
    actual_weight = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    expected_weight = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    quality_notes = models.TextField(blank=True)
    
    # Audit Trail
    reason = models.TextField()
    reference_order = models.ForeignKey(Order, null=True, blank=True, on_delete=models.SET_NULL)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
```

---

## 🎯 **Frontend Priorities**

### **Manager Dashboard (Priority 1)**
- **Stock Overview**: Real-time inventory with alerts
- **Weighing Interface**: Easy stock receipt with weight entry
- **Order Processing**: Convert WhatsApp orders to POs
- **Adjustment Tools**: Quick stock corrections and loss recording
- **Reporting**: Comprehensive audit trails and analytics

### **Restaurant Interface (Priority 2)**
- **Wishlist Management**: Save products for future orders
- **Stock Visibility**: See what's available from farm inventory
- **Order Conversion**: Convert wishlist to actual orders
- **Order History**: Track past orders and deliveries
- **WhatsApp Integration**: Seamless transition from WhatsApp to app

### **Sales Rep Interface (Future)**
- **PO Management**: Receive and confirm purchase orders
- **Inventory Updates**: Report market availability and pricing
- **Communication Hub**: Integrated messaging with manager

---

## 🤖 **WhatsApp Automation Requirements**

### **Technical Stack**
- **Selenium WebDriver**: Automate WhatsApp Web interface
- **OpenAI API**: Parse and interpret vague order messages
- **Django Integration**: Sync with backend database
- **Scheduling**: Monitor messages continuously

### **Core Functions Needed**
1. **Message Monitoring**: Continuously scan restaurant WhatsApp group
2. **Order Parsing**: Convert "1 x onions" to specific product SKUs
3. **PO Generation**: Create purchase orders in Django system
4. **Sales Rep Messaging**: Send POs to appropriate sales rep
5. **Confirmation Processing**: Handle sales rep responses
6. **Status Updates**: Keep Django system in sync

---

## 📊 **Reporting & Analytics**

### **Manager Reports**
- **Daily Stock Movements**: All receipts, adjustments, sales
- **Order Processing**: WhatsApp → PO → Confirmation → Delivery
- **Loss Analysis**: Track and categorize stock losses
- **Sales Rep Performance**: Response times, accuracy, pricing
- **Customer Patterns**: Restaurant ordering behaviors

### **Financial Tracking**
- **Cost Analysis**: Purchase costs vs. sale prices
- **Loss Impact**: Financial impact of stock adjustments
- **Profit Margins**: Per product and per customer analysis
- **Cash Flow**: Outstanding orders and payment tracking

---

## 🚀 **Implementation Phases**

### **Phase 1: WhatsApp Integration (Week 1-2)**
- Set up WhatsApp automation script
- Implement message parsing with AI
- Create basic PO generation from WhatsApp orders
- Test with one sales rep

### **Phase 2: Manager Stock Control (Week 3-4)**
- Enhanced stock movement tracking
- Weighing interface for stock receipt
- Adjustment and loss recording tools
- Basic reporting dashboard

### **Phase 3: Restaurant App Interface (Week 5-6)**
- Wishlist to order conversion
- Stock visibility for restaurants
- Order history and tracking
- Gradual migration from WhatsApp

### **Phase 4: Sales Rep Integration (Week 7-8)**
- Sales rep app interface
- Integrated PO management
- Real-time inventory updates
- Performance analytics

---

## 🎯 **Success Metrics**

### **Operational Efficiency**
- **Order Processing Time**: WhatsApp → Delivery (target: <24 hours)
- **Stock Accuracy**: Inventory variance <5%
- **Loss Reduction**: Track and minimize stock losses
- **Response Time**: Sales rep confirmation <2 hours

### **User Adoption**
- **Restaurant Migration**: % moved from WhatsApp to app
- **Manager Efficiency**: Time spent on stock management
- **Sales Rep Engagement**: Response rates and accuracy
- **System Reliability**: Uptime and error rates

---

## 💡 **Key Design Principles**

1. **WhatsApp First**: System works even if app fails
2. **Manager Control**: Central authority for all stock decisions
3. **Granular Tracking**: Every movement recorded for audit
4. **Gradual Migration**: Smooth transition from WhatsApp to app
5. **Simplicity**: Complex backend, simple user interfaces
6. **Flexibility**: System adapts to changing business needs

---

## 🔮 **Future Enhancements**

### **Advanced AI Features**
- **Predictive Ordering**: Suggest orders based on patterns
- **Quality Prediction**: Forecast stock quality degradation
- **Price Optimization**: Dynamic pricing based on market conditions
- **Customer Insights**: Personalized recommendations

### **Integration Opportunities**
- **Accounting Software**: Automated financial reporting
- **Delivery Tracking**: GPS integration for delivery status
- **Quality Sensors**: IoT devices for storage monitoring
- **Market Data**: Real-time pricing from multiple sources

---

This upgrade transforms Fambri Farms from a complex multi-supplier system into a streamlined, WhatsApp-integrated operation that maintains simplicity while providing powerful management tools. The focus shifts to what matters most: efficient stock management, clear communication, and gradual digital adoption.
