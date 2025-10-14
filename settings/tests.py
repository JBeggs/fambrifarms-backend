from django.test import TestCase
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.core.management import call_command
from decimal import Decimal

from accounts.models import User
from products.models import Department, Product
from .models import (
    SystemSetting, CustomerSegment, OrderStatus, 
    StockAdjustmentType, BusinessConfiguration, UnitOfMeasure
)


class SystemSettingModelTest(TestCase):
    """Test SystemSetting model functionality"""
    
    def test_system_setting_creation(self):
        """Test system setting is created correctly"""
        setting = SystemSetting.objects.create(
            key='test_setting',
            value='test_value',
            description='Test setting description',
            category='test'
        )
        
        self.assertEqual(setting.key, 'test_setting')
        self.assertEqual(setting.value, 'test_value')
        self.assertEqual(setting.description, 'Test setting description')
        self.assertEqual(setting.category, 'test')
        self.assertTrue(setting.is_active)
        self.assertIsNotNone(setting.created_at)
        self.assertIsNotNone(setting.updated_at)
    
    def test_system_setting_str_representation(self):
        """Test system setting string representation"""
        setting = SystemSetting.objects.create(
            key='api_timeout',
            value='30'
        )
        
        expected_str = "api_timeout: 30"
        self.assertEqual(str(setting), expected_str)
    
    def test_system_setting_unique_key(self):
        """Test system setting key uniqueness"""
        SystemSetting.objects.create(key='unique_key', value='value1')
        
        with self.assertRaises(Exception):
            SystemSetting.objects.create(key='unique_key', value='value2')


class CustomerSegmentModelTest(TestCase):
    """Test CustomerSegment model functionality"""
    
    def test_customer_segment_creation(self):
        """Test customer segment is created correctly"""
        segment = CustomerSegment.objects.create(
            name='premium',
            description='Premium customers',
            default_markup=Decimal('1.15'),
            credit_limit_multiplier=Decimal('2.0'),
            payment_terms_days=60
        )
        
        self.assertEqual(segment.name, 'premium')
        self.assertEqual(segment.description, 'Premium customers')
        self.assertEqual(segment.default_markup, Decimal('1.15'))
        self.assertEqual(segment.credit_limit_multiplier, Decimal('2.0'))
        self.assertEqual(segment.payment_terms_days, 60)
        self.assertTrue(segment.is_active)
        self.assertIsNotNone(segment.created_at)
    
    def test_customer_segment_str_representation(self):
        """Test customer segment string representation"""
        segment = CustomerSegment.objects.create(name='standard')
        self.assertEqual(str(segment), 'standard')
    
    def test_customer_segment_defaults(self):
        """Test customer segment default values"""
        segment = CustomerSegment.objects.create(name='test_segment')
        
        self.assertEqual(segment.default_markup, Decimal('1.25'))
        self.assertEqual(segment.credit_limit_multiplier, Decimal('1.0'))
        self.assertEqual(segment.payment_terms_days, 30)
        self.assertTrue(segment.is_active)


class OrderStatusModelTest(TestCase):
    """Test OrderStatus model functionality"""
    
    def test_order_status_creation(self):
        """Test order status is created correctly"""
        status = OrderStatus.objects.create(
            name='confirmed',
            display_name='Confirmed',
            description='Order confirmed and being prepared',
            color='#17a2b8',
            is_final=False,
            sort_order=2
        )
        
        self.assertEqual(status.name, 'confirmed')
        self.assertEqual(status.display_name, 'Confirmed')
        self.assertEqual(status.description, 'Order confirmed and being prepared')
        self.assertEqual(status.color, '#17a2b8')
        self.assertFalse(status.is_final)
        self.assertEqual(status.sort_order, 2)
        self.assertTrue(status.is_active)
        self.assertIsNotNone(status.created_at)
    
    def test_order_status_str_representation(self):
        """Test order status string representation"""
        status = OrderStatus.objects.create(
            name='pending',
            display_name='Pending'
        )
        self.assertEqual(str(status), 'Pending')
    
    def test_order_status_defaults(self):
        """Test order status default values"""
        status = OrderStatus.objects.create(
            name='test_status',
            display_name='Test Status'
        )
        
        self.assertEqual(status.color, '#007bff')
        self.assertFalse(status.is_final)
        self.assertEqual(status.sort_order, 0)
        self.assertTrue(status.is_active)


