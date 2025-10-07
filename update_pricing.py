#!/usr/bin/env python
"""
Update Product Pricing Script for Fambri Farms
Based on Tshwane Market data
"""

import os
import sys
from decimal import Decimal

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
import django
django.setup()

from products.models import Product

def update_pricing():
    """Update product pricing based on market data"""
    
    # Market pricing data from Tshwane Market invoices
    market_prices = {
        # High-value products (R100+)
        'Strawberries': 400.00,
        'Buttercups': 220.00,
        'Cucumbers English': 100.00,
        'LEMON': 40.00,
        'Marrows Dark Green': 40.00,
        'Sweetcorn': 404.00,
        'Peppers Green': 129.00,
        'ONIONS BROWN': 175.00,
        'ONIONS RED': 175.00,
        'AVOCADO HASS': 85.00,
        'AVOCADO FUERTE': 120.00,
        'TOMATOES': 75.00,
        'Sweet Potatoes Red': 70.00,
        'Carrots': 128.00,
        'Parsley': 100.00,
        'Coriander': 90.00,
        'Crispy Lettuce': 200.00,
        'Red Peppers': 150.00,
        'Yellow Peppers': 250.00,
        'Broccoli': 200.00,
        'Ginger': 800.00,
        
        # Medium-value products (R20-R99)
        'TOMATOES COCKTAIL': 5.00,
        'Spinach': 8.00,
        'POTATO MONDIAL': 20.00,
        'PINEAPPLE QUEEN VI': 25.00,
        'BLUEBERRIES': 240.00,
        'Butternut': 65.00,
        'Peppers Red': 150.00,
        'Cauliflower': 80.00,
        'Green Cabbage': 50.00,
        
        # New products we added
        'Kiwi (200g punnet)': 25.00,
        'Kiwi (500g punnet)': 45.00,
        'Kiwi (box)': 120.00,
        'Snap Peas (packet)': 15.00,
        'Squash (kg)': 30.00,
        'Sun Dried Tomatoes (packet)': 40.00,
    }
    
    print("=== UPDATING PRODUCT PRICING ===")
    print(f"Market prices loaded: {len(market_prices)} products")
    print()
    
    updated_count = 0
    not_found_count = 0
    
    for market_name, market_price in market_prices.items():
        # Try to find matching products
        products = Product.objects.filter(name__icontains=market_name.split()[0])
        
        if products.exists():
            for product in products:
                old_price = float(product.price)
                new_price = market_price
                
                # Only update if there's a significant difference (>20%)
                diff_percent = abs(old_price - new_price) / old_price * 100 if old_price > 0 else 100
                
                if diff_percent > 20:
                    product.price = Decimal(str(new_price))
                    product.save()
                    print(f"✅ Updated {product.name}: R{old_price:.2f} → R{new_price:.2f} ({diff_percent:.1f}% change)")
                    updated_count += 1
                else:
                    print(f"⏭️  Skipped {product.name}: R{old_price:.2f} (only {diff_percent:.1f}% difference)")
        else:
            print(f"❌ No products found for: {market_name}")
            not_found_count += 1
    
    print()
    print(f"=== PRICING UPDATE SUMMARY ===")
    print(f"✅ Updated: {updated_count} products")
    print(f"❌ Not found: {not_found_count} products")
    print(f"📊 Total products in database: {Product.objects.count()}")

def show_pricing_comparison():
    """Show current vs market pricing comparison"""
    
    market_prices = {
        'Strawberries': 400.00,
        'LEMON': 40.00,
        'Bananas': 220.00,
        'ONIONS BROWN': 175.00,
        'ONIONS RED': 175.00,
        'POTATO MONDIAL': 20.00,
        'AVOCADO HASS': 85.00,
        'AVOCADO FUERTE': 120.00,
        'TOMATOES': 75.00,
        'TOMATOES COCKTAIL': 5.00,
        'PINEAPPLE QUEEN VI': 25.00,
        'BLUEBERRIES': 240.00,
        'Butternut': 65.00,
        'Carrots': 128.00,
        'Sweet Potatoes Red': 70.00,
        'Parsley': 100.00,
        'Coriander': 90.00,
        'Spinach': 8.00,
        'Crispy Lettuce': 200.00,
        'Red Peppers': 150.00,
        'Green Peppers': 129.00,
        'Yellow Peppers': 250.00,
        'Cucumber': 100.00,
        'Broccoli': 200.00,
        'Cauliflower': 80.00,
        'Green Cabbage': 50.00,
        'Ginger': 800.00,
    }
    
    print("=== PRICING COMPARISON ===")
    print(f"{'Product':<25} {'Current':<10} {'Market':<10} {'Difference':<12} {'% Change':<10}")
    print("-" * 80)
    
    for market_name, market_price in market_prices.items():
        products = Product.objects.filter(name__icontains=market_name.split()[0])
        
        if products.exists():
            product = products.first()
            current_price = float(product.price)
            difference = current_price - market_price
            percent_change = (difference / market_price) * 100 if market_price > 0 else 0
            
            status = "✅" if abs(percent_change) <= 20 else "⚠️"
            
            print(f"{product.name[:24]:<25} {current_price:<10.2f} {market_price:<10.2f} {difference:<+12.2f} {percent_change:<+10.1f}% {status}")

def main():
    if len(sys.argv) > 1 and sys.argv[1] == 'compare':
        show_pricing_comparison()
    else:
        print("This will update product pricing based on Tshwane Market data.")
        print("Run with 'compare' to see current vs market pricing without updating.")
        print()
        
        response = input("Do you want to proceed with pricing updates? (y/N): ")
        if response.lower() == 'y':
            update_pricing()
        else:
            print("Pricing update cancelled.")

if __name__ == '__main__':
    main()
