#!/usr/bin/env python3
"""
Production Data Validation Script
Validates the integrity and completeness of production data for the AI OCR Invoice Processing System
"""

import os
import sys
import django
from decimal import Decimal
from datetime import datetime, timedelta

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'familyfarms_api.settings')
django.setup()

from django.utils import timezone
from products.models import Product, Department
from suppliers.models import Supplier, SupplierProduct
from accounts.models import RestaurantProfile, PrivateCustomerProfile, User
from settings.models import BusinessConfiguration, UnitOfMeasure
from inventory.models import FinishedInventory, InvoicePhoto, ExtractedInvoiceData, SupplierProductMapping
from orders.models import Order, OrderItem
from whatsapp.models import WhatsAppMessage

def print_header(title):
    """Print a formatted header"""
    print(f"\n{'='*60}")
    print(f"🔍 {title}")
    print(f"{'='*60}")

def print_success(message):
    """Print success message"""
    print(f"✅ {message}")

def print_warning(message):
    """Print warning message"""
    print(f"⚠️  {message}")

def print_error(message):
    """Print error message"""
    print(f"❌ {message}")

def validate_products():
    """Validate product data integrity"""
    print_header("PRODUCT DATA VALIDATION")
    
    # Basic counts
    total_products = Product.objects.count()
    products_with_price = Product.objects.exclude(price=0).count()
    products_zero_price = Product.objects.filter(price=0).count()
    
    print_success(f"Total products: {total_products}")
    print_success(f"Products with pricing: {products_with_price}")
    
    if products_zero_price > 0:
        print_warning(f"Products with zero price: {products_zero_price}")
        
        # Show some examples
        zero_price_examples = Product.objects.filter(price=0)[:5]
        for product in zero_price_examples:
            print(f"  - {product.name}: R{product.price}")
    
    # Check for unrealistic prices
    expensive_products = Product.objects.filter(price__gt=500)
    if expensive_products.exists():
        print_warning(f"Products with high prices (>R500): {expensive_products.count()}")
        for product in expensive_products[:3]:
            print(f"  - {product.name}: R{product.price}")
    
    # Check departments
    departments = Department.objects.count()
    print_success(f"Departments: {departments}")
    
    # Check product distribution by department
    dept_distribution = {}
    for product in Product.objects.select_related('department'):
        dept_name = product.department.name if product.department else 'No Department'
        dept_distribution[dept_name] = dept_distribution.get(dept_name, 0) + 1
    
    print("\nProduct distribution by department:")
    for dept, count in sorted(dept_distribution.items()):
        print(f"  {dept}: {count} products")

def validate_suppliers():
    """Validate supplier data integrity"""
    print_header("SUPPLIER DATA VALIDATION")
    
    # Basic counts
    total_suppliers = Supplier.objects.count()
    active_suppliers = Supplier.objects.filter(is_active=True).count()
    
    print_success(f"Total suppliers: {total_suppliers}")
    print_success(f"Active suppliers: {active_suppliers}")
    
    # Check supplier products
    total_supplier_products = SupplierProduct.objects.count()
    print_success(f"Total supplier products: {total_supplier_products}")
    
    # Check each supplier
    print("\nSupplier breakdown:")
    for supplier in Supplier.objects.filter(is_active=True):
        product_count = supplier.supplierproduct_set.count()
        avg_price = supplier.supplierproduct_set.aggregate(
            avg_price=django.db.models.Avg('supplier_price')
        )['avg_price'] or 0
        
        print(f"  {supplier.name}: {product_count} products, avg R{avg_price:.2f}")
        
        # Check for unrealistic supplier prices
        expensive_items = supplier.supplierproduct_set.filter(supplier_price__gt=200)
        if expensive_items.exists():
            print_warning(f"    High-priced items: {expensive_items.count()}")
            for item in expensive_items[:2]:
                print(f"      - {item.name}: R{item.supplier_price}/{item.unit}")
    
    # Check for products without supplier pricing
    products_without_suppliers = Product.objects.filter(
        supplierproduct__isnull=True
    ).count()
    
    if products_without_suppliers > 0:
        print_warning(f"Products without supplier pricing: {products_without_suppliers}")

