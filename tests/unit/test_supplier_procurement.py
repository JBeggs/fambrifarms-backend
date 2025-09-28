"""
Unit tests for supplier and procurement functionality
Tests supplier models, procurement logic, and purchase order management
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from decimal import Decimal
from datetime import date, timedelta

from suppliers.models import Supplier, SalesRep, SupplierProduct, SupplierPriceList, SupplierPriceListItem
from procurement.models import PurchaseOrder, PurchaseOrderItem
from products.models import Product, Department
from orders.models import Order, OrderItem
from accounts.models import RestaurantProfile

User = get_user_model()


class SupplierModelTest(TestCase):
    """Test Supplier model functionality"""
    
    def setUp(self):
        self.supplier = Supplier.objects.create(
            name='Test Supplier Ltd',
            contact_person='John Smith',
            email='john@testsupplier.com',
            phone='+27 11 123 4567',
            address='123 Supplier Street, Johannesburg',
            description='Premium vegetable supplier',
            supplier_type='external',
            payment_terms_days=30,
            lead_time_days=3,
            minimum_order_value=Decimal('500.00')
        )
        
        # Create test customer and order for performance calculations
        self.customer = User.objects.create_user(
            email='customer@restaurant.com',
            password='testpass123',
            user_type='restaurant'
        )
        
        RestaurantProfile.objects.create(
            user=self.customer,
            business_name='Test Restaurant',
            address='456 Restaurant St',
            city='Food City',
            postal_code='12345'
        )
        
        # Create test products
        self.department = Department.objects.create(name='Vegetables')
        
        self.product1 = Product.objects.create(
            name='Premium Lettuce',
            department=self.department,
            price=Decimal('30.00'),
            unit='kg'
        )
        
        self.product2 = Product.objects.create(
            name='Organic Tomatoes',
            department=self.department,
            price=Decimal('40.00'),
            unit='kg'
        )
        
        # Create supplier products
        SupplierProduct.objects.create(
            supplier=self.supplier,
            product=self.product1,
            supplier_price=Decimal('25.00'),
            is_available=True,
            stock_quantity=100
        )
        
        SupplierProduct.objects.create(
            supplier=self.supplier,
            product=self.product2,
            supplier_price=Decimal('35.00'),
            is_available=True,
            stock_quantity=50
        )
    
    def test_supplier_string_representation(self):
        """Test supplier string representation"""
        self.assertEqual(str(self.supplier), 'Test Supplier Ltd')
    
    def test_supplier_total_orders_calculation(self):
        """Test total orders calculation"""
        # Create orders with items from this supplier
        today = date.today()
        days_ahead = 0 - today.weekday()  # Monday
        if days_ahead <= 0:
            days_ahead += 7
        order_date = today + timedelta(days_ahead)
        
        order1 = Order.objects.create(
            restaurant=self.customer,
            order_date=order_date,
            status='confirmed'
        )
        
        OrderItem.objects.create(
            order=order1,
            product=self.product1,
            quantity=Decimal('10.00'),
            price=Decimal('30.00'),
            unit='kg'
        )
        
        order2 = Order.objects.create(
            restaurant=self.customer,
            order_date=order_date,
            status='confirmed'
        )
        
        OrderItem.objects.create(
            order=order2,
            product=self.product2,
            quantity=Decimal('5.00'),
            price=Decimal('40.00'),
            unit='kg'
        )
        
        # Should count 2 distinct orders
        self.assertEqual(self.supplier.total_orders, 2)
    
    def test_supplier_total_order_value_calculation(self):
        """Test total order value calculation"""
        # Create order with items from this supplier
        today = date.today()
        days_ahead = 0 - today.weekday()  # Monday
        if days_ahead <= 0:
            days_ahead += 7
        order_date = today + timedelta(days_ahead)
        
        order = Order.objects.create(
            restaurant=self.customer,
            order_date=order_date,
            status='confirmed'
        )
        
        OrderItem.objects.create(
            order=order,
            product=self.product1,
            quantity=Decimal('10.00'),
            price=Decimal('30.00'),
            unit='kg'
        )
        
        OrderItem.objects.create(
            order=order,
            product=self.product2,
            quantity=Decimal('5.00'),
            price=Decimal('40.00'),
            unit='kg'
        )
        
        # Total: (10 * 30) + (5 * 40) = 300 + 200 = 500
        expected_total = 500.0
        self.assertEqual(self.supplier.total_order_value, expected_total)
    
    def test_supplier_last_order_date(self):
        """Test last order date calculation"""
        # Initially no orders
        self.assertIsNone(self.supplier.last_order_date)
        
        # Create order
        today = date.today()
        days_ahead = 0 - today.weekday()  # Monday
        if days_ahead <= 0:
            days_ahead += 7
        order_date = today + timedelta(days_ahead)
        
        order = Order.objects.create(
            restaurant=self.customer,
            order_date=order_date,
            status='confirmed'
        )
        
        OrderItem.objects.create(
            order=order,
            product=self.product1,
            quantity=Decimal('10.00'),
            price=Decimal('30.00'),
            unit='kg'
        )
        
        # Should return the order creation date
        last_order_date = self.supplier.last_order_date
        self.assertIsNotNone(last_order_date)
        self.assertEqual(last_order_date, order.created_at.date())


class SalesRepModelTest(TestCase):
    """Test SalesRep model functionality"""
    
    def setUp(self):
        self.supplier = Supplier.objects.create(
            name='Test Supplier',
            supplier_type='external'
        )
        
        self.sales_rep = SalesRep.objects.create(
            supplier=self.supplier,
            name='Jane Doe',
            email='jane@testsupplier.com',
            phone='+27 11 987 6543',
            position='Senior Sales Representative',
            is_primary=True,
            total_orders=15
        )
    
    def test_sales_rep_string_representation(self):
        """Test sales rep string representation"""
        expected_str = f"Jane Doe ({self.supplier.name})"
        self.assertEqual(str(self.sales_rep), expected_str)
    
    def test_sales_rep_primary_contact(self):
        """Test primary contact functionality"""
        self.assertTrue(self.sales_rep.is_primary)
        
        # Create secondary sales rep
        secondary_rep = SalesRep.objects.create(
            supplier=self.supplier,
            name='Bob Wilson',
            email='bob@testsupplier.com',
            is_primary=False
        )
        
        self.assertFalse(secondary_rep.is_primary)
        
        # Test ordering (primary should come first)
        reps = SalesRep.objects.filter(supplier=self.supplier).order_by('-is_primary', 'name')
        self.assertEqual(reps.first(), self.sales_rep)


class SupplierProductTest(TestCase):
    """Test SupplierProduct model functionality"""
    
    def setUp(self):
        self.supplier = Supplier.objects.create(
            name='Test Supplier',
            supplier_type='external',
            lead_time_days=5
        )
        
        self.department = Department.objects.create(name='Vegetables')
        
        self.product = Product.objects.create(
            name='Test Product',
            department=self.department,
            price=Decimal('25.00'),
            unit='kg'
        )
        
        self.supplier_product = SupplierProduct.objects.create(
            supplier=self.supplier,
            product=self.product,
            supplier_product_code='SP001',
            supplier_product_name='Premium Test Product',
            supplier_category_code='VEG',
            supplier_price=Decimal('20.00'),
            is_available=True,
            stock_quantity=100,
            minimum_order_quantity=10,
            lead_time_days=3,  # Override supplier default
            quality_rating=Decimal('4.5')
        )
    
    def test_supplier_product_string_representation(self):
        """Test supplier product string representation"""
        expected_str = f"{self.supplier.name} - {self.product.name}"
        self.assertEqual(str(self.supplier_product), expected_str)
    
    def test_get_effective_lead_time_product_specific(self):
        """Test effective lead time with product-specific override"""
        # Should return product-specific lead time (3 days)
        self.assertEqual(self.supplier_product.get_effective_lead_time(), 3)
    
    def test_get_effective_lead_time_supplier_default(self):
        """Test effective lead time with supplier default"""
        # Remove product-specific lead time
        self.supplier_product.lead_time_days = None
        self.supplier_product.save()
        
        # Should return supplier default (5 days)
        self.assertEqual(self.supplier_product.get_effective_lead_time(), 5)
    
    def test_supplier_product_unique_constraint(self):
        """Test unique constraint on supplier-product combination"""
        # Try to create duplicate supplier-product combination
        with self.assertRaises(Exception):  # Should raise IntegrityError
            SupplierProduct.objects.create(
                supplier=self.supplier,
                product=self.product,  # Same combination
                supplier_price=Decimal('22.00')
            )


class SupplierPriceListTest(TestCase):
    """Test SupplierPriceList functionality"""
    
    def setUp(self):
        self.supplier = Supplier.objects.create(
            name='Test Supplier',
            supplier_type='external'
        )
        
        self.price_list = SupplierPriceList.objects.create(
            supplier=self.supplier,
            list_date=date.today(),
            file_reference='test_price_list_2025.pdf',
            is_processed=False,
            total_items=10,
            matched_items=7,
            unmatched_items=3
        )
    
    def test_price_list_string_representation(self):
        """Test price list string representation"""
        expected_str = f"{self.supplier.name} - Price List {self.price_list.list_date}"
        self.assertEqual(str(self.price_list), expected_str)
    
    def test_match_percentage_calculation(self):
        """Test match percentage calculation"""
        # 7 matched out of 10 total = 70%
        expected_percentage = 70.0
        self.assertEqual(self.price_list.match_percentage, expected_percentage)
    
    def test_match_percentage_no_items(self):
        """Test match percentage with no items"""
        empty_list = SupplierPriceList.objects.create(
            supplier=self.supplier,
            list_date=date.today() - timedelta(days=1),
            total_items=0
        )
        
        self.assertEqual(empty_list.match_percentage, 0)


class SupplierPriceListItemTest(TestCase):
    """Test SupplierPriceListItem functionality"""
    
    def setUp(self):
        self.supplier = Supplier.objects.create(
            name='Test Supplier',
            supplier_type='external'
        )
        
        self.price_list = SupplierPriceList.objects.create(
            supplier=self.supplier,
            list_date=date.today()
        )
        
        self.department = Department.objects.create(name='Vegetables')
        
        self.product = Product.objects.create(
            name='Test Lettuce',
            department=self.department,
            price=Decimal('30.00'),
            unit='kg'
        )
        
        self.price_item = SupplierPriceListItem.objects.create(
            price_list=self.price_list,
            supplier_code='VEG001',
            product_description='Fresh Lettuce - Premium Grade',
            category_code='VEG',
            quantity=50,
            unit_price=Decimal('22.00'),
            vat_amount=Decimal('3.30'),
            matched_product=self.product,
            match_confidence=Decimal('95.50'),
            match_method='exact',
            is_manually_matched=False
        )
    
    def test_price_item_string_representation(self):
        """Test price item string representation"""
        expected_str = f"{self.price_item.product_description} - R{self.price_item.unit_price}"
        self.assertEqual(str(self.price_item), expected_str)
    
    def test_price_item_auto_calculation_on_save(self):
        """Test automatic total calculations on save"""
        # Create new item to test save calculations
        new_item = SupplierPriceListItem(
            price_list=self.price_list,
            supplier_code='VEG002',
            product_description='Fresh Tomatoes',
            category_code='VEG',
            quantity=30,
            unit_price=Decimal('25.00'),
            vat_amount=Decimal('112.50')  # 30 * 25 * 0.15
        )
        
        new_item.save()
        
        # Check auto-calculated totals
        expected_total_excl = Decimal('30') * Decimal('25.00')  # 750.00
        expected_total_incl = expected_total_excl + Decimal('112.50')  # 862.50
        
        self.assertEqual(new_item.total_excl_vat, expected_total_excl)
        self.assertEqual(new_item.total_incl_vat, expected_total_incl)
    
    def test_price_item_auto_calculation_no_vat(self):
        """Test automatic total calculations without VAT"""
        new_item = SupplierPriceListItem(
            price_list=self.price_list,
            supplier_code='VEG003',
            product_description='Basic Onions',
            category_code='VEG',
            quantity=20,
            unit_price=Decimal('15.00')
            # No VAT amount provided
        )
        
        new_item.save()
        
        expected_total = Decimal('20') * Decimal('15.00')  # 300.00
        
        self.assertEqual(new_item.total_excl_vat, expected_total)
        self.assertEqual(new_item.total_incl_vat, expected_total)  # Same as excl when no VAT


class PurchaseOrderTest(TestCase):
    """Test PurchaseOrder model functionality"""
    
    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(
            email='manager@fambrifarms.com',
            password='testpass123',
            user_type='admin'
        )
        
        # Create supplier and sales rep
        self.supplier = Supplier.objects.create(
            name='Test Supplier',
            supplier_type='external'
        )
        
        self.sales_rep = SalesRep.objects.create(
            supplier=self.supplier,
            name='Sales Rep',
            email='sales@supplier.com',
            is_primary=True
        )
        
        # Create customer and order
        self.customer = User.objects.create_user(
            email='customer@restaurant.com',
            password='testpass123',
            user_type='restaurant'
        )
        
        today = date.today()
        days_ahead = 0 - today.weekday()  # Monday
        if days_ahead <= 0:
            days_ahead += 7
        order_date = today + timedelta(days_ahead)
        
        self.order = Order.objects.create(
            restaurant=self.customer,
            order_date=order_date,
            status='confirmed'
        )
        
        # Create purchase order
        self.purchase_order = PurchaseOrder.objects.create(
            supplier=self.supplier,
            sales_rep=self.sales_rep,
            order=self.order,
            status='draft',
            subtotal=Decimal('500.00'),
            tax_amount=Decimal('75.00'),
            total_amount=Decimal('575.00'),
            created_by=self.user,
            notes='Test purchase order'
        )
    
    def test_purchase_order_po_number_generation(self):
        """Test PO number generation"""
        # PO number should be auto-generated
        self.assertIsNotNone(self.purchase_order.po_number)
        self.assertTrue(len(self.purchase_order.po_number) > 0)
    
    def test_purchase_order_string_representation(self):
        """Test purchase order string representation"""
        po_str = str(self.purchase_order)
        self.assertIn(self.purchase_order.po_number, po_str)
        self.assertIn(self.supplier.name, po_str)
    
    def test_purchase_order_status_choices(self):
        """Test purchase order status transitions"""
        # Test valid status changes
        valid_statuses = ['draft', 'sent', 'confirmed', 'partial', 'received', 'cancelled']
        
        for status_choice in valid_statuses:
            self.purchase_order.status = status_choice
            self.purchase_order.save()
            
            self.purchase_order.refresh_from_db()
            self.assertEqual(self.purchase_order.status, status_choice)
    
    def test_purchase_order_financial_calculations(self):
        """Test purchase order financial field validation"""
        # Test that amounts are properly stored
        self.assertEqual(self.purchase_order.subtotal, Decimal('500.00'))
        self.assertEqual(self.purchase_order.tax_amount, Decimal('75.00'))
        self.assertEqual(self.purchase_order.total_amount, Decimal('575.00'))
        
        # Test amount validation (should not allow negative values)
        with self.assertRaises(Exception):  # ValidationError
            invalid_po = PurchaseOrder(
                supplier=self.supplier,
                subtotal=Decimal('-100.00'),  # Negative value
                created_by=self.user
            )
            invalid_po.full_clean()  # This should raise ValidationError


class PurchaseOrderItemTest(TestCase):
    """Test PurchaseOrderItem functionality"""
    
    def setUp(self):
        # Create test data
        self.user = User.objects.create_user(
            email='manager@fambrifarms.com',
            password='testpass123',
            user_type='admin'
        )
        
        self.supplier = Supplier.objects.create(
            name='Test Supplier',
            supplier_type='external'
        )
        
        self.purchase_order = PurchaseOrder.objects.create(
            supplier=self.supplier,
            status='draft',
            created_by=self.user
        )
        
        self.department = Department.objects.create(name='Vegetables')
        
        self.product = Product.objects.create(
            name='Test Product',
            department=self.department,
            price=Decimal('25.00'),
            unit='kg'
        )
        
        self.po_item = PurchaseOrderItem.objects.create(
            purchase_order=self.purchase_order,
            product=self.product,
            quantity=Decimal('20.00'),
            unit_price=Decimal('22.00'),
            notes='Premium grade required'
        )
    
    def test_po_item_total_price_calculation(self):
        """Test purchase order item total price calculation"""
        expected_total = Decimal('20.00') * Decimal('22.00')  # 440.00
        self.assertEqual(self.po_item.total_price, expected_total)
    
    def test_po_item_string_representation(self):
        """Test purchase order item string representation"""
        po_item_str = str(self.po_item)
        self.assertIn(self.product.name, po_item_str)
        self.assertIn('20.00', po_item_str)
    
    def test_po_item_unique_constraint(self):
        """Test unique constraint on purchase order-product combination"""
        # Try to create duplicate PO-product combination
        with self.assertRaises(Exception):  # Should raise IntegrityError
            PurchaseOrderItem.objects.create(
                purchase_order=self.purchase_order,
                product=self.product,  # Same combination
                quantity=Decimal('10.00'),
                unit_price=Decimal('20.00')
            )
