from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from decimal import Decimal
from datetime import date, timedelta

from inventory.models import (
    UnitOfMeasure, RawMaterial, FinishedInventory, ProductionRecipe, 
    RecipeIngredient, StockAlert
)
from suppliers.models import Supplier, SupplierProduct
from products.models import Product, Department

User = get_user_model()


class Command(BaseCommand):
    help = 'Populate inventory system with sample data for testing'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting to populate inventory data...'))

        # Create units of measure
        self.create_units()
        
        # Create suppliers with different types
        self.create_suppliers()
        
        # Create raw materials
        self.create_raw_materials()
        
        # Link suppliers to raw materials and products
        self.create_supplier_relationships()
        
        # Create production recipes
        self.create_recipes()
        
        # Create finished inventory records
        self.create_finished_inventory()
        
        # Create some sample alerts
        self.create_sample_alerts()

        self.stdout.write(self.style.SUCCESS('Successfully populated inventory data!'))

    def create_units(self):
        units_data = [
            {'name': 'Kilogram', 'abbreviation': 'kg', 'is_weight': True, 'base_unit_multiplier': Decimal('1')},
            {'name': 'Gram', 'abbreviation': 'g', 'is_weight': True, 'base_unit_multiplier': Decimal('0.001')},
            {'name': 'Pieces', 'abbreviation': 'pcs', 'is_weight': False, 'base_unit_multiplier': Decimal('1')},
            {'name': 'Bunches', 'abbreviation': 'bunch', 'is_weight': False, 'base_unit_multiplier': Decimal('1')},
            {'name': 'Boxes', 'abbreviation': 'box', 'is_weight': False, 'base_unit_multiplier': Decimal('1')},
            {'name': 'Liters', 'abbreviation': 'L', 'is_weight': False, 'base_unit_multiplier': Decimal('1')},
        ]
        
        for unit_data in units_data:
            unit, created = UnitOfMeasure.objects.get_or_create(
                name=unit_data['name'],
                defaults=unit_data
            )
            if created:
                self.stdout.write(f'Created unit: {unit.name}')

    def create_suppliers(self):
        suppliers_data = [
            {
                'name': 'FreshDirect Produce',
                'contact_name': 'Sarah Johnson',
                'contact_email': 'sarah@freshdirect.co.za',
                'contact_phone': '+27 11 123 4567',
                'city': 'Johannesburg',
            },
            {
                'name': 'Premium Seeds & Supplies',
                'contact_name': 'Mike van der Merwe',
                'contact_email': 'mike@premiumseeds.co.za',
                'contact_phone': '+27 21 987 6543',
                'city': 'Cape Town',
            },
            {
                'name': 'Valley Fresh Farms',
                'contact_name': 'Lisa Williams',
                'contact_email': 'lisa@valleyfresh.co.za',
                'contact_phone': '+27 12 555 7890',
                'city': 'Pretoria',
            },
            {
                'name': 'Organic Herbs Direct',
                'contact_name': 'David Chen',
                'contact_email': 'david@organicherbs.co.za',
                'contact_phone': '+27 31 444 5555',
                'city': 'Durban',
            },
        ]
        
        for supplier_data in suppliers_data:
            supplier, created = Supplier.objects.get_or_create(
                name=supplier_data['name'],
                defaults={
                    **supplier_data,
                    'address': f"123 Farm Road, {supplier_data['city']}, South Africa",
                    'postal_code': '0001',
                }
            )
            if created:
                self.stdout.write(f'Created supplier: {supplier.name}')

    def create_raw_materials(self):
        kg_unit = UnitOfMeasure.objects.get(abbreviation='kg')
        g_unit = UnitOfMeasure.objects.get(abbreviation='g')
        l_unit = UnitOfMeasure.objects.get(abbreviation='L')
        
        raw_materials_data = [
            {
                'name': 'Lettuce Seeds - Batavia',
                'sku': 'SEED-BAT-001',
                'unit': g_unit,
                'shelf_life_days': 365,
                'minimum_stock_level': Decimal('100'),
                'reorder_level': Decimal('200'),
                'requires_batch_tracking': True,
            },
            {
                'name': 'Coriander Seeds',
                'sku': 'SEED-COR-001',
                'unit': g_unit,
                'shelf_life_days': 365,
                'minimum_stock_level': Decimal('50'),
                'reorder_level': Decimal('100'),
                'requires_batch_tracking': True,
            },
            {
                'name': 'Organic Fertilizer',
                'sku': 'FERT-ORG-001',
                'unit': kg_unit,
                'shelf_life_days': 180,
                'minimum_stock_level': Decimal('50'),
                'reorder_level': Decimal('100'),
                'requires_batch_tracking': True,
            },
            {
                'name': 'Packaging Materials - Lettuce Bags',
                'sku': 'PKG-BAG-LET',
                'unit': UnitOfMeasure.objects.get(abbreviation='pcs'),
                'minimum_stock_level': Decimal('500'),
                'reorder_level': Decimal('1000'),
                'requires_batch_tracking': False,
            },
            {
                'name': 'Fresh Herbs - Bulk Coriander',
                'sku': 'HERB-COR-BULK',
                'unit': kg_unit,
                'shelf_life_days': 7,
                'minimum_stock_level': Decimal('5'),
                'reorder_level': Decimal('10'),
                'requires_batch_tracking': True,
            },
        ]
        
        for rm_data in raw_materials_data:
            raw_material, created = RawMaterial.objects.get_or_create(
                sku=rm_data['sku'],
                defaults={
                    **rm_data,
                    'description': f"Raw material for production: {rm_data['name']}"
                }
            )
            if created:
                self.stdout.write(f'Created raw material: {raw_material.name}')

    def create_supplier_relationships(self):
        # Get suppliers
        try:
            freshdirect = Supplier.objects.get(name='FreshDirect Produce')
            organic_herbs = Supplier.objects.get(name='Organic Herbs Direct')
        except Supplier.DoesNotExist:
            self.stdout.write(self.style.WARNING('Suppliers not found. Skipping supplier relationships.'))
            return
        
        # Get products (assuming they exist from the populate_fambri_content command)
        try:
            lettuce_products = Product.objects.filter(name__icontains='lettuce')
            herb_products = Product.objects.filter(name__icontains='coriander') | Product.objects.filter(name__icontains='chive')
            
            # Create supplier-product relationships (finished products)
            for product in lettuce_products:
                SupplierProduct.objects.get_or_create(
                    supplier=freshdirect,
                    product=product,
                    defaults={
                        'supplier_price': product.price * Decimal('0.7'),  # 70% of retail price
                        'stock_quantity': 50,
                        'is_available': True,
                    }
                )
            
            for product in herb_products:
                SupplierProduct.objects.get_or_create(
                    supplier=organic_herbs,
                    product=product,
                    defaults={
                        'supplier_price': product.price * Decimal('0.6'),
                        'stock_quantity': 20,
                        'is_available': True,
                    }
                )

            self.stdout.write('Created supplier relationships')

        except Product.DoesNotExist:
            self.stdout.write(self.style.WARNING('No products found. Make sure to run populate_fambri_content first.'))

    def create_recipes(self):
        # Create production recipes for products that are made from raw materials
        try:
            # Example: Packaged Coriander from bulk coriander
            coriander_product = Product.objects.filter(name__icontains='coriander').first()
            bulk_coriander = RawMaterial.objects.get(sku='HERB-COR-BULK')
            packaging = RawMaterial.objects.get(sku='PKG-BAG-LET')  # Using lettuce bags for example
            
            if coriander_product:
                recipe, created = ProductionRecipe.objects.get_or_create(
                    product=coriander_product,
                    version='1.0',
                    defaults={
                        'output_quantity': Decimal('1.0'),
                        'output_unit': UnitOfMeasure.objects.get(abbreviation='kg'),
                        'processing_time_minutes': 30,
                        'yield_percentage': Decimal('95.0'),
                        'processing_notes': 'Clean, trim, and package fresh coriander',
                        'created_by': User.objects.filter(is_superuser=True).first() or User.objects.first(),
                    }
                )
                
                if created:
                    # Add ingredients to recipe
                    RecipeIngredient.objects.get_or_create(
                        recipe=recipe,
                        raw_material=bulk_coriander,
                        defaults={
                            'quantity': Decimal('1.05'),  # 5% waste factor
                            'notes': 'Fresh bulk coriander for processing'
                        }
                    )
                    
                    RecipeIngredient.objects.get_or_create(
                        recipe=recipe,
                        raw_material=packaging,
                        defaults={
                            'quantity': Decimal('10'),  # 10 bags per kg
                            'notes': 'Packaging for finished product'
                        }
                    )
                    
                    self.stdout.write(f'Created recipe for {coriander_product.name}')

        except (Product.DoesNotExist, RawMaterial.DoesNotExist):
            self.stdout.write(self.style.WARNING('Could not create recipes - missing products or raw materials'))

    def create_finished_inventory(self):
        # Create finished inventory records for all products
        products = Product.objects.filter(is_active=True)
        
        for product in products:
            inventory, created = FinishedInventory.objects.get_or_create(
                product=product,
                defaults={
                    'available_quantity': Decimal('25.0'),  # Start with some stock
                    'reserved_quantity': Decimal('0.0'),
                    'minimum_level': Decimal('5.0'),
                    'reorder_level': Decimal('10.0'),
                    'average_cost': product.price * Decimal('0.6'),  # 60% cost ratio
                }
            )
            
            if created:
                self.stdout.write(f'Created inventory record for {product.name}')

    def create_sample_alerts(self):
        # Create some sample alerts to demonstrate the system
        low_stock_products = Product.objects.filter(is_active=True)[:2]
        
        for product in low_stock_products:
            StockAlert.objects.get_or_create(
                alert_type='low_stock',
                product=product,
                defaults={
                    'message': f'{product.name} stock is running low. Current level below reorder point.',
                    'severity': 'medium',
                }
            )

        # Create alert for production needed
        if low_stock_products:
            StockAlert.objects.get_or_create(
                alert_type='production_needed',
                product=low_stock_products[0],
                defaults={
                    'message': f'{low_stock_products[0].name} requires production to meet demand.',
                    'severity': 'high',
                }
            )

        self.stdout.write('Created sample alerts')