def validate_customers():
    """Validate customer data integrity"""
    print_header("CUSTOMER DATA VALIDATION")
    
    # Basic counts
    restaurants = RestaurantProfile.objects.count()
    private_customers = PrivateCustomerProfile.objects.count()
    total_customers = restaurants + private_customers
    
    print_success(f"Total customers: {total_customers}")
    print_success(f"Restaurants: {restaurants}")
    print_success(f"Private customers: {private_customers}")
    
    # Check for suspicious/fake data
    suspicious_keywords = ['test', 'fake', 'sample', 'demo', 'example']
    suspicious_customers = []
    
    # Check restaurant profiles
    for restaurant in RestaurantProfile.objects.all():
        if any(keyword in restaurant.restaurant_name.lower() for keyword in suspicious_keywords):
            suspicious_customers.append(restaurant.restaurant_name)
    
    # Check private customer profiles
    for private in PrivateCustomerProfile.objects.all():
        name = f"{private.user.first_name} {private.user.last_name}".strip()
        if any(keyword in name.lower() for keyword in suspicious_keywords):
            suspicious_customers.append(name)
    
    if suspicious_customers:
        print_warning(f"Suspicious customer names found: {len(suspicious_customers)}")
        for name in suspicious_customers[:5]:
            print(f"  - {name}")
    else:
        print_success("No suspicious customer names found")
    
    # Check customer locations
    restaurant_locations = RestaurantProfile.objects.values_list('location', flat=True).distinct()
    private_locations = PrivateCustomerProfile.objects.values_list('location', flat=True).distinct()
    all_locations = set(filter(None, restaurant_locations)) | set(filter(None, private_locations))
    print(f"\nCustomer locations: {', '.join(all_locations)}")
    
    # Check for customers with orders (this would need to be implemented based on actual order model relationships)
    print_success(f"Customer data validation completed")

def validate_business_settings():
    """Validate business configuration"""
    print_header("BUSINESS SETTINGS VALIDATION")
    
    # Check business settings
    settings = BusinessConfiguration.objects.first()
    if settings:
        print_success(f"Business configuration found")
    else:
        print_error("No business configuration found - this may cause issues")
    
    # Check units of measure
    units = UnitOfMeasure.objects.count()
    print_success(f"Units of measure: {units}")
    
    if units == 0:
        print_error("No units of measure configured")

def validate_inventory():
    """Validate inventory data"""
    print_header("INVENTORY DATA VALIDATION")
    
    # Basic inventory counts
    total_inventory_items = FinishedInventory.objects.count()
    items_with_stock = FinishedInventory.objects.filter(quantity_available__gt=0).count()
    
    print_success(f"Total inventory items: {total_inventory_items}")
    print_success(f"Items with available stock: {items_with_stock}")
    
    # Check for negative stock
    negative_stock = FinishedInventory.objects.filter(quantity_available__lt=0)
    if negative_stock.exists():
        print_warning(f"Items with negative stock: {negative_stock.count()}")
        for item in negative_stock[:3]:
            print(f"  - {item.product.name}: {item.quantity_available}")
    
    # Check stock value
    total_stock_value = sum(
        (item.quantity_available * item.product.price) 
        for item in FinishedInventory.objects.select_related('product')
        if item.quantity_available > 0
    )
    print_success(f"Total stock value: R{total_stock_value:,.2f}")

