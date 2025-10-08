from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import datetime, date, timedelta
from decimal import Decimal
import re
import traceback
import logging
from .models import WhatsAppMessage, StockUpdate, MessageProcessingLog
from orders.models import Order, OrderItem
from products.models import Product
from .production_matcher import get_production_matcher

from .smart_product_matcher import SmartProductMatcher, ParsedMessage

"""
WhatsApp message processing services
Handles classification, parsing, and order creation from WhatsApp messages
"""



User = get_user_model()

def classify_message_type(msg_data):
    """
    Classify message type based on content and sender
    
    Args:
        msg_data: Dictionary with message data from scraper
        
    Returns:
        str: Message type ('order', 'stock', 'instruction', 'demarcation', 'other')
    """
    logger = logging.getLogger(__name__)
    content_raw = msg_data.get('content')
    if content_raw is None:
        raise ValueError("Message content is required for classification")
    
    content = content_raw.upper()
    sender = msg_data.get('sender')
    if sender is None:
        raise ValueError("Message sender is required for classification")
    
    # Stock controller messages (SHALLOME +27 61 674 9368)
    # ENHANCED: Handle various typos in stock headers
    stock_header_patterns = [
        'STOCK AS AT',
        'STOKE AS AT',  # Common typo
        'TOCK AS AT',   # Missing S typo
        'STOCK AT',     # Missing AS
        'STOK AS AT'    # Another typo
    ]
    stock_header = any(pattern in content for pattern in stock_header_patterns)
    is_shallome_sender = ('+27 61 674 9368' in sender or 'SHALLOME' in sender.upper())
    is_shallome_content = 'SHALLOME' in content
    
    # CRITICAL FIX: If message contains "SHALLOME" and stock header, classify as stock
    # regardless of sender (sender might be generic "Group Member")
    if stock_header and (is_shallome_sender or is_shallome_content):
        logger.info(f"Message classified as stock: id={msg_data.get('id', 'unknown')} (sender_match={is_shallome_sender}, content_match={is_shallome_content}, stock_header={stock_header})")
        return 'stock'
    
    # ADDITIONAL FIX: If message starts with SHALLOME and has numbered items, it's likely stock
    # This catches cases where the header is completely mangled
    if is_shallome_content and content.strip().upper().startswith('SHALLOME'):
        # Check if it has numbered items like stock messages do
        numbered_items = len([line for line in content.split('\n') if re.match(r'^\d+\.', line.strip())])
        if numbered_items >= 5:  # Stock messages typically have many numbered items
            logger.info(f"Message classified as stock (SHALLOME + numbered items): id={msg_data.get('id', 'unknown')} items={numbered_items}")
            return 'stock'
    
    # Order day demarcation messages
    demarcation_patterns = [
        'ORDERS STARTS HERE',
        '👇👇👇',
        'THURSDAY ORDERS STARTS HERE',
        'TUESDAY ORDERS STARTS HERE',
        'MONDAY ORDERS STARTS HERE'
    ]
    
    demarcation = any(pattern in content for pattern in demarcation_patterns)
    if demarcation:
        logger.info(f"Message classified as demarcation: id={msg_data.get('id', 'unknown')}")
        return 'demarcation'
    
    # Company orders - check if message contains order items
    order_like = has_order_items(content)
    if order_like:
        logger.info(f"Message classified as order: id={msg_data.get('id', 'unknown')} (order_like=True)")
        return 'order'
    
    # Instructions or general messages
    instructionish = any(word in content for word in ['PLEASE', 'HELP', 'NOTE', 'INSTRUCTION', 'THANKS', 'GOOD MORNING', 'HELLO', 'HI'])
    if instructionish:
        logger.info(f"Message classified as instruction: id={msg_data.get('id', 'unknown')}")
        return 'instruction'
    
    logger.info(f"Message classified as other (fallback): id={msg_data.get('id', 'unknown')} len={len(content_raw)}")
    return 'other'

def has_order_items(content):
    """
    Check if message contains order items based on quantity patterns
    
    Args:
        content: Message content string
        
    Returns:
        bool: True if message appears to contain order items
    """
    # Get database units dynamically
    try:
        database_units = get_database_units()
        units_pattern = '|'.join(re.escape(unit) for unit in database_units)
        
        # Dynamic patterns using database units
        quantity_patterns = [
            rf'\d+\s*(?:{units_pattern})',           # 5kg, 10 boxes, etc.
            rf'\d+\s*(?:×|x)\s*\d+\s*(?:{units_pattern})',  # 2×5kg, 3x10boxes
            r'(?:×|x)\s*\d+',                        # x3, ×5
            r'\d+\s*(?:×|x)\b',                     # 2x, 3×
        ]
    except Exception as e:
        # Fallback to basic patterns if database query fails
        quantity_patterns = [
            r'\d+\s*(?:kg|g|box|bag|bunch|each|piece)',
            r'\d+\s*(?:×|x)\s*\d+\s*(?:kg|g|box|bag)',
            r'(?:×|x)\s*\d+',
            r'\d+\s*(?:×|x)\b',
        ]
    
    for pattern in quantity_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            return True
    
    return False

def create_order_from_message(message):
    """
    Create Django Order from WhatsApp message
    
    Args:
        message: WhatsAppMessage instance
        
    Returns:
        Order instance or None if creation failed
    """
    try:
        # Extract company name (usually first line)
        company_name = message.extract_company_name()
        if not company_name:
            return None
        
        # Get or create customer
        customer = get_or_create_customer(company_name, message.sender_name)
        if not customer:
            return {
                'status': 'failed',
                'message': f'Could not find or create customer for company: {company_name}',
                'failed_products': [],
                'parsing_failures': [],
                'unparseable_lines': []
            }
        
        # Determine valid order date
        from datetime import datetime
        if isinstance(message.timestamp, str):
            timestamp_dt = datetime.fromisoformat(message.timestamp.replace('Z', '+00:00'))
        else:
            timestamp_dt = message.timestamp
        order_date = get_valid_order_date(timestamp_dt.date())
        
        # Create order
        order = Order.objects.create(
            restaurant=customer,
            order_date=order_date,
            status='received',
            whatsapp_message_id=message.message_id,
            original_message=message.content,
            parsed_by_ai=True
        )
        
        # Save the order first so we can access its relationships
        order.save()
        
        # Parse and create order items
        items_result = create_order_items(order, message)
        items_created = items_result['items_created']
        failed_products = items_result['failed_products']
        parsing_failures = items_result['parsing_failures']
        unparseable_lines = items_result.get('unparseable_lines', [])
        
        # CORRECT LOGIC: Only create order if ALL items are successfully processed
        total_failures = len(failed_products) + len(parsing_failures) + len(unparseable_lines)
        
        if items_created > 0 and total_failures == 0:
            # SUCCESS: All items processed successfully, create the order
            # Order is already saved, so we can access items
            order.subtotal = sum(item.total_price for item in order.items.all())
            order.total_amount = order.subtotal  # Add tax/fees later if needed
            order.save()
            
            success_rate = items_result['success_rate']
            message.processing_notes = f"✅ Order created: {items_created}/{items_result['total_attempts']} items processed (100%)"
            
            message.processed = True
            message.order = order
            message.save()
            
            log_processing_action(message, 'order_created', {
                'order_number': order.order_number,
                'items_count': items_created,
                'total_amount': float(order.total_amount or 0),
                'success_rate': success_rate,
                'failed_products_count': 0,
                'parsing_failures_count': 0
            })
            
            return order
            
        else:
            # FAILURE: Not all items processed successfully - return suggestions for fixing
            failed_products = items_result['failed_products']
            parsing_failures = items_result['parsing_failures']
            failed_items_count = items_result['total_attempts'] - items_created
            
            if items_created > 0:
                message.processing_notes = f"❌ Order NOT created: {items_created}/{items_result['total_attempts']} items processed - All items must be processed successfully"
            else:
                message.processing_notes = f"❌ Order creation failed: 0/{items_result['total_attempts']} items processed"
            
            if failed_items_count > 0:
                message.processing_notes += f" | ⚠️ {failed_items_count} items failed"
                
                # Show all types of failures
                all_failure_details = []
                
                # Add failed products
                if failed_products:
                    for failed_item in failed_products[:3]:  # Show first 3
                        all_failure_details.append(f"'{failed_item['original_name']}': {failed_item['failure_reason']}")
                
                # Add parsing failures
                if parsing_failures:
                    for failure in parsing_failures[:2]:  # Show first 2 parsing failures
                        all_failure_details.append(f"'{failure['original_name']}': {failure['failure_reason']}")
                
                # Add unparseable lines (these are also failures)
                unparseable_lines = items_result.get('unparseable_lines', [])
                if unparseable_lines:
                    for line in unparseable_lines[:2]:  # Show first 2 unparseable lines
                        all_failure_details.append(f"'{line}': Could not parse as order item")
                
                # Display all failure details
                if all_failure_details:
                    message.processing_notes += f" | Failed items: {'; '.join(all_failure_details)}"
                    
                    # Show count of additional failures if there are more
                    total_shown = len(all_failure_details)
                    total_failures = len(failed_products) + len(parsing_failures) + len(unparseable_lines)
                    if total_failures > total_shown:
                        message.processing_notes += f" (and {total_failures - total_shown} more)"
            
            message.processed = False  # Mark as not processed since order creation failed
            message.save()
            
            # Get suggestions for failed products
            failed_products_with_suggestions = []
            for failed_product in failed_products:
                suggestions = get_product_suggestions(failed_product['original_name'])
                failed_products_with_suggestions.append({
                    **failed_product,
                    'suggestions': suggestions
                })
            
            # Get suggestions for unparseable lines too
            unparseable_lines_with_suggestions = []
            for line in unparseable_lines:
                # Try to extract a product name from the unparseable line
                # Smart approach: look for product names after quantities and units
                words = line.strip().split()
                potential_name = None
                
                if words:
                    # Look for patterns like "3 x 5kg Tomato" or "5kg Tomato" or "Tomato 3 x 5kg"
                    for i, word in enumerate(words):
                        # Skip numbers and units
                        if word.isdigit() or word in ['x', 'kg', 'g', 'box', 'bag', 'bunch', 'packet', 'each', 'piece', 'punnet', 'tray', 'head']:
                            continue
                        # Found a potential product name
                        potential_name = ' '.join(words[i:])
                        break
                    
                    # If no product name found, try the last word
                    if not potential_name and words:
                        potential_name = words[-1]
                    
                    # If still no good name, try the first word
                    if not potential_name:
                        potential_name = words[0]
                    
                    suggestions = get_product_suggestions(potential_name)
                    unparseable_lines_with_suggestions.append({
                        'original_line': line,
                        'potential_name': potential_name,
                        'suggestions': suggestions
                    })
            
            # Collect successfully processed items before deleting the order
            successful_items = []
            if items_created > 0:
                for item in order.items.all():
                    successful_items.append({
                        'id': item.id,
                        'name': item.product.name,
                        'quantity': float(item.quantity),
                        'unit': item.unit,
                        'price': float(item.price),
                        'total_price': float(item.total_price),
                        'original_text': item.original_text,
                        'confidence_score': item.confidence_score
                    })
            
            # Delete the order since it failed
            order.delete()
            
            log_processing_action(message, 'order_creation_failed', {
                'error': 'Order creation failed - not all items processed successfully',
                'action': 'order_creation',
                'items_processed': items_created,
                'items_failed': failed_items_count,
                'failed_products_count': len(failed_products),
                'parsing_failures_count': len(parsing_failures)
            })
            
            # Return failed products with suggestions for fixing, including successful items
            return {
                'status': 'failed',
                'items': successful_items,  # Include successfully processed items
                'failed_products': failed_products_with_suggestions,
                'parsing_failures': parsing_failures,
                'unparseable_lines': unparseable_lines_with_suggestions,
                'message': f'Order creation failed - {failed_items_count} items need attention. Use suggestions to fix and retry.'
            }
            
    except Exception as e:
        log_processing_action(message, 'error', {
            'error': str(e),
            'traceback': traceback.format_exc(),
            'action': 'order_creation'
        })
        return {
            'status': 'failed',
            'message': f'Order creation failed due to error: {str(e)}',
            'error': str(e)
        }

