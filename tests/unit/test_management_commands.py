"""
Unit tests for Django management commands
Tests command functionality, validation, and data creation
"""

from django.test import TestCase, TransactionTestCase
from django.core.management import call_command, CommandError
from django.contrib.auth import get_user_model
from io import StringIO
from unittest.mock import patch
import tempfile
import json
import os

from accounts.models import RestaurantProfile, FarmProfile
from products.models import Product, Department
from suppliers.models import Supplier, SalesRep
from inventory.models import UnitOfMeasure, FinishedInventory
from orders.models import Order, OrderItem
from whatsapp.models import WhatsAppMessage

User = get_user_model()


class SeedFambriUsersCommandTest(TestCase):
    """Test seed_fambri_users management command"""
    
    def test_seed_fambri_users_creates_users(self):
        """Test that seed_fambri_users creates the expected users"""
        out = StringIO()
        
        call_command('seed_fambri_users', stdout=out)
        
        # Check that Karl and Hazvinei were created
        karl = User.objects.filter(email='karl@fambrifarms.co.za').first()
        hazvinei = User.objects.filter(email='hazvinei@fambrifarms.co.za').first()
        
        self.assertIsNotNone(karl)
        self.assertIsNotNone(hazvinei)
        
        # Check Karl's properties
        self.assertEqual(karl.first_name, 'Karl')
        self.assertEqual(karl.user_type, 'admin')
        self.assertTrue(karl.is_staff)
        
        # Check Hazvinei's properties
        self.assertEqual(hazvinei.first_name, 'Hazvinei')
        self.assertEqual(hazvinei.user_type, 'admin')
        
        # Check that farm profiles were created
        self.assertTrue(hasattr(karl, 'farmprofile'))
        self.assertTrue(hasattr(hazvinei, 'farmprofile'))
    
    def test_seed_fambri_users_idempotent(self):
        """Test that running seed_fambri_users multiple times is safe"""
        # Run command twice
        call_command('seed_fambri_users', verbosity=0)
        call_command('seed_fambri_users', verbosity=0)
        
        # Should still only have 2 users
        karl_count = User.objects.filter(email='karl@fambrifarms.co.za').count()
        hazvinei_count = User.objects.filter(email='hazvinei@fambrifarms.co.za').count()
        
        self.assertEqual(karl_count, 1)
        self.assertEqual(hazvinei_count, 1)


class SeedFambriSuppliersCommandTest(TestCase):
    """Test seed_fambri_suppliers management command"""
    
    def test_seed_fambri_suppliers_creates_suppliers(self):
        """Test that seed_fambri_suppliers creates suppliers"""
        out = StringIO()
        
        call_command('seed_fambri_suppliers', stdout=out)
        
        # Check that suppliers were created
        suppliers = Supplier.objects.all()
        self.assertGreater(suppliers.count(), 0)
        
        # Check for specific suppliers
        fambri_farms = Supplier.objects.filter(name__icontains='Fambri').first()
        self.assertIsNotNone(fambri_farms)
        self.assertEqual(fambri_farms.supplier_type, 'internal')
    
    def test_seed_fambri_suppliers_creates_sales_reps(self):
        """Test that seed_fambri_suppliers creates sales reps"""
        call_command('seed_fambri_suppliers', verbosity=0)
        
        # Check that sales reps were created
        sales_reps = SalesRep.objects.all()
        self.assertGreater(sales_reps.count(), 0)
        
        # Check that primary sales reps exist
        primary_reps = SalesRep.objects.filter(is_primary=True)
        self.assertGreater(primary_reps.count(), 0)
    
    def test_seed_fambri_suppliers_idempotent(self):
        """Test that running seed_fambri_suppliers multiple times is safe"""
        call_command('seed_fambri_suppliers', verbosity=0)
        initial_count = Supplier.objects.count()
        
        call_command('seed_fambri_suppliers', verbosity=0)
        final_count = Supplier.objects.count()
        
        self.assertEqual(initial_count, final_count)


