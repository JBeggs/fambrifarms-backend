#!/usr/bin/env python3
"""
Load supplier pricing data from supplier_pricing_data.json into the database
This script ensures we have clean, accurate supplier data for testing
"""

import os
import sys
import django
import json
from decimal import Decimal
from datetime import datetime

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'familyfarms_api.settings')
django.setup()

from suppliers.models import Supplier, SupplierProduct
from products.models import Product
from django.db import transaction

def load_supplier_pricing_data():
    """Load supplier pricing data from JSON file"""
    
    print("🔄 Loading supplier pricing data from supplier_pricing_data.json...")
    
    # Load the JSON data
    json_file = 'data/supplier_pricing_data.json'
    if not os.path.exists(json_file):
        print(f"❌ File not found: {json_file}")
        return False
    
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    suppliers_data = data.get('suppliers', {})
    
    print(f"📊 Found {len(suppliers_data)} suppliers in JSON file")
    
    # Process each supplier
    for supplier_key, supplier_info in suppliers_data.items():
        supplier_name = supplier_info['supplier_name']
        print(f"\n🏭 Processing {supplier_name}...")
        
        # Get or create supplier
        try:
            supplier = Supplier.objects.get(name=supplier_name)
            print(f"   ✅ Found existing supplier: {supplier.name}")
        except Supplier.DoesNotExist:
            print(f"   ❌ Supplier not found in database: {supplier_name}")
            continue
        
        # Process invoices to get product data
        invoices = supplier_info.get('invoices', {})
        products_processed = 0
        products_updated = 0
        
        for invoice_date, invoice_data in invoices.items():
            products = invoice_data.get('products', {})
            
            for product_key, product_data in products.items():
                description = product_data['description']
                price_per_kg = product_data.get('price_per_kg')
                unit_type = product_data.get('unit_type', 'kg')
                
                if not price_per_kg:
                    continue
                
                # Try to find matching SupplierProduct
                try:
                    # Try exact match first
                    supplier_product = SupplierProduct.objects.get(
                        supplier=supplier,
                        supplier_product_name__iexact=description
                    )
                except SupplierProduct.DoesNotExist:
                    # Try partial match
                    try:
                        supplier_product = SupplierProduct.objects.get(
                            supplier=supplier,
                            supplier_product_name__icontains=description.split()[0]
                        )
                    except (SupplierProduct.DoesNotExist, SupplierProduct.MultipleObjectsReturned):
                        # Create new supplier product if it doesn't exist
                        try:
                            # Find matching internal product
                            internal_product = Product.objects.filter(
                                name__icontains=description.split()[0]
                            ).first()
                            
                            if internal_product:
                                supplier_product = SupplierProduct.objects.create(
                                    supplier=supplier,
                                    product=internal_product,
                                    supplier_product_code=product_key.upper(),
                                    supplier_product_name=description,
                                    supplier_category_code='MARKET',
                                    supplier_price=Decimal(str(price_per_kg)),
                                    currency='ZAR',
                                    is_available=True,
                                    quality_rating=Decimal('4.0')
                                )
                                print(f"   ➕ Created: {description} @ R{price_per_kg}/kg")
                                products_processed += 1
                                continue
                        except Exception as e:
                            print(f"   ❌ Error creating {description}: {e}")
                            continue
                        
                        print(f"   ⚠️  Skipped: {description} (no match found)")
                        continue
                
                # Update existing product price
                old_price = float(supplier_product.supplier_price)
                new_price = float(price_per_kg)
                
                if abs(old_price - new_price) > 0.01:  # Only update if significantly different
                    supplier_product.supplier_price = Decimal(str(price_per_kg))
                    supplier_product.save()
                    print(f"   🔄 Updated: {description} R{old_price:.2f} → R{new_price:.2f}/kg")
                    products_updated += 1
                else:
                    print(f"   ✅ Current: {description} @ R{price_per_kg}/kg")
                
                products_processed += 1
        
        print(f"   📊 Processed {products_processed} products, updated {products_updated}")
    
    return True

def validate_loaded_data():
    """Validate that the loaded data is correct"""
    print("\n🔍 Validating loaded supplier data...")
    
    # Key products to check with expected prices from JSON
    key_validations = [
        ('Tshwane Market', 'Potato Mondial', 5.77),
        ('Tshwane Market', 'Cherry Tomatoes', 72.00),
        ('Tshwane Market', 'Ginger', 94.44),
        ('Reese Mushrooms', 'White', 68.00),
        ('Prudence AgriBusiness', 'Rocket', 250.00),
    ]
    
    validation_passed = 0
    
    for supplier_name, product_partial, expected_price in key_validations:
        try:
            supplier = Supplier.objects.get(name=supplier_name)
            product = SupplierProduct.objects.filter(
                supplier=supplier,
                supplier_product_name__icontains=product_partial
            ).first()
            
            if product:
                actual_price = float(product.supplier_price)
                if abs(actual_price - expected_price) < 0.1:
                    print(f"   ✅ {supplier_name} - {product.supplier_product_name}: R{actual_price}/kg ✓")
                    validation_passed += 1
                else:
                    print(f"   ❌ {supplier_name} - {product.supplier_product_name}: R{actual_price}/kg (expected R{expected_price}/kg)")
            else:
                print(f"   ❌ {supplier_name} - {product_partial}: Not found")
        except Supplier.DoesNotExist:
            print(f"   ❌ Supplier not found: {supplier_name}")
    
    print(f"\n📊 Validation: {validation_passed}/{len(key_validations)} key products validated")
    return validation_passed >= len(key_validations) * 0.8  # 80% pass rate

def main():
    """Main function"""
    print("🚀 SUPPLIER PRICING DATA LOADER")
    print("=" * 50)
    
    try:
        # Load the data
        if load_supplier_pricing_data():
            print("\n✅ Supplier pricing data loaded successfully!")
            
            # Validate the data
            if validate_loaded_data():
                print("\n🎉 Data validation PASSED - Ready for testing!")
                return 0
            else:
                print("\n⚠️  Data validation FAILED - Check pricing accuracy")
                return 1
        else:
            print("\n❌ Failed to load supplier pricing data")
            return 1
            
    except Exception as e:
        print(f"\n💥 Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
