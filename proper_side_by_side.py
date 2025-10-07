#!/usr/bin/env python3
"""
Proper side-by-side comparison - ORIGINAL | PARSED | MATCHED | STATUS
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'familyfarms_api.settings')
django.setup()

from whatsapp.models import WhatsAppMessage
from whatsapp.services import parse_order_items, create_order_from_message

def proper_side_by_side():
    """Show proper side-by-side comparison"""
    
    messages = WhatsAppMessage.objects.filter(edited=True, message_type='order').order_by('-timestamp')
    
    print("SIDE-BY-SIDE COMPARISON")
    print("=" * 120)
    print(f"Total edited messages: {messages.count()}")
    print()
    
    for i, message in enumerate(messages[:3]):  # First 3 messages
        print(f"MESSAGE {i+1} (ID: {message.id})")
        print("-" * 120)
        
        # Parse the message
        parsed_items = parse_order_items(message.content)
        
        # Show side-by-side comparison
        print(f"{'ORIGINAL':<30} | {'PARSED':<30} | {'MATCHED':<30} | {'STATUS':<10}")
        print("-" * 120)
        
        for j, item in enumerate(parsed_items[:10], 1):  # First 10 items
            original = item.get('original_text', 'N/A')[:29]
            parsed_name = item.get('product_name', 'N/A')[:29]
            quantity = item.get('quantity', 'N/A')
            unit = item.get('unit', 'N/A')
            parsed_display = f"{parsed_name} | Qty: {quantity} | Unit: {unit}"[:29]
            
            # Test actual matching
            try:
                from whatsapp.services import get_or_create_product_enhanced
                product, qty, unit_result = get_or_create_product_enhanced(
                    product_name=item.get('product_name'),
                    quantity=item.get('quantity'),
                    unit=item.get('unit'),
                    original_message=message.content
                )
                
                if product:
                    matched_display = f"{product.name[:29]}"
                    if parsed_name.lower() in product.name.lower():
                        status = "✅ CORRECT"
                    else:
                        status = "❌ WRONG"
                else:
                    matched_display = "NO MATCH"
                    status = "❌ NO MATCH"
                    
            except Exception as e:
                matched_display = f"ERROR: {str(e)[:29]}"
                status = "❌ ERROR"
            
            print(f"{original:<30} | {parsed_display:<30} | {matched_display:<30} | {status:<10}")
        
        print()
        print("=" * 120)
        print()

if __name__ == "__main__":
    proper_side_by_side()
