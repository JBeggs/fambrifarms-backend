from django.core.management.base import BaseCommand
from django.db import transaction
from suppliers.models import Supplier, SupplierPriceList, SupplierPriceListItem
from products.models import Product, Department
from decimal import Decimal
from datetime import date
import random


class Command(BaseCommand):
    help = 'Update supplier product offerings based on their specialties and realistic sourcing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing price lists before updating',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing existing price lists...')
            SupplierPriceListItem.objects.all().delete()
            SupplierPriceList.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('Existing price lists cleared.'))

        self.update_supplier_products()
        
        self.stdout.write(self.style.SUCCESS('\n🎉 SUPPLIER PRODUCTS UPDATED SUCCESSFULLY!'))

    def update_supplier_products(self):
        """Update each supplier's products based on their specialty and realistic sourcing"""
        
        # Get all products for reference
        all_products = Product.objects.all()
        products_by_dept = {}
        for dept in Department.objects.all():
            products_by_dept[dept.name] = list(all_products.filter(department=dept))

        suppliers = Supplier.objects.all()
        
        for supplier in suppliers:
            self.stdout.write(f'\n🏢 Updating products for: {supplier.name}')
            
            if supplier.name == 'Fambri Farms Internal':
                self.create_fambri_internal_products(supplier, products_by_dept)
            elif supplier.name == 'Tshwane Market':
                self.create_tshwane_market_products(supplier, products_by_dept)
            elif supplier.name == 'Reese Mushrooms':
                self.create_reese_mushrooms_products(supplier, products_by_dept)
            elif supplier.name == 'Tshwane Fresh Produce Market':
                self.create_tshwane_market_products(supplier, products_by_dept)

    def create_fambri_internal_products(self, supplier, products_by_dept):
        """Fambri Farms Internal - Own production, core vegetables and some fruits"""
        
        # Clear existing price lists
        SupplierPriceList.objects.filter(supplier=supplier).delete()
        
        price_list = SupplierPriceList.objects.create(
            supplier=supplier,
            list_date=date.today(),
            file_reference=f'Fambri Farms Internal Production List',
            is_processed=True,
            notes='Own farm production - fresh daily harvest, core vegetables and seasonal fruits',
        )
        
        # Core farm production items (what Fambri would realistically grow)
        farm_products = [
            # Core vegetables - what a farm would grow
            {'name': 'Tomatoes', 'price': 22.00, 'qty': 50},
            {'name': 'Carrots (Loose)', 'price': 18.00, 'qty': 40},
            {'name': 'Carrots (1kg Packed)', 'price': 20.00, 'qty': 30},
            {'name': 'Green Cabbage', 'price': 18.00, 'qty': 25},
            {'name': 'Red Cabbage', 'price': 22.00, 'qty': 15},
            {'name': 'Broccoli', 'price': 32.00, 'qty': 20},
            {'name': 'Cauliflower', 'price': 28.00, 'qty': 18},
            {'name': 'Lettuce Head', 'price': 13.00, 'qty': 30},
            {'name': 'Mixed Lettuce', 'price': 32.00, 'qty': 20},
            {'name': 'Baby Spinach', 'price': 40.00, 'qty': 15},
            {'name': 'Cucumber', 'price': 7.00, 'qty': 60},
            {'name': 'Green Peppers', 'price': 45.00, 'qty': 25},
            {'name': 'Red Peppers', 'price': 50.00, 'qty': 20},
            {'name': 'Green Beans', 'price': 40.00, 'qty': 18},
            {'name': 'Baby Marrow', 'price': 32.00, 'qty': 20},
            {'name': 'Butternut', 'price': 20.00, 'qty': 30},
            {'name': 'Beetroot', 'price': 22.00, 'qty': 25},
            
            # Herbs that farms typically grow
            {'name': 'Parsley', 'price': 7.00, 'qty': 40},
            {'name': 'Coriander', 'price': 7.00, 'qty': 35},
            {'name': 'Mint', 'price': 9.00, 'qty': 30},
            {'name': 'Basil', 'price': 13.00, 'qty': 25},
            
            # Some fruits (what a farm might grow)
            {'name': 'Strawberries', 'price': 22.00, 'qty': 20},
            {'name': 'Sweet Corn', 'price': 13.00, 'qty': 25},
        ]
        
        self.add_products_to_price_list(price_list, farm_products, 'FF')
        self.stdout.write(f'   ✅ Added {len(farm_products)} farm production items')

    def create_reese_mushrooms_products(self, supplier, products_by_dept):
        """Reese Mushrooms - Mushroom specialist supplier"""
        
        # Clear existing price lists
        SupplierPriceList.objects.filter(supplier=supplier).delete()
        
        price_list = SupplierPriceList.objects.create(
            supplier=supplier,
            list_date=date.today(),
            file_reference=f'Reese Mushrooms Product List',
            is_processed=True,
            notes='Mushroom specialist - fresh mushrooms, premium quality',
        )
        
        # Mushroom products based on real supplier
        reese_products = [
            {'name': 'Button Mushrooms', 'price': 50.00, 'qty': 20},
            {'name': 'Brown Mushrooms', 'price': 55.00, 'qty': 15},
            {'name': 'Portabellini Mushrooms', 'price': 65.00, 'qty': 10},
            {'name': 'Oyster Mushrooms', 'price': 70.00, 'qty': 8},
        ]
        
        self.add_products_to_price_list(price_list, reese_products, 'REESE')
        self.stdout.write(f'   ✅ Added {len(reese_products)} mushroom products')

    def create_tshwane_market_products(self, supplier, products_by_dept):
        """Tshwane Fresh Produce Market - Wholesale market, bulk quantities, competitive prices"""
        
        # Clear existing price lists
        SupplierPriceList.objects.filter(supplier=supplier).delete()
        
        price_list = SupplierPriceList.objects.create(
            supplier=supplier,
            list_date=date.today(),
            file_reference=f'Tshwane Market Wholesale List',
            is_processed=True,
            notes='Wholesale fresh produce market - bulk quantities, competitive prices, wide variety',
        )
        
        # Wholesale market items - comprehensive selection at competitive prices
        market_products = [
            # Bulk vegetables (wholesale pricing)
            {'name': 'Potatoes', 'price': 42.00, 'qty': 50},  # Bulk pricing
            {'name': 'White Onions', 'price': 28.00, 'qty': 40},
            {'name': 'Red Onions', 'price': 32.00, 'qty': 35},
            {'name': 'Tomatoes', 'price': 23.00, 'qty': 60},  # Competitive market price
            {'name': 'Carrots (Loose)', 'price': 19.00, 'qty': 45},
            {'name': 'Carrots (1kg Packed)', 'price': 21.00, 'qty': 35},
            {'name': 'Green Cabbage', 'price': 19.00, 'qty': 30},
            {'name': 'Red Cabbage', 'price': 23.00, 'qty': 20},
            {'name': 'Broccoli', 'price': 33.00, 'qty': 25},
            {'name': 'Cauliflower', 'price': 28.00, 'qty': 22},
            {'name': 'Green Peppers', 'price': 48.00, 'qty': 30},
            {'name': 'Red Peppers', 'price': 53.00, 'qty': 25},
            {'name': 'Yellow Peppers', 'price': 58.00, 'qty': 20},
            {'name': 'Cucumber', 'price': 7.50, 'qty': 80},
            {'name': 'Butternut', 'price': 21.00, 'qty': 35},
            {'name': 'Sweet Potatoes', 'price': 26.00, 'qty': 30},
            {'name': 'Beetroot', 'price': 24.00, 'qty': 25},
            
            # Bulk fruits
            {'name': 'Bananas', 'price': 19.00, 'qty': 40},
            {'name': 'Oranges', 'price': 23.00, 'qty': 35},
            {'name': 'Lemons', 'price': 28.00, 'qty': 30},
            {'name': 'Avocados (Hard)', 'price': 95.00, 'qty': 15},
            {'name': 'Avocados (Semi-Ripe)', 'price': 105.00, 'qty': 12},
            {'name': 'Pineapple', 'price': 23.00, 'qty': 25},
            {'name': 'Strawberries', 'price': 23.00, 'qty': 30},
            {'name': 'Red Grapes', 'price': 42.00, 'qty': 20},
            {'name': 'Green Grapes', 'price': 42.00, 'qty': 18},
            {'name': 'Watermelon', 'price': 48.00, 'qty': 15},
            {'name': 'Sweet Melon', 'price': 38.00, 'qty': 12},
            
            # Lettuce and leafy greens
            {'name': 'Lettuce Head', 'price': 14.00, 'qty': 40},
            {'name': 'Mixed Lettuce', 'price': 33.00, 'qty': 25},
            {'name': 'Iceberg Lettuce', 'price': 23.00, 'qty': 20},
            {'name': 'Baby Spinach', 'price': 43.00, 'qty': 18},
            {'name': 'Deveined Spinach', 'price': 23.00, 'qty': 15},
            
            # Basic herbs (market would have these)
            {'name': 'Parsley', 'price': 7.50, 'qty': 50},
            {'name': 'Coriander', 'price': 7.50, 'qty': 45},
            {'name': 'Mint', 'price': 9.50, 'qty': 35},
            {'name': 'Spring Onions', 'price': 23.00, 'qty': 30},
        ]
        
        self.add_products_to_price_list(price_list, market_products, 'TFPM')
        self.stdout.write(f'   ✅ Added {len(market_products)} wholesale market items')

    def add_products_to_price_list(self, price_list, products_data, code_prefix):
        """Add products to a price list with proper pricing calculations"""
        
        for i, product_data in enumerate(products_data, 1):
            # Calculate VAT (15%)
            unit_price = Decimal(str(product_data['price']))
            vat_amount = unit_price * Decimal('0.15')
            total_excl_vat = unit_price * product_data['qty']
            total_incl_vat = total_excl_vat + (vat_amount * product_data['qty'])
            
            SupplierPriceListItem.objects.create(
                price_list=price_list,
                supplier_code=f'{code_prefix}{i:03d}',
                product_description=f'{product_data["name"]} - {price_list.supplier.name}',
                category_code='PROD',
                quantity=product_data['qty'],
                unit_price=unit_price,
                vat_amount=vat_amount,
                total_excl_vat=total_excl_vat,
                total_incl_vat=total_incl_vat,
                is_new_product=False,
                needs_review=False,
            )
