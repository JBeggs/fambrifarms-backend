#!/usr/bin/env python3
"""
Test script to test order parsing with the example order from the images
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'familyfarms_api.settings')
django.setup()

from whatsapp.smart_product_matcher import SmartProductMatcher
from whatsapp.services import parse_order_items
from whatsapp.models import WhatsAppMessage

def test_order_parsing():
    """Test parsing the order from the images"""
    
    # Test the edited order from the images
    order_content = """Crispy Lettuce x 1 box
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
    
    print("=== TESTING COMPLETE ORDER PARSING ===\n")
    print(f"Order content:\n{order_content}\n")
    
    # Test 1: SmartProductMatcher
    print("1. Testing SmartProductMatcher...")
    matcher = SmartProductMatcher()
    
    # Parse the message
    parsed_messages = matcher.parse_message(order_content)
    print(f"Parsed {len(parsed_messages)} items:")
    
    for i, parsed in enumerate(parsed_messages, 1):
        print(f"  {i}. {parsed.original_message}")
        print(f"     -> Product: '{parsed.product_name}'")
        print(f"     -> Quantity: {parsed.quantity}")
        print(f"     -> Unit: {parsed.unit}")
        print()
    
    # Test 2: Find matches for each item
    print("2. Testing product matching...")
    for i, parsed in enumerate(parsed_messages, 1):
        print(f"Item {i}: {parsed.original_message}")
        matches = matcher.find_matches(parsed)
        
        if matches:
            best_match = matches[0]
            print(f"  ✓ Best match: {best_match.product.name} (R{best_match.product.price}/{best_match.product.unit})")
            print(f"    Confidence: {best_match.confidence_score:.1f}%")
        else:
            print(f"  ✗ No matches found")
        print()

if __name__ == "__main__":
    test_order_parsing()
