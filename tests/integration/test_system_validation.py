"""
System validation test - demonstrates that the backend cleanup and seeding is working
"""

from django.test import TestCase
from django.core.management import call_command
from django.contrib.auth import get_user_model
from io import StringIO

from accounts.models import User, RestaurantProfile, FarmProfile
from products.models import Product, Department
from suppliers.models import Supplier
from inventory.models import UnitOfMeasure

User = get_user_model()


class SystemValidationTest(TestCase):
    """Validate that the cleaned up backend system works correctly"""
    
    def test_management_commands_exist(self):
        """Test that all our seeding commands exist and are callable"""
        
        commands_to_test = [
            'seed_fambri_users',
            'import_customers', 
            'seed_fambri_suppliers',
            'seed_fambri_units',
            'seed_fambri_products',
            'seed_fambri_pricing',
            'seed_fambri_orders',
            'seed_fambri_stock'
        ]
        
        for command in commands_to_test:
            with self.subTest(command=command):
                try:
                    # Test that command exists (this will fail if command doesn't exist)
                    call_command('help', command)
                    self.assertTrue(True, f"Command {command} exists")
                except Exception as e:
                    self.fail(f"Command {command} failed: {e}")

    def test_basic_seeding_workflow(self):
        """Test basic seeding workflow works"""
        
        # Capture output
        out = StringIO()
        
        # Test users seeding
        call_command('seed_fambri_users', stdout=out, verbosity=0)
        
        # Verify Karl exists
        karl = User.objects.filter(email='karl@fambrifarms.co.za').first()
        self.assertIsNotNone(karl, "Karl should be created")
        self.assertEqual(karl.user_type, 'farm_manager')
        
        # Verify Hazvinei exists
        hazvinei = User.objects.filter(email='hazvinei@fambrifarms.co.za').first()
        self.assertIsNotNone(hazvinei, "Hazvinei should be created")
        self.assertEqual(hazvinei.phone, '+27 61 674 9368')
        
        # Test units seeding
        call_command('seed_fambri_units', stdout=out, verbosity=0)
        
        units = UnitOfMeasure.objects.all()
        self.assertGreater(units.count(), 10, "Should have multiple units")
        
        # Test specific units
        kg_unit = UnitOfMeasure.objects.filter(abbreviation='kg').first()
        self.assertIsNotNone(kg_unit, "Kilogram unit should exist")
        self.assertTrue(kg_unit.is_weight, "Kilogram should be a weight unit")
        
        # Test products seeding
        call_command('seed_fambri_products', stdout=out, verbosity=0)
        
        departments = Department.objects.all()
        self.assertGreaterEqual(departments.count(), 5, "Should have 5+ departments")
        
        products = Product.objects.all()
        self.assertGreater(products.count(), 60, "Should have 60+ products")
        
        # Test specific products from SHALLOME data
        butternut = Product.objects.filter(name__icontains='Butternut').first()
        self.assertIsNotNone(butternut, "Butternut should exist")
        
        mixed_lettuce = Product.objects.filter(name__icontains='Mixed Lettuce').first()
        self.assertIsNotNone(mixed_lettuce, "Mixed Lettuce should exist")
        
        # Test suppliers seeding
        call_command('seed_fambri_suppliers', stdout=out, verbosity=0)
        
        suppliers = Supplier.objects.all()
        self.assertGreaterEqual(suppliers.count(), 3, "Should have 3+ suppliers")
        
        fambri_internal = Supplier.objects.filter(name__icontains='Fambri Farms Internal').first()
        self.assertIsNotNone(fambri_internal, "Fambri Internal should exist")
        self.assertEqual(fambri_internal.payment_terms_days, 0, "Internal supplier should have 0 payment terms")

    def test_whatsapp_data_preservation(self):
        """Test that WhatsApp data patterns are preserved"""
        
        # Seed the system
        call_command('seed_fambri_users', verbosity=0)
        call_command('import_customers', verbosity=0)
        call_command('seed_fambri_products', verbosity=0)
        
        # Test customer data from WhatsApp
        maltos = User.objects.filter(
            restaurantprofile__business_name__icontains='Maltos'
        ).first()
        self.assertIsNotNone(maltos, "Maltos should exist from WhatsApp data")
        
        # Test Sylvia (private customer)
        sylvia = User.objects.filter(first_name__icontains='Sylvia').first()
        self.assertIsNotNone(sylvia, "Sylvia should exist from WhatsApp data")
        self.assertEqual(sylvia.phone, '+27 73 621 2471', "Sylvia should have real WhatsApp number")
        
        # Test SHALLOME products
        shallome_products = [
            'Butternut', 'Mixed Lettuce', 'Lemons', 'Tomatoes', 
            'Broccoli', 'Cauliflower', 'Basil', 'Parsley'
        ]
        
        for product_name in shallome_products:
            product = Product.objects.filter(name__icontains=product_name).first()
            self.assertIsNotNone(product, f"{product_name} should exist from SHALLOME data")

    def test_file_organization(self):
        """Test that files are properly organized after cleanup"""
        
        import os
        
        # Test that test files are in proper locations
        backend_root = '/Users/jodybeggs/Documents/fambrifarms_after_meeting/backend'
        
        # These files should NOT be in backend root anymore
        old_test_files = [
            'test_company_assignment_scenarios.py',
            'test_integration.py', 
            'test_whatsapp_flow.py',
            'populate_units.py',
            'cleanup_pricing_rules.py'
        ]
        
        for filename in old_test_files:
            file_path = os.path.join(backend_root, filename)
            self.assertFalse(os.path.exists(file_path), 
                           f"{filename} should not be in backend root")
        
        # These directories should exist
        required_dirs = [
            'tests',
            'tests/integration',
            'tests/unit',
            'scripts/legacy'
        ]
        
        for dirname in required_dirs:
            dir_path = os.path.join(backend_root, dirname)
            self.assertTrue(os.path.exists(dir_path), 
                          f"{dirname} directory should exist")

    def test_units_system_completeness(self):
        """Test that the units system covers all WhatsApp order patterns"""
        
        call_command('seed_fambri_units', verbosity=0)
        
        # Units that appear in real WhatsApp orders
        required_units = [
            'kg',     # "30kg potato", "20kg red onion"
            'head',   # "10 heads broccoli", "10 heads cauliflower"  
            'box',    # "1 box tomatoes", "Arthur box x2"
            'bunch',  # "3-5 bunches parsley", "4-6 bunches mint"
            'punnet', # "4-6 punnets strawberries"
            'each',   # "8-15 cucumbers each"
            'bag',    # "3-6 bags potatoes"
            'g'       # "200g Parsley", "100g Chives"
        ]
        
        for unit_abbr in required_units:
            unit = UnitOfMeasure.objects.filter(abbreviation=unit_abbr).first()
            self.assertIsNotNone(unit, f"Unit {unit_abbr} should exist for WhatsApp orders")

    def test_system_performance(self):
        """Test that the system performs well with seeded data"""
        
        import time
        
        # Seed basic data
        call_command('seed_fambri_products', verbosity=0)
        call_command('seed_fambri_users', verbosity=0)
        
        # Test product query performance
        start_time = time.time()
        products = list(Product.objects.select_related('department').all())
        query_time = time.time() - start_time
        
        self.assertLess(query_time, 0.5, "Product queries should be fast")
        self.assertGreater(len(products), 50, "Should have loaded products")
        
        # Test user query performance
        start_time = time.time()
        users = list(User.objects.all())
        query_time = time.time() - start_time
        
        self.assertLess(query_time, 0.1, "User queries should be very fast")
        self.assertGreater(len(users), 5, "Should have loaded users")

    def test_data_integrity(self):
        """Test data integrity across the system"""
        
        # Seed the system
        call_command('seed_fambri_units', verbosity=0)
        call_command('seed_fambri_products', verbosity=0)
        call_command('seed_fambri_users', verbosity=0)
        
        # Test that all products have valid units
        products_without_units = Product.objects.filter(unit__isnull=True)
        self.assertEqual(products_without_units.count(), 0, "All products should have units")
        
        # Test that all products have valid departments
        products_without_departments = Product.objects.filter(department__isnull=True)
        self.assertEqual(products_without_departments.count(), 0, "All products should have departments")
        
        # Test that all products have positive prices
        products_with_zero_price = Product.objects.filter(price__lte=0)
        self.assertEqual(products_with_zero_price.count(), 0, "All products should have positive prices")
        
        # Test that farm profiles are properly linked
        karl = User.objects.filter(email='karl@fambrifarms.co.za').first()
        if karl:
            karl_profile = FarmProfile.objects.filter(user=karl).first()
            self.assertIsNotNone(karl_profile, "Karl should have a farm profile")
            self.assertTrue(karl_profile.can_manage_inventory, "Karl should be able to manage inventory")
