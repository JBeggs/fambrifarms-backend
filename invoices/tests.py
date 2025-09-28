from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal
from datetime import date, timedelta

from accounts.models import User, RestaurantProfile
from products.models import Department, Product
from orders.models import Order, OrderItem
from .models import Invoice, InvoiceItem, Payment, CreditNote


class InvoiceModelTest(TestCase):
    """Test Invoice model functionality"""
    
    def setUp(self):
        # Create test user and restaurant
        self.user = User.objects.create_user(
            email='test@restaurant.com',
            password='testpass123'
        )
        self.restaurant = RestaurantProfile.objects.create(
            user=self.user,
            business_name='Test Restaurant',
            address='123 Test St',
            city='Test City',
            postal_code='12345'
        )
        
        # Create test product and order
        self.department = Department.objects.create(name='Test Department')
        self.product = Product.objects.create(
            name='Test Product',
            price=Decimal('25.00'),
            unit='each',
            department=self.department
        )
        
        self.order = Order.objects.create(
            restaurant=self.user,
            order_date=date.today(),
            delivery_date=date.today() + timedelta(days=1),
            status='confirmed'
        )
        
        self.order_item = OrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=2,
            unit='each',
            price=Decimal('25.00')
        )
    
    def test_invoice_creation(self):
        """Test invoice is created correctly"""
        invoice = Invoice.objects.create(
            order=self.order,
            customer=self.user,
            subtotal=Decimal('50.00')
        )
        
        self.assertEqual(invoice.customer, self.user)
        self.assertEqual(invoice.order, self.order)
        self.assertEqual(invoice.subtotal, Decimal('50.00'))
        self.assertEqual(invoice.status, 'draft')
        self.assertEqual(invoice.tax_rate, Decimal('15.00'))  # Default SA VAT
        self.assertIsNotNone(invoice.invoice_number)
        self.assertIsNotNone(invoice.due_date)
    
    def test_invoice_number_generation(self):
        """Test automatic invoice number generation"""
        invoice1 = Invoice.objects.create(
            customer=self.user,
            subtotal=Decimal('50.00')
        )
        invoice2 = Invoice.objects.create(
            customer=self.user,
            subtotal=Decimal('75.00')
        )
        
        current_year = timezone.now().year
        self.assertTrue(invoice1.invoice_number.startswith(f'INV{current_year}'))
        self.assertTrue(invoice2.invoice_number.startswith(f'INV{current_year}'))
        self.assertNotEqual(invoice1.invoice_number, invoice2.invoice_number)
    
    def test_invoice_str_representation(self):
        """Test invoice string representation"""
        invoice = Invoice.objects.create(
            customer=self.user,
            subtotal=Decimal('50.00')
        )
        expected_str = f"Invoice {invoice.invoice_number} - {self.user.get_full_name()}"
        self.assertEqual(str(invoice), expected_str)
    
    def test_due_date_calculation(self):
        """Test automatic due date calculation"""
        invoice_date = date.today()
        invoice = Invoice.objects.create(
            customer=self.user,
            invoice_date=invoice_date,
            subtotal=Decimal('50.00')
        )
        
        expected_due_date = invoice_date + timedelta(days=30)
        self.assertEqual(invoice.due_date, expected_due_date)
    
    def test_tax_and_total_calculation(self):
        """Test automatic tax and total calculation"""
        invoice = Invoice.objects.create(
            customer=self.user,
            subtotal=Decimal('100.00'),
            discount_amount=Decimal('10.00'),
            tax_rate=Decimal('15.00')
        )
        
        # Tax should be calculated on (subtotal - discount) * tax_rate
        expected_tax = (Decimal('100.00') - Decimal('10.00')) * (Decimal('15.00') / 100)
        expected_total = Decimal('100.00') - Decimal('10.00') + expected_tax
        
        self.assertEqual(invoice.tax_amount, expected_tax)
        self.assertEqual(invoice.total_amount, expected_total)
    
    def test_balance_due_property(self):
        """Test balance due calculation"""
        invoice = Invoice.objects.create(
            customer=self.user,
            subtotal=Decimal('100.00'),
            amount_paid=Decimal('30.00')
        )
        
        expected_balance = invoice.total_amount - Decimal('30.00')
        self.assertEqual(invoice.balance_due, expected_balance)
    
    def test_is_overdue_property(self):
        """Test overdue status calculation"""
        # Create overdue invoice
        past_date = date.today() - timedelta(days=5)
        overdue_invoice = Invoice.objects.create(
            customer=self.user,
            due_date=past_date,
            subtotal=Decimal('100.00'),
            status='sent'
        )
        
        # Create current invoice
        future_date = date.today() + timedelta(days=5)
        current_invoice = Invoice.objects.create(
            customer=self.user,
            due_date=future_date,
            subtotal=Decimal('100.00'),
            status='sent'
        )
        
        # Create paid invoice (should not be overdue even if past due date)
        paid_invoice = Invoice.objects.create(
            customer=self.user,
            due_date=past_date,
            subtotal=Decimal('100.00'),
            status='paid'
        )
        
        self.assertTrue(overdue_invoice.is_overdue)
        self.assertFalse(current_invoice.is_overdue)
        self.assertFalse(paid_invoice.is_overdue)
    
    def test_days_overdue_property(self):
        """Test days overdue calculation"""
        past_date = date.today() - timedelta(days=10)
        overdue_invoice = Invoice.objects.create(
            customer=self.user,
            due_date=past_date,
            subtotal=Decimal('100.00'),
            status='sent'
        )
        
        current_invoice = Invoice.objects.create(
            customer=self.user,
            due_date=date.today() + timedelta(days=5),
            subtotal=Decimal('100.00'),
            status='sent'
        )
        
        self.assertEqual(overdue_invoice.days_overdue, 10)
        self.assertEqual(current_invoice.days_overdue, 0)


