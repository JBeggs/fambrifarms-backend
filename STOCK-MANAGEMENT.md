# 📦 Comprehensive Stock Management System

## Overview

The Fambri Farms stock management system has been designed to handle **two distinct supply chain models** that reflect real-world agricultural operations:

1. **Direct Product Suppliers** → Ready-to-sell products → Restaurant orders  
2. **Raw Material Suppliers** → Processing/production → Finished inventory → Restaurant orders

---

## 🔄 Two-Track Supply Chain System

### **Track 1: Direct Product Supply** 
```
Lettuce Supplier → Finished Lettuce Inventory → Restaurant Orders
Herb Supplier → Finished Herbs Inventory → Restaurant Orders
```

### **Track 2: Raw Material Processing**
```
Seeds Supplier → Growing/Processing → Finished Lettuce → Restaurant Orders
Bulk Herbs Supplier → Processing/Packaging → Packaged Herbs → Restaurant Orders
```

---

## 🏗️ System Architecture

### **Core Models Structure**

#### **1. Supplier Classification**
```python
class Supplier:
    supplier_type = [
        'raw_materials',      # Seeds, fertilizers, bulk ingredients
        'finished_products',  # Ready-to-sell lettuce, packaged herbs
        'mixed'              # Suppliers providing both types
    ]
```

#### **2. Dual Product Relationships**
- **SupplierProduct**: Links suppliers to finished products (ready to sell)
- **SupplierRawMaterial**: Links suppliers to raw materials (need processing)

#### **3. Inventory Tracking**
- **RawMaterial**: Base ingredients requiring processing
- **FinishedInventory**: Products ready for restaurant orders
- **StockMovement**: Complete audit trail for all movements

---

## 📋 Key Features

### **🎯 Supplier Management**
- **Flexible Classification**: Suppliers can provide raw materials, finished products, or both
- **Quality Ratings**: Track supplier performance (1-5 stars)
- **Business Terms**: Payment terms, minimum orders, lead times
- **Certifications**: Track quality certifications (Organic, HACCP, etc.)

### **📦 Purchase Orders**
- **Mixed Orders**: Single PO can contain both raw materials and finished products
- **Automated Numbering**: PO-YYYYMM-XXXX format
- **Status Tracking**: Draft → Sent → Confirmed → Received
- **Partial Deliveries**: Track partially received orders

### **🏭 Production Management**
- **Production Recipes**: Define how raw materials convert to finished products
- **Batch Tracking**: Complete traceability from raw materials to final products
- **Yield Calculation**: Track actual vs expected production yields
- **Cost Calculation**: Automatic costing including raw materials, labor, overhead

### **📊 Stock Tracking**
- **Real-time Inventory**: Live stock levels for both raw and finished products
- **Batch Traceability**: Full tracking from supplier delivery to customer sale
- **Expiry Management**: Automated alerts for expiring products
- **FIFO/LIFO Support**: Flexible inventory valuation methods

### **🚨 Alert System**
- **Low Stock Alerts**: Automatic notifications when reorder levels reached
- **Expiry Warnings**: Alerts for products approaching expiration
- **Production Needed**: Notifications when finished stock needs replenishment
- **Quality Issues**: Track and alert on quality concerns

---

## 🔧 Business Logic

### **Stock Deduction Flow**

#### **For Direct Products:**
1. Restaurant places order
2. System checks `FinishedInventory` availability
3. Stock reserved → Order confirmed → Stock sold on delivery

#### **For Processed Products:**
1. Raw materials received → `RawMaterialBatch` created
2. Production scheduled → Raw materials consumed
3. Finished products created → `FinishedInventory` updated
4. Restaurant orders → Finished stock deducted

### **Costing Methods**
- **Direct Products**: Simple purchase cost + markup
- **Processed Products**: Raw material cost + labor + overhead + markup
- **Automatic Updates**: Cost recalculated on each production batch

---

## 📈 Reporting & Analytics

### **Stock Reports**
- Current inventory levels (raw + finished)
- Aging reports (approaching expiry)
- Movement history (all stock transactions)
- Reorder suggestions based on consumption patterns

### **Production Reports**
- Yield analysis (actual vs planned output)
- Cost analysis (breakdown by raw materials, labor, overhead)
- Batch traceability reports
- Production efficiency metrics

### **Supplier Performance**
- Delivery performance (on-time delivery rates)
- Quality ratings and trends
- Price comparison across suppliers
- Seasonal availability tracking

---

## 🎯 Example Use Cases

### **Case 1: Lettuce Farm Operation**
- **Raw Material Suppliers**: Seeds, fertilizer, packaging materials
- **Production Process**: Growing → Harvesting → Washing → Packaging
- **Finished Product**: Packaged lettuce ready for restaurants
- **Quality Control**: Batch tracking from seed lot to final package

### **Case 2: Mixed Herb Operation**  
- **Direct Suppliers**: Pre-grown herbs from partner farms
- **Raw Material Suppliers**: Seeds for own growing operation
- **Dual Inventory**: Both directly purchased and self-grown herbs
- **Flexible Sourcing**: Switch between suppliers based on quality/price/availability

### **Case 3: Value-Added Processing**
- **Raw Materials**: Bulk herbs, oils, seasonings
- **Processing**: Cleaning, mixing, packaging specialty blends
- **Finished Products**: Custom herb mixes for specific restaurants
- **Recipe Management**: Track exact compositions for consistency

---

## 🔒 Quality & Compliance

### **Food Safety Integration**
- **HACCP Support**: Critical control points tracking
- **Batch Recalls**: Quick identification of affected inventory
- **Temperature Monitoring**: Storage condition tracking
- **Supplier Audits**: Quality certification management

### **Traceability**
- **Forward Tracing**: Track where products were sold
- **Backward Tracing**: Identify source of raw materials
- **Cross-Contamination**: Identify potential contamination sources
- **Audit Trail**: Complete history of all stock movements

---

## 🚀 Integration Points

### **With Existing Systems**
- **Orders**: Automatic stock reservation on order confirmation
- **Invoicing**: Cost-based pricing for accurate margins
- **Suppliers**: Enhanced supplier relationship management
- **Products**: Extended product catalog with raw material linkage

### **Future Enhancements**
- **IoT Integration**: Temperature sensors, weight scales
- **Mobile Apps**: Stock checking, receiving, production updates
- **Predictive Analytics**: Demand forecasting, optimal reorder points
- **API Integration**: Connection with supplier systems, accounting software

---

## 📋 Implementation Status

### ✅ **Completed**
- Core model structure for dual supply chains
- Admin interface for all stock management functions
- Basic reporting and alerting system
- Purchase order management
- Production batch tracking

### 🚧 **Next Phase**
- API endpoints for mobile/frontend integration  
- Automated stock alerts via email/SMS
- Advanced reporting dashboard
- Integration with existing order system
- Production scheduling optimization

---

This comprehensive system provides Fambri Farms with the flexibility to handle both direct product purchasing and raw material processing operations, ensuring complete traceability, cost control, and quality management throughout the supply chain.