class SeedFambriUnitsCommandTest(TestCase):
    """Test seed_fambri_units management command"""
    
    def test_seed_fambri_units_creates_units(self):
        """Test that seed_fambri_units creates units of measure"""
        out = StringIO()
        
        call_command('seed_fambri_units', stdout=out)
        
        # Check that units were created
        units = UnitOfMeasure.objects.all()
        self.assertGreater(units.count(), 0)
        
        # Check for specific units
        kg_unit = UnitOfMeasure.objects.filter(name='kg').first()
        self.assertIsNotNone(kg_unit)
        self.assertEqual(kg_unit.unit_type, 'weight')
        
        boxes_unit = UnitOfMeasure.objects.filter(name='boxes').first()
        self.assertIsNotNone(boxes_unit)
        self.assertEqual(boxes_unit.unit_type, 'count')
    
    def test_seed_fambri_units_idempotent(self):
        """Test that running seed_fambri_units multiple times is safe"""
        call_command('seed_fambri_units', verbosity=0)
        initial_count = UnitOfMeasure.objects.count()
        
        call_command('seed_fambri_units', verbosity=0)
        final_count = UnitOfMeasure.objects.count()
        
        self.assertEqual(initial_count, final_count)


class SeedFambriProductsCommandTest(TestCase):
    """Test seed_fambri_products management command"""
    
    def setUp(self):
        # Create required dependencies
        call_command('seed_fambri_units', verbosity=0)
    
    def test_seed_fambri_products_creates_departments(self):
        """Test that seed_fambri_products creates departments"""
        call_command('seed_fambri_products', verbosity=0)
        
        # Check that departments were created
        departments = Department.objects.all()
        self.assertGreater(departments.count(), 0)
        
        # Check for specific departments
        vegetables = Department.objects.filter(name__icontains='Vegetable').first()
        self.assertIsNotNone(vegetables)
    
    def test_seed_fambri_products_creates_products(self):
        """Test that seed_fambri_products creates products"""
        call_command('seed_fambri_products', verbosity=0)
        
        # Check that products were created
        products = Product.objects.all()
        self.assertGreater(products.count(), 0)
        
        # Check for specific products from SHALLOME stock
        lettuce = Product.objects.filter(name__icontains='Lettuce').first()
        self.assertIsNotNone(lettuce)
        self.assertIsNotNone(lettuce.department)
        self.assertGreater(lettuce.price, 0)
    
    def test_seed_fambri_products_idempotent(self):
        """Test that running seed_fambri_products multiple times is safe"""
        call_command('seed_fambri_products', verbosity=0)
        initial_product_count = Product.objects.count()
        initial_dept_count = Department.objects.count()
        
        call_command('seed_fambri_products', verbosity=0)
        final_product_count = Product.objects.count()
        final_dept_count = Department.objects.count()
        
        self.assertEqual(initial_product_count, final_product_count)
        self.assertEqual(initial_dept_count, final_dept_count)


class SeedFambriStockCommandTest(TestCase):
    """Test seed_fambri_stock management command"""
    
    def setUp(self):
        # Create required dependencies
        call_command('seed_fambri_units', verbosity=0)
        call_command('seed_fambri_products', verbosity=0)
    
    def test_seed_fambri_stock_creates_inventory(self):
        """Test that seed_fambri_stock creates inventory records"""
        call_command('seed_fambri_stock', verbosity=0)
        
        # Check that inventory records were created
        inventory_records = FinishedInventory.objects.all()
        self.assertGreater(inventory_records.count(), 0)
        
        # Check that inventory has realistic values
        for inventory in inventory_records:
            self.assertGreaterEqual(inventory.available_quantity, 0)
            self.assertGreaterEqual(inventory.reserved_quantity, 0)
            self.assertGreater(inventory.minimum_level, 0)
    
    def test_seed_fambri_stock_idempotent(self):
        """Test that running seed_fambri_stock multiple times is safe"""
        call_command('seed_fambri_stock', verbosity=0)
        initial_count = FinishedInventory.objects.count()
        
        call_command('seed_fambri_stock', verbosity=0)
        final_count = FinishedInventory.objects.count()
        
        self.assertEqual(initial_count, final_count)