class InvoiceItemModelTest(TestCase):
    """Test InvoiceItem model functionality"""
    
    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(
            email='test@restaurant.com',
            password='testpass123'
        )
        
        # Create test invoice
        self.invoice = Invoice.objects.create(
            customer=self.user,
            subtotal=Decimal('100.00')
        )
        
        # Create test product and order item
        self.department = Department.objects.create(name='Test Department')
        self.product = Product.objects.create(
            name='Test Product',
            price=Decimal('25.00'),
            unit='each',
            department=self.department
        )
        
        self.order = Order.objects.create(
            restaurant=self.user,
            order_date=date.today(),
            delivery_date=date.today() + timedelta(days=1),
            status='confirmed'
        )
        
        self.order_item = OrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=2,
            unit='each',
            price=Decimal('25.00')
        )
    
    def test_invoice_item_creation(self):
        """Test invoice item is created correctly"""
        item = InvoiceItem.objects.create(
            invoice=self.invoice,
            order_item=self.order_item,
            product_name='Test Product',
            quantity=2,
            unit_price=Decimal('25.00')
        )
        
        self.assertEqual(item.invoice, self.invoice)
        self.assertEqual(item.order_item, self.order_item)
        self.assertEqual(item.product_name, 'Test Product')
        self.assertEqual(item.quantity, 2)
        self.assertEqual(item.unit_price, Decimal('25.00'))
        self.assertEqual(item.line_total, Decimal('50.00'))
    
    def test_invoice_item_str_representation(self):
        """Test invoice item string representation"""
        item = InvoiceItem.objects.create(
            invoice=self.invoice,
            product_name='Test Product',
            quantity=3,
            unit_price=Decimal('15.00')
        )
        
        expected_str = "Test Product x3"
        self.assertEqual(str(item), expected_str)
    
    def test_line_total_calculation(self):
        """Test automatic line total calculation"""
        item = InvoiceItem.objects.create(
            invoice=self.invoice,
            product_name='Test Product',
            quantity=4,
            unit_price=Decimal('12.50')
        )
        
        expected_total = 4 * Decimal('12.50')
        self.assertEqual(item.line_total, expected_total)


