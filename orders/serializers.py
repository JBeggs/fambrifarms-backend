from rest_framework import serializers
from .models import Order, OrderItem
from accounts.models import RestaurantProfile

class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_description = serializers.CharField(source='product.description', read_only=True)
    product_department = serializers.CharField(source='product.department.name', read_only=True)
    product_stock_level = serializers.CharField(source='product.stock_level', read_only=True)
    product_default_unit = serializers.CharField(source='product.unit', read_only=True)
    
    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'product_name', 'product_description', 'product_department', 
                 'product_stock_level', 'product_default_unit', 'quantity', 'unit', 'price', 
                 'total_price', 'original_text', 'confidence_score', 'manually_corrected', 'notes']

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    restaurant_name = serializers.SerializerMethodField()
    restaurant_business_name = serializers.SerializerMethodField()
    restaurant_address = serializers.SerializerMethodField()
    restaurant_phone = serializers.CharField(source='restaurant.phone', read_only=True)
    restaurant_email = serializers.CharField(source='restaurant.email', read_only=True)
    purchase_orders = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = ['id', 'order_number', 'restaurant', 'restaurant_name', 'restaurant_business_name', 
                 'restaurant_address', 'restaurant_phone', 'restaurant_email', 'status', 'order_date',
                 'delivery_date', 'whatsapp_message_id', 'original_message', 'parsed_by_ai', 'subtotal', 
                 'total_amount', 'items', 'purchase_orders', 'created_at', 'updated_at']
        read_only_fields = ['id', 'order_number', 'restaurant_name', 'restaurant_business_name', 
                           'restaurant_address', 'restaurant_phone', 'restaurant_email', 'purchase_orders', 
                           'created_at', 'updated_at']
    
    def get_restaurant_name(self, obj):
        return f"{obj.restaurant.first_name} {obj.restaurant.last_name}"
    
    def get_restaurant_business_name(self, obj):
        try:
            return obj.restaurant.restaurantprofile.business_name
        except AttributeError:
            # Restaurant profile doesn't exist or business_name not set
            return None
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error getting restaurant business name for order {obj.id}: {e}")
            return None
    
    def get_restaurant_address(self, obj):
        try:
            profile = obj.restaurant.restaurantprofile
            return f"{profile.address}, {profile.city}, {profile.postal_code}"
        except AttributeError:
            # Restaurant profile doesn't exist or address fields not set
            return None
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error getting restaurant address for order {obj.id}: {e}")
            return None 
    
    def get_purchase_orders(self, obj):
        """Get basic info about purchase orders for this order"""
        try:
            pos = obj.purchase_orders.all()
            return [{'id': po.id, 'po_number': po.po_number, 'status': po.status} for po in pos]
        except AttributeError:
            # No purchase_orders relation
            return []
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error getting purchase orders for order {obj.id}: {e}")
            return []
