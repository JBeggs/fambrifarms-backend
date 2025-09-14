#!/usr/bin/env python
"""
Simple test script to check if the WhatsApp Django integration actually works
"""
import os
import sys
import django
from django.conf import settings

# Add the backend directory to Python path
sys.path.append('/Users/jodybeggs/Documents/fambrifarms_after_meeting/backend')

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'familyfarms_api.settings')
django.setup()

def test_imports():
    """Test if all imports work"""
    print("Testing imports...")
    
    try:
        from whatsapp.models import WhatsAppMessage, StockUpdate
        print("✅ WhatsApp models import OK")
    except ImportError as e:
        print(f"❌ WhatsApp models import failed: {e}")
        return False
    
    try:
        from whatsapp.services import classify_message_type, create_order_from_message
        print("✅ WhatsApp services import OK")
    except ImportError as e:
        print(f"❌ WhatsApp services import failed: {e}")
        return False
    
    try:
        from orders.models import Order, OrderItem
        print("✅ Orders models import OK")
    except ImportError as e:
        print(f"❌ Orders models import failed: {e}")
        return False
    
    try:
        from products.models import Product, Department
        print("✅ Products models import OK")
    except ImportError as e:
        print(f"❌ Products models import failed: {e}")
        return False
    
    return True

def test_message_classification():
    """Test message classification"""
    print("\nTesting message classification...")
    
    from whatsapp.services import classify_message_type
    
    # Test stock message
    stock_msg = {
        'content': 'STOKE AS AT 28 AUGUST 2025\n1.Spinach 3kg\n2.Patty pan 12 pun',
        'sender': 'SHALLOME +27 61 674 9368'
    }
    result = classify_message_type(stock_msg)
    print(f"Stock message classified as: {result}")
    
    # Test order message
    order_msg = {
        'content': 'Mugg and Bean\n\nTomatoes x3\nOnions 5kg\nThanks',
        'sender': 'Restaurant Manager'
    }
    result = classify_message_type(order_msg)
    print(f"Order message classified as: {result}")
    
    # Test demarcation message
    demarcation_msg = {
        'content': 'Thursday orders starts here. 👇👇👇',
        'sender': 'Admin'
    }
    result = classify_message_type(demarcation_msg)
    print(f"Demarcation message classified as: {result}")

def test_database_connection():
    """Test database connection"""
    print("\nTesting database connection...")
    
    try:
        from django.db import connection
        cursor = connection.cursor()
        cursor.execute("SELECT 1")
        print("✅ Database connection OK")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def test_migrations_needed():
    """Check if migrations are needed"""
    print("\nChecking migrations...")
    
    try:
        from django.core.management import execute_from_command_line
        from io import StringIO
        import sys
        
        # Capture output
        old_stdout = sys.stdout
        sys.stdout = StringIO()
        
        try:
            execute_from_command_line(['manage.py', 'showmigrations', '--plan'])
            output = sys.stdout.getvalue()
            sys.stdout = old_stdout
            
            if 'whatsapp' in output:
                print("✅ WhatsApp app found in migrations")
            else:
                print("❌ WhatsApp app not found in migrations - need to run makemigrations")
                
        except Exception as e:
            sys.stdout = old_stdout
            print(f"❌ Migration check failed: {e}")
            
    except Exception as e:
        print(f"❌ Migration check failed: {e}")

def main():
    print("🧪 Testing Django WhatsApp Integration")
    print("=" * 50)
    
    # Test imports
    if not test_imports():
        print("\n❌ Import tests failed - stopping here")
        return
    
    # Test database
    if not test_database_connection():
        print("\n❌ Database tests failed - stopping here")
        return
    
    # Test migrations
    test_migrations_needed()
    
    # Test message classification
    test_message_classification()
    
    print("\n" + "=" * 50)
    print("🎯 Basic tests completed")
    print("\nNext steps:")
    print("1. Run: python manage.py makemigrations whatsapp")
    print("2. Run: python manage.py migrate")
    print("3. Run: python manage.py runserver")
    print("4. Test API endpoints")

if __name__ == '__main__':
    main()
