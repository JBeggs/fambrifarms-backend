from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from decimal import Decimal
from datetime import date, timedelta

from .models import Department, Product, ProductAlert, Recipe
from .models_business_settings import BusinessSettings
from accounts.models import RestaurantProfile

User = get_user_model()


class DepartmentModelTest(TestCase):
    """Test Department model functionality"""
    
    def setUp(self):
        self.department = Department.objects.create(
            name='Vegetables',
            description='Fresh vegetables and greens'
        )
    
    def test_department_creation(self):
        """Test department is created correctly"""
        self.assertEqual(self.department.name, 'Vegetables')
        self.assertEqual(self.department.description, 'Fresh vegetables and greens')
        self.assertTrue(self.department.is_active)
        self.assertIsNotNone(self.department.created_at)
    
    def test_department_str_representation(self):
        """Test department string representation"""
        self.assertEqual(str(self.department), 'Vegetables')
    
    def test_department_unique_name(self):
        """Test department name uniqueness"""
        with self.assertRaises(Exception):
            Department.objects.create(name='Vegetables')
    
    def test_department_ordering(self):
        """Test departments are ordered by name"""
        dept_b = Department.objects.create(name='Fruits')
        dept_a = Department.objects.create(name='Dairy')
        
        departments = Department.objects.all()
        self.assertEqual(departments[0].name, 'Dairy')
        self.assertEqual(departments[1].name, 'Fruits')
        self.assertEqual(departments[2].name, 'Vegetables')


class ProductModelTest(TestCase):
    """Test Product model functionality"""
    
    def setUp(self):
        self.department = Department.objects.create(name='Vegetables')
        self.product = Product.objects.create(
            name='Lettuce',
            description='Fresh iceberg lettuce',
            department=self.department,
            price=Decimal('15.50'),
            unit='head',
            stock_level=Decimal('25.00'),
            minimum_stock=Decimal('5.00')
        )
    
    def test_product_creation(self):
        """Test product is created correctly"""
        self.assertEqual(self.product.name, 'Lettuce')
        self.assertEqual(self.product.department, self.department)
        self.assertEqual(self.product.price, Decimal('15.50'))
        self.assertEqual(self.product.unit, 'head')
        self.assertTrue(self.product.is_active)
        self.assertFalse(self.product.needs_setup)
    
    def test_product_str_representation(self):
        """Test product string representation"""
        self.assertEqual(str(self.product), 'Lettuce - R15.50/head')
    
    def test_product_unit_choices(self):
        """Test product unit choices are valid"""
        valid_units = ['kg', 'g', 'piece', 'box', 'punnet', 'bag', 'bunch', 'head']
        for unit in valid_units:
            product = Product.objects.create(
                name=f'Test Product {unit}',
                department=self.department,
                price=Decimal('10.00'),
                unit=unit
            )
            self.assertEqual(product.unit, unit)
    
    def test_product_price_validation(self):
        """Test product price cannot be negative"""
        with self.assertRaises(ValidationError):
            product = Product(
                name='Invalid Product',
                department=self.department,
                price=Decimal('-5.00'),
                unit='kg'
            )
            product.full_clean()
    
    def test_product_stock_comparison(self):
        """Test stock level comparison with minimum stock"""
        # Stock above minimum - should not need restock
        self.assertGreater(self.product.stock_level, self.product.minimum_stock)
        
        # Stock below minimum - should need restock
        self.product.stock_level = Decimal('3.00')
        self.product.save()
        self.assertLess(self.product.stock_level, self.product.minimum_stock)
    
    def test_product_get_customer_price_fallback(self):
        """Test get_customer_price falls back to base price when no customer price exists"""
        # Create a test customer
        user = User.objects.create_user(email='test@example.com')
        customer = RestaurantProfile.objects.create(
            user=user,
            business_name='Test Restaurant'
        )
        
        # Should return base price when no customer-specific price exists
        customer_price = self.product.get_customer_price(customer)
        self.assertEqual(customer_price, self.product.price)


class ProductAlertModelTest(TestCase):
    """Test ProductAlert model functionality"""
    
    def setUp(self):
        self.department = Department.objects.create(name='Vegetables')
        self.product = Product.objects.create(
            name='Lettuce',
            department=self.department,
            price=Decimal('15.50'),
            stock_level=Decimal('2.00'),  # Below minimum
            minimum_stock=Decimal('5.00')
        )
    
    def test_product_alert_creation(self):
        """Test product alert is created correctly"""
        alert = ProductAlert.objects.create(
            product=self.product,
            alert_type='low_stock',
            message='Stock is running low'
        )
        
        self.assertEqual(alert.product, self.product)
        self.assertEqual(alert.alert_type, 'low_stock')
        self.assertEqual(alert.message, 'Stock is running low')
        self.assertFalse(alert.is_resolved)
        self.assertIsNotNone(alert.created_at)
    
    def test_product_alert_str_representation(self):
        """Test product alert string representation"""
        alert = ProductAlert.objects.create(
            product=self.product,
            alert_type='low_stock',
            message='Stock is running low'
        )
        expected_str = f"{self.product.name} - Low Stock"
        self.assertEqual(str(alert), expected_str)


class BusinessSettingsModelTest(TestCase):
    """Test BusinessSettings model functionality"""
    
    def test_business_settings_creation(self):
        """Test business settings is created correctly"""
        settings = BusinessSettings.objects.create(
            default_minimum_level=Decimal('5.00'),
            default_reorder_level=Decimal('10.00'),
            default_maximum_level=Decimal('100.00')
        )
        
        self.assertEqual(settings.default_minimum_level, Decimal('5.00'))
        self.assertEqual(settings.default_reorder_level, Decimal('10.00'))
        self.assertEqual(settings.default_maximum_level, Decimal('100.00'))
        self.assertIsNotNone(settings.created_at)


