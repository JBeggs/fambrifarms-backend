# 💰 Set All Products Price to 100 - Scripts Guide

This folder contains scripts to set all product prices to R100 in the Fambri Farms database.

## 🚀 Quick Start (Recommended)

**Option 1: Use the convenience script**
```bash
cd backend/
python3 set_all_products_100.py
```

**Option 2: Use Django management commands directly**
```bash
cd backend/
python3 manage.py set_all_products_price_100 --backup
```

## 📋 Available Scripts

### 1. `set_all_products_100.py` (Convenience Script)
- **What it does:** Interactive script that sets all product prices to R100
- **Features:** 
  - Auto-detects virtual environment
  - Interactive confirmation
  - Creates backup by default
  - Shows progress

**Usage:**
```bash
python3 set_all_products_100.py
```

### 2. `manage.py set_all_products_price_100` (Django Command)
- **What it does:** Django management command with full control
- **Options:**
  - `--dry-run`: Preview changes without making them
  - `--backup`: Create CSV backup before changes
  - `--price X`: Set custom price (default 100)

**Usage Examples:**
```bash
# Preview what would change (safe)
python3 manage.py set_all_products_price_100 --dry-run

# Set all prices to R100 with backup
python3 manage.py set_all_products_price_100 --backup

# Set all prices to R50 with backup
python3 manage.py set_all_products_price_100 --backup --price 50
```

### 3. `manage.py restore_product_prices_from_backup` (Restore Command)
- **What it does:** Restores prices from a CSV backup file
- **Options:**
  - `--dry-run`: Preview restore without making changes

**Usage:**
```bash
# Restore from backup (replace with actual backup filename)
python3 manage.py restore_product_prices_from_backup backups/product_prices_backup_20231014_143022.csv

# Preview restore
python3 manage.py restore_product_prices_from_backup backups/product_prices_backup_20231014_143022.csv --dry-run
```

## 🔧 What Gets Changed

**The `price` field is set to the specified value (default R100) for:**
- ✅ ALL products in the database
- ✅ All departments (Vegetables, Fruits, etc.)
- ✅ All units (kg, box, punnet, etc.)

## 🛡️ Safety Features

### Backup System
- Creates timestamped CSV backups in `backups/` folder
- Backup includes: product ID, name, department, unit, old price
- Can be used to restore original prices

### Dry Run Mode
- Shows exactly what would change
- No database modifications
- Safe to run anytime

### Transaction Safety
- All changes happen in a single database transaction
- If anything fails, nothing is changed
- Database remains consistent

## 📊 Example Output

```
🎯 Setting all product prices to R100
📁 Working directory: /path/to/backend

Found 3,847 products

📋 Sample of changes:
  • Green Peppers (kg): R12.50 → R100
  • Tomatoes (punnet): R15.00 → R100
  • Potatoes (bag): R25.00 → R100
  ... and 3,844 more products

💾 Backup created at: backups/product_prices_backup_20231014_143022.csv

🎉 Successfully updated 3,847 products!
   • Price set to: R100
   • Backup: backups/product_prices_backup_20231014_143022.csv
```

## 🔄 How to Undo Changes

If you need to restore original prices:

```bash
python3 manage.py restore_product_prices_from_backup backups/product_prices_backup_YYYYMMDD_HHMMSS.csv
```

## ⚠️ Important Notes

1. **Always run with `--backup` first time** to save original prices
2. **Test with `--dry-run`** to see what will change
3. **Make sure Django is working** before running (database connected, migrations applied)
4. **Virtual environment**: Script auto-detects venv, but you can manually activate:
   ```bash
   source venv/bin/activate  # Linux/Mac
   # or
   venv\Scripts\activate     # Windows
   ```

## 🔍 Troubleshooting

**"ModuleNotFoundError: No module named 'django'"**
```bash
# Activate virtual environment first
source venv/bin/activate
# Then run the script
```

**"manage.py not found"**
```bash
# Make sure you're in the backend directory
cd backend/
```

**"No products found"**
- Check database connection
- Verify products exist: `python3 manage.py shell -c "from products.models import Product; print(Product.objects.count())"`

## 📁 File Structure
```
backend/
├── set_all_products_100.py                           # Convenience script
├── products/management/commands/
│   ├── set_all_products_price_100.py                # Main command
│   └── restore_product_prices_from_backup.py        # Restore command
├── backups/                                          # Created automatically
│   └── product_prices_backup_YYYYMMDD_HHMMSS.csv   # Backup files
└── SET_PRODUCTS_PRICE_README.md                     # This file
```

## ✅ Quick Checklist

Before running:
- [ ] Backend Django server is working
- [ ] Database is connected
- [ ] You're in the `backend/` directory
- [ ] You understand this changes ALL products

To run safely:
- [ ] First: `python3 manage.py set_all_products_price_100 --dry-run`
- [ ] Then: `python3 manage.py set_all_products_price_100 --backup`
- [ ] Keep backup file safe for potential restore
