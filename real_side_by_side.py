#!/usr/bin/env python3
"""
Real side-by-side comparison of message processing
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'familyfarms_api.settings')
django.setup()

from whatsapp.models import WhatsAppMessage
from whatsapp.services import parse_order_items, create_order_from_message

def real_side_by_side_analysis():
    """Show real side-by-side comparison of message processing"""
    
    messages = WhatsAppMessage.objects.filter(edited=True, message_type='order').order_by('-timestamp')
    
    print("REAL SIDE-BY-SIDE MESSAGE PROCESSING ANALYSIS")
    print("=" * 80)
    print(f"Total edited messages: {messages.count()}")
    print()
    
    for i, message in enumerate(messages[:3]):  # First 3 messages
        print(f"MESSAGE {i+1}: {message.id}")
        print("-" * 40)
        print(f"Content: {message.content[:100]}...")
        print()
        
        # Parse the message
        parsed_items = parse_order_items(message.content)
        print(f"Parsed {len(parsed_items)} items:")
        
        for j, item in enumerate(parsed_items[:5]):  # First 5 items
            original = item.get('original_text', 'N/A')
            parsed_name = item.get('product_name', 'N/A')
            quantity = item.get('quantity', 'N/A')
            unit = item.get('unit', 'N/A')
            
            print(f"  {j+1:2d}. ORIGINAL: {original}")
            print(f"      PARSED:   {parsed_name} | Qty: {quantity} | Unit: {unit}")
        
        print()
        
        # Test order creation
        print("ORDER CREATION TEST:")
        try:
            result = create_order_from_message(message)
            if isinstance(result, str) and result.startswith('Order'):
                print(f"  ✅ SUCCESS: {result}")
            else:
                print(f"  ❌ FAILED: {result}")
        except Exception as e:
            print(f"  ❌ ERROR: {e}")
        
        print()
        print("=" * 80)
        print()

if __name__ == "__main__":
    real_side_by_side_analysis()
