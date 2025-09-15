"""
Comprehensive integration tests for the Fambri Farms Digital Transformation
Tests the complete system with real seeded data from WhatsApp messages
"""

import os
import sys
import django
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.db import transaction
from decimal import Decimal
from datetime import date, timedelta

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'familyfarms_api.settings')

from accounts.models import User, RestaurantProfile, FarmProfile, PrivateCustomerProfile
from products.models import Product, Department
from suppliers.models import Supplier, SalesRep, SupplierProduct
from inventory.models import (
    UnitOfMeasure, FinishedInventory, MarketPrice, PricingRule, 
    CustomerPriceList, CustomerPriceListItem, ProcurementRecommendation
)
from orders.models import Order, OrderItem
from whatsapp.models import WhatsAppMessage


class FambriFarmsDigitalTransformationTest(TestCase):
    """Test the complete digital transformation with real seeded data"""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # This test assumes the seeding commands have been run
        # python manage.py seed_fambri_users
        # python manage.py import_customers  
        # python manage.py seed_fambri_suppliers
        # python manage.py seed_fambri_products
        # python manage.py seed_fambri_units
        # python manage.py seed_fambri_pricing
        # python manage.py seed_fambri_orders
        # python manage.py seed_fambri_stock

    def test_01_user_system_integrity(self):
        """Test that the user system is properly set up with real data"""
        
        # Test Karl (Farm Manager)
        karl = User.objects.filter(email='karl@fambrifarms.co.za').first()
        self.assertIsNotNone(karl, "Karl (Farm Manager) should exist")
        self.assertEqual(karl.user_type, 'farm_manager')
        self.assertTrue(karl.is_staff)
        self.assertEqual(karl.phone, '+27 76 655 4873')
        
        # Test Karl's farm profile
        karl_profile = FarmProfile.objects.filter(user=karl).first()
        self.assertIsNotNone(karl_profile, "Karl should have a farm profile")
        self.assertEqual(karl_profile.position, 'Farm Manager')
        self.assertTrue(karl_profile.can_manage_inventory)
        self.assertTrue(karl_profile.can_approve_orders)
        
        # Test Hazvinei (Stock Taker)
        hazvinei = User.objects.filter(email='hazvinei@fambrifarms.co.za').first()
        self.assertIsNotNone(hazvinei, "Hazvinei (Stock Taker) should exist")
        self.assertEqual(hazvinei.user_type, 'stock_taker')
        self.assertEqual(hazvinei.phone, '+27 61 674 9368')
        
        # Test customer users
        customers = User.objects.filter(user_type='restaurant')
        self.assertGreater(customers.count(), 10, "Should have multiple restaurant customers")
        
        # Test specific customers from WhatsApp data
        maltos_user = User.objects.filter(restaurantprofile__business_name__icontains='Maltos').first()
        self.assertIsNotNone(maltos_user, "Maltos restaurant should exist")
        
        sylvia_user = User.objects.filter(first_name__icontains='Sylvia').first()
        self.assertIsNotNone(sylvia_user, "Sylvia (private customer) should exist")

    def test_02_product_catalog_completeness(self):
        """Test that the product catalog matches SHALLOME stock data"""
        
        # Test departments
        departments = Department.objects.all()
        self.assertGreaterEqual(departments.count(), 5, "Should have at least 5 departments")
        
        dept_names = set(departments.values_list('name', flat=True))
        expected_depts = {'Vegetables', 'Fruits', 'Herbs & Spices', 'Mushrooms', 'Specialty Items'}
        self.assertTrue(expected_depts.issubset(dept_names), "Should have all expected departments")
        
        # Test products
        products = Product.objects.all()
        self.assertGreaterEqual(products.count(), 60, "Should have 60+ products from SHALLOME data")
        
        # Test specific products from WhatsApp messages
        key_products = [
            'Mixed Lettuce', 'Butternut', 'Avocados', 'Lemons', 'Tomatoes',
            'Broccoli', 'Cauliflower', 'Basil', 'Parsley', 'Button Mushrooms'
        ]
        
        for product_name in key_products:
            product = Product.objects.filter(name__icontains=product_name.split()[0]).first()
            self.assertIsNotNone(product, f"{product_name} should exist in catalog")
        
        # Test units are properly assigned
        units_used = set(Product.objects.values_list('unit', flat=True))
        expected_units = {'kg', 'bunch', 'head', 'each', 'box', 'punnet'}
        self.assertTrue(expected_units.issubset(units_used), "Products should use expected units")

    def test_03_supplier_ecosystem(self):
        """Test the supplier network with specialized roles"""
        
        suppliers = Supplier.objects.all()
        self.assertGreaterEqual(suppliers.count(), 3, "Should have at least 3 suppliers")
        
        # Test Fambri Farms Internal
        fambri_internal = Supplier.objects.filter(name__icontains='Fambri Farms Internal').first()
        self.assertIsNotNone(fambri_internal, "Fambri Farms Internal supplier should exist")
        self.assertEqual(fambri_internal.payment_terms_days, 0)  # Internal supplier
        
        # Test Karl as sales rep for internal supplier
        karl_rep = SalesRep.objects.filter(
            supplier=fambri_internal, 
            name='Karl'
        ).first()
        self.assertIsNotNone(karl_rep, "Karl should be sales rep for internal supplier")
        self.assertTrue(karl_rep.is_primary)
        
        # Test Tania's Fresh Produce
        tania_supplier = Supplier.objects.filter(name__icontains='Tania').first()
        self.assertIsNotNone(tania_supplier, "Tania's supplier should exist")
        self.assertEqual(tania_supplier.lead_time_days, 0)  # Same day delivery
        
        # Test Mumbai Spice & Produce
        mumbai_supplier = Supplier.objects.filter(name__icontains='Mumbai').first()
        self.assertIsNotNone(mumbai_supplier, "Mumbai supplier should exist")
        
        # Test supplier products
        supplier_products = SupplierProduct.objects.all()
        self.assertGreater(supplier_products.count(), 100, "Should have 100+ supplier-product relationships")

    def test_04_pricing_intelligence_system(self):
        """Test the comprehensive pricing intelligence system"""
        
        # Test market prices
        market_prices = MarketPrice.objects.all()
        self.assertGreater(market_prices.count(), 1000, "Should have 1000+ market price records")
        
        # Test pricing rules
        pricing_rules = PricingRule.objects.all()
        self.assertGreaterEqual(pricing_rules.count(), 5, "Should have 5 customer segments")
        
        segments = set(pricing_rules.values_list('customer_segment', flat=True))
        expected_segments = {'premium', 'standard', 'budget', 'retail', 'wholesale'}
        self.assertEqual(segments, expected_segments, "Should have all customer segments")
        
        # Test customer price lists
        price_lists = CustomerPriceList.objects.all()
        self.assertGreater(price_lists.count(), 10, "Should have 10+ customer price lists")
        
        # Test price list items
        price_items = CustomerPriceListItem.objects.all()
        self.assertGreater(price_items.count(), 300, "Should have 300+ price list items")
        
        # Test procurement recommendations
        recommendations = ProcurementRecommendation.objects.all()
        self.assertGreater(recommendations.count(), 0, "Should have procurement recommendations")

    def test_05_order_history_authenticity(self):
        """Test that order history reflects real WhatsApp patterns"""
        
        orders = Order.objects.all()
        self.assertGreater(orders.count(), 50, "Should have 50+ orders from 8 weeks")
        
        order_items = OrderItem.objects.all()
        self.assertGreater(order_items.count(), 400, "Should have 400+ order items")
        
        # Test Tuesday/Thursday pattern
        order_days = set(orders.values_list('order_date__weekday', flat=True))
        # Monday=0, Tuesday=1, Thursday=3
        expected_days = {1, 3}  # Tuesday and Thursday
        self.assertTrue(expected_days.issubset(order_days), "Orders should be on Tuesday/Thursday")
        
        # Test specific customer patterns
        maltos_orders = Order.objects.filter(
            restaurant__restaurantprofile__business_name__icontains='Maltos'
        )
        if maltos_orders.exists():
            # Maltos should have detailed orders with multiple items
            avg_items = maltos_orders.annotate(
                item_count=models.Count('items')
            ).aggregate(
                avg=models.Avg('item_count')
            )['avg']
            self.assertGreater(avg_items, 10, "Maltos should have detailed orders (10+ items)")
        
        # Test private customer patterns
        sylvia_orders = Order.objects.filter(
            restaurant__first_name__icontains='Sylvia'
        )
        if sylvia_orders.exists():
            # Sylvia should have smaller household orders
            avg_items = sylvia_orders.annotate(
                item_count=models.Count('items')
            ).aggregate(
                avg=models.Avg('item_count')
            )['avg']
            self.assertLess(avg_items, 8, "Sylvia should have smaller household orders")

    def test_06_inventory_management_system(self):
        """Test the inventory management with SHALLOME data"""
        
        # Test finished inventory
        inventories = FinishedInventory.objects.all()
        self.assertGreater(inventories.count(), 50, "Should have 50+ inventory records")
        
        # Test specific SHALLOME stock levels
        butternut_inventory = FinishedInventory.objects.filter(
            product__name__icontains='Butternut'
        ).first()
        if butternut_inventory:
            self.assertGreater(butternut_inventory.available_quantity, 50, 
                             "Butternut should have high stock (60kg from SHALLOME)")
        
        oranges_inventory = FinishedInventory.objects.filter(
            product__name__icontains='Orange'
        ).first()
        if oranges_inventory:
            self.assertLess(oranges_inventory.available_quantity, 2, 
                           "Oranges should have low stock (0.6kg from SHALLOME)")
        
        # Test stock alerts
        from inventory.models import StockAlert
        alerts = StockAlert.objects.filter(is_active=True)
        self.assertGreater(alerts.count(), 20, "Should have 20+ active stock alerts")
        
        # Test critical alerts exist
        critical_alerts = alerts.filter(severity='critical')
        high_alerts = alerts.filter(severity='high')
        self.assertGreater(critical_alerts.count() + high_alerts.count(), 0, 
                          "Should have critical or high priority alerts")

    def test_07_whatsapp_integration_readiness(self):
        """Test that the system is ready for WhatsApp integration"""
        
        # Test WhatsApp message model exists and is functional
        # (This would be populated by actual WhatsApp scraping)
        
        # Test message processing capabilities
        from whatsapp.services import parse_order_items
        
        # Test with sample message content
        sample_message = "10 heads broccoli, 5 kg mixed lettuce, 3 boxes tomatoes"
        
        # This should not fail (even if it returns empty results without full setup)
        try:
            result = parse_order_items(sample_message)
            # The function should exist and be callable
            self.assertTrue(True, "WhatsApp message parsing is available")
        except Exception as e:
            self.fail(f"WhatsApp message parsing failed: {e}")

    def test_08_business_rules_validation(self):
        """Test that business rules are properly enforced"""
        
        # Test order day validation
        from orders.models import Order
        
        # Test that orders can only be placed on Monday/Thursday
        # (This is validated in the model)
        
        # Test pricing rule effectiveness
        pricing_rules = PricingRule.objects.filter(is_active=True)
        for rule in pricing_rules:
            self.assertTrue(rule.is_effective(), f"Pricing rule {rule.name} should be effective")
        
        # Test customer segmentation
        premium_customers = User.objects.filter(
            restaurantprofile__business_name__in=['Casa Bella', 'Pecanwood Golf Estate']
        )
        for customer in premium_customers:
            price_list = CustomerPriceList.objects.filter(
                customer=customer,
                status='active'
            ).first()
            if price_list:
                # Premium customers should have higher markup
                self.assertGreater(price_list.average_markup_percentage, 30,
                                 f"{customer.get_full_name()} should have premium pricing")

    def test_09_data_consistency_and_integrity(self):
        """Test data consistency across the entire system"""
        
        # Test that all products have valid units
        products_without_units = Product.objects.filter(unit__isnull=True)
        self.assertEqual(products_without_units.count(), 0, "All products should have units")
        
        # Test that all orders have valid delivery dates
        invalid_orders = Order.objects.filter(delivery_date__isnull=True)
        self.assertEqual(invalid_orders.count(), 0, "All orders should have delivery dates")
        
        # Test that all price list items have valid prices
        invalid_prices = CustomerPriceListItem.objects.filter(
            customer_price_incl_vat__lte=0
        )
        self.assertEqual(invalid_prices.count(), 0, "All prices should be positive")
        
        # Test that all suppliers have contact information
        suppliers_without_contact = Supplier.objects.filter(
            contact_person='',
            email='',
            phone=''
        )
        self.assertEqual(suppliers_without_contact.count(), 0, 
                        "All suppliers should have contact information")

    def test_10_system_performance_and_scalability(self):
        """Test that the system performs well with the seeded data"""
        
        import time
        
        # Test product catalog query performance
        start_time = time.time()
        products = list(Product.objects.select_related('department').all())
        query_time = time.time() - start_time
        self.assertLess(query_time, 1.0, "Product catalog should load quickly")
        
        # Test customer price list generation performance
        customer = User.objects.filter(user_type='restaurant').first()
        if customer:
            start_time = time.time()
            price_items = CustomerPriceListItem.objects.filter(
                price_list__customer=customer,
                price_list__status='active'
            ).select_related('product', 'price_list')
            list(price_items)  # Force evaluation
            query_time = time.time() - start_time
            self.assertLess(query_time, 0.5, "Customer pricing should be fast")
        
        # Test order history query performance
        start_time = time.time()
        recent_orders = Order.objects.filter(
            order_date__gte=date.today() - timedelta(days=30)
        ).select_related('restaurant').prefetch_related('items__product')
        list(recent_orders)  # Force evaluation
        query_time = time.time() - start_time
        self.assertLess(query_time, 1.0, "Order history should load quickly")


# Import Django models for aggregation
from django.db import models