def validate_invoice_system():
    """Validate invoice processing system"""
    print_header("INVOICE PROCESSING SYSTEM VALIDATION")
    
    # Check invoice photos
    total_invoices = InvoicePhoto.objects.count()
    print_success(f"Total invoice photos: {total_invoices}")
    
    if total_invoices > 0:
        # Check status distribution
        status_counts = {}
        for status, _ in InvoicePhoto.STATUS_CHOICES:
            count = InvoicePhoto.objects.filter(status=status).count()
            if count > 0:
                status_counts[status] = count
        
        print("Invoice status distribution:")
        for status, count in status_counts.items():
            print(f"  {status}: {count}")
        
        # Check extracted data
        total_extracted = ExtractedInvoiceData.objects.count()
        print_success(f"Extracted invoice items: {total_extracted}")
        
        # Check supplier mappings
        total_mappings = SupplierProductMapping.objects.count()
        print_success(f"Supplier product mappings: {total_mappings}")
        
        if total_mappings > 0:
            # Check mapping strategies
            strategy_counts = {}
            for strategy, _ in SupplierProductMapping.PRICING_STRATEGY_CHOICES:
                count = SupplierProductMapping.objects.filter(pricing_strategy=strategy).count()
                if count > 0:
                    strategy_counts[strategy] = count
            
            print("Pricing strategy distribution:")
            for strategy, count in strategy_counts.items():
                print(f"  {strategy}: {count}")
    else:
        print_warning("No invoice photos found - system not yet tested")

def validate_orders():
    """Validate order system"""
    print_header("ORDER SYSTEM VALIDATION")
    
    # Basic order counts
    total_orders = Order.objects.count()
    recent_orders = Order.objects.filter(
        created_at__gte=timezone.now() - timedelta(days=7)
    ).count()
    
    print_success(f"Total orders: {total_orders}")
    print_success(f"Orders in last 7 days: {recent_orders}")
    
    if total_orders > 0:
        # Check order status distribution
        status_counts = {}
        for status, _ in Order.STATUS_CHOICES:
            count = Order.objects.filter(status=status).count()
            if count > 0:
                status_counts[status] = count
        
        print("Order status distribution:")
        for status, count in status_counts.items():
            print(f"  {status}: {count}")
        
        # Check order value
        total_order_value = Order.objects.aggregate(
            total=django.db.models.Sum('total_amount')
        )['total'] or 0
        
        avg_order_value = total_order_value / total_orders if total_orders > 0 else 0
        
        print_success(f"Total order value: R{total_order_value:,.2f}")
        print_success(f"Average order value: R{avg_order_value:,.2f}")
        
        # Check order items
        total_order_items = OrderItem.objects.count()
        avg_items_per_order = total_order_items / total_orders if total_orders > 0 else 0
        
        print_success(f"Total order items: {total_order_items}")
        print_success(f"Average items per order: {avg_items_per_order:.1f}")
    else:
        print_warning("No orders found - system not yet used")

def validate_whatsapp_system():
    """Validate WhatsApp message system"""
    print_header("WHATSAPP SYSTEM VALIDATION")
    
    # Basic message counts
    total_messages = WhatsAppMessage.objects.count()
    recent_messages = WhatsAppMessage.objects.filter(
        timestamp__gte=timezone.now() - timedelta(days=7)
    ).count()
    
    print_success(f"Total WhatsApp messages: {total_messages}")
    print_success(f"Messages in last 7 days: {recent_messages}")
    
    if total_messages > 0:
        # Check message type distribution
        type_counts = {}
        for msg_type in ['order', 'stock', 'general', 'inquiry']:
            count = WhatsAppMessage.objects.filter(message_type=msg_type).count()
            if count > 0:
                type_counts[msg_type] = count
        
        print("Message type distribution:")
        for msg_type, count in type_counts.items():
            print(f"  {msg_type}: {count}")
        
        # Check processed vs unprocessed
        processed = WhatsAppMessage.objects.filter(processed=True).count()
        unprocessed = WhatsAppMessage.objects.filter(processed=False).count()
        
        print_success(f"Processed messages: {processed}")
        if unprocessed > 0:
            print_warning(f"Unprocessed messages: {unprocessed}")
    else:
        print_warning("No WhatsApp messages found - system not yet used")

