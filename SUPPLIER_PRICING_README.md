# 🏭 Supplier Pricing Management Scripts

## 🎯 **What These Scripts Do**

These scripts manage **SUPPLIER PRICES** (what suppliers charge you for products), **NOT** the retail prices you charge customers.

### **Models Updated:**
- ✅ `SupplierProduct.supplier_price` - What Fambri Farms pays suppliers
- ❌ **NOT** `Product.price` - What customers pay Fambri Farms

---

## 🚀 **Quick Usage**

### **Set All Supplier Prices to R100**
```bash
# Interactive script (recommended)
python set_all_supplier_prices_100.py

# Direct command with backup
python manage.py set_all_supplier_prices_100 --backup

# Dry run (preview only)
python manage.py set_all_supplier_prices_100 --dry-run
```

### **Restore from Backup**
```bash
python manage.py restore_supplier_prices_from_backup backups/supplier_prices_backup_20251014_235959.csv

# Dry run restore
python manage.py restore_supplier_prices_from_backup backups/supplier_prices_backup_20251014_235959.csv --dry-run
```

---

## 📋 **Available Commands**

| Command | Purpose | Model Updated |
|---------|---------|---------------|
| `set_all_supplier_prices_100` | Set all supplier prices to R100 | `SupplierProduct.supplier_price` |
| `restore_supplier_prices_from_backup` | Restore from CSV backup | `SupplierProduct.supplier_price` |
| `set_all_products_price_100` | Set all retail prices to R100 | `Product.price` |

---

## 🔍 **What Gets Updated**

**Example of SupplierProduct records updated:**

| Supplier | Product | Old Price | New Price |
|----------|---------|-----------|-----------|
| Tshwane Market | Lemons | R85.50 | R100.00 |
| Reese Mushrooms | Mushrooms | R120.00 | R100.00 |
| Fambri Internal | Potatoes | R70.00 | R100.00 |

---

## 💾 **Backup & Restore**

### **Automatic Backup**
```bash
python manage.py set_all_supplier_prices_100 --backup
# Creates: backups/supplier_prices_backup_YYYYMMDD_HHMMSS.csv
```

### **Manual Restore**
```bash
# List backups
ls -la backups/supplier_prices_backup_*.csv

# Restore specific backup
python manage.py restore_supplier_prices_from_backup backups/supplier_prices_backup_20251014_235959.csv
```

---

## ⚠️ **Important Notes**

1. **Supplier vs Customer Pricing:**
   - **Supplier prices** = What you pay suppliers
   - **Customer prices** = What customers pay you (calculated with markup rules)

2. **Impact on Customer Pricing:**
   - Lower supplier prices = Higher profit margins
   - Customer prices stay the same (determined by markup rules)

3. **Production Safety:**
   - Always use `--backup` on production
   - Test with `--dry-run` first
   - Keep backups for rollback

---

## 🎯 **Use Cases**

- **Standardize supplier costs** for easier profit calculations
- **Simplify procurement** with uniform pricing
- **Test pricing scenarios** with known baseline costs
- **Clean up inconsistent** supplier price data

---

## 🆘 **Troubleshooting**

### **No SupplierProduct records?**
```bash
# Check if any exist
python manage.py shell -c "from suppliers.models import SupplierProduct; print(f'Count: {SupplierProduct.objects.count()}')"

# Create some if needed
python manage.py seed_fambri_pricing  # Creates supplier products
```

### **Command not found?**
```bash
# Make sure you're in backend directory
cd backend/

# Check if command exists
python manage.py help | grep supplier
```