class StockAdjustmentTypeModelTest(TestCase):
    """Test StockAdjustmentType model functionality"""
    
    def test_stock_adjustment_type_creation(self):
        """Test stock adjustment type is created correctly"""
        adj_type = StockAdjustmentType.objects.create(
            name='increase',
            display_name='Stock Increase',
            description='Increase stock level',
            affects_cost=True,
            requires_reason=True
        )
        
        self.assertEqual(adj_type.name, 'increase')
        self.assertEqual(adj_type.display_name, 'Stock Increase')
        self.assertEqual(adj_type.description, 'Increase stock level')
        self.assertTrue(adj_type.affects_cost)
        self.assertTrue(adj_type.requires_reason)
        self.assertTrue(adj_type.is_active)
        self.assertIsNotNone(adj_type.created_at)
    
    def test_stock_adjustment_type_str_representation(self):
        """Test stock adjustment type string representation"""
        adj_type = StockAdjustmentType.objects.create(
            name='correction',
            display_name='Stock Correction'
        )
        self.assertEqual(str(adj_type), 'Stock Correction')
    
    def test_stock_adjustment_type_defaults(self):
        """Test stock adjustment type default values"""
        adj_type = StockAdjustmentType.objects.create(
            name='test_type',
            display_name='Test Type'
        )
        
        self.assertFalse(adj_type.affects_cost)
        self.assertTrue(adj_type.requires_reason)
        self.assertTrue(adj_type.is_active)


class BusinessConfigurationModelTest(TestCase):
    """Test BusinessConfiguration model functionality"""
    
    def test_business_configuration_creation(self):
        """Test business configuration is created correctly"""
        config = BusinessConfiguration.objects.create(
            name='default_vat_rate',
            display_name='Default VAT Rate',
            value_type='decimal',
            decimal_value=Decimal('0.15'),
            description='Default VAT rate for pricing',
            category='pricing'
        )
        
        self.assertEqual(config.name, 'default_vat_rate')
        self.assertEqual(config.display_name, 'Default VAT Rate')
        self.assertEqual(config.value_type, 'decimal')
        self.assertEqual(config.decimal_value, Decimal('0.15'))
        self.assertEqual(config.description, 'Default VAT rate for pricing')
        self.assertEqual(config.category, 'pricing')
        self.assertTrue(config.is_active)
        self.assertIsNotNone(config.created_at)
        self.assertIsNotNone(config.updated_at)
    
    def test_business_configuration_str_representation(self):
        """Test business configuration string representation"""
        config = BusinessConfiguration.objects.create(
            name='test_config',
            display_name='Test Configuration',
            value_type='string',
            string_value='test_value'
        )
        
        expected_str = "Test Configuration: test_value"
        self.assertEqual(str(config), expected_str)
    
    def test_business_configuration_get_value_decimal(self):
        """Test get_value method for decimal type"""
        config = BusinessConfiguration.objects.create(
            name='decimal_config',
            display_name='Decimal Config',
            value_type='decimal',
            decimal_value=Decimal('1.25')
        )
        
        self.assertEqual(config.get_value(), Decimal('1.25'))
    
    def test_business_configuration_get_value_integer(self):
        """Test get_value method for integer type"""
        config = BusinessConfiguration.objects.create(
            name='integer_config',
            display_name='Integer Config',
            value_type='integer',
            integer_value=30
        )
        
        self.assertEqual(config.get_value(), 30)
    
    def test_business_configuration_get_value_boolean(self):
        """Test get_value method for boolean type"""
        config = BusinessConfiguration.objects.create(
            name='boolean_config',
            display_name='Boolean Config',
            value_type='boolean',
            boolean_value=True
        )
        
        self.assertEqual(config.get_value(), True)
    
    def test_business_configuration_get_value_string(self):
        """Test get_value method for string type"""
        config = BusinessConfiguration.objects.create(
            name='string_config',
            display_name='String Config',
            value_type='string',
            string_value='test_string'
        )
        
        self.assertEqual(config.get_value(), 'test_string')
    
    def test_business_configuration_set_value_decimal(self):
        """Test set_value method for decimal type"""
        config = BusinessConfiguration.objects.create(
            name='decimal_config',
            display_name='Decimal Config',
            value_type='decimal'
        )
        
        config.set_value(Decimal('2.50'))
        self.assertEqual(config.decimal_value, Decimal('2.50'))
    
    def test_business_configuration_set_value_integer(self):
        """Test set_value method for integer type"""
        config = BusinessConfiguration.objects.create(
            name='integer_config',
            display_name='Integer Config',
            value_type='integer'
        )
        
        config.set_value(45)
        self.assertEqual(config.integer_value, 45)
    
    def test_business_configuration_set_value_boolean(self):
        """Test set_value method for boolean type"""
        config = BusinessConfiguration.objects.create(
            name='boolean_config',
            display_name='Boolean Config',
            value_type='boolean'
        )
        
        config.set_value(False)
        self.assertEqual(config.boolean_value, False)
    
    def test_business_configuration_set_value_string(self):
        """Test set_value method for string type"""
        config = BusinessConfiguration.objects.create(
            name='string_config',
            display_name='String Config',
            value_type='string'
        )
        
        config.set_value('new_value')
        self.assertEqual(config.string_value, 'new_value')


