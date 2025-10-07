#!/usr/bin/env python3
"""
Visual comparison of message processing - what you actually need to see
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'familyfarms_api.settings')
django.setup()

from whatsapp.models import WhatsAppMessage
from whatsapp.services import parse_order_items, create_order_from_message

def visual_comparison():
    """Show proper side-by-side comparison"""
    
    messages = WhatsAppMessage.objects.filter(edited=True, message_type='order').order_by('-timestamp')
    
    print("SIDE-BY-SIDE COMPARISON")
    print("=" * 200)
    print(f"Total edited messages: {messages.count()}")
    print()
    
    for i, message in enumerate(messages):  # All messages
        print(f"MESSAGE {i+1} (ID: {message.id})")
        print("-" * 200)
        
        # Parse the message
        parsed_items = parse_order_items(message.content)
        
        # Show side-by-side comparison
        print(f"{'ORIGINAL':<50} | {'PARSED':<60} | {'MATCHED':<50} | {'STATUS':<15}")
        print("-" * 200)
        
        for j, item in enumerate(parsed_items, 1):  # All items
            original = item.get('original_text', 'N/A')[:49]
            parsed_name = item.get('product_name', 'N/A')[:49]
            quantity = item.get('quantity', 'N/A')
            unit = item.get('unit', 'N/A')
            parsed_display = f"{parsed_name} | Qty: {quantity} | Unit: {unit}"[:59]
            
            # Test actual matching using the same logic as parse_order_items
            try:
                from whatsapp.smart_product_matcher import SmartProductMatcher
                matcher = SmartProductMatcher()
                
                # Parse the original text to get the full context
                parsed_results = matcher.parse_message(item.get('original_text', ''))
                if parsed_results and len(parsed_results) > 0:
                    parsed_result = parsed_results[0]  # Get first parsed result
                    matches = matcher.find_matches(parsed_result)
                    if matches and len(matches) > 0:
                        best_match = matches[0]  # First match is the best
                        product = best_match.product
                        matched_display = f"{product.name} ({product.unit})"[:49]
                        if parsed_name.lower() in product.name.lower():
                            status = "✅ CORRECT"
                        else:
                            status = "❌ WRONG"
                    else:
                        matched_display = "NO MATCH"
                        status = "❌ NO MATCH"
                else:
                    matched_display = "PARSE FAILED"
                    status = "❌ PARSE FAILED"
                    
            except Exception as e:
                matched_display = f"ERROR: {str(e)[:49]}"
                status = "❌ ERROR"
            
            print(f"{original:<50} | {parsed_display:<60} | {matched_display:<50} | {status:<15}")
        
        print()
        print("=" * 200)
        print()

if __name__ == "__main__":
    visual_comparison()
