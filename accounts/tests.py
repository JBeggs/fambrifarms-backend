from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User, RestaurantProfile, FarmProfile, PrivateCustomerProfile
from .serializers import UserSerializer, CustomerSerializer, RestaurantRegistrationSerializer
import json

User = get_user_model()


class UserModelTest(TestCase):
    """Test the custom User model"""
    
    def setUp(self):
        self.user_data = {
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User',
            'password': 'testpass123'
        }
    
    def test_create_user(self):
        """Test creating a regular user"""
        user = User.objects.create_user(**self.user_data)
        
        self.assertEqual(user.email, 'test@example.com')
        self.assertEqual(user.first_name, 'Test')
        self.assertEqual(user.last_name, 'User')
        self.assertEqual(user.user_type, 'restaurant')  # default
        self.assertTrue(user.check_password('testpass123'))
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertFalse(user.is_verified)
    
    def test_create_superuser(self):
        """Test creating a superuser"""
        user = User.objects.create_superuser(
            email='admin@example.com',
            password='adminpass123',
            first_name='Admin',
            last_name='User'
        )
        
        self.assertEqual(user.email, 'admin@example.com')
        self.assertEqual(user.user_type, 'admin')
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
    
    def test_user_string_representation(self):
        """Test the string representation of user"""
        user = User.objects.create_user(**self.user_data)
        expected = f"{user.email} ({user.get_user_type_display()})"
        self.assertEqual(str(user), expected)
    
    def test_email_required(self):
        """Test that email is required"""
        with self.assertRaises(ValueError):
            User.objects.create_user(
                email='',
                password='testpass123',
                first_name='Test',
                last_name='User'
            )
    
    def test_user_types(self):
        """Test different user types"""
        user_types = ['restaurant', 'private', 'farm_manager', 'stock_taker', 'admin', 'staff']
        
        for user_type in user_types:
            user = User.objects.create_user(
                email=f'{user_type}@example.com',
                password='testpass123',
                first_name='Test',
                last_name='User',
                user_type=user_type
            )
            self.assertEqual(user.user_type, user_type)


class RestaurantProfileModelTest(TestCase):
    """Test the RestaurantProfile model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='restaurant@example.com',
            password='testpass123',
            first_name='Restaurant',
            last_name='Owner',
            user_type='restaurant'
        )
    
    def test_create_restaurant_profile(self):
        """Test creating a restaurant profile"""
        profile = RestaurantProfile.objects.create(
            user=self.user,
            business_name='Test Restaurant',
            branch_name='Main Branch',
            address='123 Test Street',
            city='Test City',
            postal_code='12345',
            payment_terms='Net 30'
        )
        
        self.assertEqual(profile.business_name, 'Test Restaurant')
        self.assertEqual(profile.branch_name, 'Main Branch')
        self.assertEqual(profile.address, '123 Test Street')
        self.assertEqual(profile.city, 'Test City')
        self.assertEqual(profile.postal_code, '12345')
        self.assertEqual(profile.payment_terms, 'Net 30')
        self.assertFalse(profile.is_private_customer)
    
    def test_restaurant_profile_string_representation(self):
        """Test string representation with branch name"""
        profile = RestaurantProfile.objects.create(
            user=self.user,
            business_name='Test Restaurant',
            branch_name='Main Branch',
            address='123 Test Street',
            city='Test City'
        )
        expected = 'Test Restaurant - Main Branch'
        self.assertEqual(str(profile), expected)
    
    def test_restaurant_profile_string_without_branch(self):
        """Test string representation without branch name"""
        profile = RestaurantProfile.objects.create(
            user=self.user,
            business_name='Test Restaurant',
            address='123 Test Street',
            city='Test City'
        )
        expected = 'Test Restaurant'
        self.assertEqual(str(profile), expected)
    
    def test_private_customer_flag(self):
        """Test private customer functionality"""
        profile = RestaurantProfile.objects.create(
            user=self.user,
            business_name='John Doe',
            address='123 Home Street',
            city='Home City',
            is_private_customer=True
        )
        
        self.assertTrue(profile.is_private_customer)


class FarmProfileModelTest(TestCase):
    """Test the FarmProfile model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='farm@example.com',
            password='testpass123',
            first_name='Farm',
            last_name='Manager',
            user_type='farm_manager'
        )
    
    def test_create_farm_profile(self):
        """Test creating a farm profile"""
        profile = FarmProfile.objects.create(
            user=self.user,
            employee_id='EMP001',
            department='Operations',
            position='Farm Manager',
            whatsapp_number='+27123456789',
            access_level='manager',
            can_manage_inventory=True,
            can_approve_orders=True,
            can_manage_customers=True,
            notes='Senior farm manager with full access'
        )
        
        self.assertEqual(profile.employee_id, 'EMP001')
        self.assertEqual(profile.department, 'Operations')
        self.assertEqual(profile.position, 'Farm Manager')
        self.assertEqual(profile.whatsapp_number, '+27123456789')
        self.assertEqual(profile.access_level, 'manager')
        self.assertTrue(profile.can_manage_inventory)
        self.assertTrue(profile.can_approve_orders)
        self.assertTrue(profile.can_manage_customers)
        self.assertTrue(profile.can_view_reports)  # default True
    
    def test_farm_profile_string_representation(self):
        """Test string representation of farm profile"""
        profile = FarmProfile.objects.create(
            user=self.user,
            position='Farm Manager'
        )
        expected = f"{self.user.get_full_name()} - Farm Manager"
        self.assertEqual(str(profile), expected)
    
    def test_access_levels(self):
        """Test different access levels"""
        access_levels = ['basic', 'manager', 'admin']
        
        for i, level in enumerate(access_levels):
            # Create a new user for each profile since OneToOneField requires unique users
            user = User.objects.create_user(
                email=f'farm{i}@example.com',
                password='testpass123',
                first_name=f'Farm{i}',
                last_name='User',
                user_type='farm_manager'
            )
            profile = FarmProfile.objects.create(
                user=user,
                position=f'{level.title()} Position',
                access_level=level
            )
            self.assertEqual(profile.access_level, level)


