"""
Sync supplier-product relationships based on ACTUAL invoice data
This uses real purchase history to assign products to suppliers intelligently

Usage: python manage.py sync_suppliers_from_invoices --invoice-data data/supplier_pricing_data.json
"""

import json
import re
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from suppliers.models import Supplier, SupplierProduct
from products.models import Product

# Optional fuzzy matching - fallback to simple string matching if not available
try:
    from fuzzywuzzy import fuzz
    FUZZY_AVAILABLE = True
except ImportError:
    FUZZY_AVAILABLE = False
    def fuzz_ratio(a, b):
        """Simple fallback fuzzy matching"""
        a, b = a.lower(), b.lower()
        if a == b:
            return 100
        elif a in b or b in a:
            return 80
        else:
            # Simple word overlap scoring
            words_a = set(a.split())
            words_b = set(b.split())
            overlap = len(words_a & words_b)
            total = len(words_a | words_b)
            return int((overlap / total) * 100) if total > 0 else 0


class Command(BaseCommand):
    help = 'Sync supplier-product relationships based on actual invoice data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--invoice-data',
            type=str,
            default='data/supplier_pricing_data.json',
            help='Path to invoice data JSON file'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes'
        )
        parser.add_argument(
            '--match-threshold',
            type=int,
            default=80,
            help='Fuzzy matching threshold (0-100)'
        )

    def handle(self, *args, **options):
        invoice_file = options['invoice_data']
        dry_run = options['dry_run']
        threshold = options['match_threshold']
        
        self.stdout.write(f'🔍 Loading invoice data from {invoice_file}...')
        
        try:
            with open(invoice_file, 'r') as f:
                invoice_data = json.load(f)
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'❌ Invoice file not found: {invoice_file}'))
            return
        except json.JSONDecodeError as e:
            self.stdout.write(self.style.ERROR(f'❌ Invalid JSON: {e}'))
            return
        
        self.stdout.write(f'✅ Loaded invoice data for {len(invoice_data["suppliers"])} suppliers')
        
        # Process each supplier's invoices
        total_matches = 0
        supplier_stats = {}
        
        for supplier_key, supplier_info in invoice_data['suppliers'].items():
            supplier_name = supplier_info['supplier_name']
            
            self.stdout.write(f'\n🏢 Processing {supplier_name}...')
            
            # Get or create supplier
            supplier, created = Supplier.objects.get_or_create(
                name=supplier_name,
                defaults={'is_active': True}
            )
            
            if created and not dry_run:
                self.stdout.write(f'   ➕ Created new supplier: {supplier_name}')
            
            # Extract all products from invoices
            invoice_products = {}
            
            for invoice_date, invoice in supplier_info.get('invoices', {}).items():
                for product_key, product_data in invoice.get('products', {}).items():
                    description = product_data['description']
                    unit_price = product_data.get('unit_price', 0)
                    unit_type = product_data.get('unit_type', 'each')
                    price_per_kg = product_data.get('price_per_kg', product_data.get('estimated_price_per_kg', 0))
                    
                    # Store product info (use latest price if multiple invoices)
                    invoice_products[description] = {
                        'unit_price': unit_price,
                        'unit_type': unit_type,
                        'price_per_kg': price_per_kg,
                        'last_seen': invoice_date
                    }
            
            # Match invoice products to database products
            matches = self._match_products_to_database(invoice_products, threshold)
            
            supplier_stats[supplier_name] = {
                'invoice_products': len(invoice_products),
                'matched_products': len(matches),
                'match_rate': len(matches) / len(invoice_products) * 100 if invoice_products else 0
            }
            
            # Create/update supplier products
            if not dry_run:
                with transaction.atomic():
                    for db_product, invoice_info in matches:
                        supplier_product, created = SupplierProduct.objects.get_or_create(
                            supplier=supplier,
                            product=db_product,
                            defaults={
                                'supplier_price': Decimal(str(invoice_info['unit_price'])),
                                'is_available': True,
                                'stock_quantity': 100,  # Default stock
                                'lead_time_days': 1,
                                'quality_rating': Decimal('4.0')
                            }
                        )
                        
                        # Update existing with latest invoice data
                        if not created:
                            supplier_product.supplier_price = Decimal(str(invoice_info['unit_price']))
                            supplier_product.is_available = True
                            supplier_product.save()
                        
                        action = "Created" if created else "Updated"
                        self.stdout.write(f'   {action}: {db_product.name} → R{invoice_info["unit_price"]}')
            else:
                # Dry run - just show matches
                for db_product, invoice_info in matches:
                    self.stdout.write(f'   ✓ Would match: {db_product.name} → R{invoice_info["unit_price"]}')
            
            total_matches += len(matches)
            self.stdout.write(f'   📊 {len(matches)}/{len(invoice_products)} products matched ({supplier_stats[supplier_name]["match_rate"]:.1f}%)')
        
        # Summary
        self.stdout.write(f'\n📋 SUMMARY:')
        self.stdout.write(f'   Total product matches: {total_matches}')
        
        for supplier_name, stats in supplier_stats.items():
            self.stdout.write(f'   • {supplier_name}: {stats["matched_products"]}/{stats["invoice_products"]} ({stats["match_rate"]:.1f}%)')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('🔍 DRY RUN - No changes made. Remove --dry-run to apply changes.'))
        else:
            self.stdout.write(self.style.SUCCESS('✅ Supplier-product relationships updated based on invoice data!'))
    
    def _match_products_to_database(self, invoice_products, threshold):
        """Match invoice product descriptions to database products using fuzzy matching"""
        db_products = list(Product.objects.all())
        matches = []
        
        for description, invoice_info in invoice_products.items():
            best_match = None
            best_score = 0
            
            # Clean description for better matching
            clean_desc = self._clean_description(description)
            
            for db_product in db_products:
                # Try exact name match first
                if db_product.name.lower() == clean_desc.lower():
                    best_match = db_product
                    best_score = 100
                    break
                
                # Fuzzy match on name
                if FUZZY_AVAILABLE:
                    name_score = fuzz.ratio(clean_desc.lower(), db_product.name.lower())
                else:
                    name_score = fuzz_ratio(clean_desc.lower(), db_product.name.lower())
                
                # Bonus for partial matches
                if clean_desc.lower() in db_product.name.lower() or db_product.name.lower() in clean_desc.lower():
                    name_score += 10
                
                # Check for keyword matches
                clean_words = clean_desc.lower().split()
                product_words = db_product.name.lower().split()
                common_words = set(clean_words) & set(product_words)
                if common_words:
                    name_score += len(common_words) * 5
                
                if name_score > best_score:
                    best_score = name_score
                    best_match = db_product
            
            # Accept match if above threshold
            if best_match and best_score >= threshold:
                matches.append((best_match, invoice_info))
                self.stdout.write(f'      Match: "{description}" → "{best_match.name}" (score: {best_score})')
            else:
                self.stdout.write(f'      ❌ No match: "{description}" (best: {best_score})')
        
        return matches
    
    def _clean_description(self, description):
        """Clean product description for better matching"""
        # Remove common suffixes/prefixes
        clean = description
        clean = re.sub(r'\s*-\s*(Large|Small|YA)\s*$', '', clean, flags=re.IGNORECASE)
        clean = re.sub(r'\s*\(.*?\)\s*', '', clean)  # Remove parentheses content
        clean = re.sub(r'\s*\d+(\.\d+)?\s*(kg|KG|g|G)\s*', '', clean)  # Remove weights
        clean = re.sub(r'\s*\d+\s*(pack|packed|cater|box|BOX)\s*$', '', clean, flags=re.IGNORECASE)
        clean = re.sub(r'\s+', ' ', clean).strip()  # Normalize whitespace
        
        return clean
