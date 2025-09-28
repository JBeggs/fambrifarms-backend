"""
Unit tests for order business logic
Tests critical order validation, scheduling, and business rules
"""

from django.test import TestCase
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from decimal import Decimal
from datetime import date, timedelta

from orders.models import Order, OrderItem, validate_order_date, validate_delivery_date, calculate_delivery_date
from products.models import Product, Department
from accounts.models import RestaurantProfile

User = get_user_model()


class OrderValidationTest(TestCase):
    """Test order date and delivery date validation logic"""
    
    def setUp(self):
        # Create test customer
        self.customer = User.objects.create_user(
            email='test@restaurant.com',
            password='testpass123',
            user_type='restaurant',
            first_name='Test',
            last_name='Restaurant'
        )
        
        # Create restaurant profile
        RestaurantProfile.objects.create(
            user=self.customer,
            business_name='Test Restaurant',
            address='123 Test St',
            city='Test City',
            postal_code='12345'
        )
    
    def test_valid_order_dates(self):
        """Test that Monday (0) and Thursday (3) are valid order dates"""
        # Find next Monday and Thursday
        today = date.today()
        days_ahead = 0 - today.weekday()  # Monday
        if days_ahead <= 0:
            days_ahead += 7
        next_monday = today + timedelta(days_ahead)
        
        days_ahead = 3 - today.weekday()  # Thursday  
        if days_ahead <= 0:
            days_ahead += 7
        next_thursday = today + timedelta(days_ahead)
        
        # Test Monday order date
        try:
            validate_order_date(next_monday)
        except ValidationError:
            self.fail("Monday should be a valid order date")
        
        # Test Thursday order date
        try:
            validate_order_date(next_thursday)
        except ValidationError:
            self.fail("Thursday should be a valid order date")
    
    def test_invalid_order_dates(self):
        """Test that non-Monday/Thursday dates are invalid"""
        # Find next Tuesday (invalid)
        today = date.today()
        days_ahead = 1 - today.weekday()  # Tuesday
        if days_ahead <= 0:
            days_ahead += 7
        next_tuesday = today + timedelta(days_ahead)
        
        with self.assertRaises(ValidationError):
            validate_order_date(next_tuesday)
    
    def test_valid_delivery_dates(self):
        """Test that Tuesday (1), Wednesday (2), and Friday (4) are valid delivery dates"""
        today = date.today()
        
        # Test Tuesday delivery
        days_ahead = 1 - today.weekday()
        if days_ahead <= 0:
            days_ahead += 7
        next_tuesday = today + timedelta(days_ahead)
        
        try:
            validate_delivery_date(next_tuesday)
        except ValidationError:
            self.fail("Tuesday should be a valid delivery date")
        
        # Test Wednesday delivery
        days_ahead = 2 - today.weekday()
        if days_ahead <= 0:
            days_ahead += 7
        next_wednesday = today + timedelta(days_ahead)
        
        try:
            validate_delivery_date(next_wednesday)
        except ValidationError:
            self.fail("Wednesday should be a valid delivery date")
        
        # Test Friday delivery
        days_ahead = 4 - today.weekday()
        if days_ahead <= 0:
            days_ahead += 7
        next_friday = today + timedelta(days_ahead)
        
        try:
            validate_delivery_date(next_friday)
        except ValidationError:
            self.fail("Friday should be a valid delivery date")
    
    def test_invalid_delivery_dates(self):
        """Test that non-delivery days are invalid"""
        today = date.today()
        
        # Test Monday (invalid delivery day)
        days_ahead = 0 - today.weekday()
        if days_ahead <= 0:
            days_ahead += 7
        next_monday = today + timedelta(days_ahead)
        
        with self.assertRaises(ValidationError):
            validate_delivery_date(next_monday)
    
    def test_calculate_delivery_date_monday_order(self):
        """Test that Monday orders default to Tuesday delivery"""
        today = date.today()
        days_ahead = 0 - today.weekday()  # Monday
        if days_ahead <= 0:
            days_ahead += 7
        next_monday = today + timedelta(days_ahead)
        
        expected_delivery = next_monday + timedelta(days=1)  # Tuesday
        actual_delivery = calculate_delivery_date(next_monday)
        
        self.assertEqual(actual_delivery, expected_delivery)
    
    def test_calculate_delivery_date_thursday_order(self):
        """Test that Thursday orders default to Friday delivery"""
        today = date.today()
        days_ahead = 3 - today.weekday()  # Thursday
        if days_ahead <= 0:
            days_ahead += 7
        next_thursday = today + timedelta(days_ahead)
        
        expected_delivery = next_thursday + timedelta(days=1)  # Friday
        actual_delivery = calculate_delivery_date(next_thursday)
        
        self.assertEqual(actual_delivery, expected_delivery)
    
    def test_calculate_delivery_date_invalid_order_date(self):
        """Test that invalid order dates raise ValidationError"""
        today = date.today()
        days_ahead = 1 - today.weekday()  # Tuesday (invalid)
        if days_ahead <= 0:
            days_ahead += 7
        next_tuesday = today + timedelta(days_ahead)
        
        with self.assertRaises(ValidationError):
            calculate_delivery_date(next_tuesday)