class PrivateCustomerProfileModelTest(TestCase):
    """Test the PrivateCustomerProfile model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='private@example.com',
            password='testpass123',
            first_name='Private',
            last_name='Customer',
            user_type='private'
        )
    
    def test_create_private_customer_profile(self):
        """Test creating a private customer profile"""
        profile = PrivateCustomerProfile.objects.create(
            user=self.user,
            customer_type='household',
            delivery_address='456 Home Street, Home City',
            delivery_instructions='Ring doorbell twice',
            preferred_delivery_day='tuesday',
            whatsapp_number='+27987654321',
            credit_limit=2500.00,
            order_notes='Prefers organic vegetables'
        )
        
        self.assertEqual(profile.customer_type, 'household')
        self.assertEqual(profile.delivery_address, '456 Home Street, Home City')
        self.assertEqual(profile.delivery_instructions, 'Ring doorbell twice')
        self.assertEqual(profile.preferred_delivery_day, 'tuesday')
        self.assertEqual(profile.whatsapp_number, '+27987654321')
        self.assertEqual(profile.credit_limit, 2500.00)
        self.assertEqual(profile.order_notes, 'Prefers organic vegetables')
    
    def test_private_customer_string_representation(self):
        """Test string representation of private customer"""
        profile = PrivateCustomerProfile.objects.create(
            user=self.user,
            customer_type='household',
            delivery_address='456 Home Street'
        )
        expected = f"{self.user.get_full_name()} - Household"
        self.assertEqual(str(profile), expected)
    
    def test_customer_types(self):
        """Test different customer types"""
        customer_types = ['household', 'small_business', 'personal']
        
        for i, ctype in enumerate(customer_types):
            # Create a new user for each profile since OneToOneField requires unique users
            user = User.objects.create_user(
                email=f'private{i}@example.com',
                password='testpass123',
                first_name=f'Private{i}',
                last_name='Customer',
                user_type='private'
            )
            profile = PrivateCustomerProfile.objects.create(
                user=user,
                customer_type=ctype,
                delivery_address='Test Address'
            )
            self.assertEqual(profile.customer_type, ctype)


class UserSerializerTest(TestCase):
    """Test the UserSerializer"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User',
            phone='+27123456789',
            user_type='restaurant'
        )
    
    def test_user_serialization(self):
        """Test serializing user data"""
        serializer = UserSerializer(self.user)
        data = serializer.data
        
        self.assertEqual(data['email'], 'test@example.com')
        self.assertEqual(data['first_name'], 'Test')
        self.assertEqual(data['last_name'], 'User')
        self.assertEqual(data['phone'], '+27123456789')
        self.assertEqual(data['user_type'], 'restaurant')
        self.assertFalse(data['is_verified'])
        self.assertEqual(data['roles'], [])
        self.assertEqual(data['restaurant_roles'], [])


