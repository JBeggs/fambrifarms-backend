from django.core.management.base import BaseCommand
from django.db import transaction
from suppliers.models import Supplier, SalesRep, SupplierPriceList, SupplierPriceListItem
from products.models import Product, Department
from decimal import Decimal
from datetime import date, datetime
import random


class Command(BaseCommand):
    help = 'Import sample suppliers and price list data for testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing suppliers and price lists before importing',
        )
        parser.add_argument(
            '--create-products',
            action='store_true',
            help='Create sample products if they don\'t exist',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing existing suppliers and price lists...')
            SupplierPriceListItem.objects.all().delete()
            SupplierPriceList.objects.all().delete()
            SalesRep.objects.all().delete()
            Supplier.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('Existing data cleared.'))

        # Create sample products if requested
        if options['create_products']:
            self.create_sample_products()

        # DISABLED: No longer creating sample suppliers - only real suppliers from seed_fambri_suppliers.py
        self.stdout.write(self.style.WARNING('Sample supplier creation disabled - use seed_fambri_suppliers.py for real suppliers'))
        self.stdout.write(self.style.SUCCESS('Use update_supplier_products.py to update supplier product offerings'))
        return

        # Create sample supplier (avoiding duplication with Tshwane Fresh Produce Market)
        supplier_data = {
            'name': 'Johannesburg Fresh Market',
            'contact_person': 'John Smith',
            'email': 'orders@jhbfresh.co.za',
            'phone': '+27 11 555 1001',
            'address': '123 Market Street, Johannesburg, 2001',
            'payment_terms_days': 30,
            'lead_time_days': 2,
            'minimum_order_value': Decimal('500.00'),
            'is_active': True,
        }
        
        # Sales reps data for the supplier
        sales_reps_data = [
            {
                'name': 'John Smith',
                'email': 'john.smith@jhbfresh.co.za',
                'phone': '+27 11 555 1001',
                'position': 'General Manager',
                'is_primary': True,
                'is_active': True,
            },
            {
                'name': 'Sarah Johnson',
                'email': 'sarah.johnson@jhbfresh.co.za',
                'phone': '+27 11 555 1002',
                'position': 'Sales Representative',
                'is_primary': False,
                'is_active': True,
            },
            {
                'name': 'Mike Williams',
                'email': 'mike.williams@jhbfresh.co.za',
                'phone': '+27 11 555 1003',
                'position': 'Account Manager',
                'is_primary': False,
                'is_active': True,
            },
        ]

        created_suppliers = []
        
        with transaction.atomic():
            # Create the supplier
            supplier, created = Supplier.objects.get_or_create(
                name=supplier_data['name'],
                defaults=supplier_data
            )
            
            if created:
                self.stdout.write(f'Created supplier: {supplier.name}')
                
                # Create multiple sales reps for the supplier
                for rep_data in sales_reps_data:
                    sales_rep = SalesRep.objects.create(
                        supplier=supplier,
                        name=rep_data['name'],
                        email=rep_data['email'],
                        phone=rep_data['phone'],
                        position=rep_data['position'],
                        is_primary=rep_data['is_primary'],
                        is_active=rep_data['is_active'],
                    )
                    self.stdout.write(f'  Created sales rep: {sales_rep.name} ({sales_rep.position})')
                    
            created_suppliers.append(supplier)

        # Create sample price lists
        self.create_sample_price_lists(created_suppliers)

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully imported {len(created_suppliers)} supplier with {len(sales_reps_data)} sales reps and sample price lists'
            )
        )

    def create_sample_products(self):
        """Create sample products based on the WhatsApp messages"""
        # Get or create departments
        departments_data = [
            {'name': 'Vegetables', 'description': 'Fresh vegetables'},
            {'name': 'Fruits', 'description': 'Fresh fruits'},
            {'name': 'Herbs', 'description': 'Fresh herbs and spices'},
            {'name': 'Mushrooms', 'description': 'Fresh mushrooms'},
        ]
        
        departments = {}
        for dept_data in departments_data:
            dept, created = Department.objects.get_or_create(
                name=dept_data['name'],
                defaults={'description': dept_data['description']}
            )
            departments[dept_data['name']] = dept
            if created:
                self.stdout.write(f'Created department: {dept.name}')

        # Sample products based on WhatsApp messages
        products_data = [
            # Vegetables
            {'name': 'Tomatoes', 'department': 'Vegetables', 'unit': 'kg', 'price': 25.00},
            {'name': 'Onions', 'department': 'Vegetables', 'unit': 'kg', 'price': 18.00},
            {'name': 'Red Onions', 'department': 'Vegetables', 'unit': 'kg', 'price': 22.00},
            {'name': 'White Onions', 'department': 'Vegetables', 'unit': 'kg', 'price': 20.00},
            {'name': 'Spring Onions', 'department': 'Vegetables', 'unit': 'kg', 'price': 35.00},
            {'name': 'Potatoes', 'department': 'Vegetables', 'unit': 'kg', 'price': 15.00},
            {'name': 'Sweet Potatoes', 'department': 'Vegetables', 'unit': 'kg', 'price': 28.00},
            {'name': 'Carrots', 'department': 'Vegetables', 'unit': 'kg', 'price': 20.00},
            {'name': 'Baby Marrow', 'department': 'Vegetables', 'unit': 'kg', 'price': 30.00},
            {'name': 'Cucumber', 'department': 'Vegetables', 'unit': 'each', 'price': 8.00},
            {'name': 'Red Peppers', 'department': 'Vegetables', 'unit': 'kg', 'price': 45.00},
            {'name': 'Green Peppers', 'department': 'Vegetables', 'unit': 'kg', 'price': 40.00},
            {'name': 'Red Chillies', 'department': 'Vegetables', 'unit': 'kg', 'price': 80.00},
            {'name': 'Green Chillies', 'department': 'Vegetables', 'unit': 'kg', 'price': 75.00},
            {'name': 'Broccoli', 'department': 'Vegetables', 'unit': 'head', 'price': 25.00},
            {'name': 'Cauliflower', 'department': 'Vegetables', 'unit': 'head', 'price': 30.00},
            {'name': 'Cabbage', 'department': 'Vegetables', 'unit': 'head', 'price': 20.00},
            {'name': 'Red Cabbage', 'department': 'Vegetables', 'unit': 'head', 'price': 25.00},
            {'name': 'Spinach', 'department': 'Vegetables', 'unit': 'kg', 'price': 35.00},
            {'name': 'Deveined Spinach', 'department': 'Vegetables', 'unit': 'kg', 'price': 45.00},
            {'name': 'Mixed Lettuce', 'department': 'Vegetables', 'unit': 'kg', 'price': 40.00},
            {'name': 'Iceberg Lettuce', 'department': 'Vegetables', 'unit': 'head', 'price': 18.00},
            {'name': 'Rocket', 'department': 'Vegetables', 'unit': 'kg', 'price': 120.00},
            {'name': 'Baby Corn', 'department': 'Vegetables', 'unit': 'punnet', 'price': 15.00},
            {'name': 'Cherry Tomatoes', 'department': 'Vegetables', 'unit': 'punnet', 'price': 20.00},
            {'name': 'Cocktail Tomatoes', 'department': 'Vegetables', 'unit': 'punnet', 'price': 18.00},
            {'name': 'Beetroot', 'department': 'Vegetables', 'unit': 'kg', 'price': 25.00},
            {'name': 'Butternut', 'department': 'Vegetables', 'unit': 'kg', 'price': 22.00},
            
            # Fruits
            {'name': 'Bananas', 'department': 'Fruits', 'unit': 'kg', 'price': 20.00},
            {'name': 'Lemons', 'department': 'Fruits', 'unit': 'kg', 'price': 30.00},
            {'name': 'Pineapple', 'department': 'Fruits', 'unit': 'each', 'price': 35.00},
            {'name': 'Strawberries', 'department': 'Fruits', 'unit': 'punnet', 'price': 25.00},
            {'name': 'Grapes', 'department': 'Fruits', 'unit': 'kg', 'price': 60.00},
            {'name': 'Green Grapes', 'department': 'Fruits', 'unit': 'punnet', 'price': 35.00},
            {'name': 'Red Grapes', 'department': 'Fruits', 'unit': 'punnet', 'price': 35.00},
            {'name': 'Avocados', 'department': 'Fruits', 'unit': 'each', 'price': 12.00},
            {'name': 'Red Apples', 'department': 'Fruits', 'unit': 'kg', 'price': 35.00},
            {'name': 'Green Apples', 'department': 'Fruits', 'unit': 'kg', 'price': 35.00},
            {'name': 'Oranges', 'department': 'Fruits', 'unit': 'kg', 'price': 25.00},
            {'name': 'Naartjies', 'department': 'Fruits', 'unit': 'kg', 'price': 30.00},
            {'name': 'Sweet Melon', 'department': 'Fruits', 'unit': 'each', 'price': 40.00},
            {'name': 'Water Melon', 'department': 'Fruits', 'unit': 'each', 'price': 50.00},
            {'name': 'Paw Paw', 'department': 'Fruits', 'unit': 'each', 'price': 25.00},
            {'name': 'Grapefruit', 'department': 'Fruits', 'unit': 'kg', 'price': 28.00},
            
            # Herbs
            {'name': 'Parsley', 'department': 'Herbs', 'unit': 'bunch', 'price': 8.00},
            {'name': 'Mint', 'department': 'Herbs', 'unit': 'bunch', 'price': 10.00},
            {'name': 'Rosemary', 'department': 'Herbs', 'unit': 'bunch', 'price': 12.00},
            {'name': 'Thyme', 'department': 'Herbs', 'unit': 'bunch', 'price': 12.00},
            {'name': 'Dill', 'department': 'Herbs', 'unit': 'bunch', 'price': 15.00},
            {'name': 'Basil', 'department': 'Herbs', 'unit': 'bunch', 'price': 15.00},
            {'name': 'Coriander', 'department': 'Herbs', 'unit': 'bunch', 'price': 8.00},
            {'name': 'Micro Herbs', 'department': 'Herbs', 'unit': 'packet', 'price': 25.00},
            {'name': 'Turmeric', 'department': 'Herbs', 'unit': 'kg', 'price': 150.00},
            
            # Mushrooms
            {'name': 'Brown Mushrooms', 'department': 'Mushrooms', 'unit': 'kg', 'price': 80.00},
            {'name': 'Portabellini Mushrooms', 'department': 'Mushrooms', 'unit': 'kg', 'price': 90.00},
            {'name': 'Button Mushrooms', 'department': 'Mushrooms', 'unit': 'kg', 'price': 70.00},
        ]

        created_count = 0
        for product_data in products_data:
            product, created = Product.objects.get_or_create(
                name=product_data['name'],
                defaults={
                    'department': departments[product_data['department']],
                    'unit': product_data['unit'],
                    'price': Decimal(str(product_data['price'])),
                    'is_active': True,
                }
            )
            if created:
                created_count += 1

        self.stdout.write(f'Created {created_count} sample products')

    def create_sample_price_lists(self, suppliers):
        """Create sample price lists with items"""
        # Sample price list items based on the images provided
        sample_items = [
            # BT category (Beetroot/Root vegetables)
            {'code': 'BT001', 'description': 'Beetroot 5kg', 'category': 'BT', 'qty': 10, 'price': 25.00},
            {'code': 'BT002', 'description': 'Carrots 10kg', 'category': 'BT', 'qty': 15, 'price': 20.00},
            {'code': 'BT003', 'description': 'Potatoes 25kg bag', 'category': 'BT', 'qty': 8, 'price': 15.00},
            
            # FRE category (Fresh vegetables)
            {'code': 'FRE001', 'description': 'Tomatoes 5kg', 'category': 'FRE', 'qty': 20, 'price': 25.00},
            {'code': 'FRE002', 'description': 'Onions white 10kg', 'category': 'FRE', 'qty': 12, 'price': 18.00},
            {'code': 'FRE003', 'description': 'Red onions 5kg', 'category': 'FRE', 'qty': 15, 'price': 22.00},
            {'code': 'FRE004', 'description': 'Cucumber each', 'category': 'FRE', 'qty': 50, 'price': 8.00},
            {'code': 'FRE005', 'description': 'Baby marrow 2kg', 'category': 'FRE', 'qty': 25, 'price': 30.00},
            {'code': 'FRE006', 'description': 'Red peppers 3kg', 'category': 'FRE', 'qty': 18, 'price': 45.00},
            {'code': 'FRE007', 'description': 'Green peppers 3kg', 'category': 'FRE', 'qty': 20, 'price': 40.00},
            {'code': 'FRE008', 'description': 'Broccoli head', 'category': 'FRE', 'qty': 30, 'price': 25.00},
            {'code': 'FRE009', 'description': 'Cauliflower head', 'category': 'FRE', 'qty': 25, 'price': 30.00},
            
            # NVL category (Novelty/Specialty items)
            {'code': 'NVL001', 'description': 'Cherry tomatoes punnet', 'category': 'NVL', 'qty': 40, 'price': 20.00},
            {'code': 'NVL002', 'description': 'Baby corn punnet', 'category': 'NVL', 'qty': 35, 'price': 15.00},
            {'code': 'NVL003', 'description': 'Mixed lettuce 1kg', 'category': 'NVL', 'qty': 20, 'price': 40.00},
            {'code': 'NVL004', 'description': 'Rocket 500g', 'category': 'NVL', 'qty': 15, 'price': 60.00},
            {'code': 'NVL005', 'description': 'Spinach deveined 2kg', 'category': 'NVL', 'qty': 12, 'price': 45.00},
            
            # PRO category (Produce/Fruits)
            {'code': 'PRO001', 'description': 'Bananas 5kg', 'category': 'PRO', 'qty': 25, 'price': 20.00},
            {'code': 'PRO002', 'description': 'Lemons 10kg', 'category': 'PRO', 'qty': 15, 'price': 30.00},
            {'code': 'PRO003', 'description': 'Pineapple each', 'category': 'PRO', 'qty': 20, 'price': 35.00},
            {'code': 'PRO004', 'description': 'Strawberries punnet', 'category': 'PRO', 'qty': 30, 'price': 25.00},
            {'code': 'PRO005', 'description': 'Avocados box 20 pieces', 'category': 'PRO', 'qty': 10, 'price': 240.00},
            {'code': 'PRO006', 'description': 'Red apples 5kg', 'category': 'PRO', 'qty': 18, 'price': 35.00},
            {'code': 'PRO007', 'description': 'Green grapes punnet', 'category': 'PRO', 'qty': 25, 'price': 35.00},
            
            # HRB category (Herbs)
            {'code': 'HRB001', 'description': 'Parsley bunch', 'category': 'HRB', 'qty': 50, 'price': 8.00},
            {'code': 'HRB002', 'description': 'Mint bunch', 'category': 'HRB', 'qty': 40, 'price': 10.00},
            {'code': 'HRB003', 'description': 'Rosemary bunch', 'category': 'HRB', 'qty': 30, 'price': 12.00},
            {'code': 'HRB004', 'description': 'Thyme bunch', 'category': 'HRB', 'qty': 25, 'price': 12.00},
            {'code': 'HRB005', 'description': 'Dill bunch', 'category': 'HRB', 'qty': 20, 'price': 15.00},
            {'code': 'HRB006', 'description': 'Basil bunch', 'category': 'HRB', 'qty': 30, 'price': 15.00},
            {'code': 'HRB007', 'description': 'Micro herbs packet', 'category': 'HRB', 'qty': 15, 'price': 25.00},
            
            # MSH category (Mushrooms)
            {'code': 'MSH001', 'description': 'Brown mushrooms 7kg', 'category': 'MSH', 'qty': 8, 'price': 80.00},
            {'code': 'MSH002', 'description': 'Portabellini mushrooms 7kg', 'category': 'MSH', 'qty': 6, 'price': 90.00},
            {'code': 'MSH003', 'description': 'Button mushrooms 5kg', 'category': 'MSH', 'qty': 10, 'price': 70.00},
        ]

        for supplier in suppliers:
            # Create a price list for the supplier
            price_list = SupplierPriceList.objects.create(
                supplier=supplier,
                list_date=date.today(),
                file_reference=f'Sample price list for {supplier.name}',
                is_processed=False,
                notes=f'Sample price list data for testing - {supplier.name}',
            )
            
            # Add random selection of items to the price list
            selected_items = random.sample(sample_items, min(len(sample_items), random.randint(20, 30)))
            
            for item_data in selected_items:
                # Add some price variation
                price_variation = random.uniform(0.9, 1.1)
                adjusted_price = Decimal(str(item_data['price'])) * Decimal(str(price_variation))
                
                # Calculate VAT (15%)
                vat_amount = adjusted_price * Decimal('0.15')
                total_excl_vat = adjusted_price * item_data['qty']
                total_incl_vat = total_excl_vat + (vat_amount * item_data['qty'])
                
                SupplierPriceListItem.objects.create(
                    price_list=price_list,
                    supplier_code=item_data['code'],
                    product_description=item_data['description'],
                    category_code=item_data['category'],
                    quantity=item_data['qty'],
                    unit_price=adjusted_price,
                    vat_amount=vat_amount,
                    total_excl_vat=total_excl_vat,
                    total_incl_vat=total_incl_vat,
                    is_new_product=False,
                    needs_review=False,
                )
            
            self.stdout.write(f'Created price list for {supplier.name} with {len(selected_items)} items')
