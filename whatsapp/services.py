"""
WhatsApp message processing services
Handles classification, parsing, and order creation from WhatsApp messages
"""

from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import datetime, date, timedelta
from decimal import Decimal
import re
import traceback

from .models import WhatsAppMessage, StockUpdate, MessageProcessingLog
from orders.models import Order, OrderItem
from products.models import Product

User = get_user_model()

def classify_message_type(msg_data):
    """
    Classify message type based on content and sender
    
    Args:
        msg_data: Dictionary with message data from scraper
        
    Returns:
        str: Message type ('order', 'stock', 'instruction', 'demarcation', 'other')
    """
    content_raw = msg_data.get('content', '')
    content = content_raw.upper()
    sender = msg_data.get('sender', '')
    
    # Stock controller messages (SHALLOME +27 61 674 9368)
    stock_header = ('STOKE AS AT' in content or 'STOCK AS AT' in content)
    is_shallome = ('+27 61 674 9368' in sender or 'SHALLOME' in sender.upper())
    if is_shallome and stock_header:
        print(f"[DJANGO][CLASSIFY] id={msg_data.get('id','')} -> stock (is_shallome={is_shallome}, stock_header={stock_header})")
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
        print(f"[DJANGO][CLASSIFY] id={msg_data.get('id','')} -> demarcation")
        return 'demarcation'
    
    # Company orders - check if message contains order items
    order_like = has_order_items(content)
    if order_like:
        print(f"[DJANGO][CLASSIFY] id={msg_data.get('id','')} -> order (order_like=True)")
        return 'order'
    
    # Instructions or general messages
    instructionish = any(word in content for word in ['PLEASE', 'HELP', 'NOTE', 'INSTRUCTION', 'THANKS', 'GOOD MORNING', 'HELLO', 'HI'])
    if instructionish:
        print(f"[DJANGO][CLASSIFY] id={msg_data.get('id','')} -> instruction")
        return 'instruction'
    
    print(f"[DJANGO][CLASSIFY] id={msg_data.get('id','')} -> other (fallback) len={len(content_raw)}")
    return 'other'