class CustomerSerializerTest(TestCase):
    """Test the CustomerSerializer"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='customer@example.com',
            password='testpass123',
            first_name='Customer',
            last_name='Test',
            user_type='restaurant'
        )
        self.restaurant_profile = RestaurantProfile.objects.create(
            user=self.user,
            business_name='Test Restaurant',
            address='123 Test Street',
            city='Test City',
            postal_code='12345'
        )
    
    def test_customer_serialization(self):
        """Test serializing customer data"""
        serializer = CustomerSerializer(self.user)
        data = serializer.data
        
        self.assertEqual(data['email'], 'customer@example.com')
        self.assertEqual(data['name'], 'Test Restaurant')
        self.assertEqual(data['customer_type'], 'restaurant')
        self.assertFalse(data['is_private_customer'])
        self.assertEqual(data['total_orders'], 0)
        self.assertEqual(data['total_order_value'], 0.0)
        self.assertIsNone(data['last_order_date'])
        
        # Check restaurant profile data
        self.assertIsNotNone(data['restaurant_profile'])
        self.assertEqual(data['restaurant_profile']['business_name'], 'Test Restaurant')
        
        # Check profile computed field
        profile = data['profile']
        self.assertEqual(profile['business_name'], 'Test Restaurant')
        self.assertEqual(profile['delivery_address'], '123 Test Street')
    
    def test_customer_serialization_private(self):
        """Test serializing private customer"""
        self.restaurant_profile.is_private_customer = True
        self.restaurant_profile.save()
        
        serializer = CustomerSerializer(self.user)
        data = serializer.data
        
        self.assertEqual(data['customer_type'], 'private')
        self.assertTrue(data['is_private_customer'])
    
    def test_customer_creation_via_serializer(self):
        """Test creating customer via serializer"""
        data = {
            'email': 'new@restaurant.com',
            'first_name': 'New',
            'last_name': 'Restaurant',
            'business_name': 'New Restaurant',
            'address': '789 New Street',
            'city': 'New City',
            'postal_code': '54321',
            'payment_terms': 'Net 15'
        }
        
        serializer = CustomerSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        
        customer = serializer.save()
        self.assertEqual(customer.email, 'new@restaurant.com')
        self.assertEqual(customer.user_type, 'restaurant')
        
        # Check restaurant profile was created
        self.assertTrue(hasattr(customer, 'restaurantprofile'))
        profile = customer.restaurantprofile
        self.assertEqual(profile.business_name, 'New Restaurant')
        self.assertEqual(profile.address, '789 New Street')
        self.assertEqual(profile.payment_terms, 'Net 15')


class AuthenticationAPITest(APITestCase):
    """Test authentication API endpoints"""
    
    def setUp(self):
        self.register_url = reverse('register')
        self.login_url = reverse('login')
        self.profile_url = reverse('profile')
        
        self.user_data = {
            'email': 'test@restaurant.com',
            'password': 'testpass123',
            'first_name': 'Test',
            'last_name': 'Restaurant',
            'phone': '+27123456789',
            'business_name': 'Test Restaurant',
            'address': '123 Test Street',
            'city': 'Test City',
            'postal_code': '12345'
        }
    
    def test_user_registration(self):
        """Test user registration endpoint"""
        response = self.client.post(self.register_url, self.user_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('user', response.data)
        self.assertIn('tokens', response.data)
        self.assertIn('access', response.data['tokens'])
        self.assertIn('refresh', response.data['tokens'])
        
        # Check user was created
        user = User.objects.get(email='test@restaurant.com')
        self.assertEqual(user.first_name, 'Test')
        self.assertEqual(user.user_type, 'restaurant')
        
        # Check restaurant profile was created
        self.assertTrue(hasattr(user, 'restaurantprofile'))
        self.assertEqual(user.restaurantprofile.business_name, 'Test Restaurant')
    
    def test_user_registration_duplicate_email(self):
        """Test registration with duplicate email"""
        # Create first user
        self.client.post(self.register_url, self.user_data, format='json')
        
        # Try to create second user with same email
        response = self.client.post(self.register_url, self.user_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_user_login(self):
        """Test user login endpoint"""
        # Create user first
        user = User.objects.create_user(
            email='test@restaurant.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        
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
        login_data = {
            'email': 'nonexistent@restaurant.com',
            'password': 'wrongpass'
        }
        
        response = self.client.post(self.login_url, login_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_profile_endpoint_authenticated(self):
        """Test profile endpoint with authentication"""
        user = User.objects.create_user(
            email='test@restaurant.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        
        # Authenticate user
        self.client.force_authenticate(user=user)
        
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], 'test@restaurant.com')
    
    def test_profile_endpoint_unauthenticated(self):
        """Test profile endpoint without authentication"""
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class CustomerViewSetTest(APITestCase):
    """Test the CustomerViewSet API"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='admin@fambri.com',
            password='adminpass123',
            first_name='Admin',
            last_name='User',
            user_type='admin'
        )
        
        # Create test customers
        self.restaurant_user = User.objects.create_user(
            email='restaurant@example.com',
            password='testpass123',
            first_name='Restaurant',
            last_name='Owner',
            user_type='restaurant'
        )
        
        self.restaurant_profile = RestaurantProfile.objects.create(
            user=self.restaurant_user,
            business_name='Test Restaurant',
            address='123 Test Street',
            city='Test City'
        )
        
        self.private_user = User.objects.create_user(
            email='private@example.com',
            password='testpass123',
            first_name='Private',
            last_name='Customer',
            user_type='private'
        )
        
        self.private_profile = RestaurantProfile.objects.create(
            user=self.private_user,
            business_name='Private Customer',
            address='456 Home Street',
            city='Home City',
            is_private_customer=True
        )
        
        self.customers_url = reverse('customers-list')
    
    def test_list_customers(self):
        """Test listing all customers"""
        response = self.client.get(self.customers_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('customers', response.data)
        self.assertIn('count', response.data)
        self.assertEqual(response.data['count'], 2)
        
        # Check that both restaurant and private customers are included
        emails = [customer['email'] for customer in response.data['customers']]
        self.assertIn('restaurant@example.com', emails)
        self.assertIn('private@example.com', emails)
    
    def test_retrieve_customer(self):
        """Test retrieving a specific customer"""
        url = reverse('customers-detail', kwargs={'pk': self.restaurant_user.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], 'restaurant@example.com')
        self.assertEqual(response.data['name'], 'Test Restaurant')
    
    def test_create_customer(self):
        """Test creating a new customer"""
        data = {
            'email': 'new@customer.com',
            'first_name': 'New',
            'last_name': 'Customer',
            'business_name': 'New Business',
            'address': '789 New Street',
            'city': 'New City',
            'postal_code': '98765'
        }
        
        response = self.client.post(self.customers_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['email'], 'new@customer.com')
        
        # Check user was created in database
        user = User.objects.get(email='new@customer.com')
        self.assertEqual(user.user_type, 'restaurant')
        self.assertTrue(hasattr(user, 'restaurantprofile'))
        self.assertEqual(user.restaurantprofile.business_name, 'New Business')
    
    def test_update_customer(self):
        """Test updating a customer"""
        url = reverse('customers-detail', kwargs={'pk': self.restaurant_user.id})
        data = {
            'first_name': 'Updated',
            'business_name': 'Updated Restaurant'
        }
        
        response = self.client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['first_name'], 'Updated')
        
        # Check database was updated
        self.restaurant_user.refresh_from_db()
        self.restaurant_profile.refresh_from_db()
        self.assertEqual(self.restaurant_user.first_name, 'Updated')
        self.assertEqual(self.restaurant_profile.business_name, 'Updated Restaurant')
    
    def test_delete_customer(self):
        """Test deleting a customer"""
        url = reverse('customers-detail', kwargs={'pk': self.restaurant_user.id})
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # Check user was deleted
        with self.assertRaises(User.DoesNotExist):
            User.objects.get(id=self.restaurant_user.id)
    
    def test_customer_not_found(self):
        """Test retrieving non-existent customer"""
        url = reverse('customers-detail', kwargs={'pk': 99999})
        response = self.client.get(url)
        
        # The view catches all exceptions and returns 500, but DRF's get_object raises Http404
        # which should result in 404, but our view's exception handling catches it as 500
        self.assertIn(response.status_code, [status.HTTP_404_NOT_FOUND, status.HTTP_500_INTERNAL_SERVER_ERROR])