class SettingsAPITest(APITestCase):
    """Test settings API endpoints"""
    
    def setUp(self):
        self.client = APIClient()
        # Create and authenticate user
        self.user = User.objects.create_user(
            email='api_test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        
        # Create test data
        self.customer_segment = CustomerSegment.objects.create(
            name='test_segment',
            description='Test segment'
        )
        
        self.order_status = OrderStatus.objects.create(
            name='test_status',
            display_name='Test Status'
        )
        
        self.adjustment_type = StockAdjustmentType.objects.create(
            name='test_adjustment',
            display_name='Test Adjustment'
        )
        
        self.department = Department.objects.create(
            name='Test Department'
        )
        
        # Create test unit of measure
        self.unit_of_measure = UnitOfMeasure.objects.create(
            name='kg',
            display_name='Kilogram',
            sort_order=1
        )
        
        self.product = Product.objects.create(
            name='Test Product',
            price=Decimal('25.00'),
            unit='kg',
            department=self.department
        )
        
        self.business_config = BusinessConfiguration.objects.create(
            name='test_config',
            display_name='Test Config',
            value_type='decimal',
            decimal_value=Decimal('1.25'),
            category='test'
        )
        
        self.system_setting = SystemSetting.objects.create(
            key='test_setting',
            value='test_value',
            category='test'
        )
    
    def test_get_customer_segments(self):
        """Test get customer segments endpoint"""
        url = '/api/settings/customer-segments/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        self.assertGreaterEqual(len(response.data), 1)
        
        # Check that our test segment is in the response
        segment_names = [seg['name'] for seg in response.data]
        self.assertIn('test_segment', segment_names)
    
    def test_get_order_statuses(self):
        """Test get order statuses endpoint"""
        url = '/api/settings/order-statuses/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        self.assertGreaterEqual(len(response.data), 1)
        
        # Check that our test status is in the response
        status_names = [stat['name'] for stat in response.data]
        self.assertIn('test_status', status_names)
    
    def test_get_adjustment_types(self):
        """Test get adjustment types endpoint"""
        url = '/api/settings/adjustment-types/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        self.assertGreaterEqual(len(response.data), 1)
        
        # Check that our test adjustment type is in the response
        type_names = [adj['name'] for adj in response.data]
        self.assertIn('test_adjustment', type_names)
    
    def test_get_departments(self):
        """Test get departments endpoint"""
        url = '/api/settings/departments/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        self.assertGreaterEqual(len(response.data), 1)
        
        # Check that our test department is in the response
        dept_names = [dept['name'] for dept in response.data]
        self.assertIn('Test Department', dept_names)
    
    def test_get_units_of_measure(self):
        """Test get units of measure endpoint"""
        url = '/api/settings/units-of-measure/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        self.assertGreaterEqual(len(response.data), 1)
        
        # Check that our test unit is in the response
        units = [unit['name'] for unit in response.data]
        self.assertIn('kg', units)
    
    def test_get_business_configuration(self):
        """Test get business configuration endpoint"""
        url = '/api/settings/business-config/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, dict)
        self.assertIn('test_config', response.data)
        
        config_data = response.data['test_config']
        self.assertEqual(config_data['value'], Decimal('1.25'))
        self.assertEqual(config_data['display_name'], 'Test Config')
        self.assertEqual(config_data['category'], 'test')
        self.assertEqual(config_data['type'], 'decimal')
    
    def test_get_system_settings(self):
        """Test get system settings endpoint"""
        url = '/api/settings/system-settings/?category=test'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, dict)
        self.assertIn('test_setting', response.data)
        self.assertEqual(response.data['test_setting'], 'test_value')
    
    def test_get_system_settings_default_category(self):
        """Test get system settings with default category"""
        url = '/api/settings/system-settings/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, dict)
    
    def test_get_form_options(self):
        """Test get form options endpoint"""
        url = '/api/settings/form-options/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, dict)
        
        # Check that all expected keys are present
        expected_keys = [
            'customer_segments', 'order_statuses', 'adjustment_types',
            'departments', 'units_of_measure', 'customer_types',
            'payment_terms', 'priority_levels'
        ]
        for key in expected_keys:
            self.assertIn(key, response.data)
        
        # Check that our test data is included
        segment_names = [seg['name'] for seg in response.data['customer_segments']]
        self.assertIn('test_segment', segment_names)
    
    def test_update_business_config_success(self):
        """Test successful business configuration update"""
        url = '/api/settings/business-config/update/'
        data = {
            'test_config': '2.50'
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
        
        # Verify the config was updated
        self.business_config.refresh_from_db()
        self.assertEqual(self.business_config.decimal_value, Decimal('2.50'))
    
    def test_update_business_config_not_found(self):
        """Test business configuration update with non-existent key"""
        url = '/api/settings/business-config/update/'
        data = {
            'non_existent_key': 'value'
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('error', response.data)
    
    def test_api_authentication_required(self):
        """Test that API endpoints require authentication"""
        self.client.force_authenticate(user=None)
        
        endpoints = [
            '/api/settings/customer-segments/',
            '/api/settings/order-statuses/',
            '/api/settings/adjustment-types/',
            '/api/settings/departments/',
            '/api/settings/units-of-measure/',
            '/api/settings/business-config/',
            '/api/settings/system-settings/',
            '/api/settings/form-options/',
        ]
        
        for endpoint in endpoints:
            response = self.client.get(endpoint)
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class SettingsManagementCommandTest(TestCase):
    """Test settings management command"""
    
    def test_seed_system_settings_command(self):
        """Test the seed_system_settings management command"""
        # Ensure we start with clean slate
        SystemSetting.objects.all().delete()
        CustomerSegment.objects.all().delete()
        OrderStatus.objects.all().delete()
        StockAdjustmentType.objects.all().delete()
        BusinessConfiguration.objects.all().delete()
        
        # Run the command
        call_command('seed_system_settings')
        
        # Verify data was created
        self.assertGreater(SystemSetting.objects.count(), 0)
        self.assertGreater(CustomerSegment.objects.count(), 0)
        self.assertGreater(OrderStatus.objects.count(), 0)
        self.assertGreater(StockAdjustmentType.objects.count(), 0)
        self.assertGreater(BusinessConfiguration.objects.count(), 0)
        
        # Verify specific expected data
        self.assertTrue(CustomerSegment.objects.filter(name='premium').exists())
        self.assertTrue(CustomerSegment.objects.filter(name='standard').exists())
        self.assertTrue(OrderStatus.objects.filter(name='pending').exists())
        self.assertTrue(OrderStatus.objects.filter(name='delivered').exists())
        self.assertTrue(StockAdjustmentType.objects.filter(name='increase').exists())
        self.assertTrue(BusinessConfiguration.objects.filter(name='default_vat_rate').exists())
        self.assertTrue(SystemSetting.objects.filter(key='whatsapp_check_interval').exists())
    
    def test_seed_system_settings_command_with_clear(self):
        """Test the seed_system_settings management command with --clear option"""
        # Create some initial data
        SystemSetting.objects.create(key='test_key', value='test_value')
        CustomerSegment.objects.create(name='test_segment')
        
        initial_setting_count = SystemSetting.objects.count()
        initial_segment_count = CustomerSegment.objects.count()
        
        # Run the command with --clear
        call_command('seed_system_settings', '--clear')
        
        # Verify data was cleared and recreated
        final_setting_count = SystemSetting.objects.count()
        final_segment_count = CustomerSegment.objects.count()
        
        # Should have more than initial count (seeded data)
        self.assertGreater(final_setting_count, 0)
        self.assertGreater(final_segment_count, 0)
        
        # Should not contain our test data
        self.assertFalse(SystemSetting.objects.filter(key='test_key').exists())
        self.assertFalse(CustomerSegment.objects.filter(name='test_segment').exists())


class SettingsIntegrationTest(TestCase):
    """Test settings integration with other parts of the system"""
    
    def setUp(self):
        # Seed the system with default settings
        call_command('seed_system_settings')
    
    def test_customer_segment_integration(self):
        """Test customer segment integration with pricing"""
        premium_segment = CustomerSegment.objects.get(name='premium')
        standard_segment = CustomerSegment.objects.get(name='standard')
        
        # Verify premium segment has better terms
        self.assertLess(premium_segment.default_markup, standard_segment.default_markup)
        self.assertGreater(premium_segment.credit_limit_multiplier, standard_segment.credit_limit_multiplier)
        self.assertGreater(premium_segment.payment_terms_days, standard_segment.payment_terms_days)
    
    def test_order_status_workflow(self):
        """Test order status workflow progression"""
        statuses = OrderStatus.objects.all().order_by('sort_order')
        
        # Verify we have a logical progression
        self.assertGreater(len(statuses), 3)
        
        # Check that final statuses are marked correctly
        final_statuses = OrderStatus.objects.filter(is_final=True)
        final_status_names = [status.name for status in final_statuses]
        self.assertIn('delivered', final_status_names)
        self.assertIn('cancelled', final_status_names)
    
    def test_business_configuration_types(self):
        """Test business configuration value types"""
        # Test decimal configuration
        vat_config = BusinessConfiguration.objects.get(name='default_vat_rate')
        self.assertEqual(vat_config.value_type, 'decimal')
        self.assertIsInstance(vat_config.get_value(), Decimal)
        
        # Test integer configuration
        payment_terms_config = BusinessConfiguration.objects.get(name='default_payment_terms')
        self.assertEqual(payment_terms_config.value_type, 'integer')
        self.assertIsInstance(payment_terms_config.get_value(), int)
        
        # Test boolean configuration
        auto_reorder_config = BusinessConfiguration.objects.get(name='auto_reorder_enabled')
        self.assertEqual(auto_reorder_config.value_type, 'boolean')
        self.assertIsInstance(auto_reorder_config.get_value(), bool)
    
    def test_stock_adjustment_types_logic(self):
        """Test stock adjustment types business logic"""
        increase_type = StockAdjustmentType.objects.get(name='increase')
        decrease_type = StockAdjustmentType.objects.get(name='decrease')
        expired_type = StockAdjustmentType.objects.get(name='expired')
        
        # Verify business logic
        self.assertTrue(increase_type.affects_cost)  # New stock affects cost
        self.assertFalse(decrease_type.affects_cost)  # Sales don't affect cost
        self.assertTrue(increase_type.requires_reason)
        self.assertFalse(expired_type.requires_reason)  # Expiry is self-explanatory
    
    def test_system_settings_categories(self):
        """Test system settings are properly categorized"""
        categories = SystemSetting.objects.values_list('category', flat=True).distinct()
        
        expected_categories = ['whatsapp', 'api', 'logging', 'procurement']
        for category in expected_categories:
            self.assertIn(category, categories)
        
        # Verify specific settings exist in correct categories
        whatsapp_settings = SystemSetting.objects.filter(category='whatsapp')
        self.assertTrue(whatsapp_settings.filter(key='whatsapp_check_interval').exists())
        
        api_settings = SystemSetting.objects.filter(category='api')
        self.assertTrue(api_settings.filter(key='api_timeout_seconds').exists())
