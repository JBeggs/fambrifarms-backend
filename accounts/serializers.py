from rest_framework import serializers
from .models import User, RestaurantProfile

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'user_type', 'phone', 'is_verified', 'roles', 'restaurant_roles']

class RestaurantProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = RestaurantProfile
        fields = ['business_name', 'branch_name', 'business_registration', 'address', 'city', 'postal_code', 'payment_terms']

class CustomerSerializer(serializers.ModelSerializer):
    """Serializer for customer (restaurant) data including profile"""
    restaurant_profile = RestaurantProfileSerializer(source='restaurantprofile', read_only=True)
    business_name = serializers.CharField(write_only=True, max_length=200)
    branch_name = serializers.CharField(write_only=True, max_length=200, required=False)
    address = serializers.CharField(write_only=True)
    city = serializers.CharField(write_only=True, max_length=100)
    postal_code = serializers.CharField(write_only=True, max_length=20, required=False)
    payment_terms = serializers.CharField(write_only=True, max_length=50, required=False, default='Net 30')
    business_registration = serializers.CharField(write_only=True, max_length=100, required=False)
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'phone', 'is_verified',
            'restaurant_profile', 'business_name', 'branch_name', 'address', 'city', 
            'postal_code', 'payment_terms', 'business_registration'
        ]
        extra_kwargs = {
            'email': {'required': True},
            'first_name': {'required': True},
            'last_name': {'required': True}
        }
    
    def create(self, validated_data):
        # Extract restaurant profile data
        profile_data = {
            'business_name': validated_data.pop('business_name'),
            'branch_name': validated_data.pop('branch_name', ''),
            'address': validated_data.pop('address'),
            'city': validated_data.pop('city'),
            'postal_code': validated_data.pop('postal_code', ''),
            'payment_terms': validated_data.pop('payment_terms', 'Net 30'),
            'business_registration': validated_data.pop('business_registration', '')
        }
        
        # Create user with restaurant type and default password
        validated_data['user_type'] = 'restaurant'
        # Generate a default password for customers created via order system
        import secrets
        import string
        default_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))
        user = User.objects.create_user(password=default_password, **validated_data)
        
        # Create restaurant profile
        RestaurantProfile.objects.create(user=user, **profile_data)
        
        return user
    
    def update(self, instance, validated_data):
        # Extract restaurant profile data
        profile_data = {}
        for field in ['business_name', 'branch_name', 'address', 'city', 'postal_code', 'payment_terms', 'business_registration']:
            if field in validated_data:
                profile_data[field] = validated_data.pop(field)
        
        # Update user fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update restaurant profile if data provided
        if profile_data:
            profile, created = RestaurantProfile.objects.get_or_create(user=instance)
            for attr, value in profile_data.items():
                setattr(profile, attr, value)
            profile.save()
        
        return instance

class RestaurantRegistrationSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(min_length=8)
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    phone = serializers.CharField(max_length=20, required=False)
    business_name = serializers.CharField(max_length=200)
    address = serializers.CharField()
    city = serializers.CharField(max_length=100)
    postal_code = serializers.CharField(max_length=20)
    
    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already exists")
        return value 