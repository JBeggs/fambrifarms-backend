"""
Django management command to process local supplier invoice JSON and upload to production API
This allows processing invoices locally without direct database access
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
import requests
import json
import os
from pathlib import Path


class Command(BaseCommand):
    help = 'Process local supplier invoice JSON and upload to production API'

    def add_arguments(self, parser):
        parser.add_argument(
            '--json-file',
            type=str,
            required=True,
            help='Path to supplier_pricing_data.json file'
        )
        parser.add_argument(
            '--production-url',
            type=str,
            required=True,
            help='Production API base URL (e.g., https://fambridevops.pythonanywhere.com/api)'
        )
        parser.add_argument(
            '--api-token',
            type=str,
            required=True,
            help='API authentication token'
        )
        parser.add_argument(
            '--supplier',
            type=str,
            help='Process specific supplier only'
        )
        parser.add_argument(
            '--date',
            type=str,
            help='Process specific date only (YYYY-MM-DD)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Test without actually uploading'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🔍 INVOICE PROCESSING TO PRODUCTION API'))
        self.stdout.write('=' * 60)
        
        # Load JSON file
        json_file_path = options['json_file']
        if not os.path.exists(json_file_path):
            raise CommandError(f'JSON file not found: {json_file_path}')
        
        self.stdout.write(f'📄 Loading: {json_file_path}')
        
        with open(json_file_path, 'r') as f:
            json_data = json.load(f)
        
        suppliers_data = json_data.get('suppliers', {})
        self.stdout.write(self.style.SUCCESS(
            f'✅ Found {len(suppliers_data)} suppliers, '
            f'{sum(len(s.get("invoices", {})) for s in suppliers_data.values())} invoices'
        ))
        self.stdout.write('')
        
        # Process each supplier
        total_uploaded = 0
        total_failed = 0
        
        for supplier_key, supplier_data in suppliers_data.items():
            supplier_name = supplier_data.get('supplier_name')
            
            # Skip if filtering by supplier
            if options.get('supplier') and options['supplier'].lower() not in supplier_name.lower():
                continue
            
            self.stdout.write(f'Processing: {supplier_name}')
            
            # Get supplier ID from production
            supplier_id = self.get_supplier_id(
                supplier_name=supplier_name,
                api_url=options['production_url'],
                token=options['api_token']
            )
            
            if not supplier_id:
                self.stdout.write(self.style.ERROR(f'  ❌ Supplier not found in production: {supplier_name}'))
                total_failed += 1
                continue
            
            # Process each invoice
            for invoice_date, invoice_data in supplier_data.get('invoices', {}).items():
                # Skip if filtering by date
                if options.get('date') and options['date'] != invoice_date:
                    continue
                
                receipt_number = invoice_data.get('receipt_number') or invoice_data.get('invoice_number', 'N/A')
                
                # Prepare extracted items
                extracted_items = []
                for line_num, (product_key, product_data) in enumerate(invoice_data.get('products', {}).items(), 1):
                    extracted_items.append({
                        'line_number': line_num,
                        'product_code': product_key,
                        'product_description': product_data.get('description'),
                        'quantity': product_data.get('quantity_purchased'),
                        'unit': product_data.get('unit_type'),
                        'unit_price': product_data.get('unit_price'),
                        'line_total': product_data.get('total_cost'),
                        'actual_weight_kg': product_data.get('actual_weight_kg') or product_data.get('total_weight_kg'),
                    })
                
                # Upload to production
                self.stdout.write(f'  📤 Uploading invoice {receipt_number} ({invoice_date})')
                self.stdout.write(f'     - {len(extracted_items)} line items extracted')
                self.stdout.write(f'     - Total amount: R{invoice_data.get("total_amount", 0):,.2f}')
                
                result = self.upload_to_production_api(
                    supplier_id=supplier_id,
                    invoice_date=invoice_date,
                    receipt_number=receipt_number,
                    extracted_items=extracted_items,
                    api_url=options['production_url'],
                    token=options['api_token'],
                    dry_run=options.get('dry_run', False)
                )
                
                if result['success']:
                    self.stdout.write(self.style.SUCCESS(
                        f'  ✅ Uploaded successfully - Invoice ID: {result.get("invoice_id")}'
                    ))
                    total_uploaded += 1
                else:
                    self.stdout.write(self.style.ERROR(
                        f'  ❌ Failed: {result.get("error")}'
                    ))
                    total_failed += 1
                
                self.stdout.write('')
        
        # Summary
        self.stdout.write('=' * 60)
        self.stdout.write(self.style.SUCCESS(
            f'✅ Completed: {total_uploaded} invoices uploaded'
        ))
        if total_failed > 0:
            self.stdout.write(self.style.ERROR(
                f'❌ Failed: {total_failed} invoices'
            ))
        self.stdout.write('')
    
    def get_supplier_id(self, supplier_name, api_url, token):
        """Get supplier ID from production API"""
        try:
            endpoint = f"{api_url}/suppliers/suppliers/"
            headers = {
                'Authorization': f'Bearer {token}',
            }
            
            response = requests.get(endpoint, headers=headers)
            response.raise_for_status()
            
            suppliers = response.json()
            
            # Find matching supplier
            for supplier in suppliers:
                if supplier_name.lower() in supplier.get('name', '').lower():
                    return supplier.get('id')
            
            return None
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error getting supplier ID: {e}'))
            return None
    
    def upload_to_production_api(self, supplier_id, invoice_date, receipt_number, extracted_items, api_url, token, dry_run):
        """Upload invoice data to production via REST API"""
        if dry_run:
            return {
                'success': True,
                'invoice_id': 'DRY_RUN',
                'message': '[DRY RUN] Would upload invoice'
            }
        
        endpoint = f"{api_url}/inventory/upload-invoice-with-extracted-data/"
        
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
        }
        
        payload = {
            'supplier_id': supplier_id,
            'invoice_date': invoice_date,
            'receipt_number': receipt_number,
            'notes': 'Imported from supplier_pricing_data.json',
            'extracted_items': extracted_items,
        }
        
        try:
            response = requests.post(endpoint, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            return {
                'success': True,
                'invoice_id': data.get('invoice_id'),
                'items_created': data.get('items_created'),
            }
            
        except requests.exceptions.RequestException as e:
            error_msg = str(e)
            if hasattr(e.response, 'text'):
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get('error', error_msg)
                except:
                    error_msg = e.response.text[:200]  # First 200 chars
            
            return {
                'success': False,
                'error': error_msg
            }

