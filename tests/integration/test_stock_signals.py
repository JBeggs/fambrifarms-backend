"""
Integration tests for stock management signals
Tests the automatic stock reservation, release, and sale operations
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from decimal import Decimal
from datetime import date, timedelta

from orders.models import Order, OrderItem
from inventory.models import FinishedInventory, StockMovement, StockAlert
from products.models import Product, Department
from accounts.models import RestaurantProfile

User = get_user_model()


class StockSignalsIntegrationTest(TestCase):
    """Test stock management signals integration"""
    
    def setUp(self):
        # Create test customer
        self.customer = User.objects.create_user(
            email='test@restaurant.com',
            password='testpass123',
            user_type='restaurant',
            first_name='Test',
            last_name='Restaurant'
        )
        
        # Create restaurant profile
        RestaurantProfile.objects.create(
            user=self.customer,
            business_name='Test Restaurant',
            address='123 Test St',
            city='Test City',
            postal_code='12345'
        )
        
        # Create test products
        self.department = Department.objects.create(
            name='Test Vegetables',
            description='Test department'
        )
        
        self.product1 = Product.objects.create(
            name='Test Lettuce',
            department=self.department,
            price=Decimal('25.00'),
            unit='kg'
        )
        
        self.product2 = Product.objects.create(
            name='Test Tomatoes',
            department=self.department,
            price=Decimal('30.00'),
            unit='kg'
        )
        
        # Create inventory records
        self.inventory1, _ = FinishedInventory.objects.get_or_create(
            product=self.product1,
            defaults={
                'available_quantity': Decimal('100.00'),
                'reserved_quantity': Decimal('0.00'),
                'minimum_level': Decimal('10.00'),
                'reorder_level': Decimal('25.00'),
                'average_cost': Decimal('15.00')
            }
        )
        
        # Ensure inventory1 has the correct values (in case it was created by signal with different values)
        self.inventory1.available_quantity = Decimal('100.00')
        self.inventory1.reserved_quantity = Decimal('0.00')
        self.inventory1.minimum_level = Decimal('10.00')
        self.inventory1.reorder_level = Decimal('25.00')
        self.inventory1.average_cost = Decimal('15.00')
        self.inventory1.save()
        
        self.inventory2, _ = FinishedInventory.objects.get_or_create(
            product=self.product2,
            defaults={
                'available_quantity': Decimal('50.00'),
                'reserved_quantity': Decimal('0.00'),
                'minimum_level': Decimal('5.00'),
                'reorder_level': Decimal('15.00'),
                'average_cost': Decimal('20.00')
            }
        )
        
        # Ensure inventory2 has the correct values (in case it was created by signal with different values)
        self.inventory2.available_quantity = Decimal('50.00')
        self.inventory2.reserved_quantity = Decimal('0.00')
        self.inventory2.minimum_level = Decimal('5.00')
        self.inventory2.reorder_level = Decimal('15.00')
        self.inventory2.average_cost = Decimal('20.00')
        self.inventory2.save()
        
        # Find next valid order date
        today = date.today()
        days_ahead = 0 - today.weekday()  # Monday
        if days_ahead <= 0:
            days_ahead += 7
        self.order_date = today + timedelta(days_ahead)
    
    def test_order_confirmation_reserves_stock(self):
        """Test that confirming an order reserves stock"""
        # Create order with items
        order = Order.objects.create(
            restaurant=self.customer,
            order_date=self.order_date,
            status='received'
        )
        
        OrderItem.objects.create(
            order=order,
            product=self.product1,
            quantity=Decimal('20.00'),
            price=Decimal('25.00'),
            unit='kg'
        )
        
        OrderItem.objects.create(
            order=order,
            product=self.product2,
            quantity=Decimal('10.00'),
            price=Decimal('30.00'),
            unit='kg'
        )
        
        # Initial stock levels
        initial_available1 = self.inventory1.available_quantity
        initial_available2 = self.inventory2.available_quantity
        
        # Confirm the order (this should trigger stock reservation)
        order.status = 'confirmed'
        order.save()
        
        # Refresh inventory records
        self.inventory1.refresh_from_db()
        self.inventory2.refresh_from_db()
        
        # Check that stock was reserved
        self.assertEqual(
            self.inventory1.available_quantity,
            initial_available1 - Decimal('20.00')
        )
        self.assertEqual(self.inventory1.reserved_quantity, Decimal('20.00'))
        
        self.assertEqual(
            self.inventory2.available_quantity,
            initial_available2 - Decimal('10.00')
        )
        self.assertEqual(self.inventory2.reserved_quantity, Decimal('10.00'))
        
        # Check that stock movements were created
        movements = StockMovement.objects.filter(
            movement_type='finished_reserve',
            reference_number=order.order_number
        )
        self.assertEqual(movements.count(), 2)
    
    def test_order_delivery_sells_stock(self):
        """Test that delivering an order sells reserved stock"""
        # Create and confirm order first
        order = Order.objects.create(
            restaurant=self.customer,
            order_date=self.order_date,
            status='confirmed'
        )
        
        OrderItem.objects.create(
            order=order,
            product=self.product1,
            quantity=Decimal('15.00'),
            price=Decimal('25.00'),
            unit='kg'
        )
        
        # Manually reserve stock (simulating confirmation signal)
        self.inventory1.reserve_stock(Decimal('15.00'))
        initial_reserved = self.inventory1.reserved_quantity
        
        # Deliver the order (this should trigger stock sale)
        order.status = 'delivered'
        order.save()
        
        # Refresh inventory
        self.inventory1.refresh_from_db()
        
        # Check that reserved stock was sold
        self.assertEqual(
            self.inventory1.reserved_quantity,
            initial_reserved - Decimal('15.00')
        )
        
        # Check that stock movement was created
        movement = StockMovement.objects.filter(
            movement_type='finished_sell',
            reference_number=order.order_number,
            product=self.product1
        ).first()
        
        self.assertIsNotNone(movement)
        self.assertEqual(movement.quantity, Decimal('15.00'))
    
    def test_order_cancellation_releases_stock(self):
        """Test that cancelling an order releases reserved stock"""
        # Create and confirm order first
        order = Order.objects.create(
            restaurant=self.customer,
            order_date=self.order_date,
            status='confirmed'
        )
        
        OrderItem.objects.create(
            order=order,
            product=self.product1,
            quantity=Decimal('25.00'),
            price=Decimal('25.00'),
            unit='kg'
        )
        
        # Manually reserve stock (simulating confirmation signal)
        initial_available = self.inventory1.available_quantity
        self.inventory1.reserve_stock(Decimal('25.00'))
        
        # Create the corresponding stock movement record
        StockMovement.objects.create(
            movement_type='finished_reserve',
            reference_number=order.order_number,
            product=self.product1,
            quantity=Decimal('25.00'),
            unit_cost=Decimal('25.00'),
            total_value=Decimal('625.00'),
            user=self.customer,
            notes=f"Reserved for order {order.order_number}"
        )
        
        # Cancel the order (this should trigger stock release)
        order.status = 'cancelled'
        order.save()
        
        # Refresh inventory
        self.inventory1.refresh_from_db()
        
        # Check that stock was released back to available
        self.assertEqual(self.inventory1.available_quantity, initial_available)
        self.assertEqual(self.inventory1.reserved_quantity, Decimal('0.00'))
        
        # Check that stock movement was created
        movement = StockMovement.objects.filter(
            movement_type='finished_release',
            reference_number=order.order_number,
            product=self.product1
        ).first()
        
        self.assertIsNotNone(movement)
        self.assertEqual(movement.quantity, Decimal('25.00'))
    
    def test_insufficient_stock_creates_alert(self):
        """Test that insufficient stock creates appropriate alerts"""
        # Create order that exceeds available stock
        order = Order.objects.create(
            restaurant=self.customer,
            order_date=self.order_date,
            status='received'
        )
        
        # Order more than available (inventory1 has 100, order 150)
        OrderItem.objects.create(
            order=order,
            product=self.product1,
            quantity=Decimal('150.00'),
            price=Decimal('25.00'),
            unit='kg'
        )
        
        # Confirm the order
        order.status = 'confirmed'
        order.save()
        
        # Check that a stock alert was created
        alert = StockAlert.objects.filter(
            alert_type='out_of_stock',
            product=self.product1
        ).first()
        
        self.assertIsNotNone(alert)
        self.assertEqual(alert.severity, 'critical')
    
    def test_low_stock_after_sale_creates_production_alert(self):
        """Test that low stock after sale creates production needed alert"""
        # Set inventory to just above reorder level
        self.inventory1.available_quantity = Decimal('30.00')
        self.inventory1.reorder_level = Decimal('25.00')
        self.inventory1.save()
        
        # Create and process order that brings stock below reorder level
        order = Order.objects.create(
            restaurant=self.customer,
            order_date=self.order_date,
            status='confirmed'
        )
        
        OrderItem.objects.create(
            order=order,
            product=self.product1,
            quantity=Decimal('20.00'),
            price=Decimal('25.00'),
            unit='kg'
        )
        
        # Manually reserve and then sell stock
        self.inventory1.reserve_stock(Decimal('20.00'))
        self.inventory1.sell_stock(Decimal('20.00'))
        
        # Deliver the order to trigger production alert check
        order.status = 'delivered'
        order.save()
        
        # Check that production needed alert was created
        alert = StockAlert.objects.filter(
            alert_type='production_needed',
            product=self.product1
        ).first()
        
        self.assertIsNotNone(alert)
        self.assertEqual(alert.severity, 'medium')
    
    def test_complete_order_lifecycle_stock_flow(self):
        """Test complete order lifecycle: create → confirm → deliver"""
        # Create order
        order = Order.objects.create(
            restaurant=self.customer,
            order_date=self.order_date,
            status='received'
        )
        
        OrderItem.objects.create(
            order=order,
            product=self.product1,
            quantity=Decimal('30.00'),
            price=Decimal('25.00'),
            unit='kg'
        )
        
        # Initial state
        initial_available = self.inventory1.available_quantity
        initial_reserved = self.inventory1.reserved_quantity
        
        # Step 1: Confirm order (should reserve stock)
        order.status = 'confirmed'
        order.save()
        
        self.inventory1.refresh_from_db()
        self.assertEqual(
            self.inventory1.available_quantity,
            initial_available - Decimal('30.00')
        )
        self.assertEqual(
            self.inventory1.reserved_quantity,
            initial_reserved + Decimal('30.00')
        )
        
        # Step 2: Deliver order (should sell reserved stock)
        order.status = 'delivered'
        order.save()
        
        self.inventory1.refresh_from_db()
        self.assertEqual(
            self.inventory1.available_quantity,
            initial_available - Decimal('30.00')  # Still reduced
        )
        self.assertEqual(
            self.inventory1.reserved_quantity,
            initial_reserved  # Back to original (sold)
        )
        
        # Check stock movements were created for both operations
        reserve_movement = StockMovement.objects.filter(
            movement_type='finished_reserve',
            reference_number=order.order_number
        ).first()
        
        sell_movement = StockMovement.objects.filter(
            movement_type='finished_sell',
            reference_number=order.order_number
        ).first()
        
        self.assertIsNotNone(reserve_movement)
        self.assertIsNotNone(sell_movement)
        self.assertEqual(reserve_movement.quantity, Decimal('30.00'))
        self.assertEqual(sell_movement.quantity, Decimal('30.00'))
