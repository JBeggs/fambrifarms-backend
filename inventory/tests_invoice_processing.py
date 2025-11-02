"""
Tests for Invoice Processing and Product Matching System
"""

from django.test import TestCase
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model
from decimal import Decimal
from datetime import date

from .models import InvoicePhoto, ExtractedInvoiceData, SupplierProductMapping
from .product_matching_service import ProductMatchingService
from products.models import Product, Department
from suppliers.models import Supplier
from procurement.models import PurchaseOrder, PurchaseOrderItem

User = get_user_model()


class ProductMatchingServiceTest(TestCase):
    """Test product matching with caching"""
    
    def setUp(self):
        self.user = User.objects.create_user(email='test@example.com', password='testpass')
        self.supplier = Supplier.objects.create(
            name='Tshwane Market',
            email='market@example.com'
        )
        self.department = Department.objects.create(name='Fruit')
        
        # Create test products
        self.products = [
            Product.objects.create(
                name='Sweet Melons',
                department=self.department,
                price=Decimal('30.00'),
                unit='kg'
            ),
            Product.objects.create(
                name='Watermelon',
                department=self.department,
                price=Decimal('25.00'),
                unit='kg'
            ),
            Product.objects.create(
                name='Potatoes',
                department=Department.objects.create(name='Vegetables'),
                price=Decimal('15.00'),
                unit='kg'
            ),
        ]
        
        self.service = ProductMatchingService()
    
    def test_get_all_products_caching(self):
        """Test that products are cached correctly"""
        # First call - should query database
        products1 = self.service.get_all_products()
        self.assertEqual(len(products1), 3)
        
        # Second call - should use cache
        products2 = self.service.get_all_products()
        self.assertEqual(len(products2), 3)
        self.assertIs(products1, products2)  # Same object reference
    
    def test_cache_invalidation(self):
        """Test cache invalidation"""
        products1 = self.service.get_all_products()
        self.assertEqual(len(products1), 3)
        
        # Invalidate cache
        self.service.invalidate_cache()
        
        # Create new product
        Product.objects.create(
            name='Tomatoes',
            department=self.department,
            price=Decimal('20.00'),
            unit='kg'
        )
        
        # Should get updated list
        products2 = self.service.get_all_products()
        self.assertEqual(len(products2), 4)
    
    def test_suggest_product_match_with_previous_mapping(self):
        """Test product suggestions with previous mapping"""
        # Create a previous mapping
        mapping = SupplierProductMapping.objects.create(
            supplier=self.supplier,
            supplier_product_description='Sweet Melons',
            our_product=self.products[0],
            pricing_strategy='per_kg',
            created_by=self.user,
            times_used=5
        )
        
        suggestions = self.service.suggest_product_match(
            supplier=self.supplier,
            description='Sweet Melons'
        )
        
        # Should have suggestions
        self.assertGreater(len(suggestions), 0)
        
        # First suggestion should be the mapped product with high confidence
        self.assertEqual(suggestions[0]['product_id'], self.products[0].id)
        self.assertEqual(suggestions[0]['confidence'], 0.95)
        self.assertEqual(suggestions[0]['reason'], 'Previously mapped for this supplier')
        self.assertEqual(suggestions[0]['times_used'], 5)
    
    def test_suggest_product_match_fuzzy(self):
        """Test fuzzy product matching"""
        suggestions = self.service.suggest_product_match(
            supplier=self.supplier,
            description='potato mondial'
        )
        
        # Should find potatoes
        potato_suggestions = [s for s in suggestions if 'Potato' in s['product_name']]
        self.assertGreater(len(potato_suggestions), 0)
    
    def test_record_mapping_usage(self):
        """Test recording mapping usage"""
        mapping = SupplierProductMapping.objects.create(
            supplier=self.supplier,
            supplier_product_description='Sweet Melons',
            our_product=self.products[0],
            pricing_strategy='per_kg',
            created_by=self.user,
            times_used=0,
            confidence_score=Decimal('1.00')
        )
        
        # Record usage with weight
        self.service.record_mapping_usage(mapping, actual_weight_kg=Decimal('19.5'))
        
        # Refresh from database
        mapping.refresh_from_db()
        
        self.assertEqual(mapping.times_used, 1)
        self.assertIsNotNone(mapping.last_used)
        self.assertEqual(mapping.average_weight_kg, Decimal('19.5'))
    
    def test_create_or_update_mapping(self):
        """Test creating/updating mappings"""
        # Create new mapping
        mapping = self.service.create_or_update_mapping(
            supplier=self.supplier,
            supplier_product_description='Sweet Melons',
            our_product=self.products[0],
            pricing_strategy='per_kg',
            created_by=self.user,
            package_size_kg=Decimal('10.0')
        )
        
        self.assertEqual(mapping.supplier, self.supplier)
        self.assertEqual(mapping.our_product, self.products[0])
        self.assertEqual(mapping.pricing_strategy, 'per_kg')
        self.assertEqual(mapping.package_size_kg, Decimal('10.0'))


