from django.core.management.base import BaseCommand
from products.models import Product, Department


class Command(BaseCommand):
    help = 'Create Wild Rocket packet size variations for production'

    def handle(self, *args, **options):
        # Get or create a department for vegetables
        department, created = Department.objects.get_or_create(name='Vegetables')
        if created:
            self.stdout.write(f'Created department: {department.name}')

        # First, rename the existing Wild Rocket kg product to avoid conflicts
        try:
            wild_rocket_kg = Product.objects.get(name='Wild Rocket', unit='kg')
            wild_rocket_kg.name = 'Wild Rocket (bulk kg)'
            wild_rocket_kg.save()
            self.stdout.write(
                self.style.SUCCESS(f'Renamed: Wild Rocket (kg) -> {wild_rocket_kg.name}')
            )
        except Product.DoesNotExist:
            self.stdout.write(
                self.style.WARNING('Wild Rocket (kg) product not found - skipping rename')
            )

        # Create Wild Rocket packet variations
        packet_sizes = [50, 100, 200, 500]
        base_price_per_gram = 25.00 / 1000  # R25 per kg = R0.025 per gram

        created_count = 0
        for size in packet_sizes:
            product_name = f'Wild Rocket ({size}g packet)'
            price = round(base_price_per_gram * size, 2)
            
            # Check if it already exists
            existing = Product.objects.filter(name=product_name, unit='packet').first()
            if existing:
                self.stdout.write(f'Already exists: {existing.name} (R{existing.price})')
            else:
                # Create new product
                product = Product.objects.create(
                    name=product_name,
                    unit='packet',
                    price=price,
                    department=department,
                    description=f'Wild Rocket in {size}g packet size',
                    stock_level=0,
                    minimum_stock=0,
                    is_active=True,
                    needs_setup=False
                )
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created: {product.name} (R{product.price})')
                )

        self.stdout.write(
            self.style.SUCCESS(f'\nSUCCESS: Created {created_count} Wild Rocket packet products')
        )

        # Show all Wild Rocket products
        self.stdout.write('\nAll Wild Rocket products:')
        all_wild_rocket = Product.objects.filter(name__icontains='wild rocket').order_by('name')
        for p in all_wild_rocket:
            self.stdout.write(f'  - {p.name} ({p.unit}) - R{p.price}')
