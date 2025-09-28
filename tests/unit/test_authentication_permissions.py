"""
Unit tests for authentication and permission classes
Tests custom authentication, API key validation, and permission logic
"""

from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.conf import settings
from rest_framework.exceptions import AuthenticationFailed
from unittest.mock import patch

from familyfarms_api.authentication import WhatsAppAPIKeyAuthentication, FlexibleAuthentication

User = get_user_model()


class WhatsAppAPIKeyAuthenticationTest(TestCase):
    """Test WhatsApp API Key authentication"""
    
    def setUp(self):
        self.factory = RequestFactory()
        self.auth = WhatsAppAPIKeyAuthentication()
        
        # Create a test API key
        self.test_api_key = 'test-whatsapp-api-key-12345'
        
    def test_authenticate_with_valid_api_key(self):
        """Test authentication with valid API key"""
        request = self.factory.get('/api/test/')
        request.META['HTTP_X_API_KEY'] = self.test_api_key
        
        with patch.object(settings, 'WHATSAPP_API_KEY', self.test_api_key):
            result = self.auth.authenticate(request)
            
            self.assertIsNotNone(result)
            user, auth = result
            self.assertEqual(user.email, 'system@fambrifarms.co.za')
            self.assertEqual(user.user_type, 'admin')
            self.assertIsNone(auth)
    
    def test_authenticate_without_api_key(self):
        """Test authentication without API key returns None"""
        request = self.factory.get('/api/test/')
        # No API key in headers
        
        result = self.auth.authenticate(request)
        
        self.assertIsNone(result)
    
    def test_authenticate_with_invalid_api_key(self):
        """Test authentication with invalid API key raises exception"""
        request = self.factory.get('/api/test/')
        request.META['HTTP_X_API_KEY'] = 'invalid-key'
        
        with patch.object(settings, 'WHATSAPP_API_KEY', self.test_api_key):
            with self.assertRaises(AuthenticationFailed) as context:
                self.auth.authenticate(request)
            
            self.assertIn('Invalid WhatsApp API key', str(context.exception))
    
    def test_authenticate_without_configured_api_key(self):
        """Test authentication when API key is not configured"""
        request = self.factory.get('/api/test/')
        request.META['HTTP_X_API_KEY'] = 'some-key'
        
        with patch.object(settings, 'WHATSAPP_API_KEY', None):
            with self.assertRaises(AuthenticationFailed) as context:
                self.auth.authenticate(request)
            
            self.assertIn('WhatsApp API key not configured', str(context.exception))
    
    def test_authenticate_creates_system_user_if_not_exists(self):
        """Test that system user is created if it doesn't exist"""
        # Ensure system user doesn't exist
        User.objects.filter(email='system@fambrifarms.co.za').delete()
        
        request = self.factory.get('/api/test/')
        request.META['HTTP_X_API_KEY'] = self.test_api_key
        
        with patch.object(settings, 'WHATSAPP_API_KEY', self.test_api_key):
            result = self.auth.authenticate(request)
            
            self.assertIsNotNone(result)
            user, auth = result
            
            # Verify system user was created
            system_user = User.objects.get(email='system@fambrifarms.co.za')
            self.assertEqual(system_user.first_name, 'WhatsApp')
            self.assertEqual(system_user.last_name, 'System')
            self.assertEqual(system_user.user_type, 'admin')
            self.assertTrue(system_user.is_active)
            self.assertFalse(system_user.is_staff)
    
    def test_authenticate_uses_existing_system_user(self):
        """Test that existing system user is used"""
        # Create system user first
        existing_user = User.objects.create_user(
            email='system@fambrifarms.co.za',
            first_name='Existing',
            last_name='System',
            user_type='admin'
        )
        
        request = self.factory.get('/api/test/')
        request.META['HTTP_X_API_KEY'] = self.test_api_key
        
        with patch.object(settings, 'WHATSAPP_API_KEY', self.test_api_key):
            result = self.auth.authenticate(request)
            
            self.assertIsNotNone(result)
            user, auth = result
            
            # Should use existing user
            self.assertEqual(user.id, existing_user.id)
            self.assertEqual(user.first_name, 'Existing')
    
    def test_authenticate_header(self):
        """Test authenticate header method"""
        request = self.factory.get('/api/test/')
        
        header = self.auth.authenticate_header(request)
        
        self.assertEqual(header, 'X-API-Key')


