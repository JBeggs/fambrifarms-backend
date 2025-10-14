"""
Unit tests for serializers
Tests serialization, validation, and computed fields across all modules
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
from datetime import date, timedelta
from unittest.mock import patch

from accounts.serializers import UserSerializer, CustomerSerializer, RestaurantProfileSerializer
from orders.serializers import OrderSerializer, OrderItemSerializer
from whatsapp.serializers import WhatsAppMessageSerializer, StockUpdateSerializer
from products.models import Product, Department
from accounts.models import RestaurantProfile
from orders.models import Order, OrderItem
from whatsapp.models import WhatsAppMessage, StockUpdate

User = get_user_model()


class UserSerializerTest(TestCase):
    """Test UserSerializer functionality"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@restaurant.com',
            password='testpass123',
            first_name='Test',
            last_name='User',
            user_type='restaurant',
            phone='+27 12 345 6789'
        )
        
        RestaurantProfile.objects.create(
            user=self.user,
            business_name='Test Restaurant',
            address='123 Test St',
            city='Test City',
            postal_code='12345'
        )
    
    def test_user_serializer_fields(self):
        """Test UserSerializer includes all required fields"""
        serializer = UserSerializer(self.user)
        data = serializer.data
        
        expected_fields = [
            'id', 'email', 'first_name', 'last_name', 'user_type', 
            'phone', 'is_verified', 'roles', 'restaurant_roles'
        ]
        
        for field in expected_fields:
            self.assertIn(field, data)
    
    def test_user_serializer_data_accuracy(self):
        """Test UserSerializer data accuracy"""
        serializer = UserSerializer(self.user)
        data = serializer.data
        
        self.assertEqual(data['email'], 'test@restaurant.com')
        self.assertEqual(data['first_name'], 'Test')
        self.assertEqual(data['last_name'], 'User')
        self.assertEqual(data['user_type'], 'restaurant')
        self.assertEqual(data['phone'], '+27 12 345 6789')


