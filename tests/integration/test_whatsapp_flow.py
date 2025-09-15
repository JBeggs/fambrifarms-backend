#!/usr/bin/env python
"""
Test script for WhatsApp order processing flow
Tests the complete flow: WhatsApp message → Parsing → Order creation → PO generation
"""
import os
import sys
import django
from decimal import Decimal

# Setup Django
sys.path.append('/Users/jodybeggs/Documents/fambrifarms_after_meeting/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'familyfarms_api.settings')
django.setup()

from django.contrib.auth import get_user_model
from whatsapp.models import WhatsAppMessage
from suppliers.models import SalesRep, Supplier
from procurement.models import PurchaseOrder, PurchaseOrderItem
from whatsapp.services import parse_order_items
from orders.models import Order, OrderItem
from products.models import Product, Department

User = get_user_model()

def setup_test_data():
    """Create test data for the flow"""
    print("🔧 Setting up test data...")
    
    # Create a manager user
    manager, created = User.objects.get_or_create(
        email='manager@fambrifarms.com',
        defaults={
            'first_name': 'Farm',
            'last_name': 'Manager',
            'user_type': 'admin',
            'is_staff': True,
            'is_active': True
        }
    )
    if created:
        manager.set_password('password123')
        manager.save()
    
    # Create a sales rep
    supplier, _ = Supplier.objects.get_or_create(name='Default Supplier')
    sales_rep, created = SalesRep.objects.get_or_create(
        supplier=supplier,
        name='John Smith',
        defaults={
            'phone': '+27123456789',
            'is_active': True,
            'is_primary': True
        }
    )
    
    print(f"✅ Manager: {manager.email}")
    print(f"✅ Sales Rep: {sales_rep.name}")
    return manager, sales_rep

def test_message_parsing():
    """Test WhatsApp message parsing"""
    print("\n📱 Testing WhatsApp message parsing...")
    
    test_messages = [
        "Hi, can I get 2 x onions and 3kg tomatoes please?",
        "Need 5kg potatoes and 2 bunches carrots",
        "1 x onions, some spinach please"
    ]
    
    results = []
    for message in test_messages:
        print(f"\n📝 Message: '{message}'")
        items = parse_order_items(message)
        
        print(f"   Items found: {len(items)}")
        
        for item in items:
            print(f"     - {item['product_name']}: {item['quantity']}{item['unit']}")
        
        results.append({'items': items, 'total_items': len(items)})
    
    return results

def test_whatsapp_message_creation():
    """Test creating WhatsApp message records"""
    print("\n💬 Testing WhatsApp message creation...")
    
    import time
    unique_id = f'test_flow_{int(time.time())}'
    
    # Create a WhatsApp message
    message = WhatsAppMessage.objects.create(
        message_id=unique_id,
        sender_phone='+27987654321',
        sender_name='Test Restaurant',
        message_text='Hi, can I get 2 x onions and 3kg tomatoes please?',
        processed=False
    )
    
    # Parse the message
    parsed_items = parse_order_items(message.message_text)
    message.parsed_items = parsed_items
    message.parsing_confidence = 0.8
    message.save()
    
    print(f"✅ Created WhatsApp message: {message.id}")
    print(f"   Sender: {message.sender_name}")
    print(f"   Confidence: {message.parsing_confidence}")
    print(f"   Items: {len(message.parsed_items)}")
    
    return message

def test_order_creation(whatsapp_message, manager):
    """Test creating order from WhatsApp message"""
    print("\n📋 Testing order creation...")
    
    # Get or create restaurant user
    restaurant_user, created = User.objects.get_or_create(
        email=f"{whatsapp_message.sender_phone}@restaurant.com",
        defaults={
            'first_name': whatsapp_message.sender_name,
            'last_name': 'Restaurant',
            'user_type': 'restaurant',
            'phone': whatsapp_message.sender_phone,
            'is_active': True
        }
    )
    
    # Create order with valid order date (Monday or Thursday)
    from datetime import date, timedelta
    
    # Find next Monday or Thursday
    today = date.today()
    days_ahead = 0 - today.weekday()  # Monday is 0
    if days_ahead <= 0:  # Target day already happened this week
        days_ahead += 7
    next_monday = today + timedelta(days_ahead)
    
    order = Order.objects.create(
        restaurant=restaurant_user,
        order_date=next_monday,  # Use next Monday as order date
        whatsapp_message_id=whatsapp_message.message_id,
        original_message=whatsapp_message.message_text,
        parsed_by_ai=True,
        status='confirmed'
    )
    
    # Create order items from parsed data
    for item_data in whatsapp_message.parsed_items:
        # Get or create product
        product, created = Product.objects.get_or_create(
            name=item_data['product_name'],
            defaults={
                'description': f'Product from WhatsApp order',
                'unit': item_data.get('unit') or 'kg',
                'price': Decimal('10.00'),  # Default price
                'is_active': True
            }
        )
        
        # Create order item
        OrderItem.objects.create(
            order=order,
            product=product,
            quantity=Decimal(str(item_data['quantity'])),
            unit=item_data.get('unit') or 'kg',
            price=product.price,  # Use product price
            original_text=item_data.get('original_text') or '',
            confidence_score=item_data.get('confidence') if item_data.get('confidence') is not None else 0.0
        )
    
    # Mark WhatsApp message as processed
    whatsapp_message.processed = True
    whatsapp_message.order = order
    whatsapp_message.save()
    
    print(f"✅ Created order: {order.order_number}")
    print(f"   Restaurant: {order.restaurant.first_name}")
    print(f"   Items: {order.items.count()}")
    print(f"   Delivery date: {order.delivery_date}")
    print(f"   Status: {order.status}")
    
    return order

def test_po_generation(order, manager, sales_rep):
    """Test Purchase Order generation"""
    print("\n📄 Testing Purchase Order generation...")
    
    # Create Purchase Order
    po = PurchaseOrder.objects.create(
        sales_rep=sales_rep,
        order=order,
        status='draft'
    )
    
    # Create PO items from order items
    total_amount = Decimal('0.00')
    for order_item in order.items.all():
        unit_price = order_item.product.price
        line_total = unit_price * order_item.quantity
        
        PurchaseOrderItem.objects.create(
            purchase_order=po,
            product=order_item.product,
            order_item=order_item,
            quantity_ordered=int(order_item.quantity),
            unit_price=unit_price,
            total_price=line_total
        )
        
        total_amount += line_total
    
    # Update PO total
    po.estimated_total = total_amount
    po.save()
    
    # Update order status
    order.status = 'po_sent'
    order.save()
    
    print(f"✅ Created PO: {po.po_number}")
    print(f"   Sales Rep: {po.sales_rep.name}")
    print(f"   Total: R{po.estimated_total}")
    print(f"   Items: {po.items.count()}")
    
    return po

def test_whatsapp_message_generation(po):
    """Test WhatsApp message generation for PO"""
    print("\n📲 Testing WhatsApp message generation...")
    
    # Generate WhatsApp message
    message_lines = [
        f"🛒 *Purchase Order: {po.po_number}*",
        f"📅 Delivery: {po.order.delivery_date.strftime('%A, %d %B %Y')}",
        f"🏪 Restaurant: {po.order.restaurant.first_name}",
        "",
        "*Items needed:*"
    ]
    
    for item in po.items.all():
        message_lines.append(f"• {item.product_name}: {item.quantity_requested}{item.unit} @ R{item.price_per_unit}")
    
    message_lines.extend([
        "",
        f"💰 *Total: R{po.estimated_total}*",
        "",
        "Please confirm availability and pricing.",
        f"Reply with: CONFIRM {po.po_number}"
    ])
    
    whatsapp_message = "\n".join(message_lines)
    
    print("✅ Generated WhatsApp message:")
    print("=" * 50)
    print(whatsapp_message)
    print("=" * 50)
    
    return whatsapp_message

def main():
    """Run the complete test flow"""
    print("🚀 Starting WhatsApp Order Processing Flow Test")
    print("=" * 60)
    
    try:
        # Setup
        manager, sales_rep = setup_test_data()
        
        # Test parsing
        parsing_results = test_message_parsing()
        
        # Test WhatsApp message creation
        whatsapp_message = test_whatsapp_message_creation()
        
        # Test order creation
        order = test_order_creation(whatsapp_message, manager)
        
        # Test PO generation
        po = test_po_generation(order, manager, sales_rep)
        
        # Test WhatsApp message generation
        whatsapp_msg = test_whatsapp_message_generation(po)
        
        print("\n🎉 Complete flow test successful!")
        print("=" * 60)
        print("✅ WhatsApp message received and parsed")
        print("✅ Order created from parsed data")
        print("✅ Purchase Order generated")
        print("✅ WhatsApp message formatted for sales rep")
        print("\n📊 Summary:")
        print(f"   WhatsApp Message ID: {whatsapp_message.id}")
        print(f"   Order Number: {order.order_number}")
        print(f"   PO Number: {po.po_number}")
        print(f"   Total Amount: R{po.estimated_total}")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
