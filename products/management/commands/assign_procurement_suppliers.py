"""
Intelligently assign procurement suppliers to products based on business rules
Usage: python manage.py assign_procurement_suppliers --products-file production_products.json
"""

import json
from django.core.management.base import BaseCommand
from django.db import transaction
from suppliers.models import Supplier
from products.models import Product, Department


class Command(BaseCommand):
    help = 'Assign procurement suppliers to products based on business rules'

    def add_arguments(self, parser):
        parser.add_argument(
            '--products-file',
            type=str,
            help='JSON file with production products (optional - can work with current DB)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show assignments without making changes'
        )
        parser.add_argument(
            '--force-reassign',
            action='store_true',
            help='Reassign even if product already has a procurement supplier'
        )

    def handle(self, *args, **options):
        products_file = options.get('products_file')
        dry_run = options['dry_run']
        force_reassign = options['force_reassign']
        
        self.stdout.write('🎯 Smart Procurement Supplier Assignment')
        self.stdout.write('=' * 50)
        
        # Load suppliers with business rules
        suppliers = self._load_suppliers()
        if not suppliers:
            self.stdout.write(self.style.ERROR('❌ No suppliers found. Please create suppliers first.'))
            return
        
        # Get products to process
        if products_file:
            products = self._load_products_from_file(products_file)
        else:
            products = list(Product.objects.select_related('department').all())
        
        self.stdout.write(f'📦 Processing {len(products)} products...')
        
        # Apply business rules
        assignments = self._apply_business_rules(products, suppliers, force_reassign)
        
        # Show results
        self._show_assignment_summary(assignments)
        
        # Apply changes
        if not dry_run:
            self._apply_assignments(assignments)
            self.stdout.write(self.style.SUCCESS('✅ Assignments completed!'))
        else:
            self.stdout.write(self.style.WARNING('🔍 DRY RUN - No changes made. Remove --dry-run to apply.'))

    def _load_suppliers(self):
        """Load suppliers and define business rules"""
        suppliers = {}
        
        # Define supplier business rules
        supplier_rules = {
            'Tshwane Market': {
                'allowed_departments': ['Fruits', 'Vegetables'],
                'keywords': ['apple', 'banana', 'avocado', 'orange', 'grape', 'carrot', 'onion', 'potato', 'tomato', 'pepper'],
                'priority': 10
            },
            'Reese Mushrooms': {
                'allowed_departments': ['Mushrooms'],
                'keywords': ['mushroom', 'portabellini', 'button', 'brown', 'oyster', 'shiitake'],
                'priority': 20
            },
            'Rooted (Pty) Ltd': {
                'allowed_departments': ['Vegetables', 'Herbs & Spices'],
                'keywords': ['lettuce', 'mixed lettuce', 'micro herbs', 'herbs', 'salad', 'greens'],
                'priority': 15
            },
            'Prudence AgriBusiness': {
                'allowed_departments': ['Herbs & Spices', 'Vegetables'],
                'keywords': ['spinach', 'rocket', 'basil', 'parsley', 'coriander', 'chives', 'dill'],
                'priority': 12
            }
        }
        
        # Load actual suppliers from database
        for supplier_name, rules in supplier_rules.items():
            try:
                supplier = Supplier.objects.get(name=supplier_name)
                suppliers[supplier_name] = {
                    'supplier': supplier,
                    'rules': rules
                }
                self.stdout.write(f'✅ Loaded supplier: {supplier_name}')
            except Supplier.DoesNotExist:
                self.stdout.write(f'⚠️  Supplier not found: {supplier_name} - skipping')
        
        return suppliers

    def _load_products_from_file(self, filename):
        """Load products from production export file"""
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
            
            products = []
            for product_data in data.get('products', []):
                # Create product objects from JSON data
                try:
                    department = Department.objects.get(name=product_data.get('department_name'))
                    product = Product(
                        id=product_data['id'],
                        name=product_data['name'],
                        department=department,
                        unit=product_data['unit']
                    )
                    products.append(product)
                except Department.DoesNotExist:
                    self.stdout.write(f'⚠️  Department not found for product: {product_data["name"]}')
            
            self.stdout.write(f'📂 Loaded {len(products)} products from {filename}')
            return products
            
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'❌ File not found: {filename}'))
            return []
        except json.JSONDecodeError as e:
            self.stdout.write(self.style.ERROR(f'❌ Invalid JSON: {e}'))
            return []

    def _apply_business_rules(self, products, suppliers, force_reassign):
        """Apply intelligent business rules to assign suppliers"""
        assignments = {
            'assigned': [],
            'no_match': [],
            'fambri_garden': [],
            'already_assigned': [],
            'department_mismatch': []
        }
        
        for product in products:
            # Skip if already assigned (unless force reassign)
            if hasattr(product, 'procurement_supplier') and product.procurement_supplier and not force_reassign:
                assignments['already_assigned'].append({
                    'product': product,
                    'current_supplier': product.procurement_supplier.name
                })
                continue
            
            # Check for Fambri garden products (these stay NULL)
            if self._is_fambri_garden_product(product):
                assignments['fambri_garden'].append({
                    'product': product,
                    'reason': 'Fambri garden product - no procurement needed'
                })
                continue
            
            # Find best supplier match
            best_match = self._find_best_supplier_match(product, suppliers)
            
            if best_match:
                assignments['assigned'].append({
                    'product': product,
                    'supplier': best_match['supplier'],
                    'reason': best_match['reason'],
                    'confidence': best_match['confidence']
                })
            else:
                assignments['no_match'].append({
                    'product': product,
                    'department': product.department.name if product.department else 'Unknown'
                })
        
        return assignments

    def _is_fambri_garden_product(self, product):
        """Check if product is grown in Fambri garden (no procurement needed)"""
        garden_keywords = [
            'microgreens', 'micro greens', 'baby spinach', 'baby lettuce',
            'herbs (fresh)', 'garden herbs', 'homegrown', 'fambri grown'
        ]
        
        product_name = product.name.lower()
        return any(keyword in product_name for keyword in garden_keywords)

    def _find_best_supplier_match(self, product, suppliers):
        """Find the best supplier match for a product"""
        if not product.department:
            return None
        
        matches = []
        product_name = product.name.lower()
        department_name = product.department.name
        
        for supplier_name, supplier_info in suppliers.items():
            supplier = supplier_info['supplier']
            rules = supplier_info['rules']
            
            # Check department compatibility
            if department_name not in rules['allowed_departments']:
                continue
            
            # Calculate match score
            score = 0
            
            # Keyword matching
            keyword_matches = sum(1 for keyword in rules['keywords'] if keyword in product_name)
            if keyword_matches > 0:
                score += keyword_matches * 20
            
            # Department exact match bonus
            if department_name in rules['allowed_departments']:
                score += 10
            
            # Supplier priority
            score += rules['priority']
            
            if score > 0:
                matches.append({
                    'supplier': supplier,
                    'score': score,
                    'reason': f'Keywords: {keyword_matches}, Dept: {department_name}',
                    'confidence': min(100, score * 2)  # Convert to percentage
                })
        
        # Return best match
        if matches:
            best = max(matches, key=lambda x: x['score'])
            return best
        
        return None

    def _show_assignment_summary(self, assignments):
        """Show summary of assignments"""
        self.stdout.write('\n📊 ASSIGNMENT SUMMARY:')
        self.stdout.write('=' * 30)
        
        # Assigned
        if assignments['assigned']:
            self.stdout.write(f'\n✅ TO BE ASSIGNED ({len(assignments["assigned"])}):')
            for item in assignments['assigned'][:10]:  # Show first 10
                confidence = item['confidence']
                color = self.style.SUCCESS if confidence >= 80 else self.style.WARNING
                self.stdout.write(color(
                    f'   • {item["product"].name} → {item["supplier"].name} '
                    f'({confidence}% confidence)'
                ))
            if len(assignments['assigned']) > 10:
                self.stdout.write(f'   ... and {len(assignments["assigned"]) - 10} more')
        
        # Fambri garden
        if assignments['fambri_garden']:
            self.stdout.write(f'\n🌱 FAMBRI GARDEN - NO PROCUREMENT ({len(assignments["fambri_garden"])}):')
            for item in assignments['fambri_garden'][:5]:
                self.stdout.write(f'   • {item["product"].name} - {item["reason"]}')
        
        # Already assigned
        if assignments['already_assigned']:
            self.stdout.write(f'\n⏸️  ALREADY ASSIGNED ({len(assignments["already_assigned"])}):')
            for item in assignments['already_assigned'][:5]:
                self.stdout.write(f'   • {item["product"].name} → {item["current_supplier"]}')
        
        # No match
        if assignments['no_match']:
            self.stdout.write(f'\n❓ NO MATCH FOUND ({len(assignments["no_match"])}):')
            for item in assignments['no_match'][:5]:
                self.stdout.write(f'   • {item["product"].name} ({item["department"]})')

    def _apply_assignments(self, assignments):
        """Apply the assignments to the database"""
        with transaction.atomic():
            # Apply assignments
            for item in assignments['assigned']:
                try:
                    # Handle both file-loaded and DB products
                    if hasattr(item['product'], 'id') and item['product'].id:
                        product = Product.objects.get(id=item['product'].id)
                    else:
                        product = Product.objects.get(name=item['product'].name)
                    
                    product.procurement_supplier = item['supplier']
                    product.save(update_fields=['procurement_supplier'])
                    
                except Product.DoesNotExist:
                    self.stdout.write(f'⚠️  Product not found in DB: {item["product"].name}')
            
            # Set Fambri garden products to NULL (explicit)
            for item in assignments['fambri_garden']:
                try:
                    if hasattr(item['product'], 'id') and item['product'].id:
                        product = Product.objects.get(id=item['product'].id)
                    else:
                        product = Product.objects.get(name=item['product'].name)
                    
                    product.procurement_supplier = None
                    product.save(update_fields=['procurement_supplier'])
                    
                except Product.DoesNotExist:
                    self.stdout.write(f'⚠️  Product not found in DB: {item["product"].name}')
        
        self.stdout.write(f'💾 Applied {len(assignments["assigned"])} supplier assignments')
        self.stdout.write(f'🌱 Set {len(assignments["fambri_garden"])} products as Fambri garden (no procurement)')