class PaymentModelTest(TestCase):
    """Test Payment model functionality"""
    
    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(
            email='test@restaurant.com',
            password='testpass123'
        )
        
        # Create processor user
        self.processor = User.objects.create_user(
            email='processor@farm.com',
            password='testpass123'
        )
        
        # Create test invoice
        self.invoice = Invoice.objects.create(
            customer=self.user,
            subtotal=Decimal('100.00')
        )
    
    def test_payment_creation(self):
        """Test payment is created correctly"""
        payment = Payment.objects.create(
            invoice=self.invoice,
            amount=Decimal('50.00'),
            payment_method='bank_transfer',
            payment_date=date.today(),
            reference_number='REF123',
            processed_by=self.processor
        )
        
        self.assertEqual(payment.invoice, self.invoice)
        self.assertEqual(payment.amount, Decimal('50.00'))
        self.assertEqual(payment.payment_method, 'bank_transfer')
        self.assertEqual(payment.reference_number, 'REF123')
        self.assertEqual(payment.processed_by, self.processor)
    
    def test_payment_str_representation(self):
        """Test payment string representation"""
        payment = Payment.objects.create(
            invoice=self.invoice,
            amount=Decimal('75.00'),
            payment_method='cash'
        )
        
        expected_str = f"Payment R75.00 for {self.invoice.invoice_number}"
        self.assertEqual(str(payment), expected_str)
    
    def test_payment_method_choices(self):
        """Test payment method choices are valid"""
        valid_methods = ['cash', 'bank_transfer', 'credit_card', 'debit_card', 'cheque', 'other']
        
        for method in valid_methods:
            payment = Payment.objects.create(
                invoice=self.invoice,
                amount=Decimal('25.00'),
                payment_method=method
            )
            self.assertEqual(payment.payment_method, method)


class CreditNoteModelTest(TestCase):
    """Test CreditNote model functionality"""
    
    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(
            email='test@restaurant.com',
            password='testpass123'
        )
        
        # Create approver user
        self.approver = User.objects.create_user(
            email='approver@farm.com',
            password='testpass123'
        )
        
        # Create test invoice
        self.invoice = Invoice.objects.create(
            customer=self.user,
            subtotal=Decimal('100.00')
        )
    
    def test_credit_note_creation(self):
        """Test credit note is created correctly"""
        credit_note = CreditNote.objects.create(
            invoice=self.invoice,
            amount=Decimal('25.00'),
            reason='return',
            description='Product returned due to quality issues',
            credit_date=date.today(),
            approved_by=self.approver
        )
        
        self.assertEqual(credit_note.invoice, self.invoice)
        self.assertEqual(credit_note.amount, Decimal('25.00'))
        self.assertEqual(credit_note.reason, 'return')
        self.assertEqual(credit_note.description, 'Product returned due to quality issues')
        self.assertEqual(credit_note.approved_by, self.approver)
        self.assertIsNotNone(credit_note.credit_note_number)
    
    def test_credit_note_number_generation(self):
        """Test automatic credit note number generation"""
        cn1 = CreditNote.objects.create(
            invoice=self.invoice,
            amount=Decimal('25.00'),
            reason='return',
            description='Test credit note 1'
        )
        cn2 = CreditNote.objects.create(
            invoice=self.invoice,
            amount=Decimal('15.00'),
            reason='discount',
            description='Test credit note 2'
        )
        
        current_year = timezone.now().year
        self.assertTrue(cn1.credit_note_number.startswith(f'CN{current_year}'))
        self.assertTrue(cn2.credit_note_number.startswith(f'CN{current_year}'))
        self.assertNotEqual(cn1.credit_note_number, cn2.credit_note_number)
    
    def test_credit_note_str_representation(self):
        """Test credit note string representation"""
        credit_note = CreditNote.objects.create(
            invoice=self.invoice,
            amount=Decimal('30.00'),
            reason='damage',
            description='Damaged goods credit'
        )
        
        expected_str = f"Credit Note {credit_note.credit_note_number} - R30.00"
        self.assertEqual(str(credit_note), expected_str)
    
    def test_credit_note_reason_choices(self):
        """Test credit note reason choices are valid"""
        valid_reasons = ['return', 'damage', 'discount', 'correction', 'goodwill', 'other']
        
        for reason in valid_reasons:
            credit_note = CreditNote.objects.create(
                invoice=self.invoice,
                amount=Decimal('10.00'),
                reason=reason,
                description=f'Test {reason} credit note'
            )
            self.assertEqual(credit_note.reason, reason)


