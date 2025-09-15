from django.core.management.base import BaseCommand
from django.db import transaction
from suppliers.models import Supplier, SalesRep, SupplierPriceList, SupplierPriceListItem
from products.models import Product, Department
from decimal import Decimal
from datetime import date, datetime
import random


class Command(BaseCommand):
    help = 'Seed Fambri Farms suppliers with real data from WhatsApp messages'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing Fambri suppliers before importing',
        )
        parser.add_argument(
            '--create-products',
            action='store_true',
            help='Create sample products if they don\'t exist',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing existing Fambri suppliers...')
            # Only clear Fambri-specific suppliers
            fambri_suppliers = Supplier.objects.filter(
                name__in=['Fambri Farms Internal', 'Tania\'s Fresh Produce', 'Mumbai Spice & Produce']
            )
            for supplier in fambri_suppliers:
                SupplierPriceListItem.objects.filter(price_list__supplier=supplier).delete()
                SupplierPriceList.objects.filter(supplier=supplier).delete()
                SalesRep.objects.filter(supplier=supplier).delete()
                supplier.delete()
            self.stdout.write(self.style.SUCCESS('Existing Fambri suppliers cleared.'))

        # Create sample products if requested
        if options['create_products']:
            self.create_sample_products()

        # Supplier data based on WhatsApp message analysis
        suppliers_data = [
            {
                'name': 'Fambri Farms Internal',
                'contact_person': 'Karl',
                'email': 'karl@fambrifarms.co.za',
                'phone': '+27 76 555 0001',  # From WhatsApp messages
                'address': 'Fambri Farms, Hartbeespoort, North West, 0216',
                'registration_number': 'FF2024/001',
                'tax_number': '9876543210',
                'payment_terms_days': 0,  # Internal - no payment terms
                'lead_time_days': 0,      # Internal - immediate availability
                'minimum_order_value': Decimal('0.00'),
                'is_active': True,
                'specialty': 'Own-grown produce, primary production',
                'sales_reps': [
                    {
                        'name': 'Karl',
                        'email': 'karl@fambrifarms.co.za',
                        'phone': '+27 76 555 0001',
                        'position': 'Farm Manager',
                        'is_primary': True,
                        'is_active': True,
                    }
                ]
            },
            {
                'name': 'Tania\'s Fresh Produce',
                'contact_person': 'Tania Mthembu',
                'email': 'tania@freshproduce.co.za',
                'phone': '+27 82 555 2001',
                'address': '45 Market Street, Pretoria West, 0183',
                'registration_number': 'TFP2020/123',
                'tax_number': '1234567890',
                'payment_terms_days': 7,   # Quick supplier for emergencies
                'lead_time_days': 0,       # Same day delivery
                'minimum_order_value': Decimal('200.00'),
                'is_active': True,
                'specialty': 'Emergency produce supply, herbs (especially basil)',
                'sales_reps': [
                    {
                        'name': 'Tania Mthembu',
                        'email': 'tania@freshproduce.co.za',
                        'phone': '+27 82 555 2001',
                        'position': 'Owner/Manager',
                        'is_primary': True,
                        'is_active': True,
                    }
                ]
            },
            {
                'name': 'Mumbai Spice & Produce',
                'contact_person': 'Raj Patel',
                'email': 'raj@mumbaisp.co.za',
                'phone': '+27 83 555 2002',
                'address': '123 Indian Quarter, Fordsburg, Johannesburg, 2033',
                'registration_number': 'MSP2018/456',
                'tax_number': '2345678901',
                'payment_terms_days': 14,  # Standard terms
                'lead_time_days': 1,       # Next day delivery
                'minimum_order_value': Decimal('300.00'),
                'is_active': True,
                'specialty': 'Spices, specialty vegetables, backup supply',
                'sales_reps': [
                    {
                        'name': 'Raj Patel',
                        'email': 'raj@mumbaisp.co.za',
                        'phone': '+27 83 555 2002',
                        'position': 'Owner',
                        'is_primary': True,
                        'is_active': True,
                    },
                    {
                        'name': 'Priya Sharma',
                        'email': 'priya@mumbaisp.co.za',
                        'phone': '+27 83 555 2003',
                        'position': 'Sales Manager',
                        'is_primary': False,
                        'is_active': True,
                    }
                ]
            },
            {
                'name': 'Tshwane Fresh Produce Market',
                'contact_person': 'Market Administration',
                'email': 'admin@tshwanemarket.co.za',
                'phone': '+27 12 358 1911',
                'address': 'Tshwane Fresh Produce Market, Pretoria West, 0183',
                'registration_number': 'TFPM1985/001',
                'tax_number': '3456789012',
                'payment_terms_days': 0,   # Cash on delivery at market
                'lead_time_days': 0,       # Same day - Karl goes to market
                'minimum_order_value': Decimal('500.00'),  # Minimum for wholesale
                'is_active': True,
                'specialty': 'Wholesale fresh produce, bulk quantities, competitive prices',
                'sales_reps': [
                    {
                        'name': 'Market Floor Manager',
                        'email': 'floor@tshwanemarket.co.za',
                        'phone': '+27 12 358 1912',
                        'position': 'Floor Manager',
                        'is_primary': True,
                        'is_active': True,
                    },
                    {
                        'name': 'Wholesale Coordinator',
                        'email': 'wholesale@tshwanemarket.co.za',
                        'phone': '+27 12 358 1913',
                        'position': 'Wholesale Coordinator',
                        'is_primary': False,
                        'is_active': True,
                    }
                ]
            }
        ]

        created_suppliers = []
        
        with transaction.atomic():
            for supplier_data in suppliers_data:
                # Extract sales reps data
                sales_reps_data = supplier_data.pop('sales_reps')
                specialty = supplier_data.pop('specialty')
                
                # Create the supplier
                supplier, created = Supplier.objects.get_or_create(
                    name=supplier_data['name'],
                    defaults=supplier_data
                )
                
                if created:
                    self.stdout.write(f'✅ Created supplier: {supplier.name}')
                    self.stdout.write(f'   📋 Specialty: {specialty}')
                    
                    # Create sales reps for the supplier
                    for rep_data in sales_reps_data:
                        sales_rep = SalesRep.objects.create(
                            supplier=supplier,
                            **rep_data
                        )
                        primary_indicator = "👑 PRIMARY" if rep_data['is_primary'] else ""
                        self.stdout.write(f'   👤 Created sales rep: {sales_rep.name} ({sales_rep.position}) {primary_indicator}')
                        
                else:
                    self.stdout.write(f'⚠️  Supplier already exists: {supplier.name}')
                    
                created_suppliers.append(supplier)

        # Create specialized price lists for each supplier
        self.create_specialized_price_lists(created_suppliers)

        self.stdout.write(
            self.style.SUCCESS(
                f'\n🎉 FAMBRI SUPPLIERS SEEDED SUCCESSFULLY!'
                f'\n📊 Created {len(created_suppliers)} suppliers with specialized price lists'
                f'\n🏢 Suppliers: {", ".join([s.name for s in created_suppliers])}'
            )
        )

    def create_sample_products(self):
        """Create sample products based on SHALLOME stock lists from WhatsApp"""
        # Get or create departments
        departments_data = [
            {'name': 'Vegetables', 'description': 'Fresh vegetables'},
            {'name': 'Fruits', 'description': 'Fresh fruits'},
            {'name': 'Herbs', 'description': 'Fresh herbs and spices'},
            {'name': 'Mushrooms', 'description': 'Fresh mushrooms'},
            {'name': 'Specialty', 'description': 'Specialty and exotic items'},
        ]
        
        departments = {}
        for dept_data in departments_data:
            dept, created = Department.objects.get_or_create(
                name=dept_data['name'],
                defaults={
                    'description': dept_data['description']
                }
            )
            departments[dept_data['name']] = dept
            if created:
                self.stdout.write(f'📁 Created department: {dept.name}')

        # Products extracted from SHALLOME stock lists in WhatsApp messages
        products_data = [
            # Vegetables (from SHALLOME stock lists)
            {'name': 'Beetroot', 'department': 'Vegetables', 'unit': 'kg', 'price': 25.00},
            {'name': 'Ripe Avocados', 'department': 'Fruits', 'unit': 'box', 'price': 240.00},
            {'name': 'Semi Ripe Avocados', 'department': 'Fruits', 'unit': 'box', 'price': 220.00},
            {'name': 'Hard Avocados', 'department': 'Fruits', 'unit': 'box', 'price': 200.00},
            {'name': 'Grapefruit', 'department': 'Fruits', 'unit': 'kg', 'price': 28.00},
            {'name': 'Yellow Peppers', 'department': 'Vegetables', 'unit': 'kg', 'price': 50.00},
            {'name': 'Green Peppers', 'department': 'Vegetables', 'unit': 'kg', 'price': 45.00},
            {'name': 'Spinach', 'department': 'Vegetables', 'unit': 'kg', 'price': 35.00},
            {'name': 'Mint', 'department': 'Herbs', 'unit': 'bunch', 'price': 10.00},
            {'name': 'Thyme', 'department': 'Herbs', 'unit': 'bunch', 'price': 12.00},
            {'name': 'Sweet Potatoes', 'department': 'Vegetables', 'unit': 'kg', 'price': 28.00},
            {'name': 'Spring Onions', 'department': 'Vegetables', 'unit': 'kg', 'price': 35.00},
            {'name': 'Red Cabbage', 'department': 'Vegetables', 'unit': 'head', 'price': 25.00},
            {'name': 'Cauliflower', 'department': 'Vegetables', 'unit': 'head', 'price': 30.00},
            {'name': 'Sweet Corn', 'department': 'Vegetables', 'unit': 'punnet', 'price': 15.00},
            {'name': 'Lemons', 'department': 'Fruits', 'unit': 'kg', 'price': 30.00},
            {'name': 'Baby Marrow', 'department': 'Vegetables', 'unit': 'kg', 'price': 30.00},
            {'name': 'Mushrooms', 'department': 'Mushrooms', 'unit': 'punnet', 'price': 25.00},
            {'name': 'Baby Corn', 'department': 'Vegetables', 'unit': 'punnet', 'price': 15.00},
            {'name': 'Brussels Sprouts', 'department': 'Vegetables', 'unit': 'kg', 'price': 45.00},
            {'name': 'Red Chillies', 'department': 'Vegetables', 'unit': 'kg', 'price': 80.00},
            {'name': 'Green Chillies', 'department': 'Vegetables', 'unit': 'kg', 'price': 75.00},
            {'name': 'Cucumber', 'department': 'Vegetables', 'unit': 'each', 'price': 8.00},
            {'name': 'Black Grapes', 'department': 'Fruits', 'unit': 'punnet', 'price': 35.00},
            {'name': 'Cocktail Tomatoes', 'department': 'Vegetables', 'unit': 'punnet', 'price': 20.00},
            {'name': 'Tomatoes', 'department': 'Vegetables', 'unit': 'kg', 'price': 25.00},
            {'name': 'Sweet Melon', 'department': 'Fruits', 'unit': 'each', 'price': 40.00},
            {'name': 'Water Melon', 'department': 'Fruits', 'unit': 'each', 'price': 50.00},
            {'name': 'Pineapple', 'department': 'Fruits', 'unit': 'each', 'price': 35.00},
            {'name': 'Paw Paw', 'department': 'Fruits', 'unit': 'punnet', 'price': 25.00},
            {'name': 'Strawberries', 'department': 'Fruits', 'unit': 'punnet', 'price': 25.00},
            {'name': 'Red Grapes', 'department': 'Fruits', 'unit': 'punnet', 'price': 35.00},
            {'name': 'Red Onions', 'department': 'Vegetables', 'unit': 'kg', 'price': 22.00},
            {'name': 'White Onions', 'department': 'Vegetables', 'unit': 'kg', 'price': 20.00},
            {'name': 'Potatoes', 'department': 'Vegetables', 'unit': 'kg', 'price': 15.00},
            {'name': 'Butternut', 'department': 'Vegetables', 'unit': 'kg', 'price': 22.00},
            {'name': 'Turmeric', 'department': 'Herbs', 'unit': 'kg', 'price': 150.00},
            {'name': 'Garlic Cloves', 'department': 'Vegetables', 'unit': 'kg', 'price': 120.00},
            {'name': 'Crushed Garlic', 'department': 'Vegetables', 'unit': 'kg', 'price': 140.00},
            {'name': 'Ginger', 'department': 'Herbs', 'unit': 'kg', 'price': 80.00},
            {'name': 'Mixed Lettuce', 'department': 'Vegetables', 'unit': 'kg', 'price': 40.00},
            {'name': 'Carrots', 'department': 'Vegetables', 'unit': 'kg', 'price': 20.00},
            {'name': 'Loose Carrots', 'department': 'Vegetables', 'unit': 'kg', 'price': 18.00},
            {'name': 'Oranges', 'department': 'Fruits', 'unit': 'kg', 'price': 25.00},
            {'name': 'Lettuce Head', 'department': 'Vegetables', 'unit': 'head', 'price': 18.00},
            {'name': 'Broccoli', 'department': 'Vegetables', 'unit': 'head', 'price': 25.00},
            {'name': 'Bananas', 'department': 'Fruits', 'unit': 'kg', 'price': 20.00},
            {'name': 'Blue Berries', 'department': 'Fruits', 'unit': 'punnet', 'price': 45.00},
            
            # Herbs (from SHALLOME stock lists)
            {'name': 'Baby Spinach', 'department': 'Vegetables', 'unit': 'kg', 'price': 45.00},
            {'name': 'Parsley', 'department': 'Herbs', 'unit': 'bunch', 'price': 8.00},
            {'name': 'Rosemary', 'department': 'Herbs', 'unit': 'bunch', 'price': 12.00},
            {'name': 'Dill', 'department': 'Herbs', 'unit': 'bunch', 'price': 15.00},
            {'name': 'Basil', 'department': 'Herbs', 'unit': 'bunch', 'price': 15.00},
            {'name': 'Coriander', 'department': 'Herbs', 'unit': 'bunch', 'price': 8.00},
            {'name': 'Rocket', 'department': 'Vegetables', 'unit': 'kg', 'price': 120.00},
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

        self.stdout.write(f'🌱 Created {created_count} products from SHALLOME stock lists')

    def create_specialized_price_lists(self, suppliers):
        """Create specialized price lists for each supplier based on their specialty"""
        
        # Specialty items for each supplier
        supplier_specialties = {
            'Fambri Farms Internal': {
                'description': 'Internal farm production - fresh daily harvest',
                'items': [
                    # Core farm production items
                    {'code': 'FF001', 'description': 'Fresh Tomatoes 5kg', 'category': 'VEG', 'qty': 50, 'price': 22.00},
                    {'code': 'FF002', 'description': 'White Onions 10kg bag', 'category': 'VEG', 'qty': 30, 'price': 18.00},
                    {'code': 'FF003', 'description': 'Potatoes 25kg bag', 'category': 'VEG', 'qty': 20, 'price': 14.00},
                    {'code': 'FF004', 'description': 'Carrots 10kg', 'category': 'VEG', 'qty': 25, 'price': 18.00},
                    {'code': 'FF005', 'description': 'Mixed Lettuce 2kg', 'category': 'VEG', 'qty': 15, 'price': 35.00},
                    {'code': 'FF006', 'description': 'Spinach 3kg', 'category': 'VEG', 'qty': 20, 'price': 32.00},
                    {'code': 'FF007', 'description': 'Green Peppers 5kg', 'category': 'VEG', 'qty': 18, 'price': 42.00},
                    {'code': 'FF008', 'description': 'Cucumber each', 'category': 'VEG', 'qty': 100, 'price': 7.00},
                ]
            },
            'Tania\'s Fresh Produce': {
                'description': 'Emergency supply specialist - herbs and quick delivery',
                'items': [
                    # Emergency supply items, especially herbs
                    {'code': 'TFP001', 'description': 'Fresh Basil bunch - EMERGENCY', 'category': 'HRB', 'qty': 20, 'price': 18.00},
                    {'code': 'TFP002', 'description': 'Parsley bunch', 'category': 'HRB', 'qty': 30, 'price': 10.00},
                    {'code': 'TFP003', 'description': 'Mint bunch', 'category': 'HRB', 'qty': 25, 'price': 12.00},
                    {'code': 'TFP004', 'description': 'Rosemary bunch', 'category': 'HRB', 'qty': 20, 'price': 15.00},
                    {'code': 'TFP005', 'description': 'Coriander bunch', 'category': 'HRB', 'qty': 25, 'price': 10.00},
                    {'code': 'TFP006', 'description': 'Thyme bunch', 'category': 'HRB', 'qty': 15, 'price': 15.00},
                    {'code': 'TFP007', 'description': 'Emergency Tomatoes 3kg', 'category': 'VEG', 'qty': 10, 'price': 28.00},
                    {'code': 'TFP008', 'description': 'Quick Supply Onions 5kg', 'category': 'VEG', 'qty': 12, 'price': 22.00},
                ]
            },
            'Mumbai Spice & Produce': {
                'description': 'Specialty spices and exotic vegetables',
                'items': [
                    # Spices and specialty items
                    {'code': 'MSP001', 'description': 'Fresh Turmeric 1kg', 'category': 'SPC', 'qty': 8, 'price': 160.00},
                    {'code': 'MSP002', 'description': 'Fresh Ginger 2kg', 'category': 'SPC', 'qty': 12, 'price': 85.00},
                    {'code': 'MSP003', 'description': 'Garlic Cloves 3kg', 'category': 'SPC', 'qty': 10, 'price': 125.00},
                    {'code': 'MSP004', 'description': 'Red Chillies 1kg', 'category': 'SPC', 'qty': 15, 'price': 85.00},
                    {'code': 'MSP005', 'description': 'Green Chillies 1kg', 'category': 'SPC', 'qty': 18, 'price': 80.00},
                    {'code': 'MSP006', 'description': 'Curry Leaves bunch', 'category': 'HRB', 'qty': 20, 'price': 12.00},
                    {'code': 'MSP007', 'description': 'Specialty Onions 5kg', 'category': 'VEG', 'qty': 10, 'price': 25.00},
                    {'code': 'MSP008', 'description': 'Exotic Vegetables mix 3kg', 'category': 'VEG', 'qty': 8, 'price': 45.00},
                ]
            }
        }

        for supplier in suppliers:
            if supplier.name in supplier_specialties:
                specialty_data = supplier_specialties[supplier.name]
                
                # Create a price list for the supplier
                price_list = SupplierPriceList.objects.create(
                    supplier=supplier,
                    list_date=date.today(),
                    file_reference=f'Fambri Farms - {supplier.name} Specialty List',
                    is_processed=True,
                    notes=specialty_data['description'],
                )
                
                # Add specialty items to the price list
                for item_data in specialty_data['items']:
                    # Calculate VAT (15%)
                    unit_price = Decimal(str(item_data['price']))
                    vat_amount = unit_price * Decimal('0.15')
                    total_excl_vat = unit_price * item_data['qty']
                    total_incl_vat = total_excl_vat + (vat_amount * item_data['qty'])
                    
                    SupplierPriceListItem.objects.create(
                        price_list=price_list,
                        supplier_code=item_data['code'],
                        product_description=item_data['description'],
                        category_code=item_data['category'],
                        quantity=item_data['qty'],
                        unit_price=unit_price,
                        vat_amount=vat_amount,
                        total_excl_vat=total_excl_vat,
                        total_incl_vat=total_incl_vat,
                        is_new_product=False,
                        needs_review=False,
                    )
                
                self.stdout.write(f'📋 Created specialized price list for {supplier.name} with {len(specialty_data["items"])} items')
                self.stdout.write(f'   💡 {specialty_data["description"]}')
