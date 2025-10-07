#!/usr/bin/env python3
"""
Debug the order processing issue
"""

import os
import sys
import django

# Add the backend directory to the Python path
sys.path.append('/Users/jodybeggs/Documents/fambrifarms_after_meeting/backend')

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'familyfarms_api.settings')
django.setup()

from whatsapp.smart_product_matcher import SmartProductMatcher
from whatsapp.services import parse_order_items, create_order_items
from whatsapp.models import WhatsAppMessage

def debug_order_processing():
    """Debug the order processing issue"""
    
    print("DEBUGGING ORDER PROCESSING")
    print("=" * 60)
    
    # Test with the order from the image
    test_message = """Good-morning-Carel, kindly add the following please.
3 Pcts Aubergines
2 Pcts Snap Peas.
Thank you."""
    
    print(f"Testing message: {test_message}")
    print()
    
    # Step 1: Test parsing
    print("STEP 1: Testing message parsing")
    matcher = SmartProductMatcher()
    parsed_items = matcher.parse_message(test_message)
    
    print(f"Parsed items: {len(parsed_items)}")
    for i, item in enumerate(parsed_items):
        print(f"  {i+1}. {item.product_name} | Qty: {item.quantity} | Unit: {item.unit} | Pkg: {item.packaging_size}")
    
    print()
    
    # Step 2: Test order item parsing
    print("STEP 2: Testing order item parsing")
    try:
        order_data = parse_order_items(test_message)
        print(f"Order data keys: {list(order_data.keys())}")
        print(f"Items: {len(order_data.get('items', []))}")
        print(f"Parsing failures: {len(order_data.get('parsing_failures', []))}")
        print(f"Failed products: {len(order_data.get('failed_products', []))}")
        
        if order_data.get('items'):
            print("Items details:")
            for i, item in enumerate(order_data['items']):
                print(f"  {i+1}. {item.get('product_name', 'N/A')} | Qty: {item.get('quantity', 'N/A')} | Unit: {item.get('unit', 'N/A')}")
                print(f"      Confidence: {item.get('confidence', 'N/A')} | Product ID: {item.get('product_id', 'N/A')}")
        
        if order_data.get('parsing_failures'):
            print("Parsing failures:")
            for i, failure in enumerate(order_data['parsing_failures']):
                print(f"  {i+1}. {failure.get('original_name', 'N/A')} - {failure.get('failure_reason', 'N/A')}")
        
        if order_data.get('failed_products'):
            print("Failed products:")
            for i, failure in enumerate(order_data['failed_products']):
                print(f"  {i+1}. {failure.get('original_name', 'N/A')} - {failure.get('failure_reason', 'N/A')}")
                
    except Exception as e:
        print(f"Error in parse_order_items: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print()
    
    # Step 3: Test with a real WhatsApp message
    print("STEP 3: Testing with real WhatsApp message")
    try:
        # Get the most recent message
        recent_message = WhatsAppMessage.objects.filter(edited=False).order_by('-id').first()
        if recent_message:
            print(f"Testing with message ID: {recent_message.id}")
            print(f"Content: {recent_message.content[:100]}...")
            
            order_data = parse_order_items(recent_message.content)
            print(f"Items: {len(order_data.get('items', []))}")
            print(f"Parsing failures: {len(order_data.get('parsing_failures', []))}")
            print(f"Failed products: {len(order_data.get('failed_products', []))}")
            
            # Check if we can create order items
            if order_data.get('items'):
                print("Attempting to create order items...")
                try:
                    # Create a test order first
                    from orders.models import Order
                    from django.contrib.auth import get_user_model
                    from django.utils import timezone
                    from datetime import date, timedelta
                    
                    User = get_user_model()
                    
                    # Get or create a test user
                    user, _ = User.objects.get_or_create(
                        email="test@example.com",
                        defaults={'first_name': 'Test', 'last_name': 'Customer'}
                    )
                    
                    # Create a test order (using Monday as order date)
                    today = date.today()
                    # Find next Monday
                    days_ahead = 0 - today.weekday()  # Monday is 0
                    if days_ahead <= 0:  # Target day already happened this week
                        days_ahead += 7
                    order_date = today + timedelta(days=days_ahead)
                    
                    test_order = Order.objects.create(
                        restaurant=user,
                        order_number=f"TEST-{timezone.now().strftime('%Y%m%d%H%M%S')}",
                        order_date=order_date,
                        delivery_date=order_date + timedelta(days=1),  # Tuesday
                        status='received'
                    )
                    
                    # Now call create_order_items with the order and message
                    result = create_order_items(test_order, recent_message)
                    print(f"Created order items: {result.get('items_created', 0)}")
                    print(f"Parsing failures: {len(result.get('parsing_failures', []))}")
                    print(f"Failed products: {len(result.get('failed_products', []))}")
                    
                    # Clean up test order
                    test_order.delete()
                    
                except Exception as e:
                    print(f"Error creating order items: {str(e)}")
                    import traceback
                    traceback.print_exc()
        else:
            print("No recent messages found")
            
    except Exception as e:
        print(f"Error testing with real message: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_order_processing()
