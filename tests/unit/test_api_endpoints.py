"""
Unit tests for API endpoints
Tests authentication, registration, product APIs, and core endpoints
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from decimal import Decimal
import json

from accounts.models import RestaurantProfile, FarmProfile
from products.models import Product, Department
from orders.models import Order, OrderItem
from datetime import date, timedelta

User = get_user_model()


class AuthenticationAPITest(TestCase):
    """Test authentication endpoints"""
    
    def setUp(self):
        self.client = APIClient()
        self.register_url = reverse('register')
        self.login_url = reverse('login')
        self.profile_url = reverse('profile')
        
        # Create test user
        self.test_user = User.objects.create_user(
            email='test@restaurant.com',
            password='testpass123',
            first_name='Test',
            last_name='Restaurant',
            user_type='restaurant'
        )
        
        RestaurantProfile.objects.create(
            user=self.test_user,
            business_name='Test Restaurant',
            address='123 Test St',
            city='Test City',
            postal_code='12345'
        )
    
    def test_user_registration_success(self):
        """Test successful user registration"""
        registration_data = {
            'email': 'newuser@restaurant.com',
            'password': 'newpass123',
            'first_name': 'New',
            'last_name': 'User',
            'business_name': 'New Restaurant',
            'address': '456 New St',
            'city': 'New City',
            'postal_code': '67890'
        }
        
        response = self.client.post(self.register_url, registration_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('user', response.data)
        self.assertIn('tokens', response.data)
        self.assertIn('access', response.data['tokens'])
        self.assertIn('refresh', response.data['tokens'])
        
        # Verify user was created
        user = User.objects.get(email='newuser@restaurant.com')
        self.assertEqual(user.first_name, 'New')
        self.assertEqual(user.user_type, 'restaurant')
        
        # Verify restaurant profile was created
        profile = RestaurantProfile.objects.get(user=user)
        self.assertEqual(profile.business_name, 'New Restaurant')
    
    def test_user_registration_invalid_data(self):
        """Test registration with invalid data"""
        invalid_data = {
            'email': 'invalid-email',
            'password': '123',  # Too short
            'first_name': '',   # Required field empty
        }
        
        response = self.client.post(self.register_url, invalid_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)
    
    def test_user_registration_duplicate_email(self):
        """Test registration with existing email"""
        duplicate_data = {
            'email': 'test@restaurant.com',  # Already exists
            'password': 'newpass123',
            'first_name': 'Duplicate',
            'last_name': 'User',
            'business_name': 'Duplicate Restaurant',
            'address': '789 Duplicate St',
            'city': 'Duplicate City',
            'postal_code': '11111'
        }
        
        response = self.client.post(self.register_url, duplicate_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_user_login_success(self):
        """Test successful user login"""
        login_data = {
            'email': 'test@restaurant.com',
            'password': 'testpass123'
        }
        
        response = self.client.post(self.login_url, login_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('user', response.data)
        self.assertIn('tokens', response.data)
        self.assertEqual(response.data['user']['email'], 'test@restaurant.com')
    
    def test_user_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        invalid_data = {
            'email': 'test@restaurant.com',
            'password': 'wrongpassword'
        }
        
        response = self.client.post(self.login_url, invalid_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('error', response.data)
    
    def test_user_login_nonexistent_user(self):
        """Test login with non-existent user"""
        nonexistent_data = {
            'email': 'nonexistent@restaurant.com',
            'password': 'somepassword'
        }
        
        response = self.client.post(self.login_url, nonexistent_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_profile_access_authenticated(self):
        """Test profile access with authentication"""
        self.client.force_authenticate(user=self.test_user)
        
        response = self.client.get(self.profile_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], 'test@restaurant.com')
        self.assertEqual(response.data['user_type'], 'restaurant')
    
    def test_profile_access_unauthenticated(self):
        """Test profile access without authentication"""
        response = self.client.get(self.profile_url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class ProductAPITest(TestCase):
    """Test product-related API endpoints"""
    
    def setUp(self):
        self.client = APIClient()
        
        # Create test data
        self.department = Department.objects.create(
            name='Test Vegetables',
            description='Fresh vegetables'
        )
        
        self.product1 = Product.objects.create(
            name='Test Lettuce',
            department=self.department,
            price=Decimal('25.00'),
            unit='kg',
            is_active=True
        )
        
        self.product2 = Product.objects.create(
            name='Test Tomatoes',
            department=self.department,
            price=Decimal('30.00'),
            unit='kg',
            is_active=True,
            needs_setup=True
        )
        
        # URLs
        self.products_url = reverse('product-list')
        self.departments_url = reverse('department-list')
        self.app_config_url = reverse('app-config')
    
    def test_product_list_all(self):
        """Test retrieving all products"""
        response = self.client.get(self.products_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        
        # Check product data structure
        product_data = response.data[0]
        self.assertIn('id', product_data)
        self.assertIn('name', product_data)
        self.assertIn('price', product_data)
        self.assertIn('department', product_data)
    
    def test_product_list_filter_by_needs_setup(self):
        """Test filtering products by needs_setup"""
        response = self.client.get(self.products_url, {'needs_setup': 'true'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], 'Test Tomatoes')
        self.assertTrue(response.data[0]['needs_setup'])
    
    def test_product_list_filter_by_department(self):
        """Test filtering products by department"""
        response = self.client.get(self.products_url, {'department': 'vegetables'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        
        # All products should be from vegetables department
        for product in response.data:
            self.assertIn('vegetables', product['department']['name'].lower())
    
    def test_product_detail_view(self):
        """Test retrieving individual product details"""
        product_detail_url = reverse('product-detail', kwargs={'pk': self.product1.pk})
        response = self.client.get(product_detail_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Test Lettuce')
        self.assertEqual(str(response.data['price']), '25.00')
    
    def test_product_detail_not_found(self):
        """Test retrieving non-existent product"""
        product_detail_url = reverse('product-detail', kwargs={'pk': 99999})
        response = self.client.get(product_detail_url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_department_list(self):
        """Test retrieving department list"""
        response = self.client.get(self.departments_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], 'Test Vegetables')
    
    def test_app_config_endpoint(self):
        """Test app configuration endpoint"""
        response = self.client.get(self.app_config_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should return configuration data
        self.assertIn('business_hours', response.data)


class CustomerAPITest(TestCase):
    """Test customer management API endpoints"""
    
    def setUp(self):
        self.client = APIClient()
        
        # Create test customers
        self.customer1 = User.objects.create_user(
            email='customer1@restaurant.com',
            password='testpass123',
            first_name='Customer',
            last_name='One',
            user_type='restaurant'
        )
        
        RestaurantProfile.objects.create(
            user=self.customer1,
            business_name='Restaurant One',
            address='123 Restaurant St',
            city='Food City',
            postal_code='12345'
        )
        
        self.customer2 = User.objects.create_user(
            email='customer2@private.com',
            password='testpass123',
            first_name='Private',
            last_name='Customer',
            user_type='private'
        )
        
        self.customers_url = reverse('customer-list')
    
    def test_customer_list(self):
        """Test retrieving customer list"""
        response = self.client.get(self.customers_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('customers', response.data)
        self.assertIn('count', response.data)
        self.assertEqual(response.data['count'], 2)
        
        # Check customer data structure
        customers = response.data['customers']
        self.assertEqual(len(customers), 2)
        
        customer_data = customers[0]
        self.assertIn('id', customer_data)
        self.assertIn('email', customer_data)
        self.assertIn('user_type', customer_data)
    
    def test_customer_create(self):
        """Test creating a new customer"""
        new_customer_data = {
            'email': 'newcustomer@restaurant.com',
            'first_name': 'New',
            'last_name': 'Customer',
            'user_type': 'restaurant',
            'business_name': 'New Restaurant',
            'address': '456 New St',
            'city': 'New City',
            'postal_code': '67890'
        }
        
        response = self.client.post(self.customers_url, new_customer_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['email'], 'newcustomer@restaurant.com')
        
        # Verify customer was created in database
        customer = User.objects.get(email='newcustomer@restaurant.com')
        self.assertEqual(customer.user_type, 'restaurant')
    
    def test_customer_create_invalid_data(self):
        """Test creating customer with invalid data"""
        invalid_data = {
            'email': 'invalid-email',
            'first_name': '',
            'user_type': 'invalid_type'
        }
        
        response = self.client.post(self.customers_url, invalid_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_customer_detail_view(self):
        """Test retrieving individual customer details"""
        customer_detail_url = reverse('customer-detail', kwargs={'pk': self.customer1.pk})
        response = self.client.get(customer_detail_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], 'customer1@restaurant.com')
    
    def test_customer_update(self):
        """Test updating customer information"""
        customer_detail_url = reverse('customer-detail', kwargs={'pk': self.customer1.pk})
        update_data = {
            'first_name': 'Updated',
            'last_name': 'Name'
        }
        
        response = self.client.patch(customer_detail_url, update_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['first_name'], 'Updated')
        
        # Verify update in database
        self.customer1.refresh_from_db()
        self.assertEqual(self.customer1.first_name, 'Updated')
    
    def test_customer_delete(self):
        """Test deleting a customer"""
        customer_detail_url = reverse('customer-detail', kwargs={'pk': self.customer2.pk})
        response = self.client.delete(customer_detail_url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # Verify customer was deleted
        with self.assertRaises(User.DoesNotExist):
            User.objects.get(pk=self.customer2.pk)


class OrderAPITest(TestCase):
    """Test order-related API endpoints"""
    
    def setUp(self):
        self.client = APIClient()
        
        # Create test data
        self.customer = User.objects.create_user(
            email='customer@restaurant.com',
            password='testpass123',
            user_type='restaurant'
        )
        
        RestaurantProfile.objects.create(
            user=self.customer,
            business_name='Test Restaurant',
            address='123 Test St',
            city='Test City',
            postal_code='12345'
        )
        
        self.department = Department.objects.create(name='Vegetables')
        self.product = Product.objects.create(
            name='Lettuce',
            department=self.department,
            price=Decimal('25.00'),
            unit='kg'
        )
        
        # Find next valid order date (Monday)
        today = date.today()
        days_ahead = 0 - today.weekday()
        if days_ahead <= 0:
            days_ahead += 7
        self.order_date = today + timedelta(days_ahead)
        
        self.order = Order.objects.create(
            restaurant=self.customer,
            order_date=self.order_date,
            status='received'
        )
        
        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=Decimal('10.00'),
            price=Decimal('25.00'),
            unit='kg'
        )
        
        self.orders_url = reverse('order-list')
    
    def test_order_list(self):
        """Test retrieving order list"""
        response = self.client.get(self.orders_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        
        order_data = response.data[0]
        self.assertIn('order_number', order_data)
        self.assertIn('restaurant', order_data)
        self.assertIn('items', order_data)
        self.assertEqual(order_data['status'], 'received')
    
    def test_order_detail_view(self):
        """Test retrieving individual order details"""
        order_detail_url = reverse('order-detail', kwargs={'pk': self.order.pk})
        response = self.client.get(order_detail_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['order_number'], self.order.order_number)
        self.assertEqual(len(response.data['items']), 1)
    
    def test_customer_orders_view(self):
        """Test retrieving orders for specific customer"""
        customer_orders_url = reverse('customer-orders', kwargs={'customer_id': self.customer.pk})
        response = self.client.get(customer_orders_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['restaurant']['id'], self.customer.pk)
    
    def test_order_update(self):
        """Test updating order information"""
        order_detail_url = reverse('order-detail', kwargs={'pk': self.order.pk})
        update_data = {
            'status': 'confirmed'
        }
        
        response = self.client.patch(order_detail_url, update_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'confirmed')
        
        # Verify update in database
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'confirmed')
    
    def test_add_order_item(self):
        """Test adding item to existing order"""
        add_item_url = reverse('add-order-item', kwargs={'order_id': self.order.pk})
        item_data = {
            'product_name': 'Tomatoes',
            'quantity': 5.0,
            'unit': 'kg',
            'price': 30.0
        }
        
        response = self.client.post(add_item_url, item_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['product']['name'], 'Tomatoes')
        
        # Verify item was added to order
        self.assertEqual(self.order.items.count(), 2)
    
    def test_update_order_item(self):
        """Test updating existing order item"""
        order_item = self.order.items.first()
        update_item_url = reverse('update-order-item', kwargs={
            'order_id': self.order.pk,
            'item_id': order_item.pk
        })
        
        update_data = {
            'quantity': 15.0,
            'price': 28.0
        }
        
        response = self.client.patch(update_item_url, update_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(float(response.data['quantity']), 15.0)
        
        # Verify update in database
        order_item.refresh_from_db()
        self.assertEqual(order_item.quantity, Decimal('15.0'))
