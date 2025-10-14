#!/usr/bin/env python3
"""
Debug script to check Lemons pricing issue
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'familyfarms_api.settings')
django.setup()

from products.models import Product
from suppliers.models import SupplierProduct
from orders.models import OrderItem
from decimal import Decimal

def debug_lemons():
    print("🔍 DEBUGGING LEMONS PRICING ISSUE")
    print("=" * 50)
    
    # 1. Find all Lemons products
    lemon_products = Product.objects.filter(name__icontains='lemon').order_by('name')
    print(f"\n1️⃣ FOUND {lemon_products.count()} LEMON PRODUCTS:")
    
    for product in lemon_products:
        print(f"   ID: {product.id} | Name: '{product.name}' | Price: R{product.price} | Active: {getattr(product, 'is_active', True)}")
    
    # 2. Check recent orders using Lemons
    print(f"\n2️⃣ RECENT ORDERS WITH LEMONS:")
    recent_lemon_orders = OrderItem.objects.filter(
        product__name__icontains='lemon'
    ).select_related('product', 'order').order_by('-order__created_at')[:5]
    
    for item in recent_lemon_orders:
        print(f"   Order: {item.order.order_number} | Product: {item.product.name} (ID: {item.product.id}) | Item Price: R{item.price} | Product Price: R{item.product.price}")
    
    # 3. Check supplier products for Lemons
    print(f"\n3️⃣ SUPPLIER PRODUCTS FOR LEMONS:")
    lemons_exact = Product.objects.filter(name='Lemons').first()
    if lemons_exact:
        supplier_products = SupplierProduct.objects.filter(product=lemons_exact)
        for sp in supplier_products:
            print(f"   Supplier: {sp.supplier.name} | Price: R{sp.supplier_price} | Updated: {getattr(sp, 'updated_at', 'N/A')}")
    
    # 4. Manual update test
    print(f"\n4️⃣ MANUAL UPDATE TEST:")
    lemons_product = Product.objects.filter(name='Lemons').first()
    if lemons_product:
        old_price = lemons_product.price
        print(f"   Current Lemons price: R{old_price}")
        
        # Try manual update
        try:
            lemons_product.price = Decimal('100.00')
            lemons_product.save()
            lemons_product.refresh_from_db()
            new_price = lemons_product.price
            print(f"   After manual update: R{new_price}")
            
            if new_price != Decimal('100.00'):
                print(f"   ❌ MANUAL UPDATE FAILED! Price didn't stick!")
            else:
                print(f"   ✅ Manual update worked")
                
        except Exception as e:
            print(f"   ❌ Manual update error: {e}")
    
    # 5. Check for database triggers or signals
    print(f"\n5️⃣ CHECKING FOR ISSUES:")
    print(f"   - Database: {os.environ.get('DATABASE_URL', 'SQLite')}")
    print(f"   - Settings: {os.environ.get('DJANGO_SETTINGS_MODULE')}")
    
    # 6. Check if there are any price overrides
    if lemons_product:
        print(f"\n6️⃣ LEMONS PRODUCT FIELDS:")
        for field in lemons_product._meta.fields:
            value = getattr(lemons_product, field.name, 'N/A')
            print(f"   {field.name}: {value}")

if __name__ == '__main__':
    debug_lemons()
