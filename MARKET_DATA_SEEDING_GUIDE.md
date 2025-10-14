# 🏪 Market Data Seeding Guide

This guide explains how to seed WhatsApp messages and stock updates that correlate with actual market purchases from supplier invoices.

## 📊 Market Invoice Correlation

The seeding commands align with actual Tshwane Market invoices:

### **Sept 30, 2025** - R18,500.00 (1,056.9kg)
- **Stock Report:** Hazvinei's comprehensive 48-item stock update  
- **Restaurant Orders:** Arthur, Die Joint orders
- **Market Activity:** Large procurement day

### **Oct 6-7, 2025** - R16,602.00 (902.7kg)  
- **Oct 6:** Restaurant orders (Casa Bella, Maltos, Valley, Barchef)
- **Oct 7:** Market trip + invoice day
- **Quality Control:** Asparagus maturity discussions

## 🛠️ Available Commands

### 1. `seed_market_messages_sept30`
Seeds WhatsApp messages for Sept 30, 2025

```bash
# Preview what will be seeded
python manage.py seed_market_messages_sept30 --dry-run

# Seed messages for Sept 30
python manage.py seed_market_messages_sept30

# Clear existing messages and reseed
python manage.py seed_market_messages_sept30 --clear
```

**What it seeds:**
- Karl's restaurant orders (Arthur, Die Joint) - classified as **'order'**
- Hazvinei's comprehensive stock report (48 items) - classified as **'stock'** 
- Related order processing messages - classified as **'other'**

**Content Quality:**
- ✅ Timestamps removed from message content
- ✅ Line breaks preserved in stock lists  
- ✅ Proper message type classification
- ✅ Clean formatting without HTML artifacts

### 2. `seed_market_messages_oct6_7`
Seeds WhatsApp messages for Oct 6-7, 2025

```bash
# Preview what will be seeded
python manage.py seed_market_messages_oct6_7 --dry-run

# Seed messages for Oct 6-7
python manage.py seed_market_messages_oct6_7

# Clear existing messages and reseed
python manage.py seed_market_messages_oct6_7 --clear
```

**What it seeds:**
- **Oct 6:** Restaurant orders from Casa Bella, Maltos, Valley, Barchef - classified as **'order'** (12 messages)
- **Oct 7:** Quality control discussions (asparagus maturity) - classified as **'stock'** (2 messages)
- Order coordination messages - classified as **'other'** (27 messages)

**Message Type Breakdown:**
- **order**: 12 messages (restaurant orders with quantities)
- **stock**: 2 messages (quality control, stock discussions)  
- **other**: 27 messages (confirmations, coordination)

### 3. `seed_market_stock_updates`
Creates stock movements based on actual market purchases

```bash
# Preview stock updates
python manage.py seed_market_stock_updates --dry-run

# Create stock updates for both dates
python manage.py seed_market_stock_updates

# Create stock updates for specific date
python manage.py seed_market_stock_updates --date 2025-09-30
python manage.py seed_market_stock_updates --date 2025-10-07
```

**What it creates:**
- Stock movements for all purchased items
- Product records (if they don't exist)
- Proper cost tracking and inventory levels
- Department categorization

## 📋 Message Categories

### Restaurant Orders
- **Casa Bella:** Large vegetable orders (sweet potato, butternut, peppers)
- **Maltos:** Mixed produce (strawberries, herbs, vegetables)  
- **Valley:** Specialty items (onions, lemons, pineapples)
- **Barchef:** Bar supplies (lemons, mint, garnishes)

### Stock Updates
- Hazvinei's comprehensive inventory reports
- Quality control issues (asparagus maturity)
- Harvest planning discussions

### System Messages
- Order confirmations
- Delivery notifications
- Administrative updates

## 🔄 Complete Workflow

To seed all market-related data:

```bash
# 1. Seed Sept 30 messages and stock
python manage.py seed_market_messages_sept30
python manage.py seed_market_stock_updates --date 2025-09-30

# 2. Seed Oct 6-7 messages and stock  
python manage.py seed_market_messages_oct6_7
python manage.py seed_market_stock_updates --date 2025-10-07

# 3. Verify seeded data
python manage.py shell
>>> from whatsapp.models import WhatsAppMessage
>>> WhatsAppMessage.objects.filter(timestamp__date='2025-09-30').count()
>>> WhatsAppMessage.objects.filter(timestamp__date='2025-10-06').count()
```

## 📊 Data Verification

After seeding, verify the data:

### Check Messages
```python
from whatsapp.models import WhatsAppMessage
from datetime import date

# Sept 30 messages
sept30_messages = WhatsAppMessage.objects.filter(timestamp__date=date(2025, 9, 30))
print(f"Sept 30: {sept30_messages.count()} messages")

# Oct 6-7 messages  
oct6_messages = WhatsAppMessage.objects.filter(timestamp__date=date(2025, 10, 6))
oct7_messages = WhatsAppMessage.objects.filter(timestamp__date=date(2025, 10, 7))
print(f"Oct 6: {oct6_messages.count()}, Oct 7: {oct7_messages.count()} messages")
```

### Check Stock Movements
```python
from inventory.models import StockMovement

# Market purchases
market_movements = StockMovement.objects.filter(
    movement_type='purchase',
    reference__contains='Market Purchase'
)
print(f"Market stock movements: {market_movements.count()}")
print(f"Total value: R{sum(m.total_cost for m in market_movements):,.2f}")
```

## 🎯 Use Cases

### Testing Order Processing
- Use seeded messages to test WhatsApp → Order pipeline
- Verify product matching accuracy
- Test customer identification

### Testing Inventory Management  
- Stock levels reflect actual market purchases
- Cost tracking matches supplier invoices
- Department categorization is accurate

### Testing Procurement Planning
- Historical data for buffer calculations
- Seasonal demand patterns
- Supplier cost analysis

## ⚠️ Important Notes

1. **Data Source:** Messages extracted from actual WhatsApp exports  
2. **Invoice Accuracy:** Stock costs match real supplier invoices
3. **Timestamps:** Preserved from original message capture
4. **Safe Operations:** All commands support `--dry-run`
5. **Idempotent:** Commands can be run multiple times safely

## 🔧 Troubleshooting

### Messages Not Appearing
```bash
# Check if messages were created
python manage.py shell -c "from whatsapp.models import WhatsAppMessage; print(WhatsAppMessage.objects.count())"

# Clear and reseed if needed
python manage.py seed_market_messages_sept30 --clear
```

### Stock Movements Issues
```bash
# Check for products with needs_setup flag
python manage.py shell -c "from products.models import Product; print(Product.objects.filter(needs_setup=True).count())"

# Review and fix product categorization manually
```

### Timestamp Parsing Errors
- Check the source JSON files for format consistency
- Commands handle multiple timestamp formats automatically

## 📈 Business Impact

This seeded data enables:
- **Realistic Testing:** Real customer patterns and volumes
- **Cost Analysis:** Actual market prices and margins  
- **Demand Planning:** Historical order patterns
- **Quality Control:** Real operational challenges
- **Performance Benchmarking:** Against real transaction volumes
