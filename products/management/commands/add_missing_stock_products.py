from django.core.management.base import BaseCommand
from products.models import Product, Department
from decimal import Decimal

class Command(BaseCommand):
    help = 'Add missing products commonly found in SHALLOME stock messages'

    def handle(self, *args, **options):
        # Get or create departments
        vegetables_dept, _ = Department.objects.get_or_create(
            name='Vegetables',
            defaults={'description': 'Fresh vegetables', 'is_active': True}
        )
        fruits_dept, _ = Department.objects.get_or_create(
            name='Fruits',
            defaults={'description': 'Fresh fruits', 'is_active': True}
        )
        
        # Missing products commonly found in stock messages
        missing_products = [
            # Vegetables
            {'name': 'Eggplant', 'department': vegetables_dept, 'unit': 'kg', 'price': 45.00, 'aliases': ['Brinjals', 'Brinjal']},
            {'name': 'Iceberg Lettuce', 'department': vegetables_dept, 'unit': 'head', 'price': 25.00, 'aliases': ['Iceberg']},
            {'name': 'Mixed Lettuce', 'department': vegetables_dept, 'unit': 'kg', 'price': 35.00, 'aliases': []},
            {'name': 'Crispy Lettuce', 'department': vegetables_dept, 'unit': 'box', 'price': 40.00, 'aliases': []},
            {'name': 'White Onions', 'department': vegetables_dept, 'unit': 'bag', 'price': 30.00, 'aliases': ['White Onion']},
            {'name': 'Red Onions', 'department': vegetables_dept, 'unit': 'bag', 'price': 35.00, 'aliases': ['Red Onion']},
            {'name': 'Spring Onions', 'department': vegetables_dept, 'unit': 'kg', 'price': 25.00, 'aliases': ['Spring Onion']},
            {'name': 'Red Peppers', 'department': vegetables_dept, 'unit': 'kg', 'price': 55.00, 'aliases': ['Red Pepper']},
            {'name': 'Green Peppers', 'department': vegetables_dept, 'unit': 'kg', 'price': 50.00, 'aliases': ['Green Pepper']},
            {'name': 'Yellow Peppers', 'department': vegetables_dept, 'unit': 'kg', 'price': 60.00, 'aliases': ['Yellow Pepper']},
            {'name': 'Red Chillies', 'department': vegetables_dept, 'unit': 'kg', 'price': 80.00, 'aliases': ['Red Chilli']},
            {'name': 'Green Chillies', 'department': vegetables_dept, 'unit': 'kg', 'price': 75.00, 'aliases': ['Green Chilli']},
            {'name': 'Sweet Corn', 'department': vegetables_dept, 'unit': 'punnet', 'price': 15.00, 'aliases': []},
            {'name': 'Baby Corn', 'department': vegetables_dept, 'unit': 'punnet', 'price': 20.00, 'aliases': []},
            {'name': 'Baby Marrow', 'department': vegetables_dept, 'unit': 'kg', 'price': 35.00, 'aliases': []},
            {'name': 'Patty Pan', 'department': vegetables_dept, 'unit': 'each', 'price': 8.00, 'aliases': []},
            
            # Fruits
            {'name': 'Naartjies', 'department': fruits_dept, 'unit': 'box', 'price': 45.00, 'aliases': ['Naartjie']},
            {'name': 'Blueberries', 'department': fruits_dept, 'unit': 'punnet', 'price': 35.00, 'aliases': ['Blue Berries']},
            {'name': 'Pineapple', 'department': fruits_dept, 'unit': 'each', 'price': 25.00, 'aliases': ['Pine Apple']},
            {'name': 'Papaya', 'department': fruits_dept, 'unit': 'punnet', 'price': 30.00, 'aliases': ['Paw Paw', 'Pawpaw']},
            {'name': 'Sweet Melon', 'department': fruits_dept, 'unit': 'each', 'price': 40.00, 'aliases': ['Sweet Mellon']},
            {'name': 'Watermelon', 'department': fruits_dept, 'unit': 'each', 'price': 50.00, 'aliases': ['Water Mellon']},
            {'name': 'Green Grapes', 'department': fruits_dept, 'unit': 'punnet', 'price': 45.00, 'aliases': []},
            {'name': 'Red Grapes', 'department': fruits_dept, 'unit': 'punnet', 'price': 45.00, 'aliases': []},
        ]

        created_count = 0
        updated_count = 0

        self.stdout.write('Adding missing stock products...')

        for product_data in missing_products:
            aliases = product_data.pop('aliases', [])
            
            product, created = Product.objects.update_or_create(
                name=product_data['name'],
                defaults={
                    'department': product_data['department'],
                    'unit': product_data['unit'],
                    'price': Decimal(str(product_data['price'])),
                    'stock_level': 0,
                    'minimum_stock': 5,
                    'is_active': True,
                    'description': f"Added for SHALLOME stock processing. Aliases: {', '.join(aliases) if aliases else 'None'}"
                }
            )
            
            if created:
                self.stdout.write(self.style.SUCCESS(f'✅ Created: {product.name}'))
                created_count += 1
            else:
                self.stdout.write(self.style.WARNING(f'🔄 Updated: {product.name}'))
                updated_count += 1

        total_products = Product.objects.count()
        self.stdout.write(self.style.SUCCESS(f'\n🎉 Missing products addition completed!'))
        self.stdout.write(self.style.SUCCESS(f'   Created: {created_count} products'))
        self.stdout.write(self.style.SUCCESS(f'   Updated: {updated_count} products'))
        self.stdout.write(self.style.SUCCESS(f'   Total products in database: {total_products}\n'))
        
        # Show alias mapping
        self.stdout.write('📋 Alias mappings for stock processing:')
        alias_examples = [
            'Avo → Avocados', 'Brinjals → Eggplant', 'Iceberg → Iceberg Lettuce',
            'Mushroom → Brown Mushrooms', 'Cabbage → Green Cabbage',
            'Red Onion → Red Onions', 'Pine Apple → Pineapple'
        ]
        for example in alias_examples:
            self.stdout.write(f'   {example}')