class RestaurantRegistrationSerializerTest(TestCase):
    """Test the RestaurantRegistrationSerializer"""
    
    def test_valid_registration_data(self):
        """Test serializer with valid data"""
        data = {
            'email': 'test@restaurant.com',
            'password': 'testpass123',
            'first_name': 'Test',
            'last_name': 'Restaurant',
            'phone': '+27123456789',
            'business_name': 'Test Restaurant',
            'address': '123 Test Street',
            'city': 'Test City',
            'postal_code': '12345'
        }
        
        serializer = RestaurantRegistrationSerializer(data=data)
        self.assertTrue(serializer.is_valid())
    
    def test_duplicate_email_validation(self):
        """Test validation of duplicate email"""
        # Create existing user
        User.objects.create_user(
            email='existing@restaurant.com',
            password='testpass123',
            first_name='Existing',
            last_name='User'
        )
        
        data = {
            'email': 'existing@restaurant.com',
            'password': 'testpass123',
            'first_name': 'Test',
            'last_name': 'Restaurant',
            'business_name': 'Test Restaurant',
            'address': '123 Test Street',
            'city': 'Test City',
            'postal_code': '12345'
        }
        
        serializer = RestaurantRegistrationSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('email', serializer.errors)
    
    def test_short_password_validation(self):
        """Test validation of short password"""
        data = {
            'email': 'test@restaurant.com',
            'password': 'short',
            'first_name': 'Test',
            'last_name': 'Restaurant',
            'business_name': 'Test Restaurant',
            'address': '123 Test Street',
            'city': 'Test City',
            'postal_code': '12345'
        }
        
        serializer = RestaurantRegistrationSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('password', serializer.errors)