class FlexibleAuthenticationTest(TestCase):
    """Test flexible authentication class"""
    
    def setUp(self):
        self.factory = RequestFactory()
        self.auth = FlexibleAuthentication()
        self.test_api_key = 'test-api-key-12345'
        
        # Create test user for JWT
        self.test_user = User.objects.create_user(
            email='test@fambrifarms.com',
            password='testpass123',
            user_type='admin'
        )
    
    def test_authenticate_with_api_key(self):
        """Test authentication with API key takes precedence"""
        request = self.factory.get('/api/test/')
        request.META['HTTP_X_API_KEY'] = self.test_api_key
        
        with patch.object(settings, 'WHATSAPP_API_KEY', self.test_api_key):
            result = self.auth.authenticate(request)
            
            self.assertIsNotNone(result)
            user, auth = result
            self.assertEqual(user.email, 'system@fambrifarms.co.za')
    
    def test_authenticate_with_jwt_fallback(self):
        """Test JWT authentication fallback when no API key"""
        from rest_framework_simplejwt.tokens import RefreshToken
        
        # Generate JWT token
        refresh = RefreshToken.for_user(self.test_user)
        access_token = str(refresh.access_token)
        
        request = self.factory.get('/api/test/')
        request.META['HTTP_AUTHORIZATION'] = f'Bearer {access_token}'
        
        result = self.auth.authenticate(request)
        
        self.assertIsNotNone(result)
        user, auth = result
        self.assertEqual(user.id, self.test_user.id)
    
    def test_authenticate_no_credentials(self):
        """Test authentication with no credentials returns None"""
        request = self.factory.get('/api/test/')
        # No credentials provided
        
        result = self.auth.authenticate(request)
        
        self.assertIsNone(result)
    
    def test_authenticate_header(self):
        """Test authenticate header method"""
        request = self.factory.get('/api/test/')
        
        header = self.auth.authenticate_header(request)
        
        self.assertEqual(header, 'Bearer')


class AuthenticationIntegrationTest(TestCase):
    """Test authentication integration with views"""
    
    def setUp(self):
        self.test_api_key = 'test-integration-key'
        
        # Create test user
        self.test_user = User.objects.create_user(
            email='integration@test.com',
            password='testpass123',
            user_type='admin'
        )
    
    def test_whatsapp_endpoint_with_api_key(self):
        """Test WhatsApp endpoint authentication with API key"""
        from django.test import Client
        
        client = Client()
        
        with patch.object(settings, 'WHATSAPP_API_KEY', self.test_api_key):
            response = client.get(
                '/api/whatsapp/health/',
                HTTP_X_API_KEY=self.test_api_key
            )
            
            # Should authenticate successfully
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()['status'], 'healthy')
    
    def test_whatsapp_endpoint_without_api_key(self):
        """Test WhatsApp endpoint without API key fails"""
        from django.test import Client
        
        client = Client()
        
        response = client.get('/api/whatsapp/health/')
        
        # Should fail authentication
        self.assertEqual(response.status_code, 401)
    
    def test_whatsapp_endpoint_with_invalid_api_key(self):
        """Test WhatsApp endpoint with invalid API key fails"""
        from django.test import Client
        
        client = Client()
        
        with patch.object(settings, 'WHATSAPP_API_KEY', self.test_api_key):
            response = client.get(
                '/api/whatsapp/health/',
                HTTP_X_API_KEY='invalid-key'
            )
            
            # Should fail authentication
            self.assertEqual(response.status_code, 401)


class SystemUserManagementTest(TestCase):
    """Test system user creation and management"""
    
    def setUp(self):
        self.auth = WhatsAppAPIKeyAuthentication()
        self.test_api_key = 'test-system-user-key'
    
    def test_system_user_properties(self):
        """Test system user has correct properties"""
        request = RequestFactory().get('/api/test/')
        request.META['HTTP_X_API_KEY'] = self.test_api_key
        
        with patch.object(settings, 'WHATSAPP_API_KEY', self.test_api_key):
            result = self.auth.authenticate(request)
            
            user, auth = result
            
            # Verify system user properties
            self.assertEqual(user.email, 'system@fambrifarms.co.za')
            self.assertEqual(user.first_name, 'WhatsApp')
            self.assertEqual(user.last_name, 'System')
            self.assertEqual(user.user_type, 'admin')
            self.assertTrue(user.is_active)
            self.assertFalse(user.is_staff)
            self.assertFalse(user.is_superuser)
    
    def test_system_user_permissions(self):
        """Test system user has appropriate permissions"""
        request = RequestFactory().get('/api/test/')
        request.META['HTTP_X_API_KEY'] = self.test_api_key
        
        with patch.object(settings, 'WHATSAPP_API_KEY', self.test_api_key):
            result = self.auth.authenticate(request)
            
            user, auth = result
            
            # System user should be admin type but not staff
            self.assertEqual(user.user_type, 'admin')
            self.assertFalse(user.is_staff)
            
            # Should be able to access WhatsApp endpoints
            self.assertTrue(user.is_active)
    
    def test_multiple_authentication_attempts_same_user(self):
        """Test multiple authentication attempts return same system user"""
        request1 = RequestFactory().get('/api/test/')
        request1.META['HTTP_X_API_KEY'] = self.test_api_key
        
        request2 = RequestFactory().get('/api/test/')
        request2.META['HTTP_X_API_KEY'] = self.test_api_key
        
        with patch.object(settings, 'WHATSAPP_API_KEY', self.test_api_key):
            result1 = self.auth.authenticate(request1)
            result2 = self.auth.authenticate(request2)
            
            user1, auth1 = result1
            user2, auth2 = result2
            
            # Should return the same user instance
            self.assertEqual(user1.id, user2.id)
            self.assertEqual(user1.email, user2.email)
            
            # Should only have one system user in database
            system_users = User.objects.filter(email='system@fambrifarms.co.za')
            self.assertEqual(system_users.count(), 1)
