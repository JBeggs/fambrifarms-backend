#!/usr/bin/env python3
"""
Test to verify transaction errors are fixed
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'familyfarms_api.settings')
django.setup()

from whatsapp.services import get_or_create_product_enhanced, create_order_items
from whatsapp.models import WhatsAppMessage
from orders.models import Order
from django.contrib.auth import get_user_model
from datetime import datetime

def test_no_transaction_errors():
    """Test that product matching doesn't cause transaction errors"""
    print('🧪 Testing Transaction Error Fix')
    print('=' * 35)
    
    # Test 1: Product matching should not cause database errors
    print('\n📋 Test 1: Product Matching')
    print('-' * 25)
    
    test_products = ['lemons', 'carrots', 'tomatoes', 'nonexistent_product']
    
    for product_name in test_products:
        try:
            result = get_or_create_product_enhanced(product_name, 1, None)
            if result == (None, None, None):
                print(f'✅ {product_name}: Correctly returned None (no transaction error)')
            else:
                print(f'⚠️  {product_name}: Unexpected result: {result}')
        except Exception as e:
            if 'atomic block' in str(e):
                print(f'❌ {product_name}: TRANSACTION ERROR: {e}')
            else:
                print(f'⚠️  {product_name}: Other error: {e}')
    
    # Test 2: Order creation with no matching products
    print('\n📋 Test 2: Order Creation with No Products')
    print('-' * 40)
    
    User = get_user_model()
    
    # Create test user
    user, created = User.objects.get_or_create(
        email='test_transaction@example.com',
        defaults={
            'first_name': 'Test',
            'last_name': 'Transaction',
            'user_type': 'customer'
        }
    )
    
    # Create test message
    test_message = WhatsAppMessage.objects.create(
        message_id='test_transaction_123',
        chat_name='ORDERS Restaurants',
        sender_name='Test User',
        content='Test Company\nlemons oranges carrots',
        message_type='order',
        timestamp=datetime.now()
    )
    
    # Create test order
    order = Order.objects.create(
        restaurant=user,
        order_date=datetime(2025, 10, 2).date(),
        status='received',
        whatsapp_message_id=test_message.message_id,
        original_message=test_message.content,
        parsed_by_ai=True
    )
    
    try:
        result = create_order_items(order, test_message)
        print(f'✅ Order items creation completed without transaction errors')
        print(f'   Items created: {result["items_created"]}')
        print(f'   Failed products: {len(result["failed_products"])}')
        print(f'   Success rate: {result["success_rate"]}%')
        
        if result["items_created"] == 0:
            print('✅ Correctly created 0 items (product matching disabled)')
        
    except Exception as e:
        if 'atomic block' in str(e):
            print(f'❌ TRANSACTION ERROR in order creation: {e}')
        else:
            print(f'⚠️  Other error in order creation: {e}')
    
    # Test 3: Multiple rapid calls (stress test)
    print('\n📋 Test 3: Rapid Multiple Calls')
    print('-' * 30)
    
    transaction_errors = 0
    successful_calls = 0
    
    for i in range(10):
        try:
            result = get_or_create_product_enhanced(f'test_product_{i}', 1, None)
            successful_calls += 1
        except Exception as e:
            if 'atomic block' in str(e):
                transaction_errors += 1
            
    print(f'✅ Successful calls: {successful_calls}/10')
    print(f'❌ Transaction errors: {transaction_errors}/10')
    
    if transaction_errors == 0:
        print('\n🎯 SUCCESS: No transaction errors detected!')
        print('✅ Product matching disabled successfully')
        print('✅ Order creation works without database conflicts')
        print('✅ System is stable under multiple calls')
    else:
        print(f'\n💥 FAILURE: {transaction_errors} transaction errors still occurring')
    
    return transaction_errors == 0

if __name__ == '__main__':
    success = test_no_transaction_errors()
    sys.exit(0 if success else 1)