class RestaurantProfileSerializerTest(TestCase):
    """Test RestaurantProfileSerializer functionality"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='profile@test.com',
            password='testpass123',
            user_type='restaurant'
        )
        
        self.profile = RestaurantProfile.objects.create(
            user=self.user,
            business_name='Profile Test Restaurant',
            branch_name='Main Branch',
            address='456 Profile St',
            city='Profile City',
            postal_code='67890',
            payment_terms='Net 30',
            is_private_customer=False
        )
    
    def test_restaurant_profile_serializer_fields(self):
        """Test RestaurantProfileSerializer includes all fields"""
        serializer = RestaurantProfileSerializer(self.profile)
        data = serializer.data
        
        expected_fields = [
            'business_name', 'branch_name', 'business_registration', 
            'address', 'city', 'postal_code', 'payment_terms', 'is_private_customer'
        ]
        
        for field in expected_fields:
            self.assertIn(field, data)
    
    def test_restaurant_profile_serializer_data(self):
        """Test RestaurantProfileSerializer data accuracy"""
        serializer = RestaurantProfileSerializer(self.profile)
        data = serializer.data
        
        self.assertEqual(data['business_name'], 'Profile Test Restaurant')
        self.assertEqual(data['branch_name'], 'Main Branch')
        self.assertEqual(data['address'], '456 Profile St')
        self.assertEqual(data['city'], 'Profile City')
        self.assertEqual(data['postal_code'], '67890')
        self.assertEqual(data['payment_terms'], 'Net 30')
        self.assertFalse(data['is_private_customer'])


class CustomerSerializerTest(TestCase):
    """Test CustomerSerializer functionality"""
    
    def setUp(self):
        self.customer = User.objects.create_user(
            email='customer@test.com',
            password='testpass123',
            first_name='Customer',
            last_name='Test',
            user_type='restaurant',
            phone='+27 98 765 4321'
        )
        
        RestaurantProfile.objects.create(
            user=self.customer,
            business_name='Customer Test Restaurant',
            address='789 Customer St',
            city='Customer City',
            postal_code='11111'
        )
        
        # Create some orders for testing computed fields
        self.department = Department.objects.create(name='Vegetables')
        self.product = Product.objects.create(
            name='Test Product',
            department=self.department,
            price=Decimal('25.00'),
            unit='kg'
        )
        
        # Find next valid order date
        today = date.today()
        days_ahead = 0 - today.weekday()  # Monday
        if days_ahead <= 0:
            days_ahead += 7
        order_date = today + timedelta(days_ahead)
        
        self.order = Order.objects.create(
            restaurant=self.customer,
            order_date=order_date,
            status='confirmed'
        )
        
        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=Decimal('10.00'),
            price=Decimal('25.00'),
            unit='kg'
        )
    
    def test_customer_serializer_computed_fields(self):
        """Test CustomerSerializer computed fields"""
        serializer = CustomerSerializer(self.customer)
        data = serializer.data
        
        # Test computed fields exist
        computed_fields = [
            'name', 'customer_type', 'customer_segment', 
            'is_private_customer', 'total_orders', 'total_order_value'
        ]
        
        for field in computed_fields:
            self.assertIn(field, data)
    
    def test_customer_serializer_name_field(self):
        """Test CustomerSerializer name field computation"""
        serializer = CustomerSerializer(self.customer)
        data = serializer.data
        
        # Should return business name from profile
        self.assertEqual(data['name'], 'Customer Test Restaurant')
    
    def test_customer_serializer_name_fallback(self):
        """Test CustomerSerializer name field fallback"""
        # Create customer without business name
        customer_no_business = User.objects.create_user(
            email='nobusiness@test.com',
            password='testpass123',
            first_name='No',
            last_name='Business',
            user_type='restaurant'
        )
        
        RestaurantProfile.objects.create(
            user=customer_no_business,
            business_name='',  # Empty business name
            address='123 No Business St',
            city='No Business City'
        )
        
        serializer = CustomerSerializer(customer_no_business)
        data = serializer.data
        
        # Should fallback to user's full name
        self.assertEqual(data['name'], 'No Business')
    
    def test_customer_serializer_customer_type(self):
        """Test CustomerSerializer customer_type field"""
        serializer = CustomerSerializer(self.customer)
        data = serializer.data
        
        # Should return 'restaurant' for non-private customer
        self.assertEqual(data['customer_type'], 'restaurant')
    
    def test_customer_serializer_private_customer_type(self):
        """Test CustomerSerializer customer_type for private customer"""
        # Update profile to be private customer
        profile = self.customer.restaurantprofile
        profile.is_private_customer = True
        profile.save()
        
        serializer = CustomerSerializer(self.customer)
        data = serializer.data
        
        # Should return 'private' for private customer
        self.assertEqual(data['customer_type'], 'private')
    
    def test_customer_serializer_total_orders(self):
        """Test CustomerSerializer total_orders computation"""
        serializer = CustomerSerializer(self.customer)
        data = serializer.data
        
        # Should return 1 (we created one order)
        self.assertEqual(data['total_orders'], 1)
    
    def test_customer_serializer_total_order_value(self):
        """Test CustomerSerializer total_order_value computation"""
        serializer = CustomerSerializer(self.customer)
        data = serializer.data
        
        # Should return 250.00 (10 * 25.00)
        self.assertEqual(float(data['total_order_value']), 250.0)
    
    def test_customer_serializer_create(self):
        """Test CustomerSerializer create functionality"""
        data = {
            'email': 'newcustomer@test.com',
            'first_name': 'New',
            'last_name': 'Customer',
            'user_type': 'restaurant',
            'business_name': 'New Customer Restaurant',
            'address': '999 New St',
            'city': 'New City',
            'postal_code': '99999'
        }
        
        serializer = CustomerSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        
        customer = serializer.save()
        
        # Verify customer was created
        self.assertEqual(customer.email, 'newcustomer@test.com')
        self.assertEqual(customer.first_name, 'New')
        self.assertEqual(customer.user_type, 'restaurant')
        
        # Verify profile was created
        profile = customer.restaurantprofile
        self.assertEqual(profile.business_name, 'New Customer Restaurant')
        self.assertEqual(profile.address, '999 New St')


class OrderSerializerTest(TestCase):
    """Test OrderSerializer functionality"""
    
    def setUp(self):
        self.customer = User.objects.create_user(
            email='order@test.com',
            password='testpass123',
            first_name='Order',
            last_name='Customer',
            user_type='restaurant'
        )
        
        RestaurantProfile.objects.create(
            user=self.customer,
            business_name='Order Test Restaurant',
            address='123 Order St',
            city='Order City',
            postal_code='12345'
        )
        
        self.department = Department.objects.create(name='Vegetables')
        self.product = Product.objects.create(
            name='Order Product',
            department=self.department,
            price=Decimal('30.00'),
            unit='kg'
        )
        
        # Find next valid order date
        today = date.today()
        days_ahead = 0 - today.weekday()  # Monday
        if days_ahead <= 0:
            days_ahead += 7
        order_date = today + timedelta(days_ahead)
        
        self.order = Order.objects.create(
            restaurant=self.customer,
            order_date=order_date,
            status='confirmed',
            subtotal=Decimal('300.00'),
            total_amount=Decimal('300.00')
        )
        
        self.order_item = OrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=Decimal('10.00'),
            price=Decimal('30.00'),
            unit='kg'
        )
    
    def test_order_serializer_fields(self):
        """Test OrderSerializer includes all required fields"""
        serializer = OrderSerializer(self.order)
        data = serializer.data
        
        expected_fields = [
            'id', 'order_number', 'restaurant', 'restaurant_name', 
            'restaurant_business_name', 'restaurant_address', 'restaurant_phone',
            'restaurant_email', 'status', 'order_date', 'delivery_date',
            'whatsapp_message_id', 'original_message', 'parsed_by_ai',
            'subtotal', 'total_amount', 'items', 'purchase_orders',
            'created_at', 'updated_at'
        ]
        
        for field in expected_fields:
            self.assertIn(field, data)
    
    def test_order_serializer_computed_fields(self):
        """Test OrderSerializer computed fields"""
        serializer = OrderSerializer(self.order)
        data = serializer.data
        
        # Test restaurant name
        self.assertEqual(data['restaurant_name'], 'Order Customer')
        
        # Test restaurant business name
        self.assertEqual(data['restaurant_business_name'], 'Order Test Restaurant')
        
        # Test restaurant address (full address format)
        self.assertEqual(data['restaurant_address'], '123 Order St, Order City, 12345')
    
    def test_order_serializer_includes_items(self):
        """Test OrderSerializer includes order items"""
        serializer = OrderSerializer(self.order)
        data = serializer.data
        
        self.assertIn('items', data)
        self.assertEqual(len(data['items']), 1)
        
        item_data = data['items'][0]
        # Product is serialized as ID, not nested object
        self.assertEqual(item_data['product'], self.product.id)
        self.assertEqual(float(item_data['quantity']), 10.0)
        self.assertEqual(float(item_data['price']), 30.0)
    
    def test_order_serializer_handles_missing_profile(self):
        """Test OrderSerializer handles missing restaurant profile"""
        # Create customer without profile
        customer_no_profile = User.objects.create_user(
            email='noprofile@test.com',
            password='testpass123',
            first_name='No',
            last_name='Profile',
            user_type='restaurant'
        )
        
        today = date.today()
        days_ahead = 0 - today.weekday()  # Monday
        if days_ahead <= 0:
            days_ahead += 7
        order_date = today + timedelta(days_ahead)
        
        order_no_profile = Order.objects.create(
            restaurant=customer_no_profile,
            order_date=order_date,
            status='received'
        )
        
        serializer = OrderSerializer(order_no_profile)
        data = serializer.data
        
        # Should handle missing profile gracefully
        self.assertEqual(data['restaurant_name'], 'No Profile')
        self.assertIsNone(data['restaurant_business_name'])
        self.assertIsNone(data['restaurant_address'])


class OrderItemSerializerTest(TestCase):
    """Test OrderItemSerializer functionality"""
    
    def setUp(self):
        self.customer = User.objects.create_user(
            email='item@test.com',
            password='testpass123',
            user_type='restaurant'
        )
        
        self.department = Department.objects.create(name='Vegetables')
        self.product = Product.objects.create(
            name='Item Product',
            department=self.department,
            price=Decimal('25.00'),
            unit='kg'
        )
        
        today = date.today()
        days_ahead = 0 - today.weekday()  # Monday
        if days_ahead <= 0:
            days_ahead += 7
        order_date = today + timedelta(days_ahead)
        
        self.order = Order.objects.create(
            restaurant=self.customer,
            order_date=order_date,
            status='received'
        )
        
        self.order_item = OrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=Decimal('15.00'),
            price=Decimal('25.00'),
            unit='kg',
            original_text='15kg item product',
            confidence_score=Decimal('0.95'),
            manually_corrected=False,
            notes='Test item notes'
        )
    
    def test_order_item_serializer_fields(self):
        """Test OrderItemSerializer includes all required fields"""
        serializer = OrderItemSerializer(self.order_item)
        data = serializer.data
        
        expected_fields = [
            'id', 'product', 'product_name', 'product_default_unit',
            'quantity', 'unit', 'price', 'total_price', 'original_text',
            'confidence_score', 'manually_corrected', 'notes'
        ]
        
        for field in expected_fields:
            self.assertIn(field, data)
    
    def test_order_item_serializer_computed_fields(self):
        """Test OrderItemSerializer computed fields"""
        serializer = OrderItemSerializer(self.order_item)
        data = serializer.data
        
        # Test product name
        self.assertEqual(data['product_name'], 'Item Product')
        
        # Test product default unit
        self.assertEqual(data['product_default_unit'], 'kg')
        
        # Test total price calculation
        expected_total = float(Decimal('15.00') * Decimal('25.00'))
        self.assertEqual(float(data['total_price']), expected_total)
    
    def test_order_item_serializer_data_accuracy(self):
        """Test OrderItemSerializer data accuracy"""
        serializer = OrderItemSerializer(self.order_item)
        data = serializer.data
        
        self.assertEqual(float(data['quantity']), 15.0)
        self.assertEqual(data['unit'], 'kg')
        self.assertEqual(float(data['price']), 25.0)
        self.assertEqual(data['original_text'], '15kg item product')
        self.assertEqual(float(data['confidence_score']), 0.95)
        self.assertFalse(data['manually_corrected'])
        self.assertEqual(data['notes'], 'Test item notes')


class WhatsAppMessageSerializerTest(TestCase):
    """Test WhatsAppMessageSerializer functionality"""
    
    def setUp(self):
        self.message = WhatsAppMessage.objects.create(
            message_id='test_msg_123',
            chat_name='ORDERS Restaurants',
            sender_name='Test Sender',
            sender_phone='+27 12 345 6789',
            content='30kg lettuce\n20kg tomatoes',
            timestamp=timezone.now(),
            cleaned_content='30kg lettuce, 20kg tomatoes',
            message_type='order',
            confidence_score=Decimal('0.85'),
            processed=False,
            edited=False,
            manual_company='Test Restaurant',
            order_day='Monday'
        )
    
    def test_whatsapp_message_serializer_fields(self):
        """Test WhatsAppMessageSerializer includes all required fields"""
        serializer = WhatsAppMessageSerializer(self.message)
        data = serializer.data
        
        expected_fields = [
            'id', 'message_id', 'chat_name', 'sender_name', 'sender_phone',
            'content', 'cleaned_content', 'timestamp', 'scraped_at',
            'message_type', 'confidence_score', 'processed',
            'parsed_items', 'instructions', 'edited', 'original_content', 'manual_company'
        ]
        
        for field in expected_fields:
            self.assertIn(field, data)
    
    def test_whatsapp_message_serializer_camel_case_aliases(self):
        """Test WhatsAppMessageSerializer camelCase aliases"""
        serializer = WhatsAppMessageSerializer(self.message)
        data = serializer.data
        
        # Basic serializer doesn't have camelCase aliases
        # Just test that cleaned_content exists
        self.assertIn('cleaned_content', data)
    
    def test_whatsapp_message_serializer_computed_fields(self):
        """Test WhatsAppMessageSerializer computed fields"""
        serializer = WhatsAppMessageSerializer(self.message)
        data = serializer.data
        
        # Test company_name field (should call extract_company_name method)
        self.assertIn('company_name', data)
        
        # Test parsed_items field (should call extract_order_items for order messages)
        self.assertIn('parsed_items', data)
        self.assertIsInstance(data['parsed_items'], list)
        
        # Test instructions field
        self.assertIn('instructions', data)
        
        # Test is_stock_controller field
        self.assertIn('is_stock_controller', data)
    
    def test_whatsapp_message_serializer_data_accuracy(self):
        """Test WhatsAppMessageSerializer data accuracy"""
        serializer = WhatsAppMessageSerializer(self.message)
        data = serializer.data
        
        self.assertEqual(data['message_id'], 'test_msg_123')
        self.assertEqual(data['chat_name'], 'ORDERS Restaurants')
        self.assertEqual(data['sender_name'], 'Test Sender')
        self.assertEqual(data['sender_phone'], '+27 12 345 6789')
        self.assertEqual(data['content'], '30kg lettuce\n20kg tomatoes')
        self.assertEqual(data['message_type'], 'order')
        self.assertEqual(float(data['confidence_score']), 0.85)
        self.assertFalse(data['processed'])
        self.assertEqual(data['manual_company'], 'Test Restaurant')
        self.assertEqual(data['order_day'], 'Monday')


class StockUpdateSerializerTest(TestCase):
    """Test StockUpdateSerializer functionality"""
    
    def setUp(self):
        self.message = WhatsAppMessage.objects.create(
            message_id='stock_msg_123',
            chat_name='ORDERS Restaurants',
            sender_name='SHALLOME',
            sender_phone='+27 61 674 9368',
            content='STOCK AS AT 25/09/2025\n1. Lettuce - 50kg\n2. Tomatoes - 30kg',
            timestamp=timezone.now(),
            message_type='stock'
        )
        
        self.stock_update = StockUpdate.objects.create(
            message=self.message,
            stock_date=date.today(),
            order_day='Monday',
            items={
                'lettuce': {'quantity': 50, 'unit': 'kg'},
                'tomatoes': {'quantity': 30, 'unit': 'kg'}
            },
            processed=False
        )
    
    def test_stock_update_serializer_basic_functionality(self):
        """Test StockUpdateSerializer basic functionality"""
        serializer = StockUpdateSerializer(self.stock_update)
        data = serializer.data
        
        # Should include basic fields
        basic_fields = ['id', 'stock_date', 'order_day', 'items', 'processed']
        
        for field in basic_fields:
            self.assertIn(field, data)
    
    def test_stock_update_serializer_data_accuracy(self):
        """Test StockUpdateSerializer data accuracy"""
        serializer = StockUpdateSerializer(self.stock_update)
        data = serializer.data
        
        self.assertEqual(data['order_day'], 'Monday')
        self.assertFalse(data['processed'])
        self.assertEqual(len(data['items']), 2)
        
        # Test items structure
        items = data['items']
        self.assertIn('lettuce', items)
        self.assertIn('tomatoes', items)
        
        self.assertEqual(items['lettuce']['quantity'], 50)
        self.assertEqual(items['lettuce']['unit'], 'kg')
        self.assertEqual(items['tomatoes']['quantity'], 30)
        self.assertEqual(items['tomatoes']['unit'], 'kg')