def has_order_items(content):
    """
    Check if message contains order items based on quantity patterns
    
    Args:
        content: Message content string
        
    Returns:
        bool: True if message appears to contain order items
    """
    # Patterns that indicate order items
    quantity_patterns = [
        r'\d+\s*(?:kg|kilos?|kilogram)',           # 5kg, 10 kilos
        r'\d+\s*(?:×|x)\s*\d+\s*kg',              # 2×5kg, 3x10kg
        r'\d+\s*(?:box|boxes|pun|punnet|punnets)', # 5 boxes, 3 punnets
        r'\d+\s*(?:bag|bags|packet|packets)',      # 2 bags, 5 packets
        r'\d+\s*(?:bunch|bunches|head|heads)',     # 3 bunches, 2 heads
        r'\d+\s*(?:piece|pieces)',                 # 10 pieces
        r'(?:×|x)\s*\d+',                          # x3, ×5
        r'\d+\s*(?:×|x)\b',                       # 2x, 3× (quantity with x suffix)
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
        
        # Determine valid order date
        order_date = get_valid_order_date(message.timestamp.date())
        
        # Create order
        order = Order.objects.create(
            restaurant=customer,
            order_date=order_date,
            status='received',
            whatsapp_message_id=message.message_id,
            original_message=message.content,
            parsed_by_ai=True
        )
        
        # Parse and create order items
        items_created = create_order_items(order, message)
        
        if items_created > 0:
            # Calculate totals
            order.subtotal = sum(item.total_price for item in order.items.all())
            order.total_amount = order.subtotal  # Add tax/fees later if needed
            order.save()
            
            log_processing_action(message, 'order_created', {
                'order_number': order.order_number,
                'items_count': items_created,
                'total_amount': float(order.total_amount or 0)
            })
            
            return order
        else:
            # No valid items found, delete order
            order.delete()
            log_processing_action(message, 'error', {
                'error': 'No valid items found in message',
                'action': 'order_creation'
            })
            return None
            
    except Exception as e:
        log_processing_action(message, 'error', {
            'error': str(e),
            'traceback': traceback.format_exc(),
            'action': 'order_creation'
        })
        return None

def get_or_create_customer(company_name, sender_name):
    """
    Get or create customer from company name
    
    Args:
        company_name: Name of the restaurant/company
        sender_name: Name of the person sending the message
        
    Returns:
        User instance (customer)
    """
    # Create email from company name
    email_base = re.sub(r'[^a-zA-Z0-9]', '', company_name.lower())
    email = f"{email_base}@restaurant.com"
    
    # Try to find existing customer
    customer, created = User.objects.get_or_create(
        email=email,
        defaults={
            'first_name': company_name,
            'last_name': f"(via {sender_name})",
            'user_type': 'restaurant',
            'is_active': True
        }
    )
    
    return customer

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
    Parse message content and create order items
    
    Args:
        order: Order instance
        message: WhatsAppMessage instance
        
    Returns:
        int: Number of items created
    """
    content = message.content
    items_created = 0
    
    # Parse items from message content
    parsed_items = parse_order_items(content)
    
    for item_data in parsed_items:
        try:
            # Find or create product
            product = get_or_create_product(item_data['product_name'])
            
            if not product:
                log_processing_action(message, 'error', {
                    'error': f"Failed to create/find product: {item_data['product_name']}",
                    'item_data': item_data,
                    'action': 'product_creation'
                })
                continue
            
            # Create order item
            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=Decimal(str(item_data['quantity'])),
                unit=item_data['unit'],
                price=product.price or Decimal('0.00'),
                total_price=Decimal(str(item_data['quantity'])) * (product.price or Decimal('0.00')),
                original_text=item_data['original_text'],
                confidence_score=item_data.get('confidence', 0.8)
            )
            items_created += 1
            
        except Exception as e:
            log_processing_action(message, 'error', {
                'error': f"Failed to create item: {str(e)}",
                'item_data': item_data,
                'action': 'item_creation'
            })
            continue
    
    return items_created

def parse_order_items(content):
    """
    Parse order items from message content using enhanced MessageParser
    
    Args:
        content: Message content string
        
    Returns:
        list: List of parsed item dictionaries
    """
    from .message_parser import django_message_parser
    
    # Use the enhanced parser to extract items
    raw_items = django_message_parser.extract_order_items(content)
    
    # Convert to Django's expected format
    items = []
    for raw_text in raw_items:
        # Parse individual item
        item = parse_single_item(raw_text)
        if item:
            items.append(item)
    
    return items

def parse_single_item(line):
    """
    Parse single order item line
    
    Args:
        line: Single line of text containing an item
        
    Returns:
        dict: Parsed item data or None if parsing failed
    """
    original_line = line
    line = line.strip()
    
    # Patterns for different quantity formats
    patterns = [
        # 2×5kg Tomatoes, 3x10kg Onions
        (r'(\d+)\s*(?:×|x)\s*(\d+)\s*(kg|kilos?|kilogram)\s*(.+)', 'multiply_kg'),
        
        # 5kg Tomatoes, 10 kilos Onions
        (r'(\d+(?:\.\d+)?)\s*(kg|kilos?|kilogram)\s*(.+)', 'simple_kg'),
        
        # 3 boxes Lettuce, 5 punnets Strawberries
        (r'(\d+)\s*(box|boxes|pun|punnet|punnets|bag|bags|packet|packets|bunch|bunches|head|heads)\s*(.+)', 'simple_unit'),
        
        # Tomatoes x3, Onions ×5
        (r'(.+?)\s*(?:×|x)\s*(\d+)\s*(.+)?', 'product_multiply'),
        
        # 5 Tomatoes, 10 Onions (simple number)
        (r'(\d+)\s*(.+)', 'simple_number'),
    ]
    
    for pattern, pattern_type in patterns:
        match = re.search(pattern, line, re.IGNORECASE)
        if match:
            groups = match.groups()
            
            try:
                if pattern_type == 'multiply_kg':
                    quantity = int(groups[0]) * int(groups[1])
                    unit = groups[2].lower()
                    product_name = groups[3].strip()
                    
                elif pattern_type == 'simple_kg':
                    quantity = float(groups[0])
                    unit = 'kg'
                    product_name = groups[2].strip()
                    
                elif pattern_type == 'simple_unit':
                    quantity = int(groups[0])
                    unit = normalize_unit(groups[1])
                    product_name = groups[2].strip()
                    
                elif pattern_type == 'product_multiply':
                    product_name = groups[0].strip()
                    quantity = int(groups[1])
                    unit = 'piece'  # Default unit
                    
                elif pattern_type == 'simple_number':
                    quantity = int(groups[0])
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
    
    # Normalize common product variations
    replacements = {
        'tomatos': 'tomatoes',
        'tomatoe': 'tomatoes',
        'onion': 'onions',
        'potato': 'potatoes',
        'potatos': 'potatoes',
        'lettuce': 'lettuce',
        'spinach': 'spinach',
        'mushroom': 'mushrooms',
        'carrot': 'carrots',
    }
    
    name_lower = name.lower()
    for old, new in replacements.items():
        if old in name_lower:
            name = name_lower.replace(old, new).title()
            break
    else:
        name = name.title()
    
    return name.strip()

def get_or_create_product(product_name):
    """
    Get or create product by name
    
    Args:
        product_name: Name of the product
        
    Returns:
        Product instance
    """
    try:
        # Try exact match first
        return Product.objects.get(name__iexact=product_name)
    except Product.DoesNotExist:
        pass
    
    try:
        # Try partial match
        return Product.objects.filter(name__icontains=product_name).first()
    except Product.DoesNotExist:
        pass
    
    # Create new product
    try:
        product = Product.objects.create(
            name=product_name,
            price=Decimal('0.00'),  # Will be updated manually
            department_id=1,  # Default department
            is_active=True,
            needs_setup=True,  # Flag for admin attention
            description=f"Auto-created from WhatsApp order. Needs pricing and inventory setup."
        )
        
        # Create alert for admin review
        from products.models import ProductAlert
        ProductAlert.objects.create(
            product=product,
            alert_type='needs_setup',
            message=f"Product '{product_name}' was auto-created from WhatsApp order and needs pricing, inventory, and possibly a recipe setup.",
        )
        
        # Log that a new product was created and needs setup
        print(f"[PRODUCT] Auto-created product '{product_name}' - NEEDS PRICING & INVENTORY SETUP")
        
        return product
    except Exception as e:
        print(f"[ERROR] Failed to create product '{product_name}': {e}")
        return None

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
        if 'STOKE AS AT' in line or 'STOCK AS AT' in line:
            date_match = re.search(r'(\d{1,2})\s+(\w+)\s+(\d{4})', line)
            if date_match:
                day, month_name, year = date_match.groups()
                try:
                    # Convert month name to number
                    month_names = {
                        'january': 1, 'february': 2, 'march': 3, 'april': 4,
                        'may': 5, 'june': 6, 'july': 7, 'august': 8,
                        'september': 9, 'october': 10, 'november': 11, 'december': 12
                    }
                    month_num = month_names.get(month_name.lower())
                    if month_num:
                        stock_date = date(int(year), month_num, int(day))
                        break
                except ValueError:
                    continue
    
    if not stock_date:
        return None
    
    # Parse numbered stock items
    items = {}
    for line in lines:
        line = line.strip()
        if re.match(r'^\d+\.', line):  # Lines starting with number.
            item = parse_stock_item(line)
            if item:
                items[item['name']] = {
                    'quantity': item['quantity'],
                    'unit': item['unit']
                }
    
    if not items:
        return None
    
    return {
        'date': stock_date,
        'order_day': determine_order_day(message.timestamp.date()),
        'items': items
    }

def parse_stock_item(line):
    """
    Parse single stock item line (e.g., "1.Spinach 3kg")
    
    Args:
        line: Stock item line
        
    Returns:
        dict: Parsed item data or None
    """
    # Remove number prefix: "1.Spinach 3kg" -> "Spinach 3kg"
    line = re.sub(r'^\d+\.', '', line).strip()
    
    # Parse quantity and unit at the end
    match = re.search(r'(.+?)\s+(\d+(?:\.\d+)?)\s*(kg|pun|box|bag|bunch|head|g|punnet)s?$', line, re.IGNORECASE)
    if match:
        name = match.group(1).strip()
        quantity = float(match.group(2))
        unit = normalize_unit(match.group(3))
        
        return {
            'name': clean_product_name(name),
            'quantity': quantity,
            'unit': unit
        }
    
    return None

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
    Log message processing action
    
    Args:
        message: WhatsAppMessage instance
        action: Action type string
        details: Additional details dictionary
    """
    try:
        MessageProcessingLog.objects.create(
            message=message,
            action=action,
            details=details or {},
        )
    except Exception as e:
        # Don't let logging errors break the main flow
        print(f"Failed to log action {action} for message {message.message_id}: {e}")
