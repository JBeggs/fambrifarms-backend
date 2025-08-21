from rest_framework import serializers
from .models import Order, OrderItem
from accounts.models import RestaurantProfile

class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    
    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'product_name', 'quantity', 'price', 'total_price', 'notes']

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    restaurant_name = serializers.SerializerMethodField()
    restaurant_business_name = serializers.SerializerMethodField()
    restaurant_address = serializers.SerializerMethodField()
    restaurant_phone = serializers.CharField(source='restaurant.phone', read_only=True)
    restaurant_email = serializers.CharField(source='restaurant.email', read_only=True)
    
    class Meta:
        model = Order
        fields = ['id', 'order_number', 'restaurant', 'restaurant_name', 'restaurant_business_name', 
                 'restaurant_address', 'restaurant_phone', 'restaurant_email', 'status', 'subtotal', 
                 'total_amount', 'items', 'created_at', 'updated_at']
    
    def get_restaurant_name(self, obj):
        return f"{obj.restaurant.first_name} {obj.restaurant.last_name}"
    
    def get_restaurant_business_name(self, obj):
        try:
            return obj.restaurant.restaurantprofile.business_name
        except:
            return None
    
    def get_restaurant_address(self, obj):
        try:
            profile = obj.restaurant.restaurantprofile
            return f"{profile.address}, {profile.city}, {profile.postal_code}"
        except:
            return None 