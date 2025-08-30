from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from products.models import Product, Department
from whatsapp.models import SalesRep
from datetime import date, timedelta

User = get_user_model()

class Command(BaseCommand):
    help = 'Set up test data for the new order system'

    def handle(self, *args, **options):
        self.stdout.write('Setting up test data...')
        
        # Create test products
        self.create_products()
        
        # Create sales reps
        self.create_sales_reps()
        
        # Create test restaurant user
        self.create_test_user()
        
        self.stdout.write(self.style.SUCCESS('Test data created successfully!'))

    def create_products(self):
        """Create basic products for testing"""
        # Create departments
        vegetables_dept, _ = Department.objects.get_or_create(
            name='Vegetables',
            defaults={'description': 'Fresh vegetables', 'color': '#16a34a'}
        )
        
        herbs_dept, _ = Department.objects.get_or_create(
            name='Herbs',
            defaults={'description': 'Fresh herbs', 'color': '#059669'}
        )
        
        # Create products
        products_data = [
            {
                'name': 'Red Onions',
                'department': vegetables_dept,
                'price': 45.00,
                'unit': 'kg',
                'common_names': ['onions', 'red onions', 'onion'],
                'typical_order_quantity': 5.0
            },
            {
                'name': 'Tomatoes',
                'department': vegetables_dept,
                'price': 38.00,
                'unit': 'kg',
                'common_names': ['tomatoes', 'tomato'],
                'typical_order_quantity': 3.0
            },
            {
                'name': 'Potatoes',
                'department': vegetables_dept,
                'price': 25.00,
                'unit': 'kg',
                'common_names': ['potatoes', 'potato', 'spuds'],
                'typical_order_quantity': 10.0
            },
            {
                'name': 'Carrots',
                'department': vegetables_dept,
                'price': 32.00,
                'unit': 'kg',
                'common_names': ['carrots', 'carrot'],
                'typical_order_quantity': 2.0
            },
            {
                'name': 'Fresh Coriander',
                'department': herbs_dept,
                'price': 15.00,
                'unit': 'bunch',
                'common_names': ['coriander', 'cilantro', 'dhania'],
                'typical_order_quantity': 5.0
            },
        ]
        
        for product_data in products_data:
            product, created = Product.objects.get_or_create(
                name=product_data['name'],
                defaults=product_data
            )
            if created:
                self.stdout.write(f'Created product: {product.name}')

    def create_sales_reps(self):
        """Create sales reps for Pretoria Market"""
        sales_reps_data = [
            {
                'name': 'John Smith',
                'phone_number': '+27123456789',
                'whatsapp_number': '+27123456789',
                'specialties': ['vegetables', 'general'],
            },
            {
                'name': 'Sarah Johnson',
                'phone_number': '+27987654321',
                'whatsapp_number': '+27987654321',
                'specialties': ['herbs', 'specialty_items'],
            }
        ]
        
        for rep_data in sales_reps_data:
            rep, created = SalesRep.objects.get_or_create(
                name=rep_data['name'],
                defaults=rep_data
            )
            if created:
                self.stdout.write(f'Created sales rep: {rep.name}')

    def create_test_user(self):
        """Create a test restaurant user"""
        if not User.objects.filter(email='test@restaurant.com').exists():
            user = User.objects.create_user(
                email='test@restaurant.com',
                password='testpass123',
                first_name='Test',
                last_name='Restaurant',
                user_type='restaurant'
            )
            self.stdout.write(f'Created test user: {user.email}')
        else:
            self.stdout.write('Test user already exists')