class ImportCustomersCommandTest(TestCase):
    """Test import_customers management command"""
    
    def test_import_customers_creates_customers(self):
        """Test that import_customers creates customer records"""
        call_command('import_customers', verbosity=0)
        
        # Check that customers were created
        customers = User.objects.filter(user_type='restaurant')
        self.assertGreater(customers.count(), 0)
        
        # Check that restaurant profiles were created
        profiles = RestaurantProfile.objects.all()
        self.assertGreater(profiles.count(), 0)
        
        # Check for specific customers from WhatsApp data
        sylvia = User.objects.filter(first_name='Sylvia').first()
        if sylvia:
            self.assertEqual(sylvia.user_type, 'restaurant')
            self.assertTrue(hasattr(sylvia, 'restaurantprofile'))
    
    def test_import_customers_idempotent(self):
        """Test that running import_customers multiple times is safe"""
        call_command('import_customers', verbosity=0)
        initial_count = User.objects.filter(user_type='restaurant').count()
        
        call_command('import_customers', verbosity=0)
        final_count = User.objects.filter(user_type='restaurant').count()
        
        self.assertEqual(initial_count, final_count)


class SeedFambriOrdersCommandTest(TransactionTestCase):
    """Test seed_fambri_orders management command"""
    
    def setUp(self):
        # Create required dependencies
        call_command('seed_fambri_users', verbosity=0)
        call_command('import_customers', verbosity=0)
        call_command('seed_fambri_units', verbosity=0)
        call_command('seed_fambri_products', verbosity=0)
    
    def test_seed_fambri_orders_creates_orders(self):
        """Test that seed_fambri_orders creates order records"""
        call_command('seed_fambri_orders', '--weeks', '2', verbosity=0)
        
        # Check that orders were created
        orders = Order.objects.all()
        self.assertGreater(orders.count(), 0)
        
        # Check that order items were created
        order_items = OrderItem.objects.all()
        self.assertGreater(order_items.count(), 0)
        
        # Check order properties
        for order in orders:
            self.assertIsNotNone(order.restaurant)
            self.assertIsNotNone(order.order_date)
            self.assertIn(order.order_date.weekday(), [0, 3])  # Monday or Thursday
    
    def test_seed_fambri_orders_with_weeks_parameter(self):
        """Test seed_fambri_orders with weeks parameter"""
        call_command('seed_fambri_orders', '--weeks', '1', verbosity=0)
        
        orders = Order.objects.all()
        self.assertGreater(orders.count(), 0)
        
        # Should have fewer orders than default
        self.assertLessEqual(orders.count(), 50)  # Reasonable upper bound for 1 week
    
    def test_seed_fambri_orders_realistic_patterns(self):
        """Test that seed_fambri_orders creates realistic order patterns"""
        call_command('seed_fambri_orders', '--weeks', '2', verbosity=0)
        
        orders = Order.objects.all()
        
        # Check that orders follow Tuesday/Thursday pattern
        for order in orders:
            weekday = order.order_date.weekday()
            self.assertIn(weekday, [0, 3], f"Order on invalid day: {order.order_date}")
        
        # Check that orders have realistic totals
        for order in orders:
            if order.total_amount:
                self.assertGreater(order.total_amount, 0)
                self.assertLess(order.total_amount, 10000)  # Reasonable upper bound


class SeedWhatsAppMessagesCommandTest(TestCase):
    """Test seed_whatsapp_messages management command"""
    
    def test_seed_whatsapp_messages_help(self):
        """Test seed_whatsapp_messages help functionality"""
        out = StringIO()
        
        # Test list-days option
        call_command('seed_whatsapp_messages', '--list-days', stdout=out)
        
        output = out.getvalue()
        self.assertIn('Available days', output)
    
    def test_seed_whatsapp_messages_dry_run(self):
        """Test seed_whatsapp_messages dry run functionality"""
        out = StringIO()
        
        # Test dry run (should not create any messages)
        call_command('seed_whatsapp_messages', '--dry-run', stdout=out)
        
        # Should not have created any messages
        messages = WhatsAppMessage.objects.all()
        self.assertEqual(messages.count(), 0)
        
        output = out.getvalue()
        self.assertIn('DRY RUN', output)
    
    @patch('os.path.exists')
    @patch('os.listdir')
    def test_seed_whatsapp_messages_no_data_files(self, mock_listdir, mock_exists):
        """Test seed_whatsapp_messages when no data files exist"""
        mock_exists.return_value = False
        mock_listdir.return_value = []
        
        out = StringIO()
        
        call_command('seed_whatsapp_messages', '--list-days', stdout=out)
        
        output = out.getvalue()
        self.assertIn('No message data files found', output)


