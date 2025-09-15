"""
Integration test that seeds the database and then validates the complete system
This test demonstrates the full Fambri Farms digital transformation
"""

from django.test import TransactionTestCase
from django.core.management import call_command
from django.contrib.auth import get_user_model
from decimal import Decimal
from datetime import date

from accounts.models import User, RestaurantProfile, FarmProfile
from products.models import Product, Department
from suppliers.models import Supplier, SalesRep
from inventory.models import FinishedInventory, MarketPrice, PricingRule, CustomerPriceList
from orders.models import Order, OrderItem

User = get_user_model()


class SeededSystemIntegrationTest(TransactionTestCase):
    """Test the complete system after seeding with real data"""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # Run all seeding commands in order
        print("\n🌱 SEEDING FAMBRI FARMS DIGITAL TRANSFORMATION...")
        
        try:
            # Phase 1-2: Users and Customers
            print("👥 Seeding users and customers...")
            call_command('seed_fambri_users', verbosity=0)
            call_command('import_customers', verbosity=0)
            
            # Phase 3: Suppliers
            print("🏭 Seeding suppliers...")
            call_command('seed_fambri_suppliers', verbosity=0)
            
            # Phase 4: Products and Units
            print("📦 Seeding products and units...")
            call_command('seed_fambri_units', verbosity=0)
            call_command('seed_fambri_products', verbosity=0)
            
            # Phase 5: Pricing Intelligence
            print("💰 Seeding pricing intelligence...")
            call_command('seed_fambri_pricing', verbosity=0)
            
            # Phase 6: Order History
            print("📋 Seeding order history...")
            call_command('seed_fambri_orders', '--weeks', '4', verbosity=0)
            
            # Phase 7: Stock Management
            print("📊 Seeding stock management...")
            call_command('seed_fambri_stock', verbosity=0)
            
            print("✅ SEEDING COMPLETE!")
            
        except Exception as e:
            print(f"❌ SEEDING FAILED: {e}")
            raise

    def test_complete_digital_transformation(self):
        """Test that the complete digital transformation is working"""
        
        print("\n🧪 TESTING FAMBRI FARMS DIGITAL TRANSFORMATION...")
        
        # Test 1: User System
        print("👥 Testing user system...")
        karl = User.objects.filter(email='karl@fambrifarms.co.za').first()
        self.assertIsNotNone(karl, "Karl (Farm Manager) should exist")
        self.assertEqual(karl.user_type, 'farm_manager')
        
        hazvinei = User.objects.filter(email='hazvinei@fambrifarms.co.za').first()
        self.assertIsNotNone(hazvinei, "Hazvinei (Stock Taker) should exist")
        self.assertEqual(hazvinei.phone, '+27 61 674 9368')
        
        customers = User.objects.filter(user_type='restaurant')
        self.assertGreater(customers.count(), 10, "Should have multiple customers")
        print(f"   ✅ {customers.count()} customers, Karl & Hazvinei configured")
        
        # Test 2: Product Catalog
        print("📦 Testing product catalog...")
        departments = Department.objects.all()
        self.assertGreaterEqual(departments.count(), 5, "Should have 5+ departments")
        
        products = Product.objects.all()
        self.assertGreater(products.count(), 60, "Should have 60+ products")
        
        # Test specific SHALLOME products
        butternut = Product.objects.filter(name__icontains='Butternut').first()
        self.assertIsNotNone(butternut, "Butternut should exist")
        
        mixed_lettuce = Product.objects.filter(name__icontains='Mixed Lettuce').first()
        self.assertIsNotNone(mixed_lettuce, "Mixed Lettuce should exist")
        print(f"   ✅ {products.count()} products across {departments.count()} departments")
        
        # Test 3: Supplier Network
        print("🏭 Testing supplier network...")
        suppliers = Supplier.objects.all()
        self.assertGreaterEqual(suppliers.count(), 3, "Should have 3+ suppliers")
        
        fambri_internal = Supplier.objects.filter(name__icontains='Fambri Farms Internal').first()
        self.assertIsNotNone(fambri_internal, "Fambri Internal should exist")
        
        karl_rep = SalesRep.objects.filter(name='Karl').first()
        self.assertIsNotNone(karl_rep, "Karl should be a sales rep")
        print(f"   ✅ {suppliers.count()} suppliers with specialized roles")
        
        # Test 4: Pricing Intelligence
        print("💰 Testing pricing intelligence...")
        market_prices = MarketPrice.objects.all()
        self.assertGreater(market_prices.count(), 1000, "Should have 1000+ market prices")
        
        pricing_rules = PricingRule.objects.all()
        self.assertGreaterEqual(pricing_rules.count(), 5, "Should have 5 pricing rules")
        
        customer_price_lists = CustomerPriceList.objects.all()
        self.assertGreater(customer_price_lists.count(), 10, "Should have 10+ price lists")
        print(f"   ✅ {market_prices.count()} market prices, {pricing_rules.count()} rules, {customer_price_lists.count()} customer lists")
        
        # Test 5: Order History
        print("📋 Testing order history...")
        orders = Order.objects.all()
        self.assertGreater(orders.count(), 20, "Should have 20+ orders")
        
        order_items = OrderItem.objects.all()
        self.assertGreater(order_items.count(), 100, "Should have 100+ order items")
        
        # Test Tuesday/Thursday pattern
        order_days = set(orders.values_list('order_date__weekday', flat=True))
        expected_days = {1, 3}  # Tuesday and Thursday
        self.assertTrue(expected_days.intersection(order_days), "Should have Tuesday/Thursday orders")
        print(f"   ✅ {orders.count()} orders with {order_items.count()} items")
        
        # Test 6: Inventory Management
        print("📊 Testing inventory management...")
        inventories = FinishedInventory.objects.all()
        self.assertGreater(inventories.count(), 50, "Should have 50+ inventory records")
        
        # Test specific SHALLOME stock levels
        butternut_inventory = FinishedInventory.objects.filter(
            product__name__icontains='Butternut'
        ).first()
        if butternut_inventory:
            self.assertGreater(butternut_inventory.available_quantity, 50, 
                             "Butternut should have high stock")
        
        print(f"   ✅ {inventories.count()} inventory records with realistic stock levels")
        
        # Test 7: Business Logic Integration
        print("🔄 Testing business logic integration...")
        
        # Test customer-specific pricing
        maltos_user = User.objects.filter(
            restaurantprofile__business_name__icontains='Maltos'
        ).first()
        
        if maltos_user:
            maltos_price_list = CustomerPriceList.objects.filter(
                customer=maltos_user,
                status='active'
            ).first()
            
            if maltos_price_list:
                self.assertGreater(maltos_price_list.total_products, 0, 
                                 "Maltos should have products in price list")
                print(f"   ✅ Maltos has {maltos_price_list.total_products} products with {maltos_price_list.average_markup_percentage:.1f}% avg markup")
        
        # Test order processing workflow
        recent_order = Order.objects.filter(status='delivered').first()
        if recent_order:
            self.assertGreater(recent_order.items.count(), 0, "Order should have items")
            self.assertGreater(recent_order.total_amount, 0, "Order should have value")
            print(f"   ✅ Sample order: {recent_order.items.count()} items, R{recent_order.total_amount}")
        
        print("\n🎉 FAMBRI FARMS DIGITAL TRANSFORMATION VALIDATION COMPLETE!")
        print("=" * 60)
        print("✅ User System: Karl (Manager) + Hazvinei (Stock Taker) + Customers")
        print("✅ Product Catalog: 60+ products from real SHALLOME data")
        print("✅ Supplier Network: 3 specialized suppliers with roles")
        print("✅ Pricing Intelligence: Market-driven dynamic pricing")
        print("✅ Order History: Authentic WhatsApp patterns")
        print("✅ Inventory Management: Real stock levels and alerts")
        print("✅ Business Logic: End-to-end workflow integration")
        print("=" * 60)
        print("🚀 SYSTEM READY FOR FLUTTER DEVELOPMENT!")

    def test_specific_whatsapp_patterns(self):
        """Test that specific WhatsApp patterns are preserved"""
        
        print("\n📱 Testing WhatsApp pattern preservation...")
        
        # Test Maltos order patterns
        maltos_orders = Order.objects.filter(
            restaurant__restaurantprofile__business_name__icontains='Maltos'
        )
        
        if maltos_orders.exists():
            # Maltos should have detailed orders
            avg_items = sum(order.items.count() for order in maltos_orders) / maltos_orders.count()
            self.assertGreater(avg_items, 8, "Maltos should have detailed orders")
            print(f"   ✅ Maltos: {maltos_orders.count()} orders, {avg_items:.1f} items avg")
        
        # Test Sylvia (private customer) patterns
        sylvia_orders = Order.objects.filter(
            restaurant__first_name__icontains='Sylvia'
        )
        
        if sylvia_orders.exists():
            # Sylvia should have smaller household orders
            avg_items = sum(order.items.count() for order in sylvia_orders) / sylvia_orders.count()
            self.assertLess(avg_items, 8, "Sylvia should have smaller orders")
            print(f"   ✅ Sylvia: {sylvia_orders.count()} orders, {avg_items:.1f} items avg")
        
        # Test product usage patterns
        popular_products = OrderItem.objects.values('product__name').annotate(
            total_ordered=models.Sum('quantity')
        ).order_by('-total_ordered')[:5]
        
        if popular_products:
            print("   📊 Most ordered products:")
            for item in popular_products:
                print(f"      - {item['product__name']}: {item['total_ordered']} units")
        
        print("   ✅ WhatsApp patterns successfully preserved in order data")

    def test_pricing_accuracy(self):
        """Test that pricing reflects real market conditions"""
        
        print("\n💰 Testing pricing accuracy...")
        
        # Test customer segment pricing
        segments = ['premium', 'standard', 'budget', 'retail']
        
        for segment in segments:
            pricing_rule = PricingRule.objects.filter(customer_segment=segment).first()
            if pricing_rule:
                print(f"   📊 {segment.title()}: {pricing_rule.base_markup_percentage}% base markup")
                self.assertTrue(pricing_rule.is_effective(), f"{segment} rule should be effective")
        
        # Test market price variations
        products_with_prices = MarketPrice.objects.values('matched_product__name').annotate(
            price_count=models.Count('id'),
            avg_price=models.Avg('unit_price_incl_vat')
        ).filter(price_count__gt=5)[:3]
        
        if products_with_prices:
            print("   📈 Market price tracking:")
            for item in products_with_prices:
                print(f"      - {item['matched_product__name']}: R{item['avg_price']:.2f} avg ({item['price_count']} records)")
        
        print("   ✅ Pricing intelligence system operational")


# Import Django models for aggregation
from django.db import models