class BulkInvoiceUploadAPITest(APITestCase):
    """Test bulk invoice upload API endpoint"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='api_test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        
        self.supplier = Supplier.objects.create(
            name='Tshwane Market',
            email='market@example.com'
        )
        self.department = Department.objects.create(name='Fruit')
        self.product = Product.objects.create(
            name='Sweet Melons',
            department=self.department,
            price=Decimal('30.00'),
            unit='kg'
        )
    
    def test_bulk_upload_success(self):
        """Test successful bulk invoice upload"""
        url = reverse('upload-invoice-with-extracted-data')
        data = {
            'supplier_id': self.supplier.id,
            'invoice_date': '2025-10-07',
            'receipt_number': '4655A061',
            'notes': 'Test import',
            'extracted_items': [
                {
                    'line_number': 1,
                    'product_description': 'Sweet Melons',
                    'quantity': 2,
                    'unit': 'each',
                    'unit_price': 300.00,
                    'line_total': 600.00,
                    'actual_weight_kg': 19.5,
                },
                {
                    'line_number': 2,
                    'product_description': 'Papinos',
                    'quantity': 1,
                    'unit': 'pack',
                    'unit_price': 96.00,
                    'line_total': 96.00,
                    'actual_weight_kg': 7.4,
                },
            ]
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], 'success')
        self.assertEqual(response.data['items_created'], 2)
        self.assertEqual(response.data['invoice_status'], 'extracted')
        
        # Verify database records
        invoice = InvoicePhoto.objects.get(id=response.data['invoice_id'])
        self.assertEqual(invoice.supplier, self.supplier)
        self.assertEqual(str(invoice.invoice_date), '2025-10-07')
        self.assertEqual(invoice.receipt_number, '4655A061')
        self.assertEqual(invoice.status, 'extracted')
        
        # Verify extracted items
        items = invoice.extracted_items.all()
        self.assertEqual(items.count(), 2)
        
        item1 = items.filter(line_number=1).first()
        self.assertEqual(item1.product_description, 'Sweet Melons')
        self.assertEqual(item1.quantity, 2)
        self.assertEqual(item1.actual_weight_kg, Decimal('19.5'))
        self.assertAlmostEqual(float(item1.calculated_cost_per_kg), 30.77, places=2)
    
    def test_bulk_upload_missing_supplier(self):
        """Test bulk upload without supplier fails"""
        url = reverse('upload-invoice-with-extracted-data')
        data = {
            'invoice_date': '2025-10-07',
            'extracted_items': []
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('supplier_id', response.data['error'])
    
    def test_bulk_upload_empty_items(self):
        """Test bulk upload with empty items fails"""
        url = reverse('upload-invoice-with-extracted-data')
        data = {
            'supplier_id': self.supplier.id,
            'invoice_date': '2025-10-07',
            'extracted_items': []
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('extracted_items', response.data['error'])
    
    def test_bulk_upload_with_purchase_order(self):
        """Test bulk upload linked to purchase order"""
        # Create a purchase order
        po = PurchaseOrder.objects.create(
            supplier=self.supplier,
            status='sent',
            order_date=timezone.now().date()
        )
        
        url = reverse('upload-invoice-with-extracted-data')
        data = {
            'supplier_id': self.supplier.id,
            'invoice_date': '2025-10-07',
            'purchase_order_id': po.id,
            'extracted_items': [
                {
                    'line_number': 1,
                    'product_description': 'Sweet Melons',
                    'quantity': 2,
                    'unit': 'each',
                    'unit_price': 300.00,
                    'line_total': 600.00,
                },
            ]
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verify purchase order link
        invoice = InvoicePhoto.objects.get(id=response.data['invoice_id'])
        self.assertEqual(invoice.purchase_order, po)


class InvoiceMigrationTest(TestCase):
    """Test that migrations are applied correctly"""
    
    def setUp(self):
        self.user = User.objects.create_user(email='test@example.com', password='testpass')
        self.supplier = Supplier.objects.create(
            name='Test Supplier',
            email='supplier@example.com'
        )
        self.department = Department.objects.create(name='Test')
        self.product = Product.objects.create(
            name='Test Product',
            department=self.department,
            price=Decimal('10.00'),
            unit='kg'
        )
    
    def test_invoice_photo_new_fields(self):
        """Test InvoicePhoto has new fields"""
        po = PurchaseOrder.objects.create(
            supplier=self.supplier,
            status='sent'
        )
        
        invoice = InvoicePhoto.objects.create(
            supplier=self.supplier,
            invoice_date=date.today(),
            uploaded_by=self.user,
            photo=None,
            original_filename='test.json',
            file_size=100,
            purchase_order=po,
            receipt_number='TEST001'
        )
        
        # Verify new fields exist and work
        self.assertEqual(invoice.purchase_order, po)
        self.assertEqual(invoice.receipt_number, 'TEST001')
    
    def test_extracted_invoice_data_new_fields(self):
        """Test ExtractedInvoiceData has new fields"""
        invoice = InvoicePhoto.objects.create(
            supplier=self.supplier,
            invoice_date=date.today(),
            uploaded_by=self.user,
            photo=None,
            original_filename='test.json',
            file_size=100
        )
        
        extracted = ExtractedInvoiceData.objects.create(
            invoice_photo=invoice,
            line_number=1,
            product_description='Test Product',
            quantity=10,
            unit='kg',
            unit_price=Decimal('10.00'),
            line_total=Decimal('100.00'),
            actual_weight_kg=Decimal('12.5'),
            matched_product=self.product,
            pricing_strategy='per_kg',
            calculated_cost_per_kg=Decimal('8.00'),
            has_discrepancy=False
        )
        
        # Verify new fields exist and work
        self.assertEqual(extracted.matched_product, self.product)
        self.assertEqual(extracted.pricing_strategy, 'per_kg')
        self.assertEqual(extracted.calculated_cost_per_kg, Decimal('8.00'))
        self.assertFalse(extracted.has_discrepancy)
    
    def test_supplier_product_mapping_new_fields(self):
        """Test SupplierProductMapping has new fields"""
        mapping = SupplierProductMapping.objects.create(
            supplier=self.supplier,
            supplier_product_description='Test Product',
            our_product=self.product,
            pricing_strategy='per_kg',
            created_by=self.user,
            times_used=5,
            confidence_score=Decimal('0.95'),
            average_weight_kg=Decimal('10.5'),
            last_used=date.today()
        )
        
        # Verify new fields exist and work
        self.assertEqual(mapping.times_used, 5)
        self.assertEqual(mapping.confidence_score, Decimal('0.95'))
        self.assertEqual(mapping.average_weight_kg, Decimal('10.5'))
        self.assertEqual(mapping.last_used, date.today())
    
    def test_product_new_fields(self):
        """Test Product has new supplier cost fields"""
        product = Product.objects.create(
            name='Product with Cost',
            department=self.department,
            price=Decimal('20.00'),
            unit='kg',
            supplier_cost=Decimal('15.00'),
            cost_unit='per_kg',
            last_supplier=self.supplier,
            last_cost_update=date.today()
        )
        
        # Verify new fields exist and work
        self.assertEqual(product.supplier_cost, Decimal('15.00'))
        self.assertEqual(product.cost_unit, 'per_kg')
        self.assertEqual(product.last_supplier, self.supplier)
        self.assertEqual(product.last_cost_update, date.today())


class PartialDeliveryTest(TestCase):
    """Test partial delivery scenario"""
    
    def setUp(self):
        self.user = User.objects.create_user(email='test@example.com', password='testpass')
        self.supplier = Supplier.objects.create(
            name='Test Supplier',
            email='supplier@example.com'
        )
        self.department = Department.objects.create(name='Test')
        self.product = Product.objects.create(
            name='Test Product',
            department=self.department,
            price=Decimal('10.00'),
            unit='kg'
        )
        
        # Create purchase order for 10 units
        self.po = PurchaseOrder.objects.create(
            supplier=self.supplier,
            status='sent',
            total_amount=Decimal('1000.00')
        )
        self.po_item = PurchaseOrderItem.objects.create(
            purchase_order=self.po,
            product=self.product,
            quantity_ordered=10,
            unit_price=Decimal('100.00')
        )
    
    def test_multiple_invoices_same_po(self):
        """Test linking multiple invoices to same PO for partial deliveries"""
        # First invoice - receive 5 units
        invoice1 = InvoicePhoto.objects.create(
            supplier=self.supplier,
            invoice_date=date.today(),
            uploaded_by=self.user,
            photo=None,
            original_filename='invoice1.json',
            file_size=100,
            purchase_order=self.po,
            receipt_number='INV001'
        )
        
        ExtractedInvoiceData.objects.create(
            invoice_photo=invoice1,
            line_number=1,
            product_description='Test Product',
            quantity=5,
            unit='units',
            unit_price=Decimal('100.00'),
            line_total=Decimal('500.00'),
            matched_product=self.product,
            po_item=self.po_item
        )
        
        # Second invoice - receive remaining 5 units
        invoice2 = InvoicePhoto.objects.create(
            supplier=self.supplier,
            invoice_date=date.today(),
            uploaded_by=self.user,
            photo=None,
            original_filename='invoice2.json',
            file_size=100,
            purchase_order=self.po,
            receipt_number='INV002'
        )
        
        ExtractedInvoiceData.objects.create(
            invoice_photo=invoice2,
            line_number=1,
            product_description='Test Product',
            quantity=5,
            unit='units',
            unit_price=Decimal('100.00'),
            line_total=Decimal('500.00'),
            matched_product=self.product,
            po_item=self.po_item
        )
        
        # Verify both invoices link to same PO
        invoices = InvoicePhoto.objects.filter(purchase_order=self.po)
        self.assertEqual(invoices.count(), 2)
        
        # Verify total quantity received
        total_received = sum(
            item.quantity 
            for invoice in invoices 
            for item in invoice.extracted_items.all()
        )
        self.assertEqual(total_received, 10)