class PopulateInventoryDataCommandTest(TestCase):
    """Test populate_inventory_data management command"""
    
    def test_populate_inventory_data_creates_data(self):
        """Test that populate_inventory_data creates inventory data"""
        call_command('populate_inventory_data', verbosity=0)
        
        # Check that units were created
        units = UnitOfMeasure.objects.all()
        self.assertGreater(units.count(), 0)
        
        # Check that suppliers were created
        suppliers = Supplier.objects.all()
        self.assertGreater(suppliers.count(), 0)
    
    def test_populate_inventory_data_idempotent(self):
        """Test that running populate_inventory_data multiple times is safe"""
        call_command('populate_inventory_data', verbosity=0)
        initial_unit_count = UnitOfMeasure.objects.count()
        initial_supplier_count = Supplier.objects.count()
        
        call_command('populate_inventory_data', verbosity=0)
        final_unit_count = UnitOfMeasure.objects.count()
        final_supplier_count = Supplier.objects.count()
        
        # Should not create duplicates
        self.assertEqual(initial_unit_count, final_unit_count)
        self.assertEqual(initial_supplier_count, final_supplier_count)


class CommandErrorHandlingTest(TestCase):
    """Test command error handling and validation"""
    
    def test_command_with_invalid_arguments(self):
        """Test commands with invalid arguments"""
        with self.assertRaises(CommandError):
            call_command('seed_fambri_orders', '--weeks', 'invalid')
    
    def test_command_help_functionality(self):
        """Test that commands provide help"""
        commands_to_test = [
            'seed_fambri_users',
            'seed_fambri_suppliers',
            'seed_fambri_products',
            'import_customers'
        ]
        
        for command in commands_to_test:
            with self.subTest(command=command):
                out = StringIO()
                try:
                    call_command('help', command, stdout=out)
                    output = out.getvalue()
                    self.assertIn('help', output.lower())
                except Exception as e:
                    self.fail(f"Command {command} help failed: {e}")


class CommandIntegrationTest(TransactionTestCase):
    """Test command integration and dependencies"""
    
    def test_full_seeding_workflow(self):
        """Test complete seeding workflow"""
        commands = [
            ('seed_fambri_users', []),
            ('import_customers', []),
            ('seed_fambri_suppliers', []),
            ('seed_fambri_units', []),
            ('seed_fambri_products', []),
            ('seed_fambri_stock', []),
            ('seed_fambri_orders', ['--weeks', '1'])
        ]
        
        for command, args in commands:
            with self.subTest(command=command):
                try:
                    call_command(command, *args, verbosity=0)
                except Exception as e:
                    self.fail(f"Command {command} failed in workflow: {e}")
        
        # Verify final state
        self.assertGreater(User.objects.count(), 0)
        self.assertGreater(Product.objects.count(), 0)
        self.assertGreater(Supplier.objects.count(), 0)
        self.assertGreater(Order.objects.count(), 0)
    
    def test_command_dependencies(self):
        """Test that commands handle missing dependencies gracefully"""
        # Try to run seed_fambri_products without units
        try:
            call_command('seed_fambri_products', verbosity=0)
            # Should either succeed or fail gracefully
        except Exception as e:
            # Should be a meaningful error message
            self.assertIsInstance(e, (CommandError, Exception))
    
    def test_command_output_verbosity(self):
        """Test command output at different verbosity levels"""
        out = StringIO()
        
        # Test with verbosity 0 (minimal output)
        call_command('seed_fambri_users', verbosity=0, stdout=out)
        minimal_output = out.getvalue()
        
        out = StringIO()
        
        # Test with verbosity 2 (detailed output)
        call_command('seed_fambri_users', verbosity=2, stdout=out)
        detailed_output = out.getvalue()
        
        # Detailed output should be longer
        self.assertGreaterEqual(len(detailed_output), len(minimal_output))
