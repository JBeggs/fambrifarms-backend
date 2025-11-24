"""
Export all products to JSON file for local development and analysis
Usage: python manage.py export_products_json --output products_export.json
       python manage.py export_products_json --output products_export.json --include-suppliers --include-stock
"""

import json
import re
from django.core.management.base import BaseCommand
from django.core.serializers.json import DjangoJSONEncoder
from django.utils import timezone
from products.models import Product, Department


class Command(BaseCommand):
    help = 'Export all products to JSON file for local development and analysis'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output',
            type=str,
            default='products_export.json',
            help='Output JSON filename'
        )
        parser.add_argument(
            '--include-suppliers',
            action='store_true',
            help='Include supplier relationships'
        )
        parser.add_argument(
            '--include-stock',
            action='store_true',
            help='Include stock information from FinishedInventory'
        )

    def extract_packaging_size(self, product_name):
        """Extract packaging size from product name (e.g., "Carrots (200g)" -> "200g")"""
        if '(' in product_name and ')' in product_name:
            try:
                match = re.search(r'\((\d+(?:\.\d+)?)(kg|g|l|ml)\s*(?:bag|box|packet|punnet)?\)', product_name, re.IGNORECASE)
                if match:
                    return f"{match.group(1)}{match.group(2)}"
            except:
                pass
        return None

    def handle(self, *args, **options):
        output_file = options['output']
        include_suppliers = options['include_suppliers']
        include_stock = options['include_stock']
        
        self.stdout.write('🔍 Exporting products from database...')
        
        # Get all products with relationships
        products = Product.objects.select_related('department').prefetch_related(
            'supplier_products__supplier' if include_suppliers else None
        ).all()
        
        # Get stock information if requested
        stock_info = {}
        if include_stock:
            from inventory.models import FinishedInventory
            self.stdout.write('📦 Fetching stock information...')
            for inventory in FinishedInventory.objects.select_related('product').all():
                stock_info[inventory.product_id] = {
                    'available_quantity': float(inventory.available_quantity or 0),
                    'reserved_quantity': float(inventory.reserved_quantity or 0),
                    'total_quantity': float((inventory.available_quantity or 0) + (inventory.reserved_quantity or 0)),
                    'minimum_level': float(inventory.minimum_level or 0),
                    'reorder_level': float(inventory.reorder_level or 0),
                }
        
        export_data = {
            'export_info': {
                'total_products': products.count(),
                'include_suppliers': include_suppliers,
                'include_stock': include_stock,
                'export_timestamp': timezone.now().isoformat()
            },
            'departments': {},
            'products': []
        }
        
        # Export departments first
        for dept in Department.objects.all():
            export_data['departments'][dept.id] = {
                'id': dept.id,
                'name': dept.name,
                'color': getattr(dept, 'color', '#2D5016')
            }
        
        # Export products
        for product in products:
            packaging_size = self.extract_packaging_size(product.name)
            
            product_data = {
                'id': product.id,
                'name': product.name,
                'description': product.description or '',
                'unit': product.unit,
                'price': float(product.price) if product.price else 0.0,
                'stock_level': float(product.stock_level) if product.stock_level else 0.0,
                'minimum_stock': float(product.minimum_stock) if product.minimum_stock else 0.0,
                'is_active': product.is_active,
                'unlimited_stock': getattr(product, 'unlimited_stock', False),
                'needs_setup': getattr(product, 'needs_setup', False),
                'department_id': product.department.id if product.department else None,
                'department_name': product.department.name if product.department else None,
                'packaging_size': packaging_size,  # Extracted from name (e.g., "200g", "5kg")
                'created_at': product.created_at.isoformat() if hasattr(product, 'created_at') else None,
                'updated_at': product.updated_at.isoformat() if hasattr(product, 'updated_at') else None,
            }
            
            # Include stock information if requested
            if include_stock:
                product_stock = stock_info.get(product.id, {
                    'available_quantity': 0.0,
                    'reserved_quantity': 0.0,
                    'total_quantity': 0.0,
                    'minimum_level': 0.0,
                    'reorder_level': 0.0,
                })
                product_data['inventory'] = product_stock
            
            # Include supplier data if requested
            if include_suppliers:
                suppliers = []
                for sp in product.supplier_products.select_related('supplier').all():
                    suppliers.append({
                        'supplier_id': sp.supplier.id,
                        'supplier_name': sp.supplier.name,
                        'supplier_price': float(sp.supplier_price) if sp.supplier_price else 0.0,
                        'is_available': sp.is_available,
                        'stock_quantity': sp.stock_quantity or 0
                    })
                product_data['suppliers'] = suppliers
            
            export_data['products'].append(product_data)
        
        # Write to file
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, cls=DjangoJSONEncoder, ensure_ascii=False)
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ Exported {len(export_data["products"])} products to {output_file}'
                )
            )
            
            # Show summary
            dept_counts = {}
            for product in export_data['products']:
                dept_name = product.get('department_name', 'Unknown')
                dept_counts[dept_name] = dept_counts.get(dept_name, 0) + 1
            
            self.stdout.write('\n📊 Products by department:')
            for dept, count in sorted(dept_counts.items()):
                self.stdout.write(f'   • {dept}: {count} products')
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error writing to {output_file}: {e}')
            )