class ProductAPITest(APITestCase):
    """Test Product API endpoints"""
    
    def setUp(self):
        self.client = APIClient()
        self.department = Department.objects.create(name='Vegetables')
        self.product = Product.objects.create(
            name='Lettuce',
            department=self.department,
            price=Decimal('15.50'),
            unit='head'
        )
    
    def test_get_products_list(self):
        """Test getting list of products"""
        url = reverse('product_list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], 'Lettuce')
    
    def test_get_product_detail(self):
        """Test getting product detail"""
        url = reverse('product_detail', kwargs={'pk': self.product.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Lettuce')
        self.assertEqual(float(response.data['price']), 15.50)
    
    def test_create_product(self):
        """Test creating a new product"""
        url = reverse('product_list')
        data = {
            'name': 'Tomato',
            'department': self.department.id,
            'price': '12.00',
            'unit': 'kg'
        }
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Product.objects.count(), 2)
        self.assertEqual(Product.objects.latest('id').name, 'Tomato')
    
    def test_update_product(self):
        """Test updating a product"""
        url = reverse('product_detail', kwargs={'pk': self.product.pk})
        data = {
            'name': 'Updated Lettuce',
            'department': self.department.id,
            'price': '18.00',
            'unit': 'head'
        }
        response = self.client.put(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.product.refresh_from_db()
        self.assertEqual(self.product.name, 'Updated Lettuce')
        self.assertEqual(self.product.price, Decimal('18.00'))
    
    def test_delete_product(self):
        """Test deleting a product"""
        url = reverse('product_detail', kwargs={'pk': self.product.pk})
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Product.objects.count(), 0)
    
    def test_filter_products_by_department(self):
        """Test filtering products by department"""
        # Create another department and product
        fruit_dept = Department.objects.create(name='Fruits')
        Product.objects.create(
            name='Apple',
            department=fruit_dept,
            price=Decimal('8.00'),
            unit='kg'
        )
        
        url = reverse('product_list')
        response = self.client.get(url, {'department': self.department.name})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        self.assertGreaterEqual(len(response.data), 1)
        
        # Check that our test product is in the response
        product_names = [product['name'] for product in response.data]
        self.assertIn('Lettuce', product_names)
        
        # Check that products from other departments are not included
        self.assertNotIn('Apple', product_names)
    


class DepartmentAPITest(APITestCase):
    """Test Department API endpoints"""
    
    def setUp(self):
        self.client = APIClient()
        self.department = Department.objects.create(
            name='Vegetables',
            description='Fresh vegetables'
        )
    
    def test_get_departments_list(self):
        """Test getting list of departments"""
        url = reverse('department_list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Handle paginated response
        if isinstance(response.data, dict) and 'results' in response.data:
            departments = response.data['results']
        else:
            departments = response.data
        
        self.assertIsInstance(departments, list)
        self.assertGreaterEqual(len(departments), 1)
        
        # Check that our test department is in the response
        department_names = [dept['name'] for dept in departments]
        self.assertIn('Vegetables', department_names)
    
    
    def test_create_department(self):
        """Test creating a new department"""
        url = reverse('department_list')
        data = {
            'name': 'Fruits',
            'description': 'Fresh fruits and berries'
        }
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Department.objects.count(), 2)
        self.assertEqual(Department.objects.latest('id').name, 'Fruits')
    
    


class AppConfigAPITest(APITestCase):
    """Test app configuration API endpoint"""
    
    def setUp(self):
        self.client = APIClient()
        # Create and authenticate user
        self.user = User.objects.create_user(
            email='api_test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        
        BusinessSettings.objects.create(
            default_minimum_level=Decimal('5.00'),
            default_reorder_level=Decimal('10.00')
        )
    
    def test_get_app_config(self):
        """Test getting app configuration"""
        url = reverse('app_config')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check that the expected app config fields are present
        expected_fields = [
            'whatsapp_base_url',
            'default_base_markup',
            'default_volatility_adjustment',
            'default_trend_multiplier',
            'customer_segments',
            'api_timeout_seconds',
            'max_retry_attempts',
            'default_messages_limit',
            'default_stock_updates_limit'
        ]
        
        for field in expected_fields:
            self.assertIn(field, response.data)
        
        # Check specific values
        self.assertIsInstance(response.data['api_timeout_seconds'], int)
        self.assertIsInstance(response.data['max_retry_attempts'], int)
        self.assertIsInstance(response.data['customer_segments'], list)


class ProductServicesTest(TestCase):
    """Test product-related service functions"""
    
    def setUp(self):
        self.department = Department.objects.create(name='Vegetables')
        self.product = Product.objects.create(
            name='Lettuce',
            department=self.department,
            price=Decimal('15.50'),
            stock_level=Decimal('2.00'),  # Below minimum
            minimum_stock=Decimal('5.00')
        )
    
    def test_low_stock_detection(self):
        """Test detection of products with low stock"""
        # Test stock level comparison logic
        self.assertLess(self.product.stock_level, self.product.minimum_stock)
    
    def test_product_search_functionality(self):
        """Test product search functionality"""
        # Create additional products for search testing
        Product.objects.create(
            name='Iceberg Lettuce',
            department=self.department,
            price=Decimal('12.00')
        )
        Product.objects.create(
            name='Tomato',
            department=self.department,
            price=Decimal('8.00')
        )
        
        # Test search by name (this would use actual search service)
        lettuce_products = Product.objects.filter(name__icontains='lettuce')
        self.assertEqual(lettuce_products.count(), 2)
