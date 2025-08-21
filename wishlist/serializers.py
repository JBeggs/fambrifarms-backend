from rest_framework import serializers
from .models import Wishlist, WishlistItem

class WishlistItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_price = serializers.DecimalField(source='product.price', max_digits=10, decimal_places=2, read_only=True)
    product_unit = serializers.CharField(source='product.unit', read_only=True)
    
    class Meta:
        model = WishlistItem
        fields = ['id', 'product', 'product_name', 'product_price', 'product_unit', 'quantity', 'notes', 'added_at']

class WishlistSerializer(serializers.ModelSerializer):
    items = WishlistItemSerializer(many=True, read_only=True)
    total_items = serializers.IntegerField(source='items.count', read_only=True)
    restaurant_name = serializers.SerializerMethodField()
    restaurant_business_name = serializers.SerializerMethodField()
    restaurant_address = serializers.SerializerMethodField()
    restaurant_phone = serializers.CharField(source='user.phone', read_only=True)
    restaurant_email = serializers.CharField(source='user.email', read_only=True)
    
    class Meta:
        model = Wishlist
        fields = ['id', 'user', 'restaurant_name', 'restaurant_business_name', 'restaurant_address', 
                 'restaurant_phone', 'restaurant_email', 'items', 'total_items', 'created_at', 'updated_at']
    
    def get_restaurant_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}"
    
    def get_restaurant_business_name(self, obj):
        try:
            return obj.user.restaurantprofile.business_name
        except:
            return None
    
    def get_restaurant_address(self, obj):
        try:
            profile = obj.user.restaurantprofile
            return f"{profile.address}, {profile.city}, {profile.postal_code}"
        except:
            return None 