def create_order_from_message_with_suggestions(message):
    """
    Create suggestions for all items in a WhatsApp message - always requires user confirmation
    
    Args:
        message: WhatsAppMessage instance
        
    Returns:
        dict: Always returns confirmation_required status with suggestions for all items
    """
    try:
        # Extract company name
        company_name = message.extract_company_name()
        if not company_name:
            return {
                'status': 'failed',
                'message': 'No company name found in message',
                'items': [],
                'suggestions': []
            }
        
        # Get or create customer
        customer = get_or_create_customer(company_name, message.sender_name)
        if not customer:
            return {
                'status': 'failed',
                'message': f'Could not find or create customer for company: {company_name}',
                'items': [],
                'suggestions': []
            }
        
        # Parse the message content
        parsed_result = parse_order_items(message.content)
        parsed_items = parsed_result['items']
        parsing_failures = parsed_result.get('parsing_failures', [])
        
        if not parsed_items and not parsing_failures:
            return {
                'status': 'failed',
                'message': 'No items could be parsed from message',
                'items': [],
                'suggestions': []
            }
        
        # Get suggestions for ALL parsed items
        matcher = SmartProductMatcher()
        items_with_suggestions = []
        
        for item_data in parsed_items:
            # Parse the item to get structured data
            parsed_message = ParsedMessage(
                product_name=item_data['product_name'],
                quantity=item_data['quantity'],
                unit=item_data['unit'],
                packaging_size=item_data.get('packaging_size'),
                extra_descriptions=item_data.get('extra_descriptions', []),
                original_message=item_data['original_text']
            )
            
            # Get suggestions for this item
            suggestions_result = matcher.get_suggestions(
                parsed_message.product_name, 
                min_confidence=5.0, 
                max_suggestions=20
            )
            
            # Format suggestions for frontend
            suggestions = []
            if suggestions_result.suggestions:
                for suggestion in suggestions_result.suggestions:
                    suggestions.append({
                        'product_id': suggestion.product.id,
                        'product_name': suggestion.product.name,
                        'unit': suggestion.product.unit,
                        'price': float(suggestion.product.price),
                        'confidence_score': suggestion.confidence_score,
                        'packaging_size': suggestion.product.name.split('(')[1].split(')')[0] if '(' in suggestion.product.name and ')' in suggestion.product.name else None
                    })
            
            items_with_suggestions.append({
                'original_text': item_data['original_text'],
                'parsed': {
                    'product_name': item_data['product_name'],
                    'quantity': item_data['quantity'],
                    'unit': item_data['unit'],
                    'packaging_size': item_data.get('packaging_size'),
                    'extra_descriptions': item_data.get('extra_descriptions', [])
                },
                'suggestions': suggestions,
                'selected_suggestion': None,  # User will select
                'is_ambiguous_packaging': "AMBIGUOUS_PACKAGING" in item_data.get('extra_descriptions', [])
            })
        
        # Handle parsing failures as suggestions too
        for failure in parsing_failures:
            # Get suggestions based on the original name
            suggestions_result = matcher.get_suggestions(
                failure['original_name'], 
                min_confidence=5.0, 
                max_suggestions=20
            )
            
            suggestions = []
            if suggestions_result.suggestions:
                for suggestion in suggestions_result.suggestions:
                    suggestions.append({
                        'product_id': suggestion.product.id,
                        'product_name': suggestion.product.name,
                        'unit': suggestion.product.unit,
                        'price': float(suggestion.product.price),
                        'confidence_score': suggestion.confidence_score,
                        'packaging_size': suggestion.product.name.split('(')[1].split(')')[0] if '(' in suggestion.product.name and ')' in suggestion.product.name else None
                    })
            
            items_with_suggestions.append({
                'original_text': failure['original_name'],
                'parsed': {
                    'product_name': failure['original_name'],
                    'quantity': failure.get('quantity', 1.0),
                    'unit': failure.get('unit', 'each'),
                    'packaging_size': None,
                    'extra_descriptions': []
                },
                'suggestions': suggestions,
                'selected_suggestion': None,
                'is_parsing_failure': True,
                'failure_reason': failure.get('failure_reason', 'Could not parse item')
            })
        
        return {
            'status': 'confirmation_required',
            'message': f'Please confirm {len(items_with_suggestions)} items for {company_name}',
            'customer': {
                'id': customer.id,
                'name': customer.username,
                'email': customer.email
            },
            'items': items_with_suggestions,
            'total_items': len(items_with_suggestions)
        }
        
    except Exception as e:
        print(f"Error in create_order_from_message_with_suggestions: {e}")
        import traceback
        traceback.print_exc()
        return {
            'status': 'failed',
            'message': f'Error processing message: {str(e)}',
            'items': [],
            'suggestions': []
        }

def reprocess_message_with_corrections(message_id, corrections):
    """
    Reprocess a message after user has applied corrections
    
    Args:
        message_id: The message ID to reprocess
        corrections: Dict of corrections applied by user
        
    Returns:
        Order instance or dict with suggestions if still failing
    """
    try:
        from .models import WhatsAppMessage
        
        # Get the message
        message = WhatsAppMessage.objects.get(message_id=message_id)
        
        # Apply corrections to the message content
        corrected_content = apply_corrections_to_content(message.content, corrections)
        
        # Update the message content temporarily for reprocessing
        original_content = message.content
        original_manual_company = message.manual_company  # Preserve the manual company
        message.content = corrected_content
        message.save()
        
        # Check if an order already exists for this message
        from orders.models import Order
        existing_orders = Order.objects.filter(whatsapp_message_id=message_id)
        print(f"[REPROCESS] Found {existing_orders.count()} existing orders for message {message_id}")
        
        if existing_orders.exists():
            # Delete all existing orders before creating a new one
            for order in existing_orders:
                print(f"[REPROCESS] Deleting existing order {order.id} for message {message_id}")
                order.delete()
        
        # Try to create order again
        result = create_order_from_message(message)
        
        # Always keep the corrected content in the message
        message.content = corrected_content
        # CRITICAL: Always preserve the manual company assignment, even if it's None/empty
        # This prevents the extract_company_name() call from overwriting it
        message.manual_company = original_manual_company
        
        # Update processing notes to indicate content was corrected and order creation status
        import json
        try:
            current_notes = json.loads(message.processing_notes) if message.processing_notes else {}
        except (json.JSONDecodeError, TypeError):
            current_notes = {}
        
        current_notes['content_corrected'] = True
        current_notes['original_content'] = original_content
        current_notes['corrected_content'] = corrected_content
        
        # Handle different result types
        if result is None:
            # Order creation failed completely
            current_notes['reprocessing_status'] = 'failed'
            current_notes['reprocessing_message'] = 'Order creation failed completely after corrections.'
            result = {'status': 'failed', 'message': 'Order creation failed completely after corrections.'}
        elif isinstance(result, dict) and result.get('status') == 'failed':
            current_notes['reprocessing_status'] = 'failed'
            current_notes['reprocessing_message'] = result.get('message', 'Reprocessing failed after corrections.')
        else:
            current_notes['reprocessing_status'] = 'success'
            current_notes['reprocessing_message'] = 'Reprocessing successful after corrections.'
            
        message.processing_notes = json.dumps(current_notes, indent=2)
        message.save()
        
        return result
        
    except WhatsAppMessage.DoesNotExist:
        return {'error': 'Message not found'}
    except Exception as e:
        return {'error': f'Reprocessing failed: {str(e)}'}

def apply_corrections_to_content(content, corrections):
    """
    Apply user corrections to message content
    
    Args:
        content: Original message content
        corrections: Dict of corrections {original_line: corrected_data}
        
    Returns:
        Corrected message content
    """
    corrected_content = content
    
    for original_line, corrected_data in corrections.items():
        if isinstance(corrected_data, dict):
            # Check if we have a corrected_line (new format)
            if 'corrected_line' in corrected_data:
                corrected_line = corrected_data['corrected_line']
                # Replace the entire original line with the corrected line (case-insensitive)
                import re
                pattern = re.escape(original_line)
                corrected_content = re.sub(pattern, corrected_line, corrected_content, flags=re.IGNORECASE)
            else:
                # Fallback to old format - just replace the name
                corrected_name = corrected_data.get('name', original_line)
                import re
                pattern = re.escape(original_line)
                corrected_content = re.sub(pattern, corrected_name, corrected_content, flags=re.IGNORECASE)
        else:
            # Fallback for non-dict corrections
            import re
            pattern = re.escape(original_line)
            corrected_content = re.sub(pattern, corrected_data, corrected_content, flags=re.IGNORECASE)
    return corrected_content

def get_product_suggestions(product_name):
    """
    Get product suggestions for failed product matches
    
    Args:
        product_name: The product name that failed to match
        
    Returns:
        list: List of suggested products with details
    """
    from .smart_product_matcher import SmartProductMatcher
    from products.models import Product
    
    try:
        # Get or create smart matcher instance
        if not hasattr(get_product_suggestions, '_matcher'):
            get_product_suggestions._matcher = SmartProductMatcher()
        
        matcher = get_product_suggestions._matcher
        
        # Get suggestions for the product
        suggestions = matcher.get_suggestions(product_name, min_confidence=10.0, max_suggestions=20)
        
        # Convert to the format expected by the frontend
        suggestion_list = []
        if hasattr(suggestions, 'suggestions') and suggestions.suggestions:
            for suggestion in suggestions.suggestions:
                suggestion_list.append({
                    'id': suggestion.product.id,
                    'name': suggestion.product.name,
                    'unit': suggestion.product.unit,
                    'price': float(suggestion.product.price) if suggestion.product.price else 0.0,
                    'confidence': suggestion.confidence_score,
                    'description': f"{suggestion.product.name} - R{float(suggestion.product.price) if suggestion.product.price else 0.0:.2f}"
                })
        
        return suggestion_list
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error getting product suggestions for '{product_name}': {e}")
        return []

def get_or_create_customer(company_name, sender_name):
    """
    Get or create customer from company name using enhanced customer recognition
    
    Args:
        company_name: Name of the restaurant/company
        sender_name: Name of the person sending the message
        
    Returns:
        User instance (customer)
    """
    # ENHANCEMENT 1: Use seeded customer database for better matching
    from accounts.models import RestaurantProfile, PrivateCustomerProfile
    
    # Try to find existing customer by business name in RestaurantProfile
    try:
        restaurant_profile = RestaurantProfile.objects.filter(
            business_name__iexact=company_name
        ).first()
        
        if restaurant_profile:
            print(f"[CUSTOMER] Matched restaurant profile: {company_name} -> {restaurant_profile.business_name}")
            return restaurant_profile.user
    except Exception as e:
        print(f"[CUSTOMER] Error matching restaurant profile: {e}")
    
    # Try partial matching with seeded restaurant data
    try:
        restaurant_profiles = RestaurantProfile.objects.filter(
            business_name__icontains=company_name
        ) or RestaurantProfile.objects.filter(
            business_name__in=[company_name.replace(' ', ''), company_name.lower(), company_name.upper()]
        )
        
        if restaurant_profiles.exists():
            matched_profile = restaurant_profiles.first()
            print(f"[CUSTOMER] Partial matched restaurant profile: {company_name} -> {matched_profile.business_name}")
            return matched_profile.user
    except Exception as e:
        print(f"[CUSTOMER] Error with partial restaurant matching: {e}")
    
    # Check if it's a private customer (Marco, Sylvia, Arthur)
    private_customer_names = ['marco', 'sylvia', 'arthur']
    if company_name.lower() in private_customer_names:
        try:
            private_profile = PrivateCustomerProfile.objects.filter(
                user__first_name__iexact=company_name
            ).first()
            
            if private_profile:
                print(f"[CUSTOMER] Private customer matched: {company_name} -> {private_profile.user.first_name}")
                return private_profile.user
        except Exception as e:
            print(f"[CUSTOMER] Error matching private customer: {e}")
    
    # ENHANCEMENT 2: Improved email generation using canonical names
    canonical_names = {
        'mugg and bean': 'muggandbean',
        'casa bella': 'casabella', 
        'debonairs': 'debonairs',
        'wimpy mooikloof': 'wimpymooikloof',
        't-junction': 'tjunction',
        'maltos': 'maltos',
        'venue': 'venue',
        'pecanwood': 'pecanwood',
        'culinary institute': 'culinaryinstitute'
    }
    
    email_base = canonical_names.get(company_name.lower(), 
                                   re.sub(r'[^a-zA-Z0-9]', '', company_name.lower()))
    email = f"{email_base}@restaurant.com"
    
    # Try to find existing customer by email
    try:
        existing_customer = User.objects.get(email=email)
        print(f"[CUSTOMER] Found existing customer by email: {company_name} -> {email}")
        return existing_customer
    except User.DoesNotExist:
        pass
    
    # ENHANCEMENT 3: Create customer with better defaults and logging
    try:
        # Extract proper first and last names from company name
        name_parts = company_name.strip().split()
        if len(name_parts) >= 2:
            first_name = name_parts[0]
            last_name = ' '.join(name_parts[1:])
        else:
            first_name = company_name
            last_name = 'Restaurant'
        
        customer = User.objects.create(
            email=email,
            first_name=first_name,
            last_name=last_name,
            user_type='restaurant',
            is_active=True,
            phone=''  # Will be updated when we get phone info
        )
        
        # Determine customer segment and assign pricing rule
        customer_segment = 'standard'  # Default segment for new restaurant customers
        
        # Create a basic RestaurantProfile for new customers
        profile = RestaurantProfile.objects.create(
            user=customer,
            business_name=company_name,
            address='',  # To be updated
            city='Pretoria',  # Default based on Fambri Farms location
            payment_terms='Net 30',  # Default payment terms
            delivery_notes=f"Auto-created from WhatsApp message via {sender_name}",
            order_pattern="To be determined from order history"
        )
        
        # Assign default pricing rule based on customer segment
        try:
            from inventory.models import PricingRule
            default_pricing_rule = PricingRule.objects.filter(
                customer_segment=customer_segment,
                is_active=True
            ).first()
            
            if default_pricing_rule:
                profile.preferred_pricing_rule = default_pricing_rule
                profile.save()
                print(f"[PRICING] Assigned pricing rule '{default_pricing_rule.name}' to new customer {company_name}")
        except Exception as e:
            print(f"[PRICING] Failed to assign pricing rule to new customer: {e}")
        
        # Customer creation logged below with print statement
        
        print(f"[CUSTOMER] Created new customer: {company_name} (ID: {customer.id}) - NEEDS PROFILE COMPLETION")
        
        return customer
        
    except Exception as e:
        print(f"[CUSTOMER] Failed to create customer '{company_name}': {e}")
        # Fallback: try to find any customer with similar name
        fallback_customer = User.objects.filter(
            first_name__icontains=company_name[:10]
        ).first()
        
        if fallback_customer:
            # Customer fallback match found
            return fallback_customer
        
        return None

