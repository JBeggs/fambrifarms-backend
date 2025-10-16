"""
Export all products to JSON file for local development
Usage: python manage.py export_products_json --output products_export.json
"""

import json
from django.core.management.base import BaseCommand
from django.core.serializers.json import DjangoJSONEncoder
from django.utils import timezone
from products.models import Product, Department


class Command(BaseCommand):
    help = 'Export all products to JSON file for local development'

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

    def handle(self, *args, **options):
        output_file = options['output']
        include_suppliers = options['include_suppliers']
        
        self.stdout.write('🔍 Exporting products from database...')
        
        # Get all products with relationships
        products = Product.objects.select_related('department').prefetch_related(
            'supplier_products__supplier' if include_suppliers else None
        ).all()
        
        export_data = {
            'export_info': {
                'total_products': products.count(),
                'include_suppliers': include_suppliers,
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
            product_data = {
                'id': product.id,
                'name': product.name,
                'unit': product.unit,
                'price': float(product.price) if product.price else 0.0,
                'department_id': product.department.id if product.department else None,
                'department_name': product.department.name if product.department else None,
                'created_at': product.created_at.isoformat() if hasattr(product, 'created_at') else None
            }
            
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
