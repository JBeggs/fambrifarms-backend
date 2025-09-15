"""
Custom authentication classes for Fambri Farms API
"""
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.conf import settings
from django.contrib.auth import get_user_model

User = get_user_model()


class WhatsAppAPIKeyAuthentication(BaseAuthentication):
    """
    API Key authentication for WhatsApp scraper
    Allows the Python WhatsApp scraper to authenticate with a secure API key
    """
    
    def authenticate(self, request):
        api_key = request.META.get('HTTP_X_API_KEY')
        
        if not api_key:
            return None
            
        expected_key = getattr(settings, 'WHATSAPP_API_KEY', None)
        
        if not expected_key:
            raise AuthenticationFailed('WhatsApp API key not configured')
            
        if api_key != expected_key:
            raise AuthenticationFailed('Invalid WhatsApp API key')
            
        # Return a system user for WhatsApp operations
        # We'll create a special system user for this
        try:
            system_user = User.objects.get(email='system@fambrifarms.co.za')
        except User.DoesNotExist:
            # Create system user if it doesn't exist
            system_user = User.objects.create_user(
                email='system@fambrifarms.co.za',
                first_name='WhatsApp',
                last_name='System',
                user_type='admin',
                is_active=True,
                is_staff=False
            )
            
        return (system_user, None)

    def authenticate_header(self, request):
        return 'X-API-Key'


class FlexibleAuthentication(BaseAuthentication):
    """
    Flexible authentication that supports both JWT and API Key
    Used for endpoints that need to support both Karl's Flutter app and WhatsApp scraper
    """
    
    def authenticate(self, request):
        # Try API Key first
        api_key_auth = WhatsAppAPIKeyAuthentication()
        result = api_key_auth.authenticate(request)
        if result:
            return result
            
        # Try JWT authentication
        from rest_framework_simplejwt.authentication import JWTAuthentication
        jwt_auth = JWTAuthentication()
        return jwt_auth.authenticate(request)

    def authenticate_header(self, request):
        return 'Bearer'
