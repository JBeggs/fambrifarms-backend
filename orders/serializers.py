from rest_framework import serializers
from .models import Order, OrderItem
from accounts.models import RestaurantProfile

class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_description = serializers.CharField(source='product.description', read_only=True)
    product_department = serializers.CharField(source='product.department.name', read_only=True)
    product_stock_level = serializers.CharField(source='product.stock_level', read_only=True)
    product_default_unit = serializers.CharField(source='product.unit', read_only=True)
    
    # Source product information (for stock deduction from different product)
    source_product_name = serializers.CharField(source='source_product.name', read_only=True)
    source_product_stock_level = serializers.CharField(source='source_product.stock_level', read_only=True)
    source_product_unit = serializers.CharField(source='source_product.unit', read_only=True)
    
    # Pricing breakdown information
    product_base_price = serializers.CharField(source='product.price', read_only=True)
    pricing_breakdown = serializers.SerializerMethodField()
    
    # Stock status information
    stock_action = serializers.SerializerMethodField()
    stock_result = serializers.SerializerMethodField()
    
    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'product_name', 'product_description', 'product_department', 
                 'product_stock_level', 'product_default_unit', 'quantity', 'unit', 'price', 
                 'total_price', 'original_text', 'confidence_score', 'manually_corrected', 'notes',
                 'source_product', 'source_quantity', 'source_product_name', 'source_product_stock_level', 
                 'source_product_unit', 'product_base_price', 'pricing_breakdown', 'stock_action', 
                 'stock_result']
    
    def get_pricing_breakdown(self, obj):
        """Get detailed pricing breakdown for this order item"""
        try:
            from whatsapp.services import determine_customer_segment
            from inventory.models import CustomerPriceListItem, PricingRule
            from datetime import date
            
            customer = obj.order.restaurant
            product = obj.product
            base_price = float(product.price or 0)
            customer_price = float(obj.price)
            
            breakdown = {
                'base_price': base_price,
                'customer_price': customer_price,
                'price_difference': customer_price - base_price,
                'markup_percentage': ((customer_price - base_price) / base_price * 100) if base_price > 0 else 0,
                'customer_segment': determine_customer_segment(customer),
                'pricing_source': 'base_price',  # Default
                'pricing_rule': None,
                'price_list_item': None
            }
            
            # Check if price comes from customer price list
            today = date.today()
            price_item = CustomerPriceListItem.objects.filter(
                price_list__customer=customer,
                product=product,
                price_list__status='active',
                price_list__effective_from__lte=today,
                price_list__effective_until__gte=today
            ).select_related('price_list', 'price_list__pricing_rule').first()
            
            if price_item:
                breakdown['pricing_source'] = 'price_list'
                breakdown['price_list_item'] = {
                    'market_price_excl_vat': float(price_item.market_price_excl_vat),
                    'market_price_incl_vat': float(price_item.market_price_incl_vat),
                    'markup_percentage': float(price_item.markup_percentage),
                    'market_price_date': price_item.market_price_date.isoformat(),
                    'price_list_name': price_item.price_list.list_name
                }
                if price_item.price_list.pricing_rule:
                    breakdown['pricing_rule'] = {
                        'name': price_item.price_list.pricing_rule.name,
                        'base_markup_percentage': float(price_item.price_list.pricing_rule.base_markup_percentage),
                        'customer_segment': price_item.price_list.pricing_rule.customer_segment
                    }
            else:
                # Check if pricing rule was applied directly
                pricing_rule = PricingRule.objects.filter(
                    customer_segment=breakdown['customer_segment'],
                    is_active=True
                ).first()
                
                if pricing_rule and abs(breakdown['markup_percentage'] - float(pricing_rule.base_markup_percentage)) < 1:
                    breakdown['pricing_source'] = 'pricing_rule'
                    breakdown['pricing_rule'] = {
                        'name': pricing_rule.name,
                        'base_markup_percentage': float(pricing_rule.base_markup_percentage),
                        'customer_segment': pricing_rule.customer_segment
                    }
            
            return breakdown
            
        except Exception as e:
            # Return basic breakdown if detailed analysis fails
            return {
                'base_price': float(obj.product.price or 0),
                'customer_price': float(obj.price),
                'price_difference': float(obj.price) - float(obj.product.price or 0),
                'markup_percentage': 0,
                'customer_segment': 'unknown',
                'pricing_source': 'base_price',
                'error': str(e)
            }
    
    def get_stock_action(self, obj):
        """Determine the stock action that was taken for this order item"""
        try:
            from inventory.models import StockMovement
            
            # FIRST: Check by reference_number (most reliable - links directly to order)
            movement_by_ref = StockMovement.objects.filter(
                product=obj.product,
                reference_number=obj.order.order_number,
                movement_type='finished_reserve'
            ).order_by('-timestamp').first()
            
            if movement_by_ref:
                return 'reserve'
            
            # SECOND: Check by customer, product, and timing (fallback for older orders)
            from datetime import timedelta
            time_window = timedelta(minutes=5)
            start_time = obj.order.created_at - time_window
            end_time = obj.order.created_at + time_window
            
            movement = StockMovement.objects.filter(
                product=obj.product,
                user=obj.order.restaurant,  # Match by customer
                movement_type__in=['finished_reserve', 'finished_release'],
                timestamp__gte=start_time,
                timestamp__lte=end_time
            ).order_by('-timestamp').first()
            
            if movement:
                if movement.movement_type == 'finished_reserve':
                    return 'reserve'
                elif movement.movement_type == 'finished_release':
                    return 'no_reserve'
            
            # If no stock movement found, check if conversion actually happened
            # Only mark as conversion in very specific cases with clear evidence
            if (hasattr(obj, 'manually_corrected') and obj.manually_corrected and
                obj.unit and obj.unit.lower() == 'kg' and 
                obj.product and obj.product.unit and 
                obj.product.unit.lower() in ['piece', 'each']):
                return 'convert_to_kg'
            
            # Default: no stock available, no reserve made
            return 'no_reserve'
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error getting stock action for order item {obj.id}: {e}")
            return None
    
    def get_stock_result(self, obj):
        """Get the result of the stock action"""
        try:
            from inventory.models import StockMovement, FinishedInventory
            
            # FIRST: Check by reference_number (most reliable - links directly to order)
            movement_by_ref = StockMovement.objects.filter(
                product=obj.product,
                reference_number=obj.order.order_number,
                movement_type='finished_reserve'
            ).order_by('-timestamp').first()
            
            if movement_by_ref:
                return {
                    'success': True,
                    'message': f'Reserved {movement_by_ref.quantity} {obj.unit}',
                    'reserved_quantity': float(movement_by_ref.quantity)
                }
            
            # SECOND: Look for stock movement by customer, product, and timing (fallback)
            from datetime import timedelta
            time_window = timedelta(minutes=5)
            start_time = obj.order.created_at - time_window
            end_time = obj.order.created_at + time_window
            
            movement = StockMovement.objects.filter(
                product=obj.product,
                user=obj.order.restaurant,  # Match by customer
                movement_type='finished_reserve',
                timestamp__gte=start_time,
                timestamp__lte=end_time
            ).order_by('-timestamp').first()
            
            if movement:
                return {
                    'success': True,
                    'message': f'Reserved {movement.quantity} {obj.unit}',
                    'reserved_quantity': float(movement.quantity)
                }
            
            # Check if stock exists but wasn't reserved
            try:
                inventory = FinishedInventory.objects.get(product=obj.product)
                available = inventory.available_quantity or 0
                
                if available < obj.quantity:
                    return {
                        'success': False,
                        'message': f'Insufficient stock - Available: {available}, Needed: {obj.quantity}',
                        'available_quantity': float(available)
                    }
                else:
                    return {
                        'success': False,
                        'message': 'Stock not reserved - needs to be ordered',
                        'available_quantity': float(available)
                    }
            except FinishedInventory.DoesNotExist:
                return {
                    'success': False,
                    'message': 'No inventory record - needs to be ordered'
                }
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error getting stock result for order item {obj.id}: {e}")
            return None

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    restaurant_name = serializers.SerializerMethodField()
    restaurant_business_name = serializers.SerializerMethodField()
    restaurant_address = serializers.SerializerMethodField()
    restaurant_phone = serializers.CharField(source='restaurant.phone', read_only=True)
    restaurant_email = serializers.CharField(source='restaurant.email', read_only=True)
    purchase_orders = serializers.SerializerMethodField()
    
    locked_by_email = serializers.CharField(source='locked_by.email', read_only=True)
    locked_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = ['id', 'order_number', 'restaurant', 'restaurant_name', 'restaurant_business_name', 
                 'restaurant_address', 'restaurant_phone', 'restaurant_email', 'status', 'order_date',
                 'delivery_date', 'whatsapp_message_id', 'original_message', 'parsed_by_ai', 'subtotal', 
                 'total_amount', 'items', 'purchase_orders', 'locked_by', 'locked_by_email', 'locked_by_name',
                 'locked_at', 'created_at', 'updated_at']
        read_only_fields = ['id', 'order_number', 'restaurant_name', 'restaurant_business_name', 
                           'restaurant_address', 'restaurant_phone', 'restaurant_email', 'purchase_orders', 
                           'locked_by_email', 'locked_by_name', 'created_at', 'updated_at']
    
    def get_locked_by_name(self, obj):
        if obj.locked_by:
            return f"{obj.locked_by.first_name} {obj.locked_by.last_name}".strip() or obj.locked_by.email
        return None
    
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
