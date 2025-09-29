from django.core.management.base import BaseCommand
from django.db import transaction
from products.models import Product, Department
from decimal import Decimal


class Command(BaseCommand):
    help = 'Add missing products that appear in WhatsApp orders but are not in the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without actually creating products',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No products will be created'))
        
        # Get departments
        try:
            vegetables_dept = Department.objects.get(name='Vegetables')
            fruits_dept = Department.objects.get(name='Fruits')
        except Department.DoesNotExist:
            self.stdout.write(self.style.ERROR('Required departments not found. Please run department seeding first.'))
            return

        # Products that appear in WhatsApp orders but are missing from database
        missing_products = [
            {
                'name': 'Mixed Peppers',
                'department': vegetables_dept,
                'unit': 'kg',
                'price': 50.00,
                'description': 'Mixed variety of peppers (red, green, yellow) - needs recipe/preparation',
                'aliases': ['mix peppers', 'pepper mix']
            },
            {
                'name': 'Red Apples',
                'department': fruits_dept,
                'unit': 'kg',
                'price': 35.00,
                'description': 'Fresh red apples',
                'aliases': ['red apple', 'apple red']
            },
            {
                'name': 'Baby Potatoes',
                'department': vegetables_dept,
                'unit': 'kg',
                'price': 30.00,
                'description': 'Small baby potatoes',
                'aliases': ['baby potato', 'small potatoes']
            }
        ]

        created_count = 0
        updated_count = 0

        self.stdout.write(f'\n📦 Adding {len(missing_products)} missing order products...')
        
        with transaction.atomic():
            for product_data in missing_products:
                aliases = product_data.pop('aliases', [])
                
                if dry_run:
                    self.stdout.write(f'Would create: {product_data["name"]} - {product_data["department"].name} - R{product_data["price"]}')
                    self.stdout.write(f'  Aliases: {", ".join(aliases)}')
                    continue
                
                product, created = Product.objects.update_or_create(
                    name=product_data['name'],
                    defaults={
                        'department': product_data['department'],
                        'unit': product_data['unit'],
                        'price': Decimal(str(product_data['price'])),
                        'stock_level': Decimal('0.00'),
                        'minimum_stock': Decimal('5.00'),
                        'is_active': True,
                        'needs_setup': False,
                        'description': product_data['description']
                    }
                )
                
                if created:
                    self.stdout.write(self.style.SUCCESS(f'✅ Created: {product.name} (R{product.price}/{product.unit})'))
                    created_count += 1
                else:
                    self.stdout.write(self.style.WARNING(f'🔄 Updated: {product.name} (R{product.price}/{product.unit})'))
                    updated_count += 1

        if not dry_run:
            total_products = Product.objects.count()
            self.stdout.write(self.style.SUCCESS(f'\n🎉 Missing order products addition completed!'))
            self.stdout.write(self.style.SUCCESS(f'   Created: {created_count} products'))
            self.stdout.write(self.style.SUCCESS(f'   Updated: {updated_count} products'))
            self.stdout.write(self.style.SUCCESS(f'   Total products in database: {total_products}'))
            
            self.stdout.write('\n📋 Alias mappings added to services.py:')
            alias_mappings = [
                "'mix peppers': 'mixed peppers'",
                "'red apple': 'red apples'", 
                "'baby potato': 'baby potatoes'"
            ]
            for mapping in alias_mappings:
                self.stdout.write(f'   {mapping}')
                
            self.stdout.write('\n⚠️  IMPORTANT NOTES:')
            self.stdout.write('   • Mixed Peppers may need recipe/preparation setup')
            self.stdout.write('   • Update aliases in whatsapp/services.py if needed')
            self.stdout.write('   • Verify pricing with current market rates')
        else:
            self.stdout.write('\n🔍 Use --dry-run=false or omit --dry-run to actually create products')
