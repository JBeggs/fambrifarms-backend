#!/usr/bin/env python3
"""
Final test of the improved suggestion system.
Tests the exact requirements from the user:
1. "g" must be next to numbers (100g, 200g not "100 g", "200 g")
2. Box sizes should be "5kg" not "5 kg"
3. If items match after applying suggestions, no more suggestions should appear
"""

import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'familyfarms_api.settings')
django.setup()

from whatsapp.views import analyze_single_item
from whatsapp.services import parse_single_item


def test_final_suggestions():
    """Test the final improved suggestion system."""
    
    print("🎯 FINAL SUGGESTION SYSTEM TEST")
    print("=" * 60)
    print("Testing user requirements:")
    print("1. 'g' must be next to numbers (100g, 200g not '100 g', '200 g')")
    print("2. Box sizes should be '5kg' not '5 kg'")
    print("3. If items match after applying suggestions, no more suggestions")
    print()
    
    # User's exact list
    user_items = [
        '1 box 3kg green pepper',
        '1 box 3kg red pepper',
        '1 box avocados 5 kg',
        '1 box avocados semi ripe 5 kg',
        '3 box lemons 5 kg',
        '3 packet dill 100 g',
        '5 packet parsley 100 g',
        '2 bag onions white 10 kg',
        '2 box cucumber 5 kg',
        '1 box 10kg carrots',
        '10 head broccoli',
        '10 head cauliflower',
        '1 box 5kg butternut cut',
        '1 box pineapple 5 kg',
        '1 packet 5kg spinach deveined',
        '5 packet mint 100 g',
        'Strawberries 5 punnet 200 g'
    ]
    
    needs_improvement = 0
    total_items = len(user_items)
    all_passed = True
    
    for i, item in enumerate(user_items, 1):
        print(f"{i:2d}. Testing: \"{item}\"")
        
        # Get suggestions
        suggestions = analyze_single_item(item)
        
        if suggestions:
            needs_improvement += 1
            suggestion = suggestions[0]
            improved_text = suggestion.get('improved_text', '')
            
            print(f"    💡 Suggestion: \"{improved_text}\"")
            
            # Test 1: Check weight format (no spaces in kg/g)
            has_spaced_weights = re.search(r'\d+\s+(kg|g)\b', improved_text)
            if has_spaced_weights:
                print(f"    ❌ FAIL: Still has spaced weights: {has_spaced_weights.group()}")
                all_passed = False
            else:
                print(f"    ✅ PASS: Weight format correct")
            
            # Test 2: Verify parsing works
            test_result = parse_single_item(improved_text)
            if test_result:
                product = test_result.get('product_name', 'FAILED')
                qty = test_result.get('quantity', 'N/A')
                unit = test_result.get('unit', 'N/A')
                print(f"    ✅ PASS: Parses to -> {product} | Qty: {qty} | Unit: {unit}")
            else:
                print(f"    ❌ FAIL: Suggestion doesn't parse")
                all_passed = False
            
            # Test 3: Check if rerunning gives no more suggestions
            rerun_suggestions = analyze_single_item(improved_text)
            if rerun_suggestions:
                print(f"    ❌ FAIL: Still has {len(rerun_suggestions)} suggestions after improvement")
                all_passed = False
            else:
                print(f"    ✅ PASS: No more suggestions after improvement")
        else:
            print(f"    ✅ PASS: No suggestions needed (already good)")
        
        print()
    
    print("📊 SUMMARY")
    print("=" * 60)
    print(f"Total items tested: {total_items}")
    print(f"Items needing improvement: {needs_improvement}")
    print(f"Items already good: {total_items - needs_improvement}")
    print(f"Improvement rate: {(needs_improvement/total_items)*100:.1f}%")
    print()
    
    if all_passed:
        print("🎉 ALL TESTS PASSED!")
        print("✅ Weight formats are correct (no spaces)")
        print("✅ All suggestions parse correctly")
        print("✅ No suggestions after applying improvements")
    else:
        print("❌ SOME TESTS FAILED!")
        print("Please check the issues above")
    
    print()
    
    # Test specific formatting examples
    print("🔍 SPECIFIC FORMAT TESTS")
    print("=" * 60)
    
    format_tests = [
        ("3 packet dill 100 g", "Should suggest 100g (no space)"),
        ("1 box avocados 5 kg", "Should suggest 5kg (no space)"),
        ("Strawberries 5 punnet 200 g", "Should suggest 200g (no space)")
    ]
    
    for test_item, expected in format_tests:
        print(f"📝 \"{test_item}\" - {expected}")
        suggestions = analyze_single_item(test_item)
        
        if suggestions:
            for s in suggestions:
                improved = s.get('improved_text', '')
                has_spaces = re.search(r'\d+\s+(kg|g)\b', improved)
                if has_spaces:
                    print(f"    ❌ FAIL: \"{improved}\" still has spaced weights")
                else:
                    print(f"    ✅ PASS: \"{improved}\" has correct format")
        else:
            print(f"    ℹ️  INFO: No suggestions (item may already be good)")
        print()


if __name__ == '__main__':
    import re
    test_final_suggestions()