class InvoiceBusinessLogicTest(TestCase):
    """Test invoice business logic and workflows"""
    
    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(
            email='test@restaurant.com',
            password='testpass123'
        )
        
        # Create test product
        self.department = Department.objects.create(name='Test Department')
        self.product = Product.objects.create(
            name='Test Product',
            price=Decimal('20.00'),
            unit='kg',
            department=self.department
        )
        
        # Create test order
        self.order = Order.objects.create(
            restaurant=self.user,
            order_date=date.today(),
            delivery_date=date.today() + timedelta(days=1),
            status='confirmed'
        )
        
        self.order_item = OrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=5,
            unit='kg',
            price=Decimal('20.00')
        )
    
    def test_invoice_from_order_workflow(self):
        """Test creating invoice from order"""
        # Create invoice linked to order
        invoice = Invoice.objects.create(
            order=self.order,
            customer=self.user,
            subtotal=Decimal('100.00')
        )
        
        # Create invoice item from order item
        invoice_item = InvoiceItem.objects.create(
            invoice=invoice,
            order_item=self.order_item,
            product_name=self.product.name,
            quantity=self.order_item.quantity,
            unit_price=self.order_item.price
        )
        
        # Verify relationships
        self.assertEqual(invoice.order, self.order)
        self.assertEqual(invoice_item.order_item, self.order_item)
        self.assertEqual(invoice_item.product_name, self.product.name)
        self.assertEqual(invoice_item.quantity, 5)
        self.assertEqual(invoice_item.unit_price, Decimal('20.00'))
        self.assertEqual(invoice_item.line_total, Decimal('100.00'))
    
    def test_payment_workflow(self):
        """Test payment processing workflow"""
        # Create invoice
        invoice = Invoice.objects.create(
            customer=self.user,
            subtotal=Decimal('100.00'),
            status='sent'
        )
        
        # Make partial payment
        payment1 = Payment.objects.create(
            invoice=invoice,
            amount=Decimal('60.00'),
            payment_method='bank_transfer',
            payment_date=date.today()
        )
        
        # Update invoice amount paid
        invoice.amount_paid = Decimal('60.00')
        invoice.save()
        
        # Check balance
        self.assertEqual(invoice.balance_due, invoice.total_amount - Decimal('60.00'))
        
        # Make final payment
        remaining_balance = invoice.balance_due
        payment2 = Payment.objects.create(
            invoice=invoice,
            amount=remaining_balance,
            payment_method='cash',
            payment_date=date.today()
        )
        
        # Update invoice
        invoice.amount_paid = invoice.total_amount
        invoice.status = 'paid'
        invoice.paid_date = date.today()
        invoice.save()
        
        # Verify fully paid
        self.assertEqual(invoice.balance_due, Decimal('0.00'))
        self.assertEqual(invoice.status, 'paid')
        self.assertIsNotNone(invoice.paid_date)
    
    def test_credit_note_workflow(self):
        """Test credit note processing workflow"""
        # Create invoice
        invoice = Invoice.objects.create(
            customer=self.user,
            subtotal=Decimal('100.00'),
            status='paid',
            amount_paid=Decimal('115.00')  # Including tax
        )
        
        # Create credit note for returned item
        credit_note = CreditNote.objects.create(
            invoice=invoice,
            amount=Decimal('25.00'),
            reason='return',
            description='Customer returned 1 unit due to quality issue',
            credit_date=date.today()
        )
        
        # Verify credit note created
        self.assertEqual(credit_note.invoice, invoice)
        self.assertEqual(credit_note.amount, Decimal('25.00'))
        self.assertEqual(credit_note.reason, 'return')
        self.assertIsNotNone(credit_note.credit_note_number)
    
    def test_overdue_invoice_detection(self):
        """Test overdue invoice detection"""
        # Create overdue invoice
        past_due_date = date.today() - timedelta(days=15)
        overdue_invoice = Invoice.objects.create(
            customer=self.user,
            subtotal=Decimal('100.00'),
            due_date=past_due_date,
            status='sent'
        )
        
        # Test overdue properties
        self.assertTrue(overdue_invoice.is_overdue)
        self.assertEqual(overdue_invoice.days_overdue, 15)
        
        # Test that paid invoices are not overdue
        overdue_invoice.status = 'paid'
        overdue_invoice.save()
        self.assertFalse(overdue_invoice.is_overdue)
        self.assertEqual(overdue_invoice.days_overdue, 0)


