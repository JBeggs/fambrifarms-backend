#!/usr/bin/env python3
"""
Comprehensive test script to process all orders from test data files
"""

import os
import sys
import json
import django
from pathlib import Path
from collections import defaultdict

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'familyfarms_api.settings')
django.setup()

from whatsapp.smart_product_matcher import SmartProductMatcher
from whatsapp.services import parse_order_items
from whatsapp.models import WhatsAppMessage

def load_test_data():
    """Load all test data files"""
    test_data_dir = Path(__file__).parent / "whatsapp" / "management" / "commands" / "test_data"
    
    all_messages = []
    file_stats = {}
    
    # Get all JSON files (excluding backups)
    json_files = [f for f in test_data_dir.glob("*.json") if not f.name.endswith('.backup') and not f.name.endswith('.pre_expand_backup')]
    
    print(f"Found {len(json_files)} test data files:")
    for file_path in sorted(json_files):
        print(f"  - {file_path.name}")
    
    for file_path in sorted(json_files):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                messages = json.load(f)
            
            file_stats[file_path.name] = {
                'total_messages': len(messages),
                'order_messages': 0,
                'processed_successfully': 0,
                'parsing_errors': 0,
                'no_items_found': 0
            }
            
            for message in messages:
                # Filter for messages that look like orders
                content = message.get('content', '').strip()
                if is_order_message(content):
                    file_stats[file_path.name]['order_messages'] += 1
                    all_messages.append({
                        'file': file_path.name,
                        'id': message.get('id', ''),
                        'sender': message.get('sender', ''),
                        'content': content,
                        'timestamp': message.get('timestamp', ''),
                        'chat_name': message.get('chat_name', '')
                    })
        
        except Exception as e:
            print(f"Error loading {file_path.name}: {e}")
            file_stats[file_path.name] = {'error': str(e)}
    
    return all_messages, file_stats

def is_order_message(content):
    """Determine if a message looks like an order"""
    if not content or len(content.strip()) < 10:
        return False
    
    # Look for common order patterns
    order_indicators = [
        'x', 'kg', 'box', 'bag', 'packet', 'bunch', 'head', 'each', 'punnets',
        'tomatoes', 'carrots', 'onions', 'lettuce', 'cucumber', 'lemon', 'broccoli',
        'cauliflower', 'peppers', 'mushrooms', 'strawberry', 'grapes', 'avos'
    ]
    
    content_lower = content.lower()
    
    # Must contain at least 2 order indicators
    indicator_count = sum(1 for indicator in order_indicators if indicator in content_lower)
    
    # Exclude obvious non-order messages
    exclude_patterns = [
        'orders starts here', 'good day', 'morning team', 'hie pliz send',
        'thanks', 'thank you', 'hi here is my order', 'for ', 'wimpy', 'mugg and bean'
    ]
    
    if any(pattern in content_lower for pattern in exclude_patterns):
        return False
    
    return indicator_count >= 2

