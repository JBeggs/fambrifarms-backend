import json
import os
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from products.models import Product, Department
from suppliers.models import Supplier

class Command(BaseCommand):
    help = 'Assign procurement suppliers to products based on production data and business rules'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--production-file',
            type=str,
            default='production_products.json',
            help='Path to production products JSON file'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be assigned without making changes'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Override existing supplier assignments'
        )

    def handle(self, *args, **options):
        production_file = options['production_file']
        dry_run = options['dry_run']
        force = options['force']
        
        if not os.path.exists(production_file):
            self.stdout.write(
                self.style.ERROR(f'Production file not found: {production_file}')
            )
            return
            
        self.stdout.write("🔄 Loading production products...")
        with open(production_file, 'r') as f:
            data = json.load(f)
            
        # Handle both export format and API format
        if isinstance(data, list):
            # API format - list of products
            production_products = data
        elif isinstance(data, dict) and 'products' in data:
            # Export format - structured object with products list
            production_products = data['products']
        else:
            self.stdout.write(
                self.style.ERROR(f"Unknown file format. Expected list of products or export format.")
            )
            return
            
        self.stdout.write(f"📊 Loaded {len(production_products)} products from production")
        
        # Debug: Show first few products to understand format
        if production_products and len(production_products) > 0:
            self.stdout.write(f"🔍 First product sample: {type(production_products[0])} - {str(production_products[0])[:200]}...")
        else:
            self.stdout.write("⚠️  No products found in file!")
        
        # Load suppliers
        suppliers = self._load_suppliers()
        if not suppliers:
            self.stdout.write(
                self.style.ERROR("No suppliers found. Please ensure suppliers are seeded first.")
            )
            return
            
        # Apply business rules
        assignments = self._apply_business_rules(production_products, suppliers)
        
        if dry_run:
            self._show_dry_run(assignments)
        else:
            self._apply_assignments(assignments, force)

    def _load_suppliers(self):
        """Load and validate suppliers"""
        try:
            suppliers = {
                'tshwane_market': Supplier.objects.get(name__icontains='Tshwane Market'),
                'reese': Supplier.objects.get(name__icontains='Reese'),
                'rooted': Supplier.objects.get(name__icontains='Rooted'),
                'prudence': Supplier.objects.get(name__icontains='Prudence'),
            }
            
            self.stdout.write("✅ Found suppliers:")
            for key, supplier in suppliers.items():
                self.stdout.write(f"  • {key}: {supplier.name}")
                
            return suppliers
            
        except Supplier.DoesNotExist as e:
            self.stdout.write(
                self.style.ERROR(f"Missing supplier: {e}")
            )
            return None

    def _apply_business_rules(self, production_products, suppliers):
        """Apply business rules to assign suppliers"""
        assignments = {
            'tshwane_market': [],
            'reese': [],
            'rooted': [],
            'prudence': [],
            'fambri_garden': []  # NULL = Fambri garden products
        }
        
        for prod_data in production_products:
            # Handle different data formats
            if isinstance(prod_data, dict):
                dept_name = prod_data.get('department_name', '').lower()
                product_name = prod_data.get('name', '').lower()
            elif isinstance(prod_data, str):
                # If it's just a string (product name), treat as unknown dept
                dept_name = ''
                product_name = prod_data.lower()
                # Convert to dict format for consistency
                prod_data = {
                    'name': prod_data,
                    'department_name': '',
                    'id': None
                }
            else:
                self.stdout.write(f"⚠️  Unknown product format: {type(prod_data)} - {prod_data}")
                continue
            
            # Business Rules
            supplier_key = self._determine_supplier(dept_name, product_name)
            assignments[supplier_key].append({
                'production_data': prod_data,
                'supplier_key': supplier_key,
                'reason': self._get_assignment_reason(dept_name, product_name, supplier_key)
            })
            
        return assignments

    def _determine_supplier(self, dept_name, product_name):
        """Determine supplier based on business rules"""
        
        # Rule 1: Mushrooms -> Reese (specialist)
        if 'mushroom' in dept_name or 'mushroom' in product_name:
            return 'reese'
            
        # Rule 2: Lettuces and Microgreens -> Rooted (specialty greens)
        if ('lettuce' in product_name or 'micro' in product_name or 
            'baby' in product_name or 'salad' in product_name):
            return 'rooted'
            
        # Rule 3: Herbs & Spices -> Prudence (herb specialist)
        if ('herb' in dept_name or 'spice' in dept_name or 
            'basil' in product_name or 'mint' in product_name or 
            'parsley' in product_name or 'coriander' in product_name):
            return 'prudence'
            
        # Rule 4: Fruits and Vegetables -> Tshwane Market (bulk produce)
        if 'fruit' in dept_name or 'vegetable' in dept_name:
            return 'tshwane_market'
            
        # Rule 5: Specialty/Other -> Best match or Fambri garden
        if ('specialty' in dept_name or 'special' in dept_name):
            # For specialty items, try to match based on product characteristics
            if any(word in product_name for word in ['green', 'leaf', 'fresh']):
                return 'rooted'
            elif any(word in product_name for word in ['fruit', 'citrus', 'berry']):
                return 'tshwane_market'
            else:
                return 'fambri_garden'  # NULL = Fambri garden
        
        # Default: Fambri garden (NULL procurement_supplier)
        return 'fambri_garden'

    def _get_assignment_reason(self, dept_name, product_name, supplier_key):
        """Get human-readable reason for assignment"""
        reasons = {
            'reese': 'Mushroom specialist',
            'tshwane_market': 'Bulk fruits & vegetables',
            'rooted': 'Specialty greens & microgreens',
            'prudence': 'Herbs & spices specialist',
            'fambri_garden': 'Fambri garden product (no external procurement)'
        }
        return reasons.get(supplier_key, 'Unknown rule')

    def _show_dry_run(self, assignments):
        """Show what would be assigned without making changes"""
        self.stdout.write("\n" + "="*80)
        self.stdout.write("🔍 DRY RUN - Supplier Assignment Preview")
        self.stdout.write("="*80)
        
        total_products = 0
        for supplier_key, products in assignments.items():
            if not products:
                continue
                
            count = len(products)
            total_products += count
            
            if supplier_key == 'fambri_garden':
                self.stdout.write(f"\n🌱 NULL (Fambri Garden): {count} products")
            else:
                supplier_name = {
                    'tshwane_market': 'Tshwane Market',
                    'reese': 'Reese Mushrooms', 
                    'rooted': 'Rooted (Pty) Ltd',
                    'prudence': 'Prudence Agribusiness'
                }.get(supplier_key, supplier_key)
                self.stdout.write(f"\n🏢 {supplier_name}: {count} products")
            
            # Show first 5 examples
            for i, assignment in enumerate(products[:5]):
                prod = assignment['production_data']
                reason = assignment['reason']
                self.stdout.write(f"  • {prod['name']} ({prod['department_name']}) - {reason}")
                
            if count > 5:
                self.stdout.write(f"  ... and {count - 5} more")
                
        self.stdout.write(f"\n📊 Total products to assign: {total_products}")
        self.stdout.write("\n💡 Use --force to apply these assignments")

    def _apply_assignments(self, assignments, force):
        """Apply supplier assignments to database"""
        self.stdout.write("\n🔄 Applying supplier assignments...")
        
        with transaction.atomic():
            updated_count = 0
            skipped_count = 0
            error_count = 0
            
            for supplier_key, products in assignments.items():
                if not products:
                    continue
                    
                # Get supplier object (None for Fambri garden)
                if supplier_key == 'fambri_garden':
                    supplier_obj = None
                    supplier_name = "NULL (Fambri Garden)"
                else:
                    supplier_mapping = {
                        'tshwane_market': Supplier.objects.get(name__icontains='Tshwane Market'),
                        'reese': Supplier.objects.get(name__icontains='Reese'),
                        'rooted': Supplier.objects.get(name__icontains='Rooted'),
                        'prudence': Supplier.objects.get(name__icontains='Prudence'),
                    }
                    supplier_obj = supplier_mapping[supplier_key]
                    supplier_name = supplier_obj.name
                
                self.stdout.write(f"\n🏢 Assigning to {supplier_name}:")
                
                for assignment in products:
                    prod_data = assignment['production_data']
                    
                    try:
                        # Find ALL local products by name (handle duplicates)
                        local_products = Product.objects.filter(name=prod_data['name'])
                        
                        if not local_products.exists():
                            self.stdout.write(f"  ⚠️  Product not found locally: {prod_data['name']}")
                            error_count += 1
                            continue
                        
                        # Assign supplier to ALL matching products
                        for local_product in local_products:
                            # Check if already assigned
                            if local_product.procurement_supplier and not force:
                                skipped_count += 1
                                continue
                                
                            # Assign supplier
                            local_product.procurement_supplier = supplier_obj
                            local_product.save(update_fields=['procurement_supplier'])
                            
                            updated_count += 1
                        
                        # Show count for this product name
                        assigned_count = local_products.count()
                        if assigned_count == 1:
                            self.stdout.write(f"  ✅ {prod_data['name']}")
                        else:
                            self.stdout.write(f"  ✅ {prod_data['name']} ({assigned_count} variants)")
                        
                    except Exception as e:
                        self.stdout.write(f"  ❌ Error assigning {prod_data['name']}: {e}")
                        error_count += 1
        
        # Summary
        self.stdout.write("\n" + "="*50)
        self.stdout.write("📊 ASSIGNMENT SUMMARY")
        self.stdout.write("="*50)
        self.stdout.write(f"✅ Updated: {updated_count} products")
        self.stdout.write(f"⏭️  Skipped: {skipped_count} products (already assigned)")
        self.stdout.write(f"❌ Errors: {error_count} products")
        
        if updated_count > 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\n🎉 Successfully assigned suppliers to {updated_count} products!"
                )
            )
