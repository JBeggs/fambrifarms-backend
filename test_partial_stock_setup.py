#!/usr/bin/env python3
"""
Quick script to set up partial stock conditions for testing order splitting.

This creates FinishedInventory records with LIMITED stock to trigger splitting.
"""

import os
import sys
import django

# Setup Django
sys.path.append('/Users/jodybeggs/Documents/fambrifarms_after_meeting/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fambrifarms.settings')
django.setup()

from inventory.models import FinishedInventory
from products.models import Product
from decimal import Decimal

def setup_partial_stock():
    """Set up products with partial stock to test splitting functionality"""
    
    # Products to set up with limited stock (enough to trigger splitting)
    test_products = [
        {'name': 'Tomatoes', 'available': 5},      # If someone orders 10, split: 5 reserved + 5 procurement
        {'name': 'Red Peppers', 'available': 3},   # If someone orders 5, split: 3 reserved + 2 procurement  
        {'name': 'Lettuce', 'available': 2},       # If someone orders 4, split: 2 reserved + 2 procurement
        {'name': 'Onions', 'available': 7},        # If someone orders 10, split: 7 reserved + 3 procurement
        {'name': 'Carrots', 'available': 1},       # If someone orders 3, split: 1 reserved + 2 procurement
    ]
    
    print("🔧 Setting up partial stock conditions for testing...")
    
    for product_info in test_products:
        try:
            # Find product (case-insensitive search)
            products = Product.objects.filter(name__icontains=product_info['name'])
            if not products.exists():
                print(f"❌ Product '{product_info['name']}' not found")
                continue
                
            product = products.first()
            available_qty = Decimal(str(product_info['available']))
            
            # Get or create FinishedInventory record
            inventory, created = FinishedInventory.objects.get_or_create(
                product=product,
                defaults={
                    'available_quantity': available_qty,
                    'reserved_quantity': Decimal('0'),
                    'minimum_level': Decimal('5'),
                    'reorder_level': Decimal('10'),
                    'average_cost': product.price or Decimal('10')
                }
            )
            
            # Update with partial stock
            inventory.available_quantity = available_qty
            inventory.reserved_quantity = Decimal('0')
            inventory.save()
            
            action = "Created" if created else "Updated"
            print(f"✅ {action} {product.name}: {available_qty} available")
            
        except Exception as e:
            print(f"❌ Error with {product_info['name']}: {e}")
    
    print("\n📋 Test scenario ready!")
    print("Now create an order with items like:")
    print("- '10 Tomatoes' (will split: 5 reserved + 5 procurement)")  
    print("- '5 Red Peppers' (will split: 3 reserved + 2 procurement)")
    print("- '4 Lettuce' (will split: 2 reserved + 2 procurement)")

if __name__ == '__main__':
    setup_partial_stock()
