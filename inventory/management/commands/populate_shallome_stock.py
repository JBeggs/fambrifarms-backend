from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from decimal import Decimal
from datetime import date, timedelta

from inventory.models import (
    UnitOfMeasure, RawMaterial, FinishedInventory, StockMovement
)
from suppliers.models import Supplier, SupplierProduct
from products.models import Product, Department

User = get_user_model()


class Command(BaseCommand):
    help = 'Populate inventory with SHALLOME supplier stock data from July 21, 2025'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Loading SHALLOME stock data from July 21, 2025...'))

        # Create units of measure for real-world units
        self.create_real_units()
        
        # Create SHALLOME as supplier
        self.create_shallome_supplier()
        
        # Create products and departments based on actual stock
        self.create_product_categories()
        
        # Create the actual products from the stock list
        self.create_stock_products()
        
        # Create supplier relationships with actual quantities
        self.create_supplier_stock()
        
        # Create finished inventory records
        self.create_finished_inventory_records()

        self.stdout.write(self.style.SUCCESS('Successfully loaded SHALLOME stock data!'))
        self.stdout.write(self.style.WARNING('Note: Rosemary and mint marked as scarce in fields'))

    def create_real_units(self):
        """Create units based on the actual supplier data"""
        # Only create units that don't already exist
        new_units_data = [
            {'name': 'Bags', 'abbreviation': 'bags', 'is_weight': False, 'base_unit_multiplier': Decimal('1')},
            {'name': 'Punnets', 'abbreviation': 'punnets', 'is_weight': False, 'base_unit_multiplier': Decimal('1')},
            {'name': 'Heads', 'abbreviation': 'heads', 'is_weight': False, 'base_unit_multiplier': Decimal('1')},
        ]
        
        for unit_data in new_units_data:
            unit, created = UnitOfMeasure.objects.get_or_create(
                abbreviation=unit_data['abbreviation'],
                defaults=unit_data
            )
            if created:
                self.stdout.write(f'Created unit: {unit.name} ({unit.abbreviation})')
        
        # Verify existing units
        existing_units = ['kg', 'g', 'pcs', 'box', 'bunch']
        for abbrev in existing_units:
            if UnitOfMeasure.objects.filter(abbreviation=abbrev).exists():
                unit = UnitOfMeasure.objects.get(abbreviation=abbrev)
                self.stdout.write(f'Using existing unit: {unit.name} ({unit.abbreviation})')

    def create_shallome_supplier(self):
        """Create SHALLOME as the main supplier"""
        supplier_data = {
            'name': 'SHALLOME Farm Supplies',
            'contact_name': 'Farm Manager',
            'contact_email': 'orders@shallome.co.za',
            'contact_phone': '+27 11 XXX XXXX',
            'address': 'SHALLOME Farm, Agricultural District',
            'city': 'Farm Location',
            'postal_code': '0000',
            'is_active': True,
        }
        
        self.shallome_supplier, created = Supplier.objects.get_or_create(
            name=supplier_data['name'],
            defaults=supplier_data
        )
        
        if created:
            self.stdout.write(f'Created supplier: {self.shallome_supplier.name}')

    def create_product_categories(self):
        """Create departments for organizing products"""
        departments_data = [
            {'name': 'Fresh Vegetables', 'color': '#4CAF50'},
            {'name': 'Fresh Fruits', 'color': '#FF9800'},
            {'name': 'Fresh Herbs', 'color': '#8BC34A'},
            {'name': 'Root Vegetables', 'color': '#795548'},
        ]
        
        for dept_data in departments_data:
            dept, created = Department.objects.get_or_create(
                name=dept_data['name'],
                defaults=dept_data
            )
            if created:
                self.stdout.write(f'Created department: {dept.name}')

    def create_stock_products(self):
        """Create products based on the actual SHALLOME stock list"""
        
        # Get departments
        vegetables = Department.objects.get(name='Fresh Vegetables')
        fruits = Department.objects.get(name='Fresh Fruits')
        herbs = Department.objects.get(name='Fresh Herbs')
        root_veg = Department.objects.get(name='Root Vegetables')
        
        # Get units (using existing abbreviations from database)
        kg_unit = UnitOfMeasure.objects.get(abbreviation='kg')
        g_unit = UnitOfMeasure.objects.get(abbreviation='g')
        pcs_unit = UnitOfMeasure.objects.get(abbreviation='pcs')
        box_unit = UnitOfMeasure.objects.get(abbreviation='box')  # Note: 'box' not 'boxes'
        bags_unit = UnitOfMeasure.objects.get(abbreviation='bags')
        punnets_unit = UnitOfMeasure.objects.get(abbreviation='punnets')
        heads_unit = UnitOfMeasure.objects.get(abbreviation='heads')
        
        # Product data from SHALLOME stock list
        products_data = [
            # Fruits
            {'name': 'Hard Avocado', 'department': fruits, 'unit': 'kg', 'price': Decimal('45.00')},
            {'name': 'Soft Avocado', 'department': fruits, 'unit': 'kg', 'price': Decimal('50.00')},
            {'name': 'Naartjies', 'department': fruits, 'unit': 'kg', 'price': Decimal('25.00')},
            {'name': 'Grapefruit', 'department': fruits, 'unit': 'kg', 'price': Decimal('20.00')},
            {'name': 'Pineapple (Green)', 'department': fruits, 'unit': 'pcs', 'price': Decimal('35.00')},
            {'name': 'Oranges', 'department': fruits, 'unit': 'kg', 'price': Decimal('22.00')},
            {'name': 'Watermelon', 'department': fruits, 'unit': 'pcs', 'price': Decimal('60.00')},
            {'name': 'Strawberries', 'department': fruits, 'unit': 'punnets', 'price': Decimal('45.00')},
            {'name': 'Red Apple', 'department': fruits, 'unit': 'kg', 'price': Decimal('35.00')},
            {'name': 'Green Apple', 'department': fruits, 'unit': 'kg', 'price': Decimal('32.00')},
            {'name': 'Blueberries', 'department': fruits, 'unit': 'punnets', 'price': Decimal('85.00')},
            {'name': 'Small Lemons', 'department': fruits, 'unit': 'kg', 'price': Decimal('30.00')},
            {'name': 'Large Lemons', 'department': fruits, 'unit': 'kg', 'price': Decimal('28.00')},
            
            # Root Vegetables  
            {'name': 'Ginger', 'department': root_veg, 'unit': 'kg', 'price': Decimal('120.00')},
            {'name': 'Potatoes', 'department': root_veg, 'unit': 'kg', 'price': Decimal('18.00')},
            {'name': 'White Onion', 'department': root_veg, 'unit': 'kg', 'price': Decimal('25.00')},
            {'name': 'Garlic', 'department': root_veg, 'unit': 'kg', 'price': Decimal('180.00')},
            {'name': 'Sweet Potatoes', 'department': root_veg, 'unit': 'kg', 'price': Decimal('35.00')},
            {'name': 'Carrots', 'department': root_veg, 'unit': 'kg', 'price': Decimal('22.00')},
            
            # Fresh Vegetables
            {'name': 'Baby Corn', 'department': vegetables, 'unit': 'punnets', 'price': Decimal('25.00')},
            {'name': 'Spinach', 'department': vegetables, 'unit': 'kg', 'price': Decimal('45.00')},
            {'name': 'Tomatoes', 'department': vegetables, 'unit': 'kg', 'price': Decimal('30.00')},
            {'name': 'Cherry Tomatoes', 'department': vegetables, 'unit': 'pcs', 'price': Decimal('8.00')},
            {'name': 'Baby Marrow', 'department': vegetables, 'unit': 'kg', 'price': Decimal('28.00')},
            {'name': 'Yellow Petit Pois', 'department': vegetables, 'unit': 'punnets', 'price': Decimal('15.00')},
            {'name': 'Green Petit Pois', 'department': vegetables, 'unit': 'punnets', 'price': Decimal('15.00')},
            {'name': 'Cayenne Pepper', 'department': vegetables, 'unit': 'kg', 'price': Decimal('180.00')},
            {'name': 'Sweet Corn', 'department': vegetables, 'unit': 'punnets', 'price': Decimal('18.00')},
            {'name': 'Brinjals (Eggplant)', 'department': vegetables, 'unit': 'kg', 'price': Decimal('35.00')},
            {'name': 'Red Cabbage', 'department': vegetables, 'unit': 'heads', 'price': Decimal('25.00')},
            {'name': 'White Cabbage', 'department': vegetables, 'unit': 'heads', 'price': Decimal('20.00')},
            {'name': 'Celery', 'department': vegetables, 'unit': 'kg', 'price': Decimal('55.00')},
            {'name': 'Zucchini', 'department': vegetables, 'unit': 'kg', 'price': Decimal('32.00')},
            {'name': 'White Cauliflower', 'department': vegetables, 'unit': 'heads', 'price': Decimal('35.00')},
            {'name': 'Broccoli', 'department': vegetables, 'unit': 'heads', 'price': Decimal('28.00')},
            {'name': 'Red Pepper', 'department': vegetables, 'unit': 'kg', 'price': Decimal('65.00')},
            {'name': 'Green Pepper', 'department': vegetables, 'unit': 'kg', 'price': Decimal('45.00')},
            {'name': 'Yellow Pepper', 'department': vegetables, 'unit': 'kg', 'price': Decimal('55.00')},
            {'name': 'Cucumber', 'department': vegetables, 'unit': 'pcs', 'price': Decimal('8.00')},
            {'name': 'Pumpkin', 'department': vegetables, 'unit': 'pcs', 'price': Decimal('45.00')},
            {'name': 'Green Chillies', 'department': vegetables, 'unit': 'g', 'price': Decimal('2.50')},
            
            # Fresh Herbs
            {'name': 'Rocket', 'department': herbs, 'unit': 'g', 'price': Decimal('0.85')},
            {'name': 'Rosemary', 'department': herbs, 'unit': 'g', 'price': Decimal('0.95')},
            {'name': 'Coriander', 'department': herbs, 'unit': 'g', 'price': Decimal('0.75')},
            {'name': 'Parsley', 'department': herbs, 'unit': 'g', 'price': Decimal('0.65')},
            {'name': 'Basil', 'department': herbs, 'unit': 'g', 'price': Decimal('1.20')},
            {'name': 'Mint', 'department': herbs, 'unit': 'g', 'price': Decimal('0.95')},
        ]
        
        for prod_data in products_data:
            # Get the unit object
            unit_obj = UnitOfMeasure.objects.get(abbreviation=prod_data['unit'])
            
            product, created = Product.objects.get_or_create(
                name=prod_data['name'],
                defaults={
                    'description': f"Fresh {prod_data['name']} from SHALLOME Farm",
                    'department': prod_data['department'],
                    'unit': prod_data['unit'],
                    'price': prod_data['price'],
                    'is_active': True,
                }
            )
            if created:
                self.stdout.write(f'Created product: {product.name}')

    def create_supplier_stock(self):
        """Create supplier-product relationships with actual stock quantities"""
        
        # Stock data from SHALLOME list (July 21, 2025)
        stock_data = [
            # Format: (product_name, quantity, notes)
            ('Hard Avocado', Decimal('4'), 'boxes - 4 boxes available'),
            ('Soft Avocado', Decimal('5'), 'boxes - 5 boxes available'),
            ('Ginger', Decimal('12'), 'kg - 12kg available'),
            ('Potatoes', Decimal('3'), 'bags - 3 bags available'),
            ('White Onion', Decimal('1'), 'bag plus 1.5kg - mixed units'),
            ('Garlic', Decimal('2'), 'kg - 2x1kg packages'),
            ('Baby Corn', Decimal('15'), 'punnets - 15 punnets available'),
            ('Naartjies', Decimal('2'), 'boxes - 2 boxes available'),
            ('Grapefruit', Decimal('1'), 'kg - 1kg available'),
            ('Spinach', Decimal('3'), 'kg - 3kg available'),
            ('Tomatoes', Decimal('14'), 'kg - 14kg available'),
            ('Sweet Potatoes', Decimal('8'), 'kg - 8kg available'),
            ('Carrots', Decimal('8'), 'kg - 8x1kg + 300g loose'),
            ('Green Chillies', Decimal('20'), 'g - 20g available'),
            ('Rocket', Decimal('300'), 'g - 300g available'),
            ('Rosemary', Decimal('500'), 'g - 500g available (SCARCE)'),
            ('Coriander', Decimal('200'), 'g - 200g available'),
            ('Parsley', Decimal('500'), 'g - 500g available'),
            ('Basil', Decimal('500'), 'g - 500g available'),
            ('Mint', Decimal('580'), 'g - 580g available (SCARCE)'),
            ('Pineapple (Green)', Decimal('24'), 'pcs - 24 pieces available'),
            ('Oranges', Decimal('17'), 'kg - 17kg available'),
            ('Baby Marrow', Decimal('3.8'), 'kg - 3.8kg available'),
            ('Yellow Petit Pois', Decimal('9'), 'punnets - 9 punnets available'),
            ('Green Petit Pois', Decimal('9'), 'punnets - 9 punnets available'),
            ('Cayenne Pepper', Decimal('3.8'), 'kg - 3.8kg available'),
            ('Watermelon', Decimal('2'), 'pcs - 2 whole watermelons'),
            ('Sweet Corn', Decimal('5'), 'punnets - 5 punnets available'),
            ('Brinjals (Eggplant)', Decimal('3'), 'kg - 3kg available'),
            ('Red Cabbage', Decimal('4'), 'heads - 4 heads available'),
            ('Celery', Decimal('0.8'), 'kg - 800g available'),
            ('Zucchini', Decimal('3'), 'kg - 3kg available'),
            ('White Cauliflower', Decimal('5'), 'heads - 5 heads available'),
            ('Small Lemons', Decimal('2'), 'kg - 2kg small size'),
            ('Strawberries', Decimal('9'), 'punnets - 9 punnets available'),
            ('Cherry Tomatoes', Decimal('20'), 'pcs - 20 pieces available'),
            ('Broccoli', Decimal('7'), 'heads - 7 heads available'),
            ('Red Pepper', Decimal('2'), 'kg - 2kg available'),
            ('Cucumber', Decimal('28'), 'pcs - 28 pieces available'),
            ('White Cabbage', Decimal('6'), 'heads - 6 heads available'),
            ('Large Lemons', Decimal('8'), 'kg - 8kg regular size'),
            ('Green Pepper', Decimal('2.5'), 'kg - 2.5kg available'),
            ('Yellow Pepper', Decimal('3'), 'kg - 3kg available'),
            ('Red Apple', Decimal('5'), 'kg - 5kg available'),
            ('Green Apple', Decimal('7'), 'kg - 7kg available'),
            ('Pumpkin', Decimal('1'), 'pcs - 1 whole pumpkin'),
            ('Blueberries', Decimal('9'), 'punnets - 9 punnets available'),
        ]
        
        for product_name, quantity, notes in stock_data:
            try:
                product = Product.objects.get(name=product_name)
                
                # Create supplier price (70% of retail price as wholesale)
                supplier_price = product.price * Decimal('0.70')
                
                supplier_product, created = SupplierProduct.objects.get_or_create(
                    supplier=self.shallome_supplier,
                    product=product,
                    defaults={
                        'supplier_price': supplier_price,
                        'stock_quantity': int(quantity),
                        'is_available': True,
                    }
                )
                
                if created:
                    self.stdout.write(f'Added stock: {product.name} - {quantity} units ({notes})')
                    
                    # Add special notes for scarce items
                    if 'SCARCE' in notes:
                        self.stdout.write(self.style.WARNING(f'  >>> {product.name} marked as SCARCE in fields'))
                        
            except Product.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'Product not found: {product_name}'))
                continue

    def create_finished_inventory_records(self):
        """Create finished inventory records for all products with actual quantities"""
        products_with_stock = SupplierProduct.objects.filter(supplier=self.shallome_supplier)
        
        for supplier_product in products_with_stock:
            product = supplier_product.product
            stock_qty = Decimal(str(supplier_product.stock_quantity))
            
            # Set minimum levels based on product type
            if 'herb' in product.department.name.lower() or product.unit == 'g':
                min_level = Decimal('50')  # herbs need higher minimum due to low quantities
                reorder_level = Decimal('100')
            else:
                min_level = Decimal('2')
                reorder_level = Decimal('5')
            
            inventory, created = FinishedInventory.objects.get_or_create(
                product=product,
                defaults={
                    'available_quantity': stock_qty,
                    'reserved_quantity': Decimal('0'),
                    'minimum_level': min_level,
                    'reorder_level': reorder_level,
                    'average_cost': supplier_product.supplier_price,
                    'needs_production': False,  # These are finished products from supplier
                }
            )
            
            if created:
                self.stdout.write(f'Created inventory: {product.name} - {stock_qty} available')
                
                # Create initial stock movement record
                StockMovement.objects.create(
                    product=product,
                    movement_type='in',
                    quantity=stock_qty,
                    reference_type='supplier_delivery',
                    reference_id=str(supplier_product.id),
                    notes=f'Initial stock from SHALLOME supplier - July 21, 2025',
                    created_by=User.objects.filter(is_superuser=True).first()
                )
