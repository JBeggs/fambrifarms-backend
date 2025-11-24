"""
Reorganize products into correct departments based on analysis.

This command will:
1. Move mushrooms from Vegetables to Mushrooms
2. Move herbs from Vegetables to Herbs & Spices
3. Move garlic, ginger, spinach, peppers from Herbs & Spices to Vegetables
4. Move cucumbers, potatoes, pumpkins from Fruits to Vegetables
5. Keep tomatoes in Vegetables (no change)
6. Merge "Herbs" department into "Herbs & Spices"
7. Merge "Special" department into "Specialty Items"

Usage:
    python manage.py reorganize_product_departments --dry-run  # Preview changes
    python manage.py reorganize_product_departments             # Apply changes
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from products.models import Product, Department
from collections import defaultdict


class Command(BaseCommand):
    help = 'Reorganize products into correct departments based on analysis'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview changes without applying them',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed output for each product',
        )

    def get_or_create_department(self, name):
        """Get or create a department by name"""
        dept, created = Department.objects.get_or_create(name=name)
        if created:
            self.stdout.write(self.style.WARNING(f'Created new department: {name}'))
        return dept

    def categorize_product(self, product_name):
        """Categorize a product based on its name"""
        name_lower = product_name.lower()
        
        # Mushroom keywords
        mushroom_keywords = ['mushroom', 'shiitake', 'portobello', 'portabellini', 'oyster', 'enoki', 'maitake', 'reishi', 'champignon', 'button mushroom', 'brown mushroom']
        if any(keyword in name_lower for keyword in mushroom_keywords):
            return 'Mushrooms'
        
        # Herb keywords
        herb_keywords = ['basil', 'cilantro', 'coriander', 'dill', 'mint', 'oregano', 'parsley', 'rosemary', 'sage', 'thyme', 'chive', 'tarragon', 'bay', 'lemongrass']
        if any(keyword in name_lower for keyword in herb_keywords):
            return 'Herbs & Spices'
        
        # Vegetable keywords (garlic, ginger, spinach, peppers)
        vegetable_keywords = ['garlic', 'ginger', 'spinach', 'cucumber', 'potato', 'pumpkin']
        if any(keyword in name_lower for keyword in vegetable_keywords):
            return 'Vegetables'
        
        # Pepper keywords (cayenne, bell pepper, etc.) - but not herbs
        if 'pepper' in name_lower and 'cayenne' in name_lower:
            return 'Vegetables'
        
        return None  # No change needed

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        verbose = options['verbose']
        
        self.stdout.write(self.style.SUCCESS('=' * 80))
        self.stdout.write(self.style.SUCCESS('PRODUCT DEPARTMENT REORGANIZATION'))
        self.stdout.write(self.style.SUCCESS('=' * 80))
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\n🔍 DRY RUN MODE - No changes will be applied\n'))
        else:
            self.stdout.write(self.style.WARNING('\n⚠️  LIVE MODE - Changes will be applied\n'))
        
        # Get all departments (case-insensitive lookup)
        departments = {}
        dept_name_map = {}  # Map lowercase names to actual names
        for dept in Department.objects.all():
            departments[dept.name] = dept
            dept_name_map[dept.name.lower()] = dept.name
        
        # Helper to find department by name (case-insensitive)
        def find_department(name):
            """Find department by name, case-insensitive"""
            name_lower = name.lower()
            if name_lower in dept_name_map:
                actual_name = dept_name_map[name_lower]
                return departments.get(actual_name)
            return None
        
        # Helper to get or create department safely
        def get_dept(name):
            """Get department by name, creating if needed (unless dry-run)"""
            dept = find_department(name)
            if not dept:
                if not dry_run:
                    dept = self.get_or_create_department(name)
                    departments[name] = dept
                    dept_name_map[name.lower()] = name
                else:
                    # For dry-run, check if it exists but with different case
                    for existing_name, existing_dept in departments.items():
                        if existing_name.lower() == name.lower():
                            return existing_dept
                    self.stdout.write(self.style.WARNING(f'Would create department: {name}'))
                    return None
            return dept
        
        # Ensure required departments exist
        required_depts = ['Vegetables', 'Fruits', 'Herbs & Spices', 'Mushrooms', 'Specialty Items']
        for dept_name in required_depts:
            get_dept(dept_name)
        
        # Track changes
        changes = defaultdict(list)
        stats = defaultdict(int)
        
        # 1. Move mushrooms from Vegetables to Mushrooms
        self.stdout.write(self.style.SUCCESS('\n1. Moving mushrooms from Vegetables to Mushrooms...'))
        mushrooms_dept = get_dept('Mushrooms')
        vegetables_dept = get_dept('Vegetables')
        
        if mushrooms_dept and vegetables_dept:
            mushroom_products = Product.objects.filter(department=vegetables_dept)
            mushroom_keywords = ['mushroom', 'shiitake', 'portobello', 'portabellini', 'oyster', 'enoki', 'maitake', 'reishi', 'champignon', 'button mushroom', 'brown mushroom']
            
            for product in mushroom_products:
                name_lower = product.name.lower()
                if any(keyword in name_lower for keyword in mushroom_keywords):
                    if product.department != mushrooms_dept:
                        changes['Vegetables → Mushrooms'].append(product)
                        stats['mushrooms_moved'] += 1
                        if verbose:
                            self.stdout.write(f'  • {product.name} (ID: {product.id})')
        
        # 2. Move herbs from Vegetables to Herbs & Spices
        self.stdout.write(self.style.SUCCESS('\n2. Moving herbs from Vegetables to Herbs & Spices...'))
        herbs_spices_dept = get_dept('Herbs & Spices')
        
        if herbs_spices_dept and vegetables_dept:
            herb_products = Product.objects.filter(department=vegetables_dept)
            herb_keywords = ['basil', 'cilantro', 'coriander', 'dill', 'mint', 'oregano', 'parsley', 'rosemary', 'sage', 'thyme', 'chive', 'tarragon', 'bay', 'lemongrass']
            
            for product in herb_products:
                name_lower = product.name.lower()
                if any(keyword in name_lower for keyword in herb_keywords):
                    if product.department != herbs_spices_dept:
                        changes['Vegetables → Herbs & Spices'].append(product)
                        stats['herbs_moved'] += 1
                        if verbose:
                            self.stdout.write(f'  • {product.name} (ID: {product.id})')
        
        # 3. Move garlic, ginger, spinach, peppers from Herbs & Spices to Vegetables
        self.stdout.write(self.style.SUCCESS('\n3. Moving garlic, ginger, spinach, peppers from Herbs & Spices to Vegetables...'))
        
        if herbs_spices_dept:
            veg_from_herbs = Product.objects.filter(department=herbs_spices_dept)
            veg_keywords = ['garlic', 'ginger', 'spinach', 'pepper']
            
            for product in veg_from_herbs:
                name_lower = product.name.lower()
                # Check for garlic, ginger, spinach, or peppers (but not herb peppers like peppermint)
                if any(keyword in name_lower for keyword in ['garlic', 'ginger', 'spinach']):
                    if product.department != vegetables_dept:
                        changes['Herbs & Spices → Vegetables'].append(product)
                        stats['veg_from_herbs_moved'] += 1
                        if verbose:
                            self.stdout.write(f'  • {product.name} (ID: {product.id})')
                elif 'pepper' in name_lower and 'cayenne' in name_lower:
                    # Cayenne peppers are vegetables
                    if product.department != vegetables_dept:
                        changes['Herbs & Spices → Vegetables'].append(product)
                        stats['veg_from_herbs_moved'] += 1
                        if verbose:
                            self.stdout.write(f'  • {product.name} (ID: {product.id})')
        
        # 4. Move cucumbers, potatoes, pumpkins from Fruits to Vegetables
        self.stdout.write(self.style.SUCCESS('\n4. Moving cucumbers, potatoes, pumpkins from Fruits to Vegetables...'))
        fruits_dept = get_dept('Fruits')
        
        if fruits_dept and vegetables_dept:
            veg_from_fruits = Product.objects.filter(department=fruits_dept)
            veg_keywords = ['cucumber', 'potato', 'pumpkin']
            
            for product in veg_from_fruits:
                name_lower = product.name.lower()
                if any(keyword in name_lower for keyword in veg_keywords):
                    if product.department != vegetables_dept:
                        changes['Fruits → Vegetables'].append(product)
                        stats['veg_from_fruits_moved'] += 1
                        if verbose:
                            self.stdout.write(f'  • {product.name} (ID: {product.id})')
        
        # 5. Merge "Herbs" into "Herbs & Spices"
        self.stdout.write(self.style.SUCCESS('\n5. Merging "Herbs" into "Herbs & Spices"...'))
        herbs_dept = find_department('Herbs')
        
        if herbs_dept and herbs_spices_dept:
            herbs_products = Product.objects.filter(department=herbs_dept)
            for product in herbs_products:
                if product.department != herbs_spices_dept:
                    changes['Herbs → Herbs & Spices'].append(product)
                    stats['herbs_merged'] += 1
                    if verbose:
                        self.stdout.write(f'  • {product.name} (ID: {product.id})')
        
        # 6. Merge "Special" into "Specialty Items"
        self.stdout.write(self.style.SUCCESS('\n6. Merging "Special" into "Specialty Items"...'))
        special_dept = find_department('Special')
        specialty_items_dept = get_dept('Specialty Items')
        
        if special_dept and specialty_items_dept:
            special_products = Product.objects.filter(department=special_dept)
            for product in special_products:
                if product.department != specialty_items_dept:
                    changes['Special → Specialty Items'].append(product)
                    stats['special_merged'] += 1
                    if verbose:
                        self.stdout.write(f'  • {product.name} (ID: {product.id})')
        
        # Print summary
        self.stdout.write(self.style.SUCCESS('\n' + '=' * 80))
        self.stdout.write(self.style.SUCCESS('SUMMARY'))
        self.stdout.write(self.style.SUCCESS('=' * 80))
        
        total_changes = 0
        for category, products in changes.items():
            count = len(products)
            total_changes += count
            self.stdout.write(f'\n{category}: {count} products')
            if verbose and count > 0:
                for product in products[:10]:  # Show first 10
                    self.stdout.write(f'  • {product.name} (ID: {product.id})')
                if count > 10:
                    self.stdout.write(f'  ... and {count - 10} more')
        
        self.stdout.write(self.style.SUCCESS(f'\n\nTotal products to move: {total_changes}'))
        
        # Apply changes if not dry run
        if not dry_run and total_changes > 0:
            self.stdout.write(self.style.WARNING('\nApplying changes...'))
            
            try:
                with transaction.atomic():
                    # Apply all moves
                    for category, products in changes.items():
                        if '→' in category:
                            source, target = category.split(' → ')
                            target_dept = departments.get(target)
                            
                            if target_dept:
                                for product in products:
                                    product.department = target_dept
                                    product.save()
                    
                    # Delete merged departments if empty
                    if herbs_dept:
                        remaining = Product.objects.filter(department=herbs_dept).count()
                        if remaining == 0:
                            herbs_dept.delete()
                            self.stdout.write(self.style.SUCCESS(f'Deleted empty department: Herbs'))
                    
                    if special_dept:
                        remaining = Product.objects.filter(department=special_dept).count()
                        if remaining == 0:
                            special_dept.delete()
                            self.stdout.write(self.style.SUCCESS(f'Deleted empty department: Special'))
                
                self.stdout.write(self.style.SUCCESS('\n✅ All changes applied successfully!'))
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'\n❌ Error applying changes: {str(e)}'))
                raise
        
        elif dry_run:
            self.stdout.write(self.style.WARNING('\n🔍 Dry run complete. Use without --dry-run to apply changes.'))
        else:
            self.stdout.write(self.style.SUCCESS('\n✅ No changes needed.'))