class OrderModelTest(TestCase):
    """Test Order model business logic"""
    
    def setUp(self):
        # Create test customer
        self.customer = User.objects.create_user(
            email='test@restaurant.com',
            password='testpass123',
            user_type='restaurant',
            first_name='Test',
            last_name='Restaurant'
        )
        
        # Create restaurant profile
        RestaurantProfile.objects.create(
            user=self.customer,
            business_name='Test Restaurant',
            address='123 Test St',
            city='Test City',
            postal_code='12345'
        )
        
        # Create test product
        self.department = Department.objects.create(
            name='Test Vegetables',
            description='Test department'
        )
        
        self.product = Product.objects.create(
            name='Test Lettuce',
            department=self.department,
            price=Decimal('25.00'),
            unit='kg'
        )
    
    def test_order_number_auto_generation(self):
        """Test that order numbers are automatically generated"""
        # Find next valid order date
        today = date.today()
        days_ahead = 0 - today.weekday()  # Monday
        if days_ahead <= 0:
            days_ahead += 7
        order_date = today + timedelta(days_ahead)
        
        order = Order.objects.create(
            restaurant=self.customer,
            order_date=order_date,
            status='received'
        )
        
        self.assertIsNotNone(order.order_number)
        self.assertTrue(order.order_number.startswith('FB'))
        self.assertEqual(len(order.order_number), 14)  # FB + 8 digits date + 4 digits random
    
    def test_delivery_date_auto_calculation(self):
        """Test that delivery dates are automatically calculated"""
        # Find next Monday
        today = date.today()
        days_ahead = 0 - today.weekday()  # Monday
        if days_ahead <= 0:
            days_ahead += 7
        order_date = today + timedelta(days_ahead)
        
        order = Order.objects.create(
            restaurant=self.customer,
            order_date=order_date,
            status='received'
        )
        
        expected_delivery = order_date + timedelta(days=1)  # Tuesday
        self.assertEqual(order.delivery_date, expected_delivery)
    
    def test_order_clean_validation(self):
        """Test that Order.clean() validates business rules"""
        # Test invalid order date
        today = date.today()
        days_ahead = 1 - today.weekday()  # Tuesday (invalid)
        if days_ahead <= 0:
            days_ahead += 7
        invalid_order_date = today + timedelta(days_ahead)
        
        order = Order(
            restaurant=self.customer,
            order_date=invalid_order_date,
            status='received'
        )
        
        with self.assertRaises(ValidationError):
            order.clean()
    
    def test_order_static_methods(self):
        """Test Order static utility methods"""
        # Find next Monday and Tuesday
        today = date.today()
        days_ahead = 0 - today.weekday()  # Monday
        if days_ahead <= 0:
            days_ahead += 7
        next_monday = today + timedelta(days_ahead)
        
        days_ahead = 1 - today.weekday()  # Tuesday
        if days_ahead <= 0:
            days_ahead += 7
        next_tuesday = today + timedelta(days_ahead)
        
        # Test is_order_day
        self.assertTrue(Order.is_order_day(next_monday))
        self.assertFalse(Order.is_order_day(next_tuesday))
        
        # Test is_delivery_day
        self.assertFalse(Order.is_delivery_day(next_monday))
        self.assertTrue(Order.is_delivery_day(next_tuesday))


class OrderItemTest(TestCase):
    """Test OrderItem model calculations"""
    
    def setUp(self):
        # Create test data
        self.customer = User.objects.create_user(
            email='test@restaurant.com',
            password='testpass123',
            user_type='restaurant'
        )
        
        self.department = Department.objects.create(name='Test Vegetables')
        self.product = Product.objects.create(
            name='Test Lettuce',
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
            status='received'
        )
    
    def test_total_price_calculation(self):
        """Test that total_price is automatically calculated"""
        order_item = OrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=Decimal('5.00'),
            price=Decimal('25.00'),
            unit='kg'
        )
        
        expected_total = Decimal('5.00') * Decimal('25.00')
        self.assertEqual(order_item.total_price, expected_total)
    
    def test_order_item_string_representation(self):
        """Test OrderItem string representation"""
        order_item = OrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=Decimal('5.00'),
            price=Decimal('25.00'),
            unit='kg'
        )
        
        expected_str = f"{self.product.name} x5.00kg"
        self.assertEqual(str(order_item), expected_str)