class InvoiceIntegrationTest(TestCase):
    """Test invoice integration with other models"""
    
    def setUp(self):
        # Create test user and restaurant
        self.user = User.objects.create_user(
            email='test@restaurant.com',
            password='testpass123'
        )
        self.restaurant = RestaurantProfile.objects.create(
            user=self.user,
            business_name='Test Restaurant',
            address='123 Test St',
            city='Test City',
            postal_code='12345'
        )
        
        # Create test products
        self.department = Department.objects.create(name='Vegetables')
        self.product1 = Product.objects.create(
            name='Lettuce',
            price=Decimal('15.00'),
            unit='head',
            department=self.department
        )
        self.product2 = Product.objects.create(
            name='Tomatoes',
            price=Decimal('25.00'),
            unit='kg',
            department=self.department
        )
        
        # Create test order with multiple items
        self.order = Order.objects.create(
            restaurant=self.user,
            order_date=date.today(),
            delivery_date=date.today() + timedelta(days=1),
            status='confirmed'
        )
        
        self.order_item1 = OrderItem.objects.create(
            order=self.order,
            product=self.product1,
            quantity=10,
            unit='head',
            price=Decimal('15.00')
        )
        
        self.order_item2 = OrderItem.objects.create(
            order=self.order,
            product=self.product2,
            quantity=3,
            unit='kg',
            price=Decimal('25.00')
        )
    
    def test_complete_invoice_lifecycle(self):
        """Test complete invoice lifecycle from order to payment"""
        # Step 1: Create invoice from order
        total_order_value = (10 * Decimal('15.00')) + (3 * Decimal('25.00'))  # 150 + 75 = 225
        
        invoice = Invoice.objects.create(
            order=self.order,
            customer=self.user,
            subtotal=total_order_value,
            payment_terms='Net 15'
        )
        
        # Step 2: Create invoice items from order items
        invoice_item1 = InvoiceItem.objects.create(
            invoice=invoice,
            order_item=self.order_item1,
            product_name=self.product1.name,
            quantity=self.order_item1.quantity,
            unit_price=self.order_item1.price
        )
        
        invoice_item2 = InvoiceItem.objects.create(
            invoice=invoice,
            order_item=self.order_item2,
            product_name=self.product2.name,
            quantity=self.order_item2.quantity,
            unit_price=self.order_item2.price
        )
        
        # Step 3: Verify invoice calculations
        expected_tax = total_order_value * (Decimal('15.00') / 100)  # 15% VAT
        expected_total = total_order_value + expected_tax
        
        self.assertEqual(invoice.subtotal, total_order_value)
        self.assertEqual(invoice.tax_amount, expected_tax)
        self.assertEqual(invoice.total_amount, expected_total)
        self.assertEqual(invoice.balance_due, expected_total)
        
        # Step 4: Process payment
        payment = Payment.objects.create(
            invoice=invoice,
            amount=expected_total,
            payment_method='bank_transfer',
            payment_date=date.today(),
            reference_number='TXN123456'
        )
        
        # Update invoice
        invoice.amount_paid = expected_total
        invoice.status = 'paid'
        invoice.paid_date = date.today()
        invoice.save()
        
        # Step 5: Verify final state
        self.assertEqual(invoice.balance_due, Decimal('0.00'))
        self.assertEqual(invoice.status, 'paid')
        self.assertFalse(invoice.is_overdue)
        
        # Verify relationships
        self.assertEqual(invoice.items.count(), 2)
        self.assertEqual(invoice.payments.count(), 1)
        self.assertEqual(invoice.order, self.order)
    
    def test_invoice_with_discount_and_credit_note(self):
        """Test invoice with discount and subsequent credit note"""
        # Create invoice with discount
        invoice = Invoice.objects.create(
            customer=self.user,
            subtotal=Decimal('200.00'),
            discount_amount=Decimal('20.00'),  # 10% discount
            status='paid'
        )
        
        # Verify calculations with discount
        expected_tax = (Decimal('200.00') - Decimal('20.00')) * (Decimal('15.00') / 100)
        expected_total = Decimal('200.00') - Decimal('20.00') + expected_tax
        
        self.assertEqual(invoice.tax_amount, expected_tax)
        self.assertEqual(invoice.total_amount, expected_total)
        
        # Create credit note for partial return
        credit_note = CreditNote.objects.create(
            invoice=invoice,
            amount=Decimal('30.00'),
            reason='return',
            description='Customer returned damaged items',
            credit_date=date.today()
        )
        
        # Verify credit note
        self.assertEqual(credit_note.invoice, invoice)
        self.assertEqual(invoice.credit_notes.count(), 1)
        self.assertIsNotNone(credit_note.credit_note_number)