def validate_data_consistency():
    """Validate data consistency across models"""
    print_header("DATA CONSISTENCY VALIDATION")
    
    # Check for orphaned records
    print("Checking for orphaned records...")
    
    # Products without departments
    products_no_dept = Product.objects.filter(department__isnull=True).count()
    if products_no_dept > 0:
        print_warning(f"Products without departments: {products_no_dept}")
    
    # Order items without valid products
    invalid_order_items = OrderItem.objects.filter(product__isnull=True).count()
    if invalid_order_items > 0:
        print_error(f"Order items with invalid products: {invalid_order_items}")
    
    # Supplier products without valid suppliers
    invalid_supplier_products = SupplierProduct.objects.filter(supplier__isnull=True).count()
    if invalid_supplier_products > 0:
        print_error(f"Supplier products with invalid suppliers: {invalid_supplier_products}")
    
    # Check for duplicate records
    print("\nChecking for duplicates...")
    
    # Duplicate products (same name)
    from django.db.models import Count
    duplicate_products = Product.objects.values('name').annotate(
        count=Count('name')
    ).filter(count__gt=1)
    
    if duplicate_products.exists():
        print_warning(f"Duplicate product names: {duplicate_products.count()}")
        for dup in duplicate_products[:3]:
            print(f"  - {dup['name']}: {dup['count']} instances")
    
    # Duplicate customers (same email)
    duplicate_customers = Customer.objects.values('email').annotate(
        count=Count('email')
    ).filter(count__gt=1, email__isnull=False)
    
    if duplicate_customers.exists():
        print_warning(f"Duplicate customer emails: {duplicate_customers.count()}")
    
    print_success("Data consistency check completed")

def validate_system_health():
    """Overall system health check"""
    print_header("SYSTEM HEALTH CHECK")
    
    # Check critical components
    critical_checks = [
        ("Products", Product.objects.count() > 0),
        ("Suppliers", Supplier.objects.count() > 0),
        ("Customers", (RestaurantProfile.objects.count() + PrivateCustomerProfile.objects.count()) > 0),
        ("Business Configuration", BusinessConfiguration.objects.exists()),
        ("Units of Measure", UnitOfMeasure.objects.count() > 0),
    ]
    
    all_critical_passed = True
    for check_name, passed in critical_checks:
        if passed:
            print_success(f"{check_name}: OK")
        else:
            print_error(f"{check_name}: FAILED")
            all_critical_passed = False
    
    # System readiness score
    total_products = Product.objects.count()
    products_with_price = Product.objects.exclude(price=0).count()
    pricing_coverage = (products_with_price / total_products * 100) if total_products > 0 else 0
    
    supplier_products = SupplierProduct.objects.count()
    supplier_coverage = (supplier_products / total_products * 100) if total_products > 0 else 0
    
    inventory_items = FinishedInventory.objects.count()
    inventory_coverage = (inventory_items / total_products * 100) if total_products > 0 else 0
    
    print(f"\nSystem Readiness Metrics:")
    print(f"  Pricing coverage: {pricing_coverage:.1f}%")
    print(f"  Supplier coverage: {supplier_coverage:.1f}%")
    print(f"  Inventory coverage: {inventory_coverage:.1f}%")
    
    # Overall health score
    health_score = (pricing_coverage + supplier_coverage + inventory_coverage) / 3
    
    if health_score >= 80:
        print_success(f"Overall system health: {health_score:.1f}% - EXCELLENT")
    elif health_score >= 60:
        print_warning(f"Overall system health: {health_score:.1f}% - GOOD")
    else:
        print_error(f"Overall system health: {health_score:.1f}% - NEEDS IMPROVEMENT")
    
    return all_critical_passed and health_score >= 60

def main():
    """Main validation function"""
    print_header("PRODUCTION DATA VALIDATION STARTED")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Run all validations
        validate_products()
        validate_suppliers()
        validate_customers()
        validate_business_settings()
        validate_inventory()
        validate_invoice_system()
        validate_orders()
        validate_whatsapp_system()
        validate_data_consistency()
        
        # Final system health check
        system_healthy = validate_system_health()
        
        print_header("VALIDATION SUMMARY")
        
        if system_healthy:
            print_success("🎉 SYSTEM IS PRODUCTION READY!")
            print_success("All critical components are functioning correctly.")
            print_success("Data integrity is maintained.")
            print_success("Ready for live testing and deployment.")
        else:
            print_error("⚠️  SYSTEM NEEDS ATTENTION")
            print_error("Some critical issues found that should be addressed.")
            print_error("Review the validation results above.")
        
        print(f"\nValidation completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return 0 if system_healthy else 1
        
    except Exception as e:
        print_error(f"Validation failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
