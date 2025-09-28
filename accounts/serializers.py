from rest_framework import serializers
from .models import User, RestaurantProfile

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'user_type', 'phone', 'is_verified', 'roles', 'restaurant_roles']

class RestaurantProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = RestaurantProfile
        fields = ['business_name', 'branch_name', 'business_registration', 'address', 'city', 'postal_code', 'payment_terms', 'is_private_customer']

class CustomerSerializer(serializers.ModelSerializer):
    """Serializer for customer (restaurant) data including profile"""
    restaurant_profile = RestaurantProfileSerializer(source='restaurantprofile', read_only=True)
    business_name = serializers.CharField(write_only=True, max_length=200)
    branch_name = serializers.CharField(write_only=True, max_length=200, required=False, allow_blank=True)
    address = serializers.CharField(write_only=True)
    city = serializers.CharField(write_only=True, max_length=100)
    postal_code = serializers.CharField(write_only=True, max_length=20, required=False, allow_blank=True)
    payment_terms = serializers.CharField(write_only=True, max_length=50, required=False, allow_blank=True, default='Net 30')
    business_registration = serializers.CharField(write_only=True, max_length=100, required=False, allow_blank=True)
    delivery_notes = serializers.CharField(write_only=True, required=False, allow_blank=True)
    order_pattern = serializers.CharField(write_only=True, max_length=200, required=False, allow_blank=True)
    preferred_pricing_rule_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    
    # Add computed fields for Flutter
    name = serializers.SerializerMethodField()
    customer_type = serializers.SerializerMethodField()
    customer_segment = serializers.SerializerMethodField()
    is_private_customer = serializers.SerializerMethodField()
    total_orders = serializers.SerializerMethodField()
    total_order_value = serializers.SerializerMethodField()
    last_order_date = serializers.SerializerMethodField()
    profile = serializers.SerializerMethodField()
    
    # Add read-only fields for business name and pricing rule
    business_name_display = serializers.SerializerMethodField()
    preferred_pricing_rule_id_display = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'phone', 'is_verified', 'user_type',
            'restaurant_profile', 'business_name', 'branch_name', 'address', 'city', 
            'postal_code', 'payment_terms', 'business_registration', 'delivery_notes', 'order_pattern', 'preferred_pricing_rule_id',
            'name', 'customer_type', 'customer_segment', 'is_private_customer', 'total_orders', 'total_order_value', 
            'last_order_date', 'profile', 'business_name_display', 'preferred_pricing_rule_id_display'
        ]
        extra_kwargs = {
            'email': {'required': True},
            'first_name': {'required': True},
            'last_name': {'required': True}
        }
    
    def get_name(self, obj):
        """Return the business name from profile or user's full name"""
        try:
            if hasattr(obj, 'restaurantprofile') and obj.restaurantprofile.business_name:
                return obj.restaurantprofile.business_name
            return f"{obj.first_name} {obj.last_name}".strip() or obj.email.split('@')[0]
        except:
            return obj.email.split('@')[0]
    
    def get_customer_type(self, obj):
        """Return customer type based on private customer flag"""
        try:
            if hasattr(obj, 'restaurantprofile') and obj.restaurantprofile.is_private_customer:
                return 'private'
            return 'restaurant'
        except:
            return 'restaurant'
    
    def get_customer_segment(self, obj):
        """Return customer segment for pricing"""
        try:
            from whatsapp.services import determine_customer_segment
            return determine_customer_segment(obj)
        except:
            return 'standard'
    
    def get_is_private_customer(self, obj):
        """Return whether this is a private customer"""
        try:
            return hasattr(obj, 'restaurantprofile') and obj.restaurantprofile.is_private_customer
        except:
            return False
    
    def get_total_orders(self, obj):
        """Return total number of orders for this customer"""
        try:
            return obj.orders.count()
        except:
            return 0
    
    def get_total_order_value(self, obj):
        """Return total value of all orders for this customer"""
        try:
            from django.db.models import Sum
            total = obj.orders.aggregate(total=Sum('total_amount'))['total']
            return float(total) if total else 0.0
        except:
            return 0.0
    
    def get_last_order_date(self, obj):
        """Return the date of the most recent order"""
        try:
            last_order = obj.orders.order_by('-created_at').first()
            return last_order.created_at.date().isoformat() if last_order else None
        except:
            return None
    
    def get_profile(self, obj):
        """Return customer profile data in the format expected by Flutter"""
        try:
            if hasattr(obj, 'restaurantprofile'):
                profile = obj.restaurantprofile
                return {
                    'id': profile.id,
                    'business_name': profile.business_name,
                    'branch_name': profile.branch_name,
                    'delivery_address': profile.address,
                    'delivery_notes': profile.delivery_notes,
                    'order_pattern': profile.order_pattern,
                    'payment_terms_days': self._extract_payment_days(profile.payment_terms),
                }
            return None
        except:
            return None
    
    def get_business_name_display(self, obj):
        """Return business name for display purposes"""
        try:
            if hasattr(obj, 'restaurantprofile') and obj.restaurantprofile.business_name:
                return obj.restaurantprofile.business_name
            return None
        except:
            return None
    
    def get_preferred_pricing_rule_id_display(self, obj):
        """Return preferred pricing rule ID for display purposes"""
        try:
            if hasattr(obj, 'restaurantprofile') and obj.restaurantprofile.preferred_pricing_rule:
                return obj.restaurantprofile.preferred_pricing_rule.id
            return None
        except:
            return None
    
    def _extract_payment_days(self, payment_terms):
        """Extract number of days from payment terms like 'Net 30' or '30 days'"""
        if not payment_terms:
            return None
        try:
            import re
            match = re.search(r'(\d+)', payment_terms)
            return int(match.group(1)) if match else None
        except:
            return None
    
    def create(self, validated_data):
        # Extract restaurant profile data
        profile_data = {
            'business_name': validated_data.pop('business_name'),
            'branch_name': validated_data.pop('branch_name', ''),
            'address': validated_data.pop('address'),
            'city': validated_data.pop('city'),
            'postal_code': validated_data.pop('postal_code', ''),
            'payment_terms': validated_data.pop('payment_terms', 'Net 30'),
            'business_registration': validated_data.pop('business_registration', ''),
            'delivery_notes': validated_data.pop('delivery_notes', ''),
            'order_pattern': validated_data.pop('order_pattern', ''),
            'preferred_pricing_rule_id': validated_data.pop('preferred_pricing_rule_id', None)
        }
        
        # Create user with restaurant type and default password
        validated_data['user_type'] = 'restaurant'
        # Generate a default password for customers created via order system
        import secrets
        import string
        default_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))
        user = User.objects.create_user(password=default_password, **validated_data)
        
        # Create restaurant profile
        profile = RestaurantProfile.objects.create(user=user, **profile_data)
        
        # Assign default pricing rule if not specified
        if not profile_data.get('preferred_pricing_rule_id'):
            try:
                from inventory.models import PricingRule
                from whatsapp.services import determine_customer_segment
                
                # Determine customer segment
                customer_segment = determine_customer_segment(user)
                
                # Find appropriate pricing rule
                default_pricing_rule = PricingRule.objects.filter(
                    customer_segment=customer_segment,
                    is_active=True
                ).first()
                
                if default_pricing_rule:
                    profile.preferred_pricing_rule = default_pricing_rule
                    profile.save()
                    print(f"[PRICING] Auto-assigned pricing rule '{default_pricing_rule.name}' to customer {user.email}")
            except Exception as e:
                print(f"[PRICING] Failed to auto-assign pricing rule: {e}")
        
        return user
    
    def update(self, instance, validated_data):
        # Extract restaurant profile data
        profile_data = {}
        for field in ['business_name', 'branch_name', 'address', 'city', 'postal_code', 'payment_terms', 'business_registration', 'delivery_notes', 'order_pattern', 'preferred_pricing_rule_id']:
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
                if attr == 'preferred_pricing_rule_id':
                    # Handle foreign key relationship
                    if value is not None:
                        from inventory.models import PricingRule
                        try:
                            pricing_rule = PricingRule.objects.get(id=value)
                            profile.preferred_pricing_rule = pricing_rule
                        except PricingRule.DoesNotExist:
                            print(f"[PRICING] Pricing rule with id {value} not found")
                            profile.preferred_pricing_rule = None
                    else:
                        profile.preferred_pricing_rule = None
                else:
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