def get_valid_order_date(message_date):
    """
    Get valid order date (Monday or Thursday)
    
    Args:
        message_date: Date when message was sent
        
    Returns:
        date: Valid order date (Monday=0 or Thursday=3)
    """
    # If message is from Monday (0) or Thursday (3), use that date
    if message_date.weekday() in [0, 3]:
        return message_date
    
    # Otherwise, find next valid order date
    days_ahead = 1
    while days_ahead <= 7:
        check_date = message_date + timedelta(days=days_ahead)
        if check_date.weekday() in [0, 3]:
            return check_date
        days_ahead += 1
    
    # Fallback to original date (will trigger validation error)
    return message_date

def create_order_items(order, message):
    """
    Parse message content and create order items with fallback to notes
    
    Args:
        order: Order instance
        message: WhatsAppMessage instance
        
    Returns:
        dict: Results including items_created, failed_products, parsing_failures
    """
    content = message.content
    items_created = 0
    failed_products = []
    parsing_failures = []
    unparseable_lines = []
    
    # Parse items from message content
    parsed_result = parse_order_items(content)
    parsed_items = parsed_result['items']
    
    # Get parsing failures from the parse_order_items result
    parsing_failures_from_parsing = parsed_result.get('parsing_failures', [])
    
    # Track lines that couldn't be parsed for fallback notes
    content_lines = [line.strip() for line in content.split('\n') if line.strip()]
    parsed_line_texts = [item['original_text'] for item in parsed_items]
    
    for line in content_lines:
        # Skip company names and common headers
        if (not any(parsed_text.lower() in line.lower() for parsed_text in parsed_line_texts) and
            not message.extract_company_name() in line and
            not re.match(r'^(good\s+morning|hi|hello|order|please)', line.lower()) and
            len(line) > 3):  # Ignore very short lines
            unparseable_lines.append(line)
    
    # PRE-MATCH all products AND get pricing OUTSIDE transaction to avoid database query conflicts
    matched_products = {}
    customer_prices = {}
    
    for item_data in parsed_items:
        try:
            # Do product matching outside transaction
            match_result = get_or_create_product_enhanced(
                item_data['product_name'], 
                item_data.get('quantity'),
                item_data.get('unit'),
                original_message=item_data.get('original_text')
            )
            matched_products[item_data['product_name']] = match_result
            
            # Pre-calculate pricing outside transaction
            if match_result and isinstance(match_result, tuple):
                product, _, _ = match_result
                if product:
                    try:
                        # Fix: Use order.restaurant instead of order.customer
                        customer_price = get_customer_specific_price(product, order.restaurant)
                        customer_prices[product.id] = customer_price
                    except Exception as pricing_e:
                        print(f"Pre-pricing error for {product.name}: {pricing_e}")
                        customer_prices[product.id] = product.price
            
        except Exception as e:
            print(f"Pre-matching error for {item_data['product_name']}: {e}")
            matched_products[item_data['product_name']] = None
    
    # Now process items using pre-matched products
    for item_data in parsed_items:
        try:
            # Get pre-matched product
            match_result = matched_products.get(item_data['product_name'])
            
            # Handle the tuple return from enhanced matcher
            if match_result and isinstance(match_result, tuple):
                product, matched_quantity, matched_unit = match_result
                # Update item data with matched values if they're more specific
                if matched_quantity and matched_quantity != item_data.get('quantity'):
                    item_data['quantity'] = matched_quantity
                if matched_unit and matched_unit != item_data.get('unit'):
                    item_data['unit'] = matched_unit
            else:
                product = match_result
            
            if not product:
                # Check if this is a parsing error with suggestions
                if item_data.get('parsing_error', False):
                    parsing_failures.append({
                        'original_name': item_data['product_name'],
                        'failure_reason': item_data.get('error_reason', 'No matching product found'),
                        'original_text': item_data.get('original_text', ''),
                        'error_type': 'parsing_error',
                        'suggestions': item_data.get('suggestions', []),
                        'quantity': item_data.get('quantity'),
                        'unit': item_data.get('unit')
                    })
                else:
                    failed_products.append({
                        'original_name': item_data['product_name'],
                        'normalized_name': normalize_product_name_for_matching(item_data['product_name']),
                        'failure_reason': 'Product not found in database',
                        'original_text': item_data['original_text'],
                        'quantity': item_data['quantity'],
                        'unit': item_data['unit']
                    })
                log_processing_action(message, 'error', {
                    'error': f"Product not found: {item_data['product_name']}",
                    'item_data': item_data,
                    'action': 'product_lookup'
                })
                continue
            
            # Use pre-calculated pricing to avoid transaction conflicts
            customer_price = customer_prices.get(product.id, product.price)
            quantity_decimal = Decimal(str(item_data['quantity']))
            
            # Ensure customer_price is a Decimal
            if not isinstance(customer_price, Decimal):
                customer_price = Decimal(str(customer_price))
            
            # Ensure unit is not empty (required field)
            unit = item_data.get('unit')
            if unit is None or (isinstance(unit, str) and not unit.strip()):
                unit = 'each'  # Default unit if none provided
            else:
                unit = str(unit).strip()
            
            # Create order item with dynamic pricing
            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=quantity_decimal,
                unit=unit,
                price=customer_price,
                total_price=quantity_decimal * customer_price,
                original_text=item_data['original_text'],
                confidence_score=item_data.get('confidence', 0.8)
            )
            items_created += 1
            
            # Log pricing decision
            log_processing_action(message, 'dynamic_pricing_applied', {
                'product_name': product.name,
                'base_price': float(product.price or 0),
                'customer_price': float(customer_price),
                'customer_id': order.restaurant.id,
                'quantity': float(quantity_decimal),
                'total_price': float(quantity_decimal * customer_price)
            })
            
        except Exception as e:
            parsing_failures.append({
                'original_name': item_data['product_name'],
                'failure_reason': f"Failed to create item: {str(e)}",
                'original_text': item_data['original_text'],
                'error_type': 'item_creation_error'
            })
            log_processing_action(message, 'error', {
                'error': f"Failed to create item: {str(e)}",
                'item_data': item_data,
                'action': 'item_creation'
            })
            continue
    
    # Add unparseable lines as notes if any items were created successfully
    if unparseable_lines and items_created > 0:
        notes_text = "Unparsed items (added as notes):\n" + "\n".join(f"• {line}" for line in unparseable_lines)
        
        # Add to order notes or create a special note item
        if hasattr(order, 'notes'):
            existing_notes = order.notes or ""
            order.notes = f"{existing_notes}\n\n{notes_text}".strip()
            order.save()
        
        log_processing_action(message, 'unparsed_as_notes', {
            'unparsed_lines': unparseable_lines,
            'count': len(unparseable_lines),
            'action': 'fallback_notes'
        })
    
    # If no items were parsed but there are unparseable lines, create a note-only order
    elif not items_created and unparseable_lines:
        # Create a special "Notes" product for unparseable content
        # Get or create the Special department
        from products.models import Department
        special_dept, _ = Department.objects.get_or_create(
            name='Special',
            defaults={'description': 'Special order items and notes'}
        )
        
        notes_product, created = Product.objects.get_or_create(
            name="Order Notes",
            defaults={
                'price': Decimal('0.00'),
                'unit': 'note',
                'department': special_dept,
                'is_active': True
            }
        )
        
        notes_content = "\n".join(unparseable_lines)
        OrderItem.objects.create(
            order=order,
            product=notes_product,
            quantity=1,
            unit='note',
            price=Decimal('0.00'),
            total_price=Decimal('0.00'),
            original_text=f"Unparsed content: {notes_content[:100]}...",
            confidence_score=0.1,  # Low confidence since it's unparsed
            notes=notes_content
        )
        items_created = 1
        
        log_processing_action(message, 'note_item_created', {
            'unparsed_content': notes_content,
            'action': 'fallback_note_item'
        })
    
    # Add unparseable lines to parsing failures if no items were created
    if not items_created and unparseable_lines:
        for line in unparseable_lines:
            parsing_failures.append({
                'original_name': line,
                'failure_reason': 'Could not parse as order item',
                'original_text': line,
                'error_type': 'parsing_failure'
            })
    
    # Add parsing failures from the parsing step
    parsing_failures.extend(parsing_failures_from_parsing)
    
    # Calculate success rate
    total_attempts = len(parsed_items) + len(unparseable_lines) + len(parsing_failures_from_parsing)
    success_rate = round((items_created / total_attempts * 100), 1) if total_attempts > 0 else 0
    
    return {
        'items_created': items_created,
        'failed_products': failed_products,
        'parsing_failures': parsing_failures,
        'unparseable_lines': unparseable_lines,
        'total_attempts': total_attempts,
        'success_rate': success_rate
    }

def parse_order_items(content):
    """
    Parse order items from message content using SmartProductMatcher
    
    Args:
        content: Message content string
        
    Returns:
        list: List of parsed item dictionaries
    """
    from .smart_product_matcher import SmartProductMatcher
    from .message_parser import MessageParser
    
    try:
        # Get or create smart matcher instance
        if not hasattr(parse_order_items, '_matcher'):
            parse_order_items._matcher = SmartProductMatcher()
        
        matcher = parse_order_items._matcher
        
        # Extract company name to exclude it from product parsing
        message_parser = MessageParser()
        company_name = message_parser.to_canonical_company(content)
        
        # Remove company name from content before parsing products
        content_for_parsing = content
        if company_name:
            # Remove the company name line from the content
            lines = content.split('\n')
            filtered_lines = []
            for line in lines:
                line_stripped = line.strip()
                # Check if this line contains the company name
                if not message_parser.to_canonical_company(line_stripped):
                    filtered_lines.append(line)
                else:
                    # This line is a company name, skip it
                    continue
            content_for_parsing = '\n'.join(filtered_lines)
        
        # Parse the message (excluding company name)
        parsed_items = matcher.parse_message(content_for_parsing)
        
        # Get all lines from the filtered content to identify rejected items
        content_lines = [line.strip() for line in content_for_parsing.split('\n') if line.strip()]
        
        # Convert to Django's expected format using matched quantities
        items = []
        parsing_failures = []
        for parsed_item in parsed_items:
            # Check if this is ambiguous packaging that needs suggestions
            is_ambiguous_packaging = "AMBIGUOUS_PACKAGING" in parsed_item.extra_descriptions
            
            if is_ambiguous_packaging:
                # For ambiguous packaging, always generate suggestions based on product name
                suggestions = matcher.get_suggestions(parsed_item.product_name, min_confidence=5.0, max_suggestions=20)
                suggestions_list = []
                
                if suggestions.suggestions:
                    for suggestion in suggestions.suggestions:
                        suggestions_list.append({
                            'name': suggestion.product.name,
                            'confidence': suggestion.confidence_score,
                            'unit': suggestion.product.unit,
                            'price': float(suggestion.product.price) if suggestion.product.price else 0.0,
                            'id': suggestion.product.id
                        })
                
                # Add to parsing_failures instead of items for Flutter display
                parsing_failure = {
                    'original_name': parsed_item.product_name,
                    'failure_reason': 'Ambiguous packaging specification - please specify size (e.g., "5kg box" instead of "box")',
                    'original_text': parsed_item.original_message,
                    'error_type': 'parsing_error',
                    'suggestions': suggestions_list,
                    'quantity': parsed_item.quantity,
                    'unit': parsed_item.unit
                }
                parsing_failures.append(parsing_failure)
                # Skip adding to items - only add to parsing_failures
                continue
            else:
                # Normal processing for non-ambiguous items
                matches = matcher.find_matches(parsed_item)
                if matches and matches[0].confidence_score >= 60.0:  # Stricter threshold for main matching
                    best_match = matches[0]
                    
                    # Always use database product name when we have a good match
                    product_name = best_match.product.name
                    
                    item = {
                        'product_name': product_name,
                        'quantity': best_match.quantity,  # Use matched quantity, not parsed quantity
                        'unit': best_match.unit,  # Use matched unit, not parsed unit
                        'original_text': parsed_item.original_message,
                        'confidence': best_match.confidence_score
                    }
                else:
                    # No good match found - get suggestions for this product
                    suggestions = matcher.get_suggestions(parsed_item.product_name, min_confidence=5.0, max_suggestions=20)
                    suggestions_list = []
                    
                    if suggestions.suggestions:
                        for suggestion in suggestions.suggestions:
                            suggestions_list.append({
                                'name': suggestion.product.name,
                                'confidence': suggestion.confidence_score,
                                'unit': suggestion.product.unit,
                                'price': float(suggestion.product.price) if suggestion.product.price else 0.0,
                                'id': suggestion.product.id
                            })
                    
                    # Fallback to parsed values if no good match, but include suggestions
                    item = {
                        'product_name': parsed_item.product_name,
                        'quantity': parsed_item.quantity,
                        'unit': parsed_item.unit,
                        'original_text': parsed_item.original_message,
                        'confidence': 0.0,  # Low confidence since no match found
                        'suggestions': suggestions_list,
                        'parsing_error': True,
                        'error_reason': 'No matching product found in database'
                    }
                items.append(item)
        
        # Handle rejected items (lines that couldn't be parsed due to ambiguous packaging)
        # Include both items and parsing_failures to avoid processing the same line twice
        parsed_line_texts = [item['original_text'] for item in items]
        parsed_line_texts.extend([failure['original_text'] for failure in parsing_failures])
        for line in content_lines:
            # Skip if this line was already parsed
            if any(parsed_text.lower() in line.lower() for parsed_text in parsed_line_texts):
                continue
                
            # Skip company names and common headers
            if (not re.match(r'^(good\s+morning|hi|hello|order|please)', line.lower()) and
                len(line) > 3):  # Ignore very short lines
                
                # Try to extract a product name from the rejected line
                # Remove common prefixes and clean up the line
                clean_line = re.sub(r'^\d+[\.\)]\s*', '', line)  # Remove "1.", "2)", etc.
                clean_line = re.sub(r'^\d+\s*[x×]\s*', '', clean_line)  # Remove "3x", "2×", etc.
                clean_line = re.sub(r'\s+\d+\s*[x×]\s*', ' ', clean_line)  # Remove " 3x", " 2×", etc.
                
                # Extract potential product name
                product_name = clean_line
                
                # Remove container words and quantities to get the base product name
                container_words = ['box', 'bag', 'packet', 'pack', 'punnet', 'bunch', 'head', 'each', 'piece']
                words = clean_line.split()
                
                # Find the last container word and remove everything after it
                last_container_index = -1
                for i, word in enumerate(words):
                    if word.lower() in container_words:
                        last_container_index = i
                
                if last_container_index >= 0:
                    # Keep only words before the last container word
                    product_name = ' '.join(words[:last_container_index]).strip()
                else:
                    # No container word found, try to remove number+unit combinations
                    if re.search(r'\d+[a-zA-Z]+', clean_line):
                        parts = re.split(r'\s+(\d+[a-zA-Z]+)', clean_line)
                        if len(parts) >= 2:
                            product_name = parts[0].strip()
                
                # If product name is empty or too short, use the original line
                if not product_name or len(product_name) < 2:
                    product_name = clean_line
                
                # Generate suggestions for the rejected item
                suggestions = matcher.get_suggestions(product_name, min_confidence=5.0, max_suggestions=20)
                suggestions_list = []
                
                if suggestions.suggestions:
                    for suggestion in suggestions.suggestions:
                        suggestions_list.append({
                            'name': suggestion.product.name,
                            'confidence': suggestion.confidence_score,
                            'unit': suggestion.product.unit,
                            'price': float(suggestion.product.price) if suggestion.product.price else 0.0,
                            'id': suggestion.product.id
                        })
                
                # Add as a rejected item with suggestions
                item = {
                    'product_name': product_name,
                    'quantity': 1.0,  # Default quantity
                    'unit': None,
                    'original_text': line,
                    'confidence': 0.0,
                    'suggestions': suggestions_list,
                    'parsing_error': True,
                    'error_reason': 'Ambiguous packaging specification - please specify size (e.g., "5kg box" instead of "box")'
                }
                items.append(item)
        
        return {
            'items': items,
            'parsing_failures': parsing_failures,
            'failed_products': []
        }
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error parsing order items: {e}")
        return {
            'items': [],
            'parsing_failures': [],
            'failed_products': []
        }

def detect_and_correct_irregular_format(line):
    """
    Detect and correct irregular message formats where items and quantities appear flipped
    
    This handles cases like:
    - "Basil 200g" -> "200g Basil" (product name followed by weight)
    - "Carrots 10kg" -> "10kg Carrots" (product name followed by weight)
    - "Green peppers 1box" -> "1 box Green peppers" (product name followed by unit)
    - "20piece @ R18.75" -> "20 piece" (pricing format)
    
    Args:
        line: Original line from message
        
    Returns:
        str: Corrected line or original if no correction needed
    """
    if not line or not line.strip():
        return line
    
    original_line = line.strip()
    
    # Pattern 1: Handle "20piece @ R18.75" format - extract quantity and unit, ignore pricing
    price_pattern = r'^(\d+(?:\.\d+)?)\s*(piece|kg|g|gram|box|boxes|bag|bags|bunch|bunches|head|heads|punnets?|packets?)\s*@\s*R[\d.,]+'
    match = re.search(price_pattern, original_line, re.IGNORECASE)
    if match:
        quantity = match.group(1)
        unit = match.group(2)
        corrected = f"{quantity} {unit}"
        return corrected
    
    # Pattern 2: Handle "300g @ R31.25" format - weight with price, ignore pricing
    weight_price_pattern = r'^(\d+(?:\.\d+)?)\s*(g|gram|kg|kilos?)\s*@\s*R[\d.,]+'
    match = re.search(weight_price_pattern, original_line, re.IGNORECASE)
    if match:
        quantity = match.group(1)
        unit = match.group(2)
        corrected = f"{quantity}{unit}"
        return corrected
    
    # Pattern 3: Handle "Product Name 200g" format - product followed by weight
    product_weight_pattern = r'^([A-Za-z][A-Za-z\s]+?)\s+(\d+(?:\.\d+)?)\s*(g|gram|kg|kilos?)$'
    match = re.search(product_weight_pattern, original_line, re.IGNORECASE)
    if match:
        product_name = match.group(1).strip()
        quantity = match.group(2)
        unit = match.group(3)
        
        # Only correct if the product name doesn't look like a quantity itself
        if not re.match(r'^\d+', product_name):
            corrected = f"{quantity}{unit} {product_name}"
            return corrected
    
    # Pattern 4: Handle "Product Name 1box" format - product followed by unit quantity
    # BUT avoid correcting lines with "x" multiplier (e.g., "Lemon x 1 box")
    product_unit_pattern = r'^([A-Za-z][A-Za-z\s]+?)\s+(\d+)\s*(box|boxes|bag|bags|bunch|bunches|head|heads|punnets?|packets?|piece|pieces)$'
    match = re.search(product_unit_pattern, original_line, re.IGNORECASE)
    if match:
        product_name = match.group(1).strip()
        quantity = match.group(2)
        unit = match.group(3)
        
        # Only correct if the product name doesn't look like a quantity itself
        # AND doesn't contain "x" multiplier (avoid correcting "Lemon x 1 box")
        if (not re.match(r'^\d+', product_name) and 
            'x' not in product_name.lower() and 
            '×' not in product_name):
            corrected = f"{quantity} {unit} {product_name}"
            return corrected
    
    # If no irregular format detected, return original
    return original_line

def get_database_units():
    """Get all units from database for regex patterns"""
    from settings.models import UnitOfMeasure
    try:
        # Get units from the new configuration system
        units = list(UnitOfMeasure.objects.filter(is_active=True).values_list('name', flat=True))
        return units
    except:
        # Fallback to old method if new system not available
        from products.models import Product
        units = list(Product.objects.values_list('unit', flat=True).distinct())
        return units

def parse_single_item(line):
    """
    Simplified parsing using database units and product names
    
    Args:
        line: Single line of text containing an item
        
    Returns:
        dict: Parsed item data or None if parsing failed
    """
    original_line = line
    line = line.strip()
    
    # Normalize symbols
    line = re.sub(r'\s*[×*]\s*', ' x ', line)
    
    # Get database units for regex
    db_units = get_database_units()
    units_pattern = '|'.join(re.escape(unit) for unit in db_units)
    
    # Simplified patterns using database units
    patterns = [
        # Special pattern for packet items: "3 x mint packet 100g" -> extract 100g as the key info
        (rf'(\d+(?:\.\d+)?)\s*[x×]\s*(.+?)\s+packet\s+(\d+(?:\.\d+)?)\s*g', 'qty_x_product_packet_grams'),
        
        # Product x Quantity Unit: "Carrots x 10kg", "Onions x 20kg" 
        (rf'(.+?)\s*[x×]\s*(\d+(?:\.\d+)?)\s*({units_pattern})', 'product_x_qty_unit'),
        
        # Product x Quantity: "Cucumber x 10", "Broccoli x 5 heads"
        (rf'(.+?)\s*[x×]\s*(\d+(?:\.\d+)?)\s*({units_pattern})?', 'product_x_qty'),
        
        # Quantity x Unit Product: "2x box lemons", "1 x bag oranges"
        (rf'(\d+(?:\.\d+)?)\s*[x×]\s*({units_pattern})\s+(.+)', 'qty_x_unit_product'),
        
        # Quantity Unit Product (with space): "2 box lemons", "5 kg tomatoes"  
        (rf'(\d+(?:\.\d+)?)\s+({units_pattern})\s+(.+)', 'qty_unit_product'),
        
        # Quantity Unit Product (no space): "3kg carrots", "2kg tomato"
        (rf'(\d+(?:\.\d+)?)({units_pattern})\s+(.+)', 'qty_unit_product_nospace'),
        
        # Quantity x Product: "2x lemons", "5 × tomatoes"
        (rf'(\d+(?:\.\d+)?)\s*[x×]\s*(.+)', 'qty_x_product'),
        
        # Product Quantity Each: "Cucumber 2 each", "Pineapple 1 each"
        (rf'(.+?)\s+(\d+(?:\.\d+)?)\s+each', 'product_qty_each'),
        
        # Product Quantity (no unit): "Potato 6", "Onion 3" -> assume piece/each
        (rf'(.+?)\s+(\d+(?:\.\d+)?)$', 'product_qty_nounit'),
        
        # Simple Quantity Product: "5 tomatoes", "10 lemons"
        (rf'(\d+(?:\.\d+)?)\s+(.+)', 'qty_product'),
    ]
    
    for pattern, pattern_type in patterns:
        match = re.search(pattern, line, re.IGNORECASE)
        if match:
            groups = match.groups()
            
            try:
                if pattern_type == 'qty_x_product_packet_grams':
                    # "3 x mint packet 100g" -> qty=100, unit=packet, product=mint (ignore the 3x)
                    # We want the packet size (100g) as the key quantity, not the multiplier (3x)
                    multiplier = float(groups[0])  # The "3" in "3 x"
                    product_name = groups[1].strip()  # The "mint" part
                    packet_size = float(groups[2])  # The "100" in "100g"
                    
                    # Use packet size as quantity and packet as unit
                    quantity = packet_size
                    unit = 'packet'
                    
                elif pattern_type == 'product_x_qty_unit':
                    # "Carrots x 10kg" -> product=Carrots, qty=10, unit=kg
                    product_name = groups[0].strip()
                    quantity = float(groups[1])
                    unit = normalize_unit(groups[2])
                    
                elif pattern_type == 'product_x_qty':
                    # "Cucumber x 10" or "Broccoli x 5 heads" -> product=Cucumber, qty=10, unit=piece/heads
                    product_name = groups[0].strip()
                    quantity = float(groups[1])
                    unit = normalize_unit(groups[2]) if groups[2] else 'piece'
                    
                elif pattern_type == 'qty_x_unit_product':
                    # "2x box lemons" -> qty=2, unit=box, product=lemons
                    quantity = float(groups[0])
                    unit = normalize_unit(groups[1])
                    product_name = groups[2].strip()
                    
                elif pattern_type == 'qty_unit_product':
                    # "2 box lemons" -> qty=2, unit=box, product=lemons
                    quantity = float(groups[0])
                    unit = normalize_unit(groups[1])
                    product_name = groups[2].strip()
                    
                elif pattern_type == 'qty_unit_product_nospace':
                    # "3kg carrots" -> qty=3, unit=kg, product=carrots
                    quantity = float(groups[0])
                    unit = normalize_unit(groups[1])
                    product_name = groups[2].strip()
                    
                elif pattern_type == 'qty_x_product':
                    # "2x lemons" -> qty=2, product=lemons, unit=piece (default)
                    quantity = float(groups[0])
                    product_name = groups[1].strip()
                    unit = 'piece'  # Default unit
                    
                elif pattern_type == 'product_qty_each':
                    # "Cucumber 2 each" -> product=Cucumber, qty=2, unit=each
                    product_name = groups[0].strip()
                    quantity = float(groups[1])
                    unit = 'each'
                    
                elif pattern_type == 'product_qty_nounit':
                    # "Potato 6" -> product=Potato, qty=6, unit=piece (default, but prefer each if exists)
                    product_name = groups[0].strip()
                    quantity = float(groups[1])
                    # For items that commonly come as individual pieces, prefer 'each'
                    each_items = ['cucumber', 'pineapple', 'watermelon', 'melon', 'avocado', 'avo']
                    if any(item in product_name.lower() for item in each_items):
                        unit = 'each'
                    else:
                        unit = 'piece'  # Default
                    
                elif pattern_type == 'qty_product':
                    # "5 tomatoes" -> qty=5, product=tomatoes, unit=piece (default)
                    quantity = float(groups[0])
                    product_name = groups[1].strip()
                    unit = 'piece'  # Default unit
                    
                else:
                    continue
                
                # Clean product name
                product_name = clean_product_name(product_name)
                
                if product_name and quantity > 0:
                    return {
                        'quantity': quantity,
                        'unit': unit,
                        'product_name': product_name,
                        'original_text': original_line,
                        'confidence': 0.8
                    }
                    
            except (ValueError, IndexError):
                continue
    
    return None

def normalize_unit(unit):
    """Normalize unit names to standard forms"""
    unit = unit.lower().strip()
    
    unit_mappings = {
        'pun': 'punnet',
        'punnets': 'punnet',
        'boxes': 'box',
        'bags': 'bag',
        'packets': 'packet',
        'bunches': 'bunch',
        'heads': 'head',
        'pieces': 'piece',
        'kilos': 'kg',
        'kilogram': 'kg',
        'kilograms': 'kg',
    }
    
    return unit_mappings.get(unit, unit)

def clean_product_name(name):
    """
    Clean and normalize product name
    
    Args:
        name: Raw product name from message
        
    Returns:
        str: Cleaned product name
    """
    if not name:
        return ''
    
    # Remove common prefixes/suffixes
    name = re.sub(r'^(fresh|organic|local|good|quality)\s+', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\s+(fresh|organic|local|please|thanks?|tnx)$', '', name, flags=re.IGNORECASE)
    
    # Remove extra whitespace and punctuation
    name = re.sub(r'\s+', ' ', name)
    name = re.sub(r'^[^\w]+|[^\w]+$', '', name)
    
    # Normalize common product variations - only for exact matches to avoid double replacements
    replacements = {
        'tomatos': 'tomatoes',
        'tomatoe': 'tomatoes',
        'onion': 'onions',
        'potato': 'potatoes',
        'potatos': 'potatoes',
        'mushroom': 'mushrooms',
        'carrot': 'carrots',
    }
    
    name_lower = name.lower()
    for old, new in replacements.items():
        if old == name_lower:  # Only exact matches to avoid "tomatoes" -> "tomatoess"
            name = new.title()
            break
    else:
        name = name.title()
    
    return name.strip()

def match_size_specific_product(product_name, quantity, unit):
    """
    Match products with specific sizes based on quantity and unit
    
    Args:
        product_name: Base product name (e.g., "Red Onions", "Basil")
        quantity: Quantity from parsing (e.g., 2, 100)
        unit: Unit from parsing (e.g., "bag", "packet", "g")
        
    Returns:
        Product instance or None
    """
    # Handle gram quantities that should match packet products
    if unit == 'g' and quantity in [50, 100, 200, 500]:
        # Check if product name contains "packet" - if so, treat as packet unit
        if 'packet' in product_name.lower():
            # Remove "packet" from product name and treat as packet unit
            clean_name = re.sub(r'\s*packet\s*', ' ', product_name, flags=re.IGNORECASE).strip()
            return match_size_specific_product(clean_name, quantity, 'packet')
        
        # Also try direct packet matching for herbs/spices
        herb_names = ['basil', 'parsley', 'thyme', 'mint', 'coriander', 'rosemary', 'oregano', 'sage', 'micro herbs', 'edible flowers', 'wild rocket', 'rocket']
        if any(herb in product_name.lower() for herb in herb_names):
            # Try matching as packet
            packet_match = match_size_specific_product(product_name, quantity, 'packet')
            if packet_match:
                return packet_match
    
    if unit not in ['bag', 'packet']:
        return None
    
    # Determine size format based on unit
    if unit == 'bag':
        # Format: "Red Onions (2kg bag)" for quantity=2, unit=bag
        size_specific_name = f"{product_name} ({int(quantity)}kg bag)"
        variations = [
            f"{product_name} ({int(quantity)}kg bag)",
            f"{product_name} ({quantity}kg bag)",
            f"{product_name} {int(quantity)}kg bag",
            f"{product_name} {quantity}kg bag",
        ]
    elif unit == 'packet':
        # Format: "Basil (100g packet)" for quantity=100, unit=packet
        size_specific_name = f"{product_name} ({int(quantity)}g packet)"
        variations = [
            f"{product_name} ({int(quantity)}g packet)",
            f"{product_name} ({quantity}g packet)",
            f"{product_name} {int(quantity)}g packet",
            f"{product_name} {quantity}g packet",
        ]
    
    # Try exact match first
    try:
        product = Product.objects.get(name=size_specific_name, is_active=True)
        print(f"[PRODUCT] {unit.title()} size match: '{product_name}' {quantity}{unit} -> {product.name}")
        return product
    except Product.DoesNotExist:
        # Try variations with different formatting
        for variation in variations:
            try:
                product = Product.objects.get(name=variation, is_active=True)
                print(f"[PRODUCT] {unit.title()} size variation match: '{product_name}' {quantity}{unit} -> {product.name}")
                return product
            except Product.DoesNotExist:
                continue
    
    return None




def get_or_create_product_enhanced(product_name, quantity, unit, customer=None, original_message=None):
    """
    Enhanced product matching using SmartProductMatcher with production data
    """
    from .smart_product_matcher import SmartProductMatcher
    from products.models import Product
    from settings.models import BusinessConfiguration
    import logging
    
    logger = logging.getLogger(__name__)
    
    try:
        # Get configuration from database
        confidence_threshold_config = BusinessConfiguration.objects.filter(
            name='product_matching_confidence_threshold',
            is_active=True
        ).first()
        
        confidence_threshold = 25.0  # Default fallback
        if confidence_threshold_config:
            confidence_threshold = float(confidence_threshold_config.get_value())
        
        # Get or create smart matcher instance
        if not hasattr(get_or_create_product_enhanced, '_matcher'):
            get_or_create_product_enhanced._matcher = SmartProductMatcher()
        
        matcher = get_or_create_product_enhanced._matcher
        
        # If we have an original message, re-parse it for better matching
        if original_message:
            parsed_items = matcher.parse_message(original_message)
            if parsed_items:
                parsed_message = parsed_items[0]  # Use the first parsed item
            else:
                # Fallback to manual parsing
                parsed_message = ParsedMessage(
                    product_name=product_name,
                    quantity=quantity or 1.0,
                    unit=unit or 'each',
                    extra_descriptions=[],
                    original_message=original_message
                )
        else:
            # Create a full parsed message for better matching
            from .smart_product_matcher import ParsedMessage
            parsed_message = ParsedMessage(
                product_name=product_name,
                quantity=quantity or 1.0,
                unit=unit or 'each',
                extra_descriptions=[],
                original_message=f"{product_name} {quantity or 1}{unit or 'each'}"
            )
        
        # Use find_matches directly for better quantity-specific matching
        matches = matcher.find_matches(parsed_message)
        
        # Create suggestions object manually
        from .smart_product_matcher import SmartMatchSuggestions
        suggestions = SmartMatchSuggestions(
            best_match=matches[0] if matches and matches[0].confidence_score >= confidence_threshold else None,
            suggestions=matches[:5],
            parsed_input=parsed_message,
            total_candidates=len(matches)
        )
        
        if suggestions.best_match and suggestions.best_match.confidence_score >= confidence_threshold:
            # Should now get real Django Product from database
            product = suggestions.best_match.product
            
            # Verify it's a real Django Product (has _state attribute)
            if hasattr(product, '_state'):
                # Use the unit from the matched product, not the original parsed unit
                matched_unit = suggestions.best_match.unit
                logger.info(f"Smart matcher: '{product_name}' -> '{product.name}' "
                          f"({suggestions.best_match.confidence_score:.1f}% confidence) "
                          f"unit: {unit} -> {matched_unit}")
                return product, quantity, matched_unit
            else:
                logger.error(f"SmartProductMatcher returned non-Django object: {type(product)}")
                return None, None, None
        
        # No good match found - log suggestions but return standard format
        logger.warning(f"No match found for '{product_name}'")
        if suggestions.suggestions:
            logger.info(f"Available suggestions for '{product_name}':")
            for i, suggestion in enumerate(suggestions.suggestions[:5]):
                logger.info(f"  {i+1}. {suggestion.product.name} ({suggestion.confidence_score:.1f}% match)")
        
        return None, None, None
        
    except Exception as e:
        logger.error(f"Smart matcher error: {e}")
        return None, None, None



def normalize_product_name_for_matching(name):
    """Normalize product name for better matching"""
    if not name:
        return ''
    
    # Remove quantities first (e.g., "x3", "3x", "2kg", etc.)
    name = re.sub(r'\s*[xX×]\s*\d+\s*$', '', name)  # Remove "x3", "X3", "×3" at end
    name = re.sub(r'^\d+\s*[xX×]\s*', '', name)     # Remove "3x", "3X", "3×" at start
    
    # Remove standalone "X" at end (e.g., "Carrots X" -> "Carrots")
    name = re.sub(r'\s+[xX]\s*$', '', name)
    
    name = re.sub(r'\s*\d+\s*(kg|g|ml|l|pcs?|pieces?|box|boxes?|bag|bags?|punnet|punnets?|heads?)\s*$', '', name, flags=re.IGNORECASE)
    
    # Remove standalone quantity + unit patterns (e.g., "10 heads", "5 kg")
    name = re.sub(r'^\d+\s+(heads?|kg|g|ml|l|pcs?|pieces?|box|boxes?|bag|bags?|punnet|punnets?)\s+', '', name, flags=re.IGNORECASE)
    
    # Remove standalone unit patterns without numbers (e.g., "heads broccoli" -> "broccoli")
    name = re.sub(r'^(heads?|kg|g|ml|l|pcs?|pieces?|box|boxes?|bag|bags?|punnet|punnets?)\s+', '', name, flags=re.IGNORECASE)
    
    # Remove single letter prefixes that are likely quantity descriptors (e.g., "S Broccoli" -> "Broccoli")
    # This handles cases where "S Broccoli Head" becomes "S Broccoli" after removing "Head"
    name = re.sub(r'^[A-Z]\s+', '', name)
    
    # Remove unit suffixes that might remain (e.g., "Broccoli Head" -> "Broccoli")
    name = re.sub(r'\s+(heads?|kg|g|ml|l|pcs?|pieces?|box|boxes?|bag|bags?|punnet|punnets?)$', '', name, flags=re.IGNORECASE)
    
    # Remove common prefixes/suffixes
    name = re.sub(r'^(fresh|organic|local|good|quality|farm)\s+', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\s+(fresh|organic|local|please|thanks?|tnx)$', '', name, flags=re.IGNORECASE)
    
    # Normalize spacing and punctuation
    name = re.sub(r'\s+', ' ', name)
    name = re.sub(r'^[^\w]+|[^\w]+$', '', name)
    
    # Convert to title case
    return name.strip().title()


def determine_product_department(product_name):
    """Determine product department based on name"""
    from products.models import Department
    
    # Department mapping based on SHALLOME data
    department_keywords = {
        'vegetables': ['tomato', 'potato', 'onion', 'lettuce', 'spinach', 'carrot', 'mushroom', 
                     'pepper', 'cucumber', 'broccoli', 'cauliflower', 'cabbage', 'corn', 'pea'],
        'fruits': ['apple', 'banana', 'orange', 'lemon', 'lime', 'strawberry', 'avocado', 
                  'naartjie', 'grape', 'pear', 'peach'],
        'herbs & spices': ['basil', 'parsley', 'coriander', 'rosemary', 'mint', 'thyme', 
                          'chilli', 'chili', 'ginger', 'garlic'],
        'mushrooms': ['mushroom', 'oyster', 'button', 'shiitake'],
        'specialty items': ['microgreen', 'sprout', 'edible flower']
    }
    
    product_lower = product_name.lower()
    
    for dept_name, keywords in department_keywords.items():
        if any(keyword in product_lower for keyword in keywords):
            try:
                return Department.objects.get(name__iexact=dept_name)
            except Department.DoesNotExist:
                pass
    
    # Default to vegetables (most common)
    try:
        return Department.objects.get(name__iexact='vegetables')
    except Department.DoesNotExist:
        return Department.objects.first()  # Fallback to any department


def determine_product_unit(product_name):
    """Determine appropriate unit based on product name"""
    product_lower = product_name.lower()
    
    # Unit patterns based on SHALLOME data
    if any(word in product_lower for word in ['lettuce', 'cabbage', 'cauliflower', 'broccoli']):
        return 'head'
    elif any(word in product_lower for word in ['herb', 'basil', 'parsley', 'coriander', 'mint']):
        return 'bunch'  
    elif any(word in product_lower for word in ['tomato', 'avocado', 'apple', 'orange']):
        return 'kg'
    elif any(word in product_lower for word in ['strawberry', 'cherry']):
        return 'punnet'
    else:
        return 'kg'  # Default unit


def estimate_product_price(product_name):
    """Estimate product price based on similar products and market data"""
    from inventory.models import MarketPrice
    from decimal import Decimal
    
    # Try to find similar products for pricing
    try:
        similar_products = Product.objects.filter(
            name__icontains=product_name[:6],
            price__gt=0
        ).exclude(price=0)
        
        if similar_products.exists():
            from django.db import models
            avg_price = similar_products.aggregate(
                avg_price=models.Avg('price')
            )['avg_price']
            return Decimal(str(avg_price)) if avg_price else Decimal('25.00')
    except Exception:
        pass
    
    # Fallback pricing based on product type
    product_lower = product_name.lower()
    
    if any(word in product_lower for word in ['herb', 'basil', 'parsley', 'coriander']):
        return Decimal('15.00')  # Herbs are typically cheaper per bunch
    elif any(word in product_lower for word in ['strawberry', 'cherry', 'specialty']):
        return Decimal('45.00')  # Premium items
    elif any(word in product_lower for word in ['mushroom', 'avocado']):
        return Decimal('35.00')  # Mid-range items
    else:
        return Decimal('25.00')  # Default price


def get_customer_specific_price(product, customer):
    """
    Get customer-specific pricing using the dynamic pricing system
    
    Args:
        product: Product instance
        customer: User instance (customer)
        
    Returns:
        Decimal: Customer-specific price
    """
    try:
        # ENHANCEMENT 6: Integrate with dynamic pricing system
        from inventory.models import CustomerPriceListItem, PricingRule
        from accounts.models import RestaurantProfile
        
        # Try to get customer-specific price from price list
        try:
            from datetime import date
            today = date.today()
            
            price_item = CustomerPriceListItem.objects.filter(
                price_list__customer=customer,
                product=product,
                price_list__status='active',
                price_list__effective_from__lte=today,
                price_list__effective_until__gte=today
            ).select_related('price_list').first()
            
            if price_item:
                # Customer price list item found
                return price_item.customer_price_incl_vat
        except Exception as e:
            print(f"[PRICING] Error getting customer price list: {e}")
        
        # Determine customer segment for pricing rules
        customer_segment = determine_customer_segment(customer)
        
        # Apply pricing rules based on customer segment
        try:
            pricing_rule = PricingRule.objects.filter(
                customer_segment=customer_segment,
                is_active=True
            ).first()
            
            if pricing_rule and product.price:
                # Apply markup/discount
                if pricing_rule.base_markup_percentage:
                    adjusted_price = product.price * (1 + pricing_rule.base_markup_percentage / 100)
                    print(f"[PRICING] Applied {pricing_rule.base_markup_percentage}% markup to {product.name}: {product.price} -> {adjusted_price}")
                    return adjusted_price
                elif hasattr(pricing_rule, 'discount_percentage') and pricing_rule.discount_percentage:
                    adjusted_price = product.price * (1 - pricing_rule.discount_percentage / 100)
                    print(f"[PRICING] Applied {pricing_rule.discount_percentage}% discount to {product.name}: {product.price} -> {adjusted_price}")
                    return adjusted_price
                else:
                    print(f"[PRICING] No markup/discount configured for pricing rule: {pricing_rule.name}")
                    return product.price
            else:
                print(f"[PRICING] No pricing rule found for segment '{customer_segment}' or product has no price")
                
        except Exception as e:
            print(f"[PRICING] Error applying pricing rule: {e}")
        
        # Fallback to base product price
        return product.price or Decimal('25.00')
        
    except Exception as e:
        print(f"[PRICING] Error in customer-specific pricing: {e}")
        return product.price or Decimal('25.00')


def determine_customer_segment(customer):
    """
    Determine customer segment for pricing
    
    Args:
        customer: User instance
        
    Returns:
        str: Customer segment
    """
    try:
        from accounts.models import RestaurantProfile
        
        # Check user type first
        if customer.user_type == 'private':
            return 'retail'  # Private customers use retail pricing
        
        # Check if customer has a preferred pricing rule set
        if hasattr(customer, 'restaurantprofile'):
            profile = customer.restaurantprofile
            
            # If customer has a preferred pricing rule, use its segment
            if hasattr(profile, 'preferred_pricing_rule') and profile.preferred_pricing_rule:
                return profile.preferred_pricing_rule.customer_segment
            
            # Segment based on payment terms and business characteristics
            payment_terms = profile.payment_terms.lower() if profile.payment_terms else ''
            
            # Wholesale customers (quick payment, bulk orders)
            if 'net 7' in payment_terms or '7 days' in payment_terms:
                return 'wholesale'
            
            # Premium customers (longer payment terms, established businesses)
            elif 'net 60' in payment_terms or '60 days' in payment_terms:
                return 'premium'
            
            # Budget customers (private or small businesses)
            elif hasattr(profile, 'is_private_customer') and profile.is_private_customer:
                return 'budget'
            
            # Standard customers (default business customers)
            else:
                return 'standard'
        
        # Default segment for customers without profiles
        return 'standard'
        
    except Exception as e:
        print(f"[PRICING] Error determining customer segment: {e}")
        return 'standard'


def process_stock_updates(messages):
    """
    Process stock update messages from SHALLOME
    
    Args:
        messages: List of WhatsAppMessage instances
        
    Returns:
        int: Number of stock updates created
    """
    stock_updates_created = 0
    
    for message in messages:
        if message.message_type == 'stock' and message.is_stock_controller():
            try:
                stock_data = parse_stock_message(message)
                if stock_data:
                    stock_update, created = StockUpdate.objects.get_or_create(
                        message=message,
                        defaults={
                            'stock_date': stock_data['date'],
                            'order_day': stock_data['order_day'],
                            'items': stock_data['items']
                        }
                    )
                    
                    if created:
                        stock_updates_created += 1
                        log_processing_action(message, 'stock_updated', {
                            'items_count': len(stock_data['items']),
                            'order_day': stock_data['order_day']
                        })
                        
            except Exception as e:
                log_processing_action(message, 'error', {
                    'error': str(e),
                    'action': 'stock_processing'
                })
    
    return stock_updates_created

def parse_stock_message(message):
    """
    Parse stock update message from SHALLOME
    
    Args:
        message: WhatsAppMessage instance
        
    Returns:
        dict: Parsed stock data or None
    """
    content = message.content
    lines = content.split('\n')
    
    # Find date line (STOKE AS AT 28 AUGUST 2025)
    stock_date = None
    for line in lines:
        if 'STOKE AS AT' in line.upper() or 'STOCK AS AT' in line.upper():
            # Try different date formats: "02 SEP 2025", "1Sep 2025", "02SEP2025"
            date_match = re.search(r'(\d{1,2})\s*(\w+)\s*(\d{4})', line)
            if date_match:
                day, month_name, year = date_match.groups()
                try:
                    # Convert month name to number (support both full names and abbreviations)
                    month_names = {
                        'january': 1, 'february': 2, 'march': 3, 'april': 4,
                        'may': 5, 'june': 6, 'july': 7, 'august': 8,
                        'september': 9, 'october': 10, 'november': 11, 'december': 12,
                        # Abbreviations
                        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4,
                        'may': 5, 'jun': 6, 'jul': 7, 'aug': 8,
                        'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
                    }
                    month_num = month_names.get(month_name.lower())
                    if month_num:
                        stock_date = date(int(year), month_num, int(day))
                        break
                except ValueError:
                    continue
    
    # If no date found in header, use message timestamp date as fallback
    if not stock_date:
        if message.timestamp:
            stock_date = message.timestamp.date()
        else:
            # Last resort: use today's date
            stock_date = timezone.now().date()
    
    # Parse stock items (both numbered and unnumbered) with detailed tracking
    items = {}
    parsing_failures = []
    total_lines_processed = 0
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Skip header lines and non-stock lines
        skip_patterns = [
            r'^hazvinei',  # Contact info
            r'^stock as at',  # Date header
            r'^temp \d+',  # Temperature
            r'^sorry',  # Apology text
            r'we have enough',  # Availability notes
            r'^\+27',  # Phone numbers
            r'^SHALLOME$',  # Company name alone
        ]
        
        should_skip = any(re.match(pattern, line, re.IGNORECASE) for pattern in skip_patterns)
        if should_skip:
            continue
        
        # Try to parse as stock item if it contains quantity patterns
        has_quantity = re.search(r'\d+(?:\.\d+)?\s*(kg|g|ml|l|pcs?|pieces?|boxes?|box|bags?|bag|bunches?|bunch|heads?|head|punnets?|punnet|pun|each)', line, re.IGNORECASE)
        
        if has_quantity:
            total_lines_processed += 1
            item = parse_stock_item(line)
            if item:
                items[item['name']] = {
                    'quantity': item['quantity'],
                    'unit': item['unit'],
                    'original_line': line
                }
            else:
                # Track parsing failures
                parsing_failures.append({
                    'original_line': line,
                    'failure_reason': 'Failed to parse quantity/unit pattern',
                    'error_type': 'parsing_failure'
                })
    
    if not items and not parsing_failures:
        return None
    
    result = {
        'date': stock_date,
        'order_day': determine_order_day(message.timestamp.date()),
        'items': items,
        'total_lines_processed': total_lines_processed,
        'successful_parses': len(items),
        'parsing_failures': parsing_failures,
        'parsing_success_rate': round((len(items) / (len(items) + len(parsing_failures)) * 100), 1) if (len(items) + len(parsing_failures)) > 0 else 0
    }
    
    return result

def create_stock_update_from_message_with_suggestions(message):
    """
    Parse stock message and return suggestions for all items - requires user confirmation
    Similar to create_order_from_message_with_suggestions but for stock updates
    """
    from .smart_product_matcher import SmartProductMatcher, ParsedMessage
    from products.models import Product
    from inventory.models import FinishedInventory
    import logging
    
    logger = logging.getLogger(__name__)
    
    try:
        # Parse the stock message using existing logic
        stock_data = parse_stock_message(message)
        
        if not stock_data:
            return {
                'status': 'error',
                'message': 'Could not parse stock message',
                'items': []
            }
        
        # Initialize the smart matcher
        matcher = SmartProductMatcher()
        
        # Get customer info (SHALLOME)
        customer = {
            'name': 'SHALLOME',
            'phone': '+27 61 674 9368',
            'company': 'SHALLOME'
        }
        
        items_with_suggestions = []
        
        # Process each parsed stock item
        for item_name, item_data in stock_data['items'].items():
            # Create ParsedMessage for the stock item
            parsed_message = ParsedMessage(
                product_name=item_name,
                quantity=item_data['quantity'],
                unit=item_data['unit'],
                packaging_size=None,
                extra_descriptions=[],
                original_message=item_data.get('original_line', item_name)
            )
            
            # Get suggestions for this item
            suggestions_result = matcher.get_suggestions(
                parsed_message.product_name, 
                min_confidence=5.0, 
                max_suggestions=20
            )
            
            # Format suggestions for frontend
            suggestions = []
            if suggestions_result.suggestions:
                for suggestion in suggestions_result.suggestions:
                    # Get current inventory level
                    current_inventory = 0
                    try:
                        inventory = FinishedInventory.objects.get(product=suggestion.product)
                        current_inventory = float(inventory.available_quantity or 0)
                    except FinishedInventory.DoesNotExist:
                        current_inventory = 0
                    
                    suggestions.append({
                        'product_id': suggestion.product.id,
                        'product_name': suggestion.product.name,
                        'unit': suggestion.product.unit,
                        'price': float(suggestion.product.price),
                        'confidence_score': suggestion.confidence_score,
                        'current_inventory': current_inventory,
                        'department': suggestion.product.department.name if suggestion.product.department else 'Other'
                    })
            
            items_with_suggestions.append({
                'original_text': item_data.get('original_line', item_name),
                'parsed_quantity': item_data['quantity'],
                'parsed_unit': item_data['unit'],
                'parsed_product_name': item_name,
                'suggestions': suggestions,
                'has_suggestions': len(suggestions) > 0
            })
        
        # Add parsing failures as items needing suggestions
        for failure in stock_data.get('parsing_failures', []):
            # Try to get suggestions for failed items
            suggestions_result = matcher.get_suggestions(
                failure['original_line'], 
                min_confidence=5.0, 
                max_suggestions=20
            )
            
            suggestions = []
            if suggestions_result.suggestions:
                for suggestion in suggestions_result.suggestions:
                    # Get current inventory level
                    current_inventory = 0
                    try:
                        inventory = FinishedInventory.objects.get(product=suggestion.product)
                        current_inventory = float(inventory.available_quantity or 0)
                    except FinishedInventory.DoesNotExist:
                        current_inventory = 0
                    
                    suggestions.append({
                        'product_id': suggestion.product.id,
                        'product_name': suggestion.product.name,
                        'unit': suggestion.product.unit,
                        'price': float(suggestion.product.price),
                        'confidence_score': suggestion.confidence_score,
                        'current_inventory': current_inventory,
                        'department': suggestion.product.department.name if suggestion.product.department else 'Other'
                    })
            
            items_with_suggestions.append({
                'original_text': failure['original_line'],
                'parsed_quantity': 1.0,  # Default quantity
                'parsed_unit': 'piece',  # Default unit
                'parsed_product_name': failure['original_line'],
                'suggestions': suggestions,
                'has_suggestions': len(suggestions) > 0,
                'parsing_failed': True
            })
        
        return {
            'status': 'confirmation_required',
            'message': f'Stock take parsed: {len(items_with_suggestions)} items need confirmation',
            'customer': customer,
            'items': items_with_suggestions,
            'total_items': len(items_with_suggestions),
            'stock_date': stock_data['date'].isoformat(),
            'order_day': stock_data['order_day']
        }
        
    except Exception as e:
        import traceback
        logger.error(f"Error creating stock suggestions: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {
            'status': 'error',
            'message': f'Failed to process stock message: {str(e)}',
            'items': []
        }

def create_stock_update_from_confirmed_suggestions(message_id, confirmed_items, stock_date, order_day, reset_before_processing=True):
    """
    Create stock update from user-confirmed suggestions and apply to inventory
    """
    from .models import WhatsAppMessage, StockUpdate
    from products.models import Product
    from django.db import transaction
    import logging
    from datetime import datetime
    
    logger = logging.getLogger(__name__)
    
    try:
        # Get the message
        message = WhatsAppMessage.objects.get(message_id=message_id)
        
        # Parse stock_date if it's a string
        if isinstance(stock_date, str):
            stock_date = datetime.fromisoformat(stock_date).date()
        
        with transaction.atomic():
            # Build items dictionary from confirmed suggestions
            items = {}
            for item in confirmed_items:
                product_id = item['product_id']
                quantity = float(item['quantity'])
                unit = item['unit']
                
                # Get product to use its name as key
                try:
                    product = Product.objects.get(id=product_id)
                    items[product.name] = {
                        'quantity': quantity,
                        'unit': unit,
                        'original_line': item.get('original_text', product.name)
                    }
                except Product.DoesNotExist:
                    logger.warning(f"Product with ID {product_id} not found")
                    continue
            
            # Create or update StockUpdate
            stock_update, created = StockUpdate.objects.get_or_create(
                message=message,
                defaults={
                    'stock_date': stock_date,
                    'order_day': order_day,
                    'items': items
                }
            )
            
            if not created:
                # Update existing stock update
                stock_update.stock_date = stock_date
                stock_update.order_day = order_day
                stock_update.items = items
                stock_update.processed = False  # Mark as unprocessed for reprocessing
                stock_update.save()
            
            # Update message status
            message.processed = True
            success_count = len(items)
            total_items = len(confirmed_items)
            success_rate = (success_count / total_items * 100) if total_items > 0 else 0
            
            message.processing_notes = f"✅ Stock confirmed: {success_count}/{total_items} items ({success_rate:.1f}%)"
            message.save()
            
            # Apply to inventory
            from .services import apply_stock_updates_to_inventory
            inventory_result = apply_stock_updates_to_inventory(reset_before_processing=reset_before_processing)
            
            return {
                'status': 'success',
                'message': f'Stock update created and applied: {success_count} items processed',
                'stock_update_id': stock_update.id,
                'items_processed': success_count,
                'inventory_result': inventory_result
            }
            
    except WhatsAppMessage.DoesNotExist:
        return {
            'status': 'error',
            'message': 'Message not found'
        }
    except Exception as e:
        logger.error(f"Error creating stock update from suggestions: {str(e)}")
        return {
            'status': 'error',
            'message': f'Failed to create stock update: {str(e)}'
        }

def parse_stock_item(line):
    """
    Parse single stock item line (e.g., "1.Spinach 3kg" or "18 Strawberry Pun")
    
    Args:
        line: Stock item line
        
    Returns:
        dict: Parsed item data or None
    """
    # Remove number prefix: "1.Spinach 3kg" -> "Spinach 3kg"
    line = re.sub(r'^\d+\.', '', line).strip()
    
    # Check for explicit quantity at the beginning: "18 Strawberry Pun" or "5 Tomatoes 47kg"
    qty_at_start_match = re.search(r'^(\d+(?:\.\d+)?)\s+(.+?)\s+(\d+(?:\.\d+)?)\s*(kg|g|ml|l|pcs?|pieces?|boxes?|box|bags?|bag|bunches?|bunch|heads?|head|punnets?|punnet|pun|each)s?$', line, re.IGNORECASE)
    if qty_at_start_match:
        quantity = float(qty_at_start_match.group(1))  # The explicit quantity (18, 5, etc.)
        name = qty_at_start_match.group(2).strip()     # The product name
        # group(3) is the packaging size number (ignored for stock)
        unit = normalize_unit(qty_at_start_match.group(4))  # The unit
        
        return {
            'name': clean_product_name(name),
            'quantity': quantity,
            'unit': unit
        }
    
    # Check for explicit quantity at the beginning (simple): "18 Strawberry Pun"
    simple_qty_at_start_match = re.search(r'^(\d+(?:\.\d+)?)\s+(.+?)\s+(kg|g|ml|l|pcs?|pieces?|boxes?|box|bags?|bag|bunches?|bunch|heads?|head|punnets?|punnet|pun|each)s?$', line, re.IGNORECASE)
    if simple_qty_at_start_match:
        quantity = float(simple_qty_at_start_match.group(1))  # The explicit quantity
        name = simple_qty_at_start_match.group(2).strip()     # The product name
        unit = normalize_unit(simple_qty_at_start_match.group(3))  # The unit
        
        return {
            'name': clean_product_name(name),
            'quantity': quantity,
            'unit': unit
        }
    
    # Check for quantity in the middle: "Strawberry 18 Pun" 
    qty_in_middle_match = re.search(r'^(.+?)\s+(\d+(?:\.\d+)?)\s+(kg|g|ml|l|pcs?|pieces?|boxes?|box|bags?|bag|bunches?|bunch|heads?|head|punnets?|punnet|pun|each)s?$', line, re.IGNORECASE)
    if qty_in_middle_match:
        name = qty_in_middle_match.group(1).strip()     # The product name
        quantity = float(qty_in_middle_match.group(2))  # The explicit quantity (18, etc.)
        unit = normalize_unit(qty_in_middle_match.group(3))  # The unit
        
        return {
            'name': clean_product_name(name),
            'quantity': quantity,
            'unit': unit
        }
    
    # Handle complex format: "Red onions 2bag (18kg)" or "Parsley 3kg( Fresh)"
    complex_match = re.search(r'(.+?)\s+(\d+(?:\.\d+)?)\s*(kg|g|ml|l|pcs?|pieces?|boxes?|box|bags?|bag|bunches?|bunch|heads?|head|punnets?|punnet|pun|each)s?\s*\([^)]*\)', line, re.IGNORECASE)
    if complex_match:
        name = complex_match.group(1).strip()
        # For stock items without explicit quantity, default to 1.0
        quantity = 1.0  # No explicit quantity, so default to 1
        unit = normalize_unit(complex_match.group(3))
        
        return {
            'name': clean_product_name(name),
            'quantity': quantity,
            'unit': unit
        }
    
    # Parse items without explicit quantity: "Tomatoes 47kg" or "Green Grapes 3 pun"
    # Try with space first: "Green Grapes 3 pun"
    match = re.search(r'(.+?)\s+(\d+(?:\.\d+)?)\s*(kg|g|ml|l|pcs?|pieces?|boxes?|box|bags?|bag|bunches?|bunch|heads?|head|punnets?|punnet|pun|each)s?$', line, re.IGNORECASE)
    
    # If no match, try without space: "Green Grapes3pun" or "Parsley1.5kg"
    if not match:
        match = re.search(r'(.+?)(\d+(?:\.\d+)?)\s*(kg|g|ml|l|pcs?|pieces?|boxes?|box|bags?|bag|bunches?|bunch|heads?|head|punnets?|punnet|pun|each)s?$', line, re.IGNORECASE)
    
    # If still no match, try without unit (default to "piece"): "Avo Soft 5"
    if not match:
        match = re.search(r'(.+?)\s+(\d+(?:\.\d+)?)$', line, re.IGNORECASE)
        if match:
            name = match.group(1).strip()
            # For stock items without explicit quantity, default to 1.0
            quantity = 1.0  # No explicit quantity, so default to 1
            unit = 'piece'  # Default unit when none specified
            
            return {
                'name': clean_product_name(name),
                'quantity': quantity,
                'unit': unit
            }
    
    if match:
        name = match.group(1).strip()
        # For stock items, the number IS the quantity (e.g., "Red Onions 18kg" = 18kg of Red Onions)
        quantity = float(match.group(2))  # Use the captured number as quantity
        unit = normalize_unit(match.group(3))
        
        return {
            'name': clean_product_name(name),
            'quantity': quantity,
            'unit': unit
        }
    
    return None

def get_product_alias(product_name):
    """
    Get product alias for better matching
    
    Args:
        product_name: Original product name from stock message
        
    Returns:
        str: Aliased product name or original if no alias
    """
    # Common aliases for stock items
    aliases = {
        # Avocados (default to hard)
        'avo': 'Avocados (Hard)',
        'avos': 'Avocados (Hard)',
        'avocado': 'Avocados (Hard)',
        
        # Avocados - Soft variations
        'avo soft': 'Avocados (Soft)',
        'avos soft': 'Avocados (Soft)',
        'soft avo': 'Avocados (Soft)',
        'soft avos': 'Avocados (Soft)',
        'avocado soft': 'Avocados (Soft)',
        'avocados soft': 'Avocados (Soft)',
        'soft avocado': 'Avocados (Soft)',
        'soft avocados': 'Avocados (Soft)',
        
        # Avocados - Semi-ripe variations
        'avo semi-ripe': 'Avocados (Semi-Ripe)',
        'avos semi-ripe': 'Avocados (Semi-Ripe)',
        'avocado semi-ripe': 'Avocados (Semi-Ripe)',
        'avocados semi-ripe': 'Avocados (Semi-Ripe)',
        'avo semi ripe': 'Avocados (Semi-Ripe)',
        'avos semi ripe': 'Avocados (Semi-Ripe)',
        'avocado semi ripe': 'Avocados (Semi-Ripe)',
        'avocados semi ripe': 'Avocados (Semi-Ripe)',
        'semi-ripe avo': 'Avocados (Semi-Ripe)',
        'semi-ripe avos': 'Avocados (Semi-Ripe)',
        'semi-ripe avocado': 'Avocados (Semi-Ripe)',
        'semi-ripe avocados': 'Avocados (Semi-Ripe)',
        'semi ripe avo': 'Avocados (Semi-Ripe)',
        'semi ripe avos': 'Avocados (Semi-Ripe)',
        'semi ripe avocado': 'Avocados (Semi-Ripe)',
        'semi ripe avocados': 'Avocados (Semi-Ripe)',
        
        # Vegetables
        'brinjals': 'Eggplant',
        'brinjal': 'Eggplant',
        'aubergine': 'Eggplant',
        
        # Lettuce varieties
        'iceberg': 'Iceberg Lettuce',
        'mixed lettuce': 'Mixed Lettuce',
        'crispy lettuce': 'Crispy Lettuce',
        
        # Mushrooms
        'mushroom': 'Button Mushrooms',  # Default to punnet unit (most common for retail)
        'mushrooms': 'Button Mushrooms',
        'porta': 'Portabellini',
        'porta mushroom': 'Portabellini',
        'porta mushrooms': 'Portabellini',
        
        # Cabbage
        'cabbage': 'Green Cabbage',  # Default to green
        
        # Onions
        'onion': 'Onions',
        'onions': 'Onions',
        'red onion': 'Red Onions',
        'red onions': 'Red Onions',
        'white onion': 'White Onions',
        'white onions': 'White Onions',
        'spring onion': 'Spring Onions',
        
        # Peppers
        'red pepper': 'Red Peppers',
        'green pepper': 'Green Peppers',
        'yellow pepper': 'Yellow Peppers',
        
        # Chillies
        'red chilli': 'Red Chillies',
        'green chilli': 'Green Chillies',
        'red chillies': 'Red Chillies',
        
        # Fix the failing stock items
        'cauliflower heads': 'Cauliflower',
        'cauliflower head': 'Cauliflower',
        'straw berry': 'Strawberries',
        'strawberry': 'Strawberries',
        'grape fruits': 'Grapefruit',
        'grape fruit': 'Grapefruit',
        'tumeric': 'Turmeric',
        'turmeric': 'Turmeric',
        'green chillies': 'Green Chillies',
        
        # Fruits
        'naartjies': 'Naartjies',
        'naartjie': 'Naartjies',
        'pine apple': 'Pineapple',
        'pineapple': 'Pineapple',
        'paw paw': 'Papaya',
        'pawpaw': 'Papaya',
        'sweet mellon': 'Sweet Melon',
        'water mellon': 'Watermelon',
        
        # Berries
        'blue berries': 'Blueberries',
        'blueberries': 'Blueberries',
        'blueberry': 'Blueberries',
        'blue berry': 'Blueberries',
        
        # Corn
        'sweet corn': 'Sweet Corn',
        'baby corn': 'Baby Corn',
        
        # Spinach
        'deveined spinarch': 'Deveined Spinach',  # Common typo
        'deveined spinach': 'Deveined Spinach',
        'spinach': 'Spinach',
        
        # Marrow
        'baby marrow': 'Baby Marrow',
        'baby marrow normal size': 'Baby Marrow',
        'baby marrow medium': 'Baby Marrow',
        
        # Potatoes (smart handling to exclude sweet potatoes)
        'potato': 'Potatoes',
        'potatos': 'Potatoes',
        'potatoe': 'Potatoes',
        'potatoes': 'Potatoes',
        
        # Herbs & Spices (packet variations)
        'fresh basil': 'Basil',
        'dried basil': 'Basil',
        'fresh parsley': 'Parsley',
        'flat leaf parsley': 'Parsley',
        'curly parsley': 'Parsley',
        'fresh thyme': 'Thyme',
        'dried thyme': 'Thyme',
        'fresh mint': 'Mint',
        'spearmint': 'Mint',
        'peppermint': 'Mint',
        'fresh coriander': 'Coriander',
        'cilantro': 'Coriander',
        'fresh rosemary': 'Rosemary',
        'dried rosemary': 'Rosemary',
        'fresh oregano': 'Oregano',
        'dried oregano': 'Oregano',
        'fresh sage': 'Sage',
        'dried sage': 'Sage',
    }
    
    # Smart handling for potato variations
    product_lower = product_name.lower()
    
    # Handle sweet potato separately (don't convert to regular potatoes)
    if 'sweet' in product_lower and any(p in product_lower for p in ['potato', 'potatos', 'potatoe']):
        # Keep sweet potato variations as-is or map to specific sweet potato products
        sweet_potato_aliases = {
            'sweet potato': 'Sweet Potatoes',
            'sweet potatos': 'Sweet Potatoes', 
            'sweet potatoe': 'Sweet Potatoes',
            'sweet potatoes': 'Sweet Potatoes',
        }
        for sweet_alias, sweet_target in sweet_potato_aliases.items():
            if product_lower == sweet_alias:
                return sweet_target
        return product_name  # Return as-is if no specific sweet potato match
    
    # Try exact match first, then case-insensitive
    if product_name in aliases:
        return aliases[product_name]
    
    for alias, target in aliases.items():
        if product_name.lower() == alias.lower():
            return target
    
    return product_name

def select_best_product_match(product_name, products):
    """
    Select the best product match when multiple products are found
    
    Args:
        product_name: Original product name from stock
        products: QuerySet of matching products
        
    Returns:
        Product: Best matching product
    """
    product_name_lower = product_name.lower().strip()
    
    # Strategy 1: Exact lowercase match
    for p in products:
        if p.name.lower().strip() == product_name_lower:
            return p
    
    # Strategy 2: Prefer products without parentheses (more generic)
    simple_products = [p for p in products if '(' not in p.name]
    if simple_products:
        return simple_products[0]
    
    # Strategy 3: For avocados, prefer "Hard" as default
    if 'avo' in product_name_lower:
        for p in products:
            if 'hard' in p.name.lower():
                return p
    
    # Strategy 4: For mushrooms, prefer "Brown" as default
    if 'mushroom' in product_name_lower:
        for p in products:
            if 'brown' in p.name.lower():
                return p
    
    # Strategy 5: For cabbage, prefer "Green" as default
    if 'cabbage' in product_name_lower:
        for p in products:
            if 'green' in p.name.lower():
                return p
    
    # Fallback: Return first match
    return products.first()

def determine_order_day(message_date):
    """
    Determine which order day this stock applies to
    
    Args:
        message_date: Date when message was sent
        
    Returns:
        str: 'Monday' or 'Thursday'
    """
    weekday = message_date.weekday()
    
    if weekday <= 0:  # Sunday or Monday
        return 'Monday'
    elif weekday <= 3:  # Tuesday through Thursday
        return 'Thursday'
    else:  # Friday or Saturday
        return 'Monday'  # Next week's Monday

def validate_order_against_stock(order):
    """
    Validate order items against available stock
    
    Args:
        order: Order instance
        
    Returns:
        dict: Validation results
    """
    try:
        # Determine order day
        order_day = 'Monday' if order.order_date.weekday() == 0 else 'Thursday'
        
        # Get latest stock update for this order day
        stock_update = StockUpdate.objects.filter(
            order_day=order_day,
            processed=False
        ).order_by('-stock_date').first()
        
        if not stock_update:
            return {
                'order_id': order.id,
                'validation_status': 'no_stock_data',
                'items': [],
                'stock_update_date': None,
                'total_requested': 0,
                'total_allocated': 0,
                'allocation_percentage': 0
            }
        
        validated_items = []
        total_requested = Decimal('0')
        total_allocated = Decimal('0')
        
        for item in order.items.all():
            product_name = item.product.name
            requested_qty = item.quantity
            total_requested += requested_qty
            
            # Check available stock
            available_qty = stock_update.get_available_quantity(product_name)
            
            if available_qty >= requested_qty:
                status = 'available'
                allocated_qty = requested_qty
            elif available_qty > 0:
                status = 'partial'
                allocated_qty = available_qty
            else:
                status = 'out_of_stock'
                allocated_qty = 0
            
            total_allocated += Decimal(str(allocated_qty))
            
            validated_items.append({
                'item_id': item.id,
                'product': product_name,
                'requested': float(requested_qty),
                'allocated': allocated_qty,
                'unit': item.unit,
                'status': status
            })
        
        # Calculate allocation percentage
        allocation_percentage = (
            float(total_allocated / total_requested * 100) 
            if total_requested > 0 else 0
        )
        
        # Determine overall status
        if allocation_percentage == 100:
            validation_status = 'fully_available'
        elif allocation_percentage > 0:
            validation_status = 'partially_available'
        else:
            validation_status = 'out_of_stock'
        
        return {
            'order_id': order.id,
            'validation_status': validation_status,
            'items': validated_items,
            'stock_update_date': stock_update.stock_date,
            'total_requested': float(total_requested),
            'total_allocated': float(total_allocated),
            'allocation_percentage': allocation_percentage
        }
        
    except Exception as e:
        return {
            'order_id': order.id,
            'validation_status': 'error',
            'error': str(e),
            'items': [],
            'stock_update_date': None,
            'total_requested': 0,
            'total_allocated': 0,
            'allocation_percentage': 0
        }

def log_processing_action(message, action, details=None):
    """
    Log message processing action - deferred until after transaction commits
    
    Args:
        message: WhatsAppMessage instance
        action: Action type string
        details: Additional details dictionary
    """
    from django.db import transaction
    
    def create_log():
        try:
            MessageProcessingLog.objects.create(
                message=message,
                action=action,
                details=details or {},
            )
        except Exception as e:
            print(f"Failed to log action {action} for message {message.message_id}: {e}")
    
    # Defer logging until after current transaction commits
    transaction.on_commit(create_log)


def reset_all_stock_levels():
    """
    Reset all product stock levels to 0 before processing new stock updates
    This prevents old stock levels from interfering with fresh stock data
    
    Returns:
        dict: Summary of reset operation
    """
    from inventory.models import FinishedInventory
    from products.models import Product
    from django.db import transaction
    
    reset_count = 0
    
    with transaction.atomic():
        # Reset all product stock levels
        products_updated = Product.objects.filter(stock_level__gt=0).update(stock_level=0)
        
        # Reset all finished inventory quantities
        inventory_updated = FinishedInventory.objects.filter(available_quantity__gt=0).update(available_quantity=0)
        
        reset_count = products_updated + inventory_updated
    
    return {
        'products_reset': products_updated,
        'inventory_reset': inventory_updated,
        'total_reset': reset_count,
        'message': f'Reset {products_updated} products and {inventory_updated} inventory records to 0'
    }

def apply_stock_updates_to_inventory(reset_before_processing=True):
    """
    Apply processed StockUpdate data to FinishedInventory
    
    This bridges the gap between WhatsApp stock updates and inventory management.
    It transfers stock data from SHALLOME messages to the inventory system.
    
    Args:
        reset_before_processing: If True, reset all stock levels to 0 first
    
    Returns:
        dict: Detailed summary with parsed items, failed items, and processing stats
    """
    from inventory.models import FinishedInventory, StockMovement
    from products.models import Product
    from django.db import transaction
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    
    # Reset all stock levels to 0 before processing if requested
    reset_summary = None
    if reset_before_processing:
        reset_summary = reset_all_stock_levels()
        print(f"[STOCK] Reset {reset_summary['total_reset']} items to 0 before processing new stock take")
    
    # Get unprocessed stock updates
    unprocessed_updates = StockUpdate.objects.filter(processed=False)
    
    if not unprocessed_updates.exists():
        return {
            'applied_updates': 0,
            'products_updated': 0,
            'errors': [],
            'message': 'No unprocessed stock updates found'
        }
    
    applied_updates = 0
    products_updated = 0
    errors = []
    parsed_items = []
    failed_items = []
    processing_warnings = []
    
    # Get system user for stock movements
    try:
        system_user = User.objects.filter(is_staff=True).first()
        if not system_user:
            system_user = User.objects.first()
    except:
        system_user = None
    
    with transaction.atomic():
        for stock_update in unprocessed_updates:
            try:
                stock_update_items = []
                stock_update_failed = []
                
                for product_name, stock_data in stock_update.items.items():
                    quantity = stock_data.get('quantity', 0)
                    unit = stock_data.get('unit', '')
                    
                    # Create item tracking record
                    item_record = {
                        'original_name': product_name,
                        'quantity': quantity,
                        'unit': unit,
                        'stock_date': stock_update.stock_date.isoformat(),
                        'message_id': stock_update.message.message_id if stock_update.message else None
                    }
                    
                    # Try to match product by name with enhanced matching logic
                    product = None
                    matching_info = []
                    matching_method = None
                    
                    # Step 1: Try exact match
                    try:
                        products = Product.objects.filter(name__iexact=product_name)
                        if products.count() == 1:
                            product = products.first()
                            matching_method = 'exact_match'
                        elif products.count() > 1:
                            # Multiple matches - prefer kg unit as default
                            kg_product = products.filter(unit='kg').first()
                            if kg_product:
                                product = kg_product
                                matching_method = 'exact_match_kg_preferred'
                            else:
                                product = products.first()
                                matching_method = 'exact_match_first'
                        else:
                            raise Product.DoesNotExist()
                    except Product.DoesNotExist:
                        # Step 2: Try with aliases
                        aliased_name = get_product_alias(product_name)
                        if aliased_name != product_name:
                            try:
                                alias_products = Product.objects.filter(name__iexact=aliased_name)
                                if alias_products.count() == 1:
                                    product = alias_products.first()
                                elif alias_products.count() > 1:
                                    # Multiple matches - prefer kg unit as default
                                    kg_product = alias_products.filter(unit='kg').first()
                                    if kg_product:
                                        product = kg_product
                                    else:
                                        product = alias_products.first()
                                else:
                                    raise Product.DoesNotExist()
                                matching_method = 'alias_match'
                                matching_info.append(f"Used alias: '{product_name}' -> '{aliased_name}'")
                            except Product.DoesNotExist:
                                pass
                        
                        # Step 3: Try partial match if no alias worked
                        if not product:
                            products = Product.objects.filter(name__icontains=product_name)
                            if products.count() == 1:
                                product = products.first()
                                matching_method = 'partial_match'
                            elif products.count() > 1:
                                # Multiple matches - use smart selection
                                product = select_best_product_match(product_name, products)
                                matching_method = 'smart_selection'
                                matching_info.append(f"Multiple matches found: {[p.name for p in products]}")
                                matching_info.append(f"Smart selection chose: '{product.name}'")
                                processing_warnings.append(f"Multiple matches for '{product_name}': {[p.name for p in products]}. Selected: '{product.name}'")
                    
                    if not product:
                        # Enhanced error reporting for failed items
                        similar_products = Product.objects.filter(name__icontains=product_name[:3])[:3]
                        failure_reason = "Product not found"
                        suggestions = []
                        
                        if similar_products:
                            suggestions = [p.name for p in similar_products]
                            failure_reason += f". Similar products: {suggestions}"
                        else:
                            failure_reason += ". No similar products found."
                        
                        # Add to failed items
                        failed_item = {
                            **item_record,
                            'failure_reason': failure_reason,
                            'suggestions': suggestions,
                            'error_type': 'product_not_found'
                        }
                        failed_items.append(failed_item)
                        stock_update_failed.append(failed_item)
                        errors.append(failure_reason)
                        continue
                    
                    # Get or create FinishedInventory record
                    inventory, created = FinishedInventory.objects.get_or_create(
                        product=product,
                        defaults={
                            'available_quantity': 0,
                            'reserved_quantity': 0,
                            'minimum_level': product.minimum_stock or 10,
                            'reorder_level': product.minimum_stock or 20,
                            'average_cost': product.price or 0,
                        }
                    )
                    
                    # Calculate the difference
                    old_quantity = inventory.available_quantity or 0
                    new_quantity = quantity
                    difference = new_quantity - old_quantity
                    
                    # Create successful item record
                    parsed_item = {
                        **item_record,
                        'matched_product_id': product.id,
                        'matched_product_name': product.name,
                        'matching_method': matching_method,
                        'matching_info': matching_info,
                        'old_quantity': float(old_quantity),
                        'new_quantity': float(new_quantity),
                        'quantity_difference': float(difference),
                        'inventory_created': created,
                        'status': 'updated' if difference != 0 else 'no_change'
                    }
                    
                    if difference != 0:
                        # Update inventory
                        inventory.available_quantity = new_quantity
                        inventory.save()
                        
                        # Update product stock level to match
                        product.stock_level = new_quantity
                        product.save()
                        
                        # Create stock movement record
                        movement_reference = f"SHALLOME-{stock_update.stock_date.strftime('%Y%m%d')}"
                        if system_user:
                            StockMovement.objects.create(
                                movement_type='finished_adjust',
                                reference_number=movement_reference,
                                product=product,
                                quantity=difference,
                                user=system_user,
                                notes=f"Stock update from SHALLOME message on {stock_update.stock_date}. "
                                      f"Updated from {old_quantity} to {new_quantity} {unit}"
                            )
                        
                        parsed_item['movement_reference'] = movement_reference
                        products_updated += 1
                    
                    # Add to parsed items
                    parsed_items.append(parsed_item)
                    stock_update_items.append(parsed_item)
                
                # Mark stock update as processed
                stock_update.processed = True
                stock_update.save()
                applied_updates += 1
                
            except Exception as e:
                errors.append(f"Error processing stock update {stock_update.id}: {str(e)}")
    
    # Calculate summary statistics
    total_items_processed = len(parsed_items) + len(failed_items)
    success_rate = (len(parsed_items) / total_items_processed * 100) if total_items_processed > 0 else 0
    
    result = {
        'applied_updates': applied_updates,
        'products_updated': products_updated,
        'total_items_processed': total_items_processed,
        'successful_items': len(parsed_items),
        'failed_items_count': len(failed_items),
        'success_rate': round(success_rate, 1),
        'parsed_items': parsed_items,
        'failed_items': failed_items,
        'processing_warnings': processing_warnings,
        'errors': errors,
        'message': f"Applied {applied_updates} stock updates, updated {products_updated} products. Success rate: {success_rate:.1f}% ({len(parsed_items)}/{total_items_processed})"
    }
    
    # Add reset summary if stock was reset
    if reset_summary:
        result['reset_summary'] = reset_summary
        result['message'] = f"Reset {reset_summary['total_reset']} items to 0, then applied {applied_updates} stock updates, updated {products_updated} products. Success rate: {success_rate:.1f}% ({len(parsed_items)}/{total_items_processed})"
    
    return result


def get_stock_take_data(only_with_stock=True):
    """
    Get stock take data, optionally filtered to only show items with stock
    
    Args:
        only_with_stock (bool): If True, only return products with stock > 0
        
    Returns:
        dict: Stock take data with products and latest stock updates
    """
    from inventory.models import FinishedInventory
    from products.models import Product
    from django.db.models import Q
    
    # Get products with inventory records
    query = Product.objects.select_related('inventory').filter(
        inventory__isnull=False
    )
    
    if only_with_stock:
        query = query.filter(
            Q(inventory__available_quantity__gt=0) | 
            Q(stock_level__gt=0)
        )
    
    products_data = []
    
    for product in query:
        inventory = product.inventory
        
        # Get latest stock update for this product
        latest_stock_update = None
        for stock_update in StockUpdate.objects.filter(processed=True).order_by('-stock_date'):
            for item_name, item_data in stock_update.items.items():
                if item_name.lower().strip() == product.name.lower().strip():
                    latest_stock_update = {
                        'date': stock_update.stock_date,
                        'quantity': item_data.get('quantity', 0),
                        'unit': item_data.get('unit', ''),
                        'order_day': stock_update.order_day
                    }
                    break
            if latest_stock_update:
                break
        
        products_data.append({
            'id': product.id,
            'name': product.name,
            'current_stock': inventory.available_quantity or 0,
            'reserved_stock': inventory.reserved_quantity or 0,
            'minimum_stock': inventory.minimum_level or 0,
            'unit': product.unit,
            'price': product.price,
            'department': product.department.name if product.department else None,
            'latest_shallome_update': latest_stock_update,
            'needs_attention': (inventory.available_quantity or 0) <= (inventory.minimum_level or 0)
        })
    
    return {
        'products': products_data,
        'total_products': len(products_data),
        'products_needing_attention': len([p for p in products_data if p['needs_attention']]),
        'last_updated': StockUpdate.objects.filter(processed=True).order_by('-stock_date').first()
    }
