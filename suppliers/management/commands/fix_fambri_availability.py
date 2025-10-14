from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q
from decimal import Decimal

from suppliers.models import Supplier, SupplierProduct


class Command(BaseCommand):
    help = 'Fix Fambri supplier products that are marked as unavailable or have zero stock'

    def add_arguments(self, parser):
        parser.add_argument(
            '--product',
            type=str,
            help='Specific product name to fix (optional - fixes all if not provided)',
        )
        parser.add_argument(
            '--stock',
            type=int,
            default=100,
            help='Stock quantity to set (default: 100)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without making changes',
        )

    def handle(self, *args, **options):
        product_name = options.get('product')
        stock_quantity = options['stock']
        dry_run = options['dry_run']
        
        self.stdout.write(self.style.SUCCESS(f'🔧 {"DRY RUN: " if dry_run else ""}Fixing Fambri supplier availability'))
        
        # Find Fambri supplier
        fambri = Supplier.objects.filter(name__icontains='fambri').first()
        if not fambri:
            self.stdout.write(self.style.ERROR('❌ Fambri supplier not found!'))
            return
        
        self.stdout.write(f'Found Fambri supplier: {fambri.name} (ID: {fambri.id})')
        
        # Build query for supplier products to fix
        query = SupplierProduct.objects.filter(supplier=fambri)
        
        if product_name:
            query = query.filter(product__name=product_name)
            self.stdout.write(f'Targeting specific product: {product_name}')
        
        # Find problematic supplier products
        problematic_products = query.filter(
            Q(is_available=False) | Q(stock_quantity__lte=0)
        ).select_related('product')
        
        total_count = problematic_products.count()
        
        if total_count == 0:
            self.stdout.write(self.style.SUCCESS('✅ No problematic Fambri supplier products found!'))
            return
        
        self.stdout.write(f'\nFound {total_count} Fambri supplier products to fix:')
        
        # Show what will be changed
        for sp in problematic_products:
            issues = []
            if not sp.is_available:
                issues.append('not available')
            if sp.stock_quantity <= 0:
                issues.append(f'zero stock ({sp.stock_quantity})')
            
            self.stdout.write(f'  • {sp.product.name}: {", ".join(issues)}')
        
        if not dry_run:
            confirm = input(f'\nFix {total_count} Fambri supplier products? (yes/no): ').lower()
            if confirm != 'yes':
                self.stdout.write(self.style.ERROR('❌ Operation cancelled.'))
                return
            
            # Apply fixes
            with transaction.atomic():
                updated_count = 0
                
                for sp in problematic_products:
                    old_available = sp.is_available
                    old_stock = sp.stock_quantity
                    
                    sp.is_available = True
                    if sp.stock_quantity <= 0:
                        sp.stock_quantity = stock_quantity
                    sp.save()
                    
                    self.stdout.write(f'  ✅ {sp.product.name}:')
                    if not old_available:
                        self.stdout.write(f'    Available: {old_available} → True')
                    if old_stock <= 0:
                        self.stdout.write(f'    Stock: {old_stock} → {sp.stock_quantity}')
                    
                    updated_count += 1
                
                self.stdout.write(self.style.SUCCESS(f'\n🎉 Successfully updated {updated_count} Fambri supplier products!'))
        else:
            self.stdout.write(self.style.WARNING('\n🔍 DRY RUN COMPLETE - No changes made'))
        
        self.stdout.write(f'\n📊 Summary:')
        self.stdout.write(f'   • Fambri supplier: {fambri.name}')
        self.stdout.write(f'   • Products to fix: {total_count}')
        self.stdout.write(f'   • Target stock level: {stock_quantity}')
        
        self.stdout.write(self.style.SUCCESS('\n✅ Command completed!'))
