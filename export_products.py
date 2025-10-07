#!/usr/bin/env python
"""
Product Export/Import Scripts for Fambri Farms
Usage: python export_products.py [export|import] [filename]
"""

import os
import sys
import json
import csv
from datetime import datetime
from decimal import Decimal

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
import django
django.setup()

from products.models import Product, Department

def export_products_json(filename=None):
    """Export products to JSON format"""
    if not filename:
        filename = f'products_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    
    products = Product.objects.all().select_related('department')
    data = []
    
    for product in products:
        data.append({
            'name': product.name,
            'description': product.description,
            'department': product.department.name,
            'price': float(product.price),
            'unit': product.unit,
            'stock_level': float(product.stock_level),
            'minimum_stock': float(product.minimum_stock),
            'is_active': product.is_active,
            'needs_setup': product.needs_setup,
            'created_at': product.created_at.isoformat(),
            'updated_at': product.updated_at.isoformat()
        })
    
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f'✅ Exported {len(data)} products to {filename}')
    return filename

def export_products_csv(filename=None):
    """Export products to CSV format for easy editing"""
    if not filename:
        filename = f'products_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    
    products = Product.objects.all().select_related('department')
    
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # Write header
        writer.writerow([
            'name', 'description', 'department', 'price', 'unit', 
            'stock_level', 'minimum_stock', 'is_active', 'needs_setup'
        ])
        
        # Write data
        for product in products:
            writer.writerow([
                product.name,
                product.description,
                product.department.name,
                float(product.price),
                product.unit,
                float(product.stock_level),
                float(product.minimum_stock),
                product.is_active,
                product.needs_setup
            ])
    
    print(f'✅ Exported {products.count()} products to {filename}')
    return filename

def import_products_json(filename):
    """Import products from JSON format"""
    with open(filename, 'r') as f:
        data = json.load(f)
    
    created_count = 0
    updated_count = 0
    
    for item in data:
        department, _ = Department.objects.get_or_create(name=item['department'])
        
        product, created = Product.objects.get_or_create(
            name=item['name'],
            defaults={
                'description': item.get('description', ''),
                'department': department,
                'price': Decimal(str(item['price'])),
                'unit': item['unit'],
                'stock_level': Decimal(str(item.get('stock_level', 0))),
                'minimum_stock': Decimal(str(item.get('minimum_stock', 5))),
                'is_active': item.get('is_active', True),
                'needs_setup': item.get('needs_setup', False),
            }
        )
        
        if created:
            created_count += 1
        else:
            # Update existing product
            product.description = item.get('description', '')
            product.department = department
            product.price = Decimal(str(item['price']))
            product.unit = item['unit']
            product.stock_level = Decimal(str(item.get('stock_level', 0)))
            product.minimum_stock = Decimal(str(item.get('minimum_stock', 5)))
            product.is_active = item.get('is_active', True)
            product.needs_setup = item.get('needs_setup', False)
            product.save()
            updated_count += 1
    
    print(f'✅ Imported {created_count} new products, updated {updated_count} existing products')
    return created_count, updated_count

def import_products_csv(filename):
    """Import products from CSV format"""
    with open(filename, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        data = list(reader)
    
    created_count = 0
    updated_count = 0
    
    for item in data:
        department, _ = Department.objects.get_or_create(name=item['department'])
        
        product, created = Product.objects.get_or_create(
            name=item['name'],
            defaults={
                'description': item.get('description', ''),
                'department': department,
                'price': Decimal(str(item['price'])),
                'unit': item['unit'],
                'stock_level': Decimal(str(item.get('stock_level', 0))),
                'minimum_stock': Decimal(str(item.get('minimum_stock', 5))),
                'is_active': item.get('is_active', 'True').lower() == 'true',
                'needs_setup': item.get('needs_setup', 'False').lower() == 'true',
            }
        )
        
        if created:
            created_count += 1
        else:
            # Update existing product
            product.description = item.get('description', '')
            product.department = department
            product.price = Decimal(str(item['price']))
            product.unit = item['unit']
            product.stock_level = Decimal(str(item.get('stock_level', 0)))
            product.minimum_stock = Decimal(str(item.get('minimum_stock', 5)))
            product.is_active = item.get('is_active', 'True').lower() == 'true'
            product.needs_setup = item.get('needs_setup', 'False').lower() == 'true'
            product.save()
            updated_count += 1
    
    print(f'✅ Imported {created_count} new products, updated {updated_count} existing products')
    return created_count, updated_count

def main():
    if len(sys.argv) < 2:
        print("Usage: python export_products.py [export|import] [format] [filename]")
        print("Formats: json, csv")
        print("Examples:")
        print("  python export_products.py export json")
        print("  python export_products.py export csv")
        print("  python export_products.py import json products.json")
        print("  python export_products.py import csv products.csv")
        return
    
    action = sys.argv[1]
    format_type = sys.argv[2] if len(sys.argv) > 2 else 'json'
    filename = sys.argv[3] if len(sys.argv) > 3 else None
    
    if action == 'export':
        if format_type == 'json':
            export_products_json(filename)
        elif format_type == 'csv':
            export_products_csv(filename)
        else:
            print("❌ Invalid format. Use 'json' or 'csv'")
    
    elif action == 'import':
        if not filename:
            print("❌ Please specify filename for import")
            return
        
        if not os.path.exists(filename):
            print(f"❌ File {filename} not found")
            return
        
        if format_type == 'json':
            import_products_json(filename)
        elif format_type == 'csv':
            import_products_csv(filename)
        else:
            print("❌ Invalid format. Use 'json' or 'csv'")
    
    else:
        print("❌ Invalid action. Use 'export' or 'import'")

if __name__ == '__main__':
    main()