def test_message_parsing():
    """Test parsing all messages from test data"""
    print("=== COMPREHENSIVE MESSAGE PARSING TEST ===\n")
    
    # Load all test data
    all_messages, file_stats = load_test_data()
    
    print(f"Total messages loaded: {len(all_messages)}")
    print(f"Files processed: {len(file_stats)}\n")
    
    # Initialize matcher
    matcher = SmartProductMatcher()
    
    # Process each message
    total_processed = 0
    total_successful = 0
    total_errors = 0
    total_items_parsed = 0
    
    parsing_results = []
    
    for i, message in enumerate(all_messages, 1):
        print(f"\n--- Message {i}/{len(all_messages)} ---")
        print(f"File: {message['file']}")
        print(f"Sender: {message['sender']}")
        print(f"Content: {message['content'][:100]}{'...' if len(message['content']) > 100 else ''}")
        
        try:
            # Parse the message
            parsed_items = parse_order_items(message['content'])
            
            if parsed_items:
                print(f"✅ Parsed {len(parsed_items)} items successfully")
                total_items_parsed += len(parsed_items)
                
                # Show first few items
                for j, item in enumerate(parsed_items[:3], 1):
                    print(f"  {j}. {item['original_text']} → {item['product_name']} {item['quantity']}{item['unit']}")
                
                if len(parsed_items) > 3:
                    print(f"  ... and {len(parsed_items) - 3} more items")
                
                total_successful += 1
                file_stats[message['file']]['processed_successfully'] += 1
                
                parsing_results.append({
                    'file': message['file'],
                    'message_id': message['id'],
                    'content': message['content'],
                    'items_parsed': len(parsed_items),
                    'success': True,
                    'items': parsed_items
                })
            else:
                print("❌ No items parsed")
                file_stats[message['file']]['no_items_found'] += 1
                
                parsing_results.append({
                    'file': message['file'],
                    'message_id': message['id'],
                    'content': message['content'],
                    'items_parsed': 0,
                    'success': False,
                    'error': 'No items parsed'
                })
            
            total_processed += 1
            
        except Exception as e:
            print(f"❌ Error parsing message: {e}")
            total_errors += 1
            file_stats[message['file']]['parsing_errors'] += 1
            
            parsing_results.append({
                'file': message['file'],
                'message_id': message['id'],
                'content': message['content'],
                'items_parsed': 0,
                'success': False,
                'error': str(e)
            })
    
    # Print summary statistics
    print("\n" + "="*60)
    print("SUMMARY STATISTICS")
    print("="*60)
    
    print(f"Total messages processed: {total_processed}")
    print(f"Successfully parsed: {total_successful} ({total_successful/total_processed*100:.1f}%)")
    print(f"Parsing errors: {total_errors} ({total_errors/total_processed*100:.1f}%)")
    print(f"Total items parsed: {total_items_parsed}")
    print(f"Average items per successful message: {total_items_parsed/max(total_successful, 1):.1f}")
    
    print(f"\nPer-file breakdown:")
    for filename, stats in file_stats.items():
        if 'error' in stats:
            print(f"  {filename}: ERROR - {stats['error']}")
        else:
            total = stats['total_messages']
            orders = stats['order_messages']
            success = stats['processed_successfully']
            errors = stats['parsing_errors']
            no_items = stats['no_items_found']
            
            print(f"  {filename}:")
            print(f"    Total messages: {total}")
            print(f"    Order messages: {orders}")
            print(f"    Successfully parsed: {success} ({success/max(orders, 1)*100:.1f}%)")
            print(f"    Parsing errors: {errors}")
            print(f"    No items found: {no_items}")
    
    # Find problematic messages
    print(f"\nPROBLEMATIC MESSAGES:")
    problematic = [r for r in parsing_results if not r['success']]
    
    if problematic:
        print(f"Found {len(problematic)} problematic messages:")
        for i, result in enumerate(problematic[:10], 1):  # Show first 10
            print(f"  {i}. {result['file']} - {result['error']}")
            print(f"     Content: {result['content'][:100]}...")
        
        if len(problematic) > 10:
            print(f"  ... and {len(problematic) - 10} more problematic messages")
    else:
        print("No problematic messages found! 🎉")
    
    # Find most common parsing issues
    print(f"\nCOMMON PARSING PATTERNS:")
    pattern_stats = defaultdict(int)
    
    for result in parsing_results:
        if result['success'] and result['items']:
            for item in result['items']:
                original = item['original_text']
                # Categorize by format
                if ' x ' in original:
                    pattern_stats['"Product x quantity unit"'] += 1
                elif 'x' in original and not ' x ' in original:
                    pattern_stats['"Productxquantity"'] += 1
                elif any(unit in original for unit in ['kg', 'g', 'box', 'bag', 'packet']):
                    if any(char.isdigit() for char in original):
                        pattern_stats['"Product quantityunit"'] += 1
                    else:
                        pattern_stats['"Product only"'] += 1
                else:
                    pattern_stats['"Other format"'] += 1
    
    for pattern, count in sorted(pattern_stats.items(), key=lambda x: x[1], reverse=True):
        print(f"  {pattern}: {count} items")
    
    return parsing_results, file_stats

def test_specific_problematic_messages():
    """Test specific messages that might be problematic"""
    print("\n" + "="*60)
    print("TESTING SPECIFIC PROBLEMATIC MESSAGES")
    print("="*60)
    
    # Some known problematic patterns from the data
    test_cases = [
        "Tomatoes x3",
        "Sweet melonx1", 
        "Bananas 2kg",
        "Mixed lettuce x3box",
        "Cherry tomatoes x15 200g",
        "6*packets mint",
        "6* punnets strawberries",
        "1*box lemons",
        "1* box lettuce",
        "6*punnets cherry tomatoes",
        "3*packets micro herbs",
        "3kg red pepper",
        "1* box pineapple",
        "Lemon 5kg × 2 box",
        "Pineapple × 1 box",
        "Orange × 1 bag",
        "Strawberry × 6 small pack",
        "Rosemary × 2 small pack",
        "Mints × 5 small pack",
        "Cucumber × 2",
        "Onions × 2 bags",
        "5kg mushroom",
        "10 heads cauliflower",
        "10 heads broccoli",
        "5* packets parsley",
        "3*packets rocket",
        "5* boxes avos",
        "2* box Mixed lettuce",
        "0,5kg brinjals",
        "1*bag red onions",
        "4 box lettuce",
        "30 kg onions",
        "1kg red onions",
        "3 box tomatoes",
        "4 packet cherry tomatoes",
        "1kg red pepper",
        "1 cucumber",
        "200g parsley"
    ]
    
    matcher = SmartProductMatcher()
    
    print(f"Testing {len(test_cases)} specific patterns:")
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i:2d}. Testing: '{test_case}'")
        
        try:
            parsed_items = parse_order_items(test_case)
            
            if parsed_items:
                for item in parsed_items:
                    print(f"    ✅ {item['original_text']} → {item['product_name']} {item['quantity']}{item['unit']} (conf: {item['confidence']:.1f})")
            else:
                print(f"    ❌ No items parsed")
                
        except Exception as e:
            print(f"    ❌ Error: {e}")

if __name__ == "__main__":
    # Run the comprehensive test
    parsing_results, file_stats = test_message_parsing()
    
    # Test specific problematic patterns
    test_specific_problematic_messages()
    
    print(f"\n" + "="*60)
    print("TEST COMPLETED")
    print("="*60)
