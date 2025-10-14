#!/usr/bin/env python
"""
Fix pricing for existing orders by recalculating customer-specific prices
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'familyfarms_api.settings')
django.setup()

from orders.models import Order, OrderItem
from whatsapp.services import get_customer_specific_price, determine_customer_segment
from decimal import Decimal

print("=" * 70)
print("FIXING ORDER ITEM PRICING")
print("=" * 70)

# Get all orders
orders = Order.objects.select_related('restaurant').prefetch_related('items__product').all()

total_orders = orders.count()
total_items_updated = 0
total_price_difference = Decimal('0.00')

print(f"\nProcessing {total_orders} orders...")
print("")

for order in orders:
    customer = order.restaurant
    segment = determine_customer_segment(customer)
    
    items_in_order = 0
    order_price_diff = Decimal('0.00')
    
    for item in order.items.all():
        try:
            # Skip note/special items with 0 price
            if item.product.price == 0:
                continue
                
            # Calculate what the price should be
            correct_price = get_customer_specific_price(item.product, customer)
            
            # Check if it's wrong
            if abs(item.price - correct_price) > Decimal('0.01'):
                old_price = item.price
                old_total = item.total_price
                
                # Update the item
                item.price = correct_price
                item.total_price = item.quantity * correct_price
                item.save()
                
                price_diff = (correct_price - old_price) * item.quantity
                order_price_diff += price_diff
                total_price_difference += price_diff
                
                items_in_order += 1
                total_items_updated += 1
                
                print(f"  ✓ {item.product.name}: R{old_price} → R{correct_price} "
                      f"(Qty: {item.quantity}, Diff: R{price_diff:.2f})")
                
        except Exception as e:
            print(f"  ✗ Error updating {item.product.name}: {e}")
    
    if items_in_order > 0:
        # Recalculate order totals
        order.subtotal = sum(item.total_price for item in order.items.all())
        order.total_amount = order.subtotal
        order.save()
        
        print(f"\n{order.order_number} ({customer.get_full_name()} - {segment})")
        print(f"  Updated {items_in_order} items, Order total change: +R{order_price_diff:.2f}")
        print(f"  New order total: R{order.total_amount:.2f}")
        print("")

print("=" * 70)
print(f"SUMMARY:")
print(f"  Total Orders Processed: {total_orders}")
print(f"  Total Items Updated: {total_items_updated}")
print(f"  Total Revenue Adjustment: +R{total_price_difference:.2f}")
print("=" * 70)
print("\nNOTE: This is the ADDITIONAL revenue that should have been charged")
print("based on customer-specific pricing rules.")
print("=" * 70)

