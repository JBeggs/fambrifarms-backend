"""
Django management command to process uploaded invoice photos
This command acts as the interface between uploaded photos and the AI OCR (me)
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from inventory.models import InvoicePhoto, ExtractedInvoiceData
from suppliers.models import Supplier
import os


class Command(BaseCommand):
    help = 'Process uploaded invoice photos using AI OCR'

    def add_arguments(self, parser):
        parser.add_argument(
            '--invoice-id',
            type=int,
            help='Process specific invoice photo by ID'
        )
        parser.add_argument(
            '--supplier',
            type=str,
            help='Process all pending invoices for specific supplier'
        )
        parser.add_argument(
            '--date',
            type=str,
            help='Process all invoices for specific date (YYYY-MM-DD)'
        )
        parser.add_argument(
            '--all-pending',
            action='store_true',
            help='Process all pending invoices'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be processed without actually processing'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🔍 INVOICE PROCESSING SYSTEM'))
        self.stdout.write('=' * 60)
        
        # Get invoices to process
        invoices_to_process = self.get_invoices_to_process(options)
        
        if not invoices_to_process:
            self.stdout.write(self.style.WARNING('No invoices found to process'))
            return
        
        self.stdout.write(f'📄 Found {len(invoices_to_process)} invoice(s) to process')
        
        if options['dry_run']:
            self.stdout.write(self.style.WARNING('🔍 DRY RUN MODE - No actual processing'))
            for invoice in invoices_to_process:
                self.stdout.write(f'   Would process: {invoice}')
            return
        
        # Process each invoice
        for invoice in invoices_to_process:
            self.process_single_invoice(invoice)
        
        self.stdout.write(self.style.SUCCESS('✅ Invoice processing complete'))

    def get_invoices_to_process(self, options):
        """Get list of invoices to process based on command options"""
        queryset = InvoicePhoto.objects.filter(status='uploaded')
        
        if options['invoice_id']:
            return queryset.filter(id=options['invoice_id'])
        
        if options['supplier']:
            try:
                supplier = Supplier.objects.get(name__icontains=options['supplier'])
                return queryset.filter(supplier=supplier)
            except Supplier.DoesNotExist:
                raise CommandError(f'Supplier "{options["supplier"]}" not found')
        
        if options['date']:
            return queryset.filter(invoice_date=options['date'])
        
        if options['all_pending']:
            return queryset.all()
        
        # Default: process today's invoices
        today = timezone.now().date()
        return queryset.filter(invoice_date=today)

    def process_single_invoice(self, invoice_photo):
        """Process a single invoice photo"""
        self.stdout.write(f'\\n📄 Processing: {invoice_photo}')
        
        # Update status to processing
        invoice_photo.status = 'processing'
        invoice_photo.save()
        
        try:
            # Check if data already exists
            if invoice_photo.extracted_items.exists():
                self.stdout.write(self.style.WARNING('⚠️  Extracted data already exists for this invoice.'))
                self.stdout.write('   Use the Flutter app to add weights and match products.')
                return
            
            # This is where I (Claude) act as the AI OCR system
            self.stdout.write('🤖 AI OCR PROCESSING REQUIRED')
            self.stdout.write('   I (Claude) need to analyze the invoice image and extract data.')
            
            # Show the invoice details for AI processing
            self.show_ai_ocr_instructions(invoice_photo)
            
            # Create sample data for testing if requested
            if input('\\nCreate sample data for testing? (y/N): ').lower() == 'y':
                self.create_sample_extracted_data(invoice_photo)
                self.stdout.write(self.style.SUCCESS('✅ Created sample extracted data'))
            else:
                self.stdout.write(self.style.WARNING('⏳ Waiting for AI OCR data extraction...'))
                self.stdout.write('   Please provide extracted data via Django admin or API.')
            
            # Update status to extracted (waiting for weight input)
            invoice_photo.status = 'extracted'
            invoice_photo.save()
            
            self.stdout.write(self.style.SUCCESS(f'✅ Invoice ready for weight input: {invoice_photo}'))
            
        except Exception as e:
            # Update status to error
            invoice_photo.status = 'error'
            invoice_photo.notes = f'Processing error: {str(e)}'
            invoice_photo.save()
            
            self.stdout.write(self.style.ERROR(f'❌ Error processing {invoice_photo}: {e}'))

    def show_ai_ocr_instructions(self, invoice_photo):
        """Show instructions for AI (Claude) to process the invoice"""
        self.stdout.write('\\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('🤖 AI OCR PROCESSING INSTRUCTIONS'))
        self.stdout.write('=' * 60)
        self.stdout.write(f'📄 Invoice: {invoice_photo}')
        self.stdout.write(f'📁 File: {invoice_photo.photo.path if invoice_photo.photo else "No file"}')
        self.stdout.write(f'🏢 Supplier: {invoice_photo.supplier.name}')
        self.stdout.write(f'📅 Date: {invoice_photo.invoice_date}')
        self.stdout.write(f'📝 Notes: {invoice_photo.notes or "None"}')
        
        self.stdout.write('\\n🎯 CLAUDE (AI OCR) TASKS:')
        self.stdout.write('   1. 📖 Read the invoice image carefully')
        self.stdout.write('   2. 📝 Extract each line item with:')
        self.stdout.write('      • Product code (if visible)')
        self.stdout.write('      • Product description (exact text)')
        self.stdout.write('      • Quantity (number)')
        self.stdout.write('      • Unit (bag, box, each, kg, etc)')
        self.stdout.write('      • Unit price (R amount)')
        self.stdout.write('      • Line total (R amount)')
        self.stdout.write('   3. ⚠️  DO NOT extract handwritten weights - Karl adds these later')
        self.stdout.write('   4. 💾 Create ExtractedInvoiceData records via Django admin or API')
        
        self.stdout.write('\\n🔧 NEXT WORKFLOW STEPS:')
        self.stdout.write('   1. ✅ AI extracts basic invoice data (YOU)')
        self.stdout.write('   2. ⚖️  Karl adds actual weights via Flutter app')
        self.stdout.write('   3. 🔗 Karl matches products and selects pricing strategy')
        self.stdout.write('   4. 💰 System calculates final pricing and updates inventory')
        
        self.stdout.write('\\n📋 SAMPLE DATA STRUCTURE:')
        self.stdout.write('   ExtractedInvoiceData(')
        self.stdout.write('       invoice_photo=invoice,')
        self.stdout.write('       line_number=1,')
        self.stdout.write('       product_description="Sweet Melons",')
        self.stdout.write('       quantity=2,')
        self.stdout.write('       unit="each",')
        self.stdout.write('       unit_price=300.00,')
        self.stdout.write('       line_total=600.00,')
        self.stdout.write('       actual_weight_kg=None,  # Karl adds this later')
        self.stdout.write('   )')
        
        self.stdout.write('\\n' + '=' * 60)

    def show_ocr_instructions(self, invoice_photo):
        """Show instructions for manual OCR (until AI integration is complete)"""
        self.stdout.write('\\n' + '=' * 60)
        self.stdout.write(self.style.WARNING('📋 MANUAL OCR REQUIRED'))
        self.stdout.write('=' * 60)
        self.stdout.write(f'Invoice: {invoice_photo}')
        self.stdout.write(f'File: {invoice_photo.photo.path if invoice_photo.photo else "No file"}')
        self.stdout.write(f'Supplier: {invoice_photo.supplier.name}')
        self.stdout.write(f'Date: {invoice_photo.invoice_date}')
        
        self.stdout.write('\\n📝 PLEASE EXTRACT THE FOLLOWING DATA:')
        self.stdout.write('   1. Invoice header info (number, date, totals)')
        self.stdout.write('   2. Each line item:')
        self.stdout.write('      - Product code (if visible)')
        self.stdout.write('      - Product description (e.g., "Sweet Melons", "Pear Packhaas Trio")')
        self.stdout.write('      - Quantity (e.g., 2, 1)')
        self.stdout.write('      - Unit (bag, box, each, kg, etc)')
        self.stdout.write('      - Unit price (e.g., R300.00, R144.00)')
        self.stdout.write('      - Line total (e.g., R600.00, R144.00)')
        self.stdout.write('      - 🔍 HANDWRITTEN WEIGHT (e.g., "19.5kg", "11.8kg") - CRITICAL!')
        
        self.stdout.write('\\n🎯 NEXT STEPS:')
        self.stdout.write('   1. Create ExtractedInvoiceData records for each line item')
        self.stdout.write('   2. Include actual_weight_kg from handwritten notes on invoice')
        self.stdout.write('   3. Karl will match products and select pricing strategy')
        self.stdout.write('   4. System will calculate price per kg using: line_total ÷ actual_weight_kg')
        
        self.stdout.write('\\n💡 EXAMPLE COMMAND TO CREATE EXTRACTED DATA:')
        self.stdout.write(f'   python manage.py shell')
        self.stdout.write(f'   from inventory.models import InvoicePhoto, ExtractedInvoiceData')
        self.stdout.write(f'   invoice = InvoicePhoto.objects.get(id={invoice_photo.id})')
        self.stdout.write(f'   ExtractedInvoiceData.objects.create(')
        self.stdout.write(f'       invoice_photo=invoice,')
        self.stdout.write(f'       line_number=1,')
        self.stdout.write(f'       product_description="Product Name",')
        self.stdout.write(f'       quantity=10,')
        self.stdout.write(f'       unit="bag",')
        self.stdout.write(f'       unit_price=50.00,')
        self.stdout.write(f'       line_total=500.00')
        self.stdout.write(f'   )')
        
        self.stdout.write('\\n' + '=' * 60)

    def create_sample_extracted_data(self, invoice_photo):
        """Create sample extracted data for testing - based on real Tshwane Market invoice"""
        sample_items = [
            {
                'line_number': 1,
                'product_code': '',  # Often blank on real invoices
                'product_description': 'Sweet Melons',
                'quantity': 2,
                'unit': 'each',
                'unit_price': 300.00,
                'line_total': 600.00,
                'actual_weight_kg': 19.5,  # Handwritten weight from invoice
            },
            {
                'line_number': 2,
                'product_code': '',
                'product_description': 'Pear Packhaas Trio',
                'quantity': 1,
                'unit': 'pack',
                'unit_price': 144.00,
                'line_total': 144.00,
                'actual_weight_kg': 11.8,  # Handwritten weight from invoice
            },
            {
                'line_number': 3,
                'product_code': '',
                'product_description': 'Papinos',
                'quantity': 1,
                'unit': 'pack',
                'unit_price': 96.00,
                'line_total': 96.00,
                'actual_weight_kg': 7.4,  # Handwritten weight from invoice
            }
        ]
        
        for item_data in sample_items:
            ExtractedInvoiceData.objects.create(
                invoice_photo=invoice_photo,
                **item_data
            )
            self.stdout.write(f'   Created: Line {item_data["line_number"]} - {item_data["product_description"]}')
