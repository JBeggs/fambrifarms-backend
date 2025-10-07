#!/usr/bin/env python3
"""
Test the actual order creation process that Flutter calls
"""

import os
import sys
import django
from pathlib import Path

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'familyfarms_api.settings')
django.setup()

from whatsapp.models import WhatsAppMessage
from whatsapp.services import create_order_from_message

def test_order_creation():
    """Test the actual order creation process"""
    
    # Create a test message with the edited order
    order_content = """Valley

Crispy Lettuce x 1 box
Cucumber x 1 each
carrots x 10kg
Lemon x 10kg
onions x 10kg
Cocktail tomatoes x 5 pkts
Whole tomatoes x 3kg
Red peppers x 5kg
Green peppers x 5 kg
Sweet corn x 5 pkts
spinach x 10 bunch
cabbage x 1 head
broccoli x 5 head
cauliflower x 5head
Parsley x 300g
Coriander x 200g
Fresh chillie green x2 kg"""
    
    print("=== TESTING ORDER CREATION PROCESS ===\n")
    print(f"Order content:\n{order_content}\n")
    
    # Create a test WhatsApp message
    test_message = WhatsAppMessage.objects.create(
        message_id="test_order_creation_123",
        sender_name="Test Customer",
        content=order_content,
        timestamp="2025-01-01 12:00:00",
        chat_name="Test Chat",
        message_type="order",
        processed=False
    )
    
    print(f"Created test message: {test_message.id}")
    print(f"Message ID: {test_message.message_id}")
    print(f"Company name extracted: {test_message.extract_company_name()}")
    print()
    
    # Test the order creation process
    print("Testing create_order_from_message...")
    result = create_order_from_message(test_message)
    
    if isinstance(result, dict) and result.get('status') == 'failed':
        print("❌ ORDER CREATION FAILED")
        print(f"Error: {result.get('message')}")
        print(f"Failed products: {len(result.get('failed_products', []))}")
        print(f"Parsing failures: {len(result.get('parsing_failures', []))}")
        print(f"Unparseable lines: {len(result.get('unparseable_lines', []))}")
        
        print("\nFailed products details:")
        for i, failed in enumerate(result.get('failed_products', [])[:5], 1):
            print(f"  {i}. {failed['original_name']} - {failed['failure_reason']}")
        
        print("\nParsing failures details:")
        for i, failure in enumerate(result.get('parsing_failures', [])[:5], 1):
            print(f"  {i}. {failure}")
            
        print("\nUnparseable lines details:")
        for i, line in enumerate(result.get('unparseable_lines', [])[:5], 1):
            print(f"  {i}. {line}")
            
    elif result:
        print("✅ ORDER CREATED SUCCESSFULLY")
        print(f"Order number: {result.order_number}")
        print(f"Total amount: R{result.total_amount}")
        print(f"Items created: {result.items.count()}")
        
        print("\nOrder items:")
        for item in result.items.all():
            print(f"  - {item.product.name} x {item.quantity} {item.unit} = R{item.total_price}")
    else:
        print("❌ ORDER CREATION FAILED - No result returned")
    
    # Clean up
    test_message.delete()
    if result and hasattr(result, 'delete'):
        result.delete()

if __name__ == "__main__":
    test_order_creation()
