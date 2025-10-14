from django.core.management.base import BaseCommand
from django.db import transaction
from decimal import Decimal

from products.models import Product, MarketProcurementItem
from suppliers.models import Supplier, SupplierProduct
from products.services import ProcurementIntelligenceService


class Command(BaseCommand):
    help = 'Debug Market Trip pricing for Lemons to find why it shows R70 instead of R100'

    def add_arguments(self, parser):
        parser.add_argument(
            '--product',
            type=str,
            default='Lemons',
            help='Product name to debug (default: Lemons)',
        )

    def handle(self, *args, **options):
        product_name = options['product']
        
        self.stdout.write(self.style.SUCCESS(f'🚛 DEBUGGING MARKET TRIP PRICING FOR {product_name.upper()}'))
        self.stdout.write('=' * 60)
        
        # 1. Find the product
        product = Product.objects.filter(name=product_name).first()
        if not product:
            self.stdout.write(self.style.ERROR(f'❌ {product_name} product not found!'))
            return
            
        self.stdout.write(f"\n1️⃣ PRODUCT INFO:")
        self.stdout.write(f"   ID: {product.id}")
        self.stdout.write(f"   Name: {product.name}")
        self.stdout.write(f"   Base Price: R{product.price}")
        
        # 2. Check Fambri Internal supplier
        fambri = Supplier.objects.filter(name__icontains='fambri').first()
        self.stdout.write(f"\n2️⃣ FAMBRI INTERNAL SUPPLIER:")
        if fambri:
            self.stdout.write(f"   Name: {fambri.name}")
            self.stdout.write(f"   ID: {fambri.id}")
            
            # Check if Fambri supplies this product
            fambri_product = SupplierProduct.objects.filter(supplier=fambri, product=product).first()
            if fambri_product:
                self.stdout.write(self.style.SUCCESS(f"   ✅ Supplies {product_name}: R{fambri_product.supplier_price}"))
                self.stdout.write(f"   Available: {fambri_product.is_available}")
                self.stdout.write(f"   Stock: {fambri_product.stock_quantity}")
                self.stdout.write(f"   Updated: {getattr(fambri_product, 'updated_at', 'N/A')}")
            else:
                self.stdout.write(self.style.ERROR(f"   ❌ Does NOT supply {product_name}"))
        else:
            self.stdout.write(self.style.ERROR(f"   ❌ Fambri supplier not found!"))
        
        # 3. Check all suppliers for this product
        self.stdout.write(f"\n3️⃣ ALL {product_name.upper()} SUPPLIERS:")
        all_suppliers = SupplierProduct.objects.filter(product=product).select_related('supplier')
        if all_suppliers.exists():
            for sp in all_suppliers:
                available_icon = "✅" if sp.is_available else "❌"
                self.stdout.write(f"   {available_icon} {sp.supplier.name}: R{sp.supplier_price} (Stock: {sp.stock_quantity})")
        else:
            self.stdout.write(f"   ❌ No suppliers found for {product_name}")
        
        # 4. Test the actual pricing service
        self.stdout.write(f"\n4️⃣ TESTING PROCUREMENT SERVICE:")
        try:
            service = ProcurementIntelligenceService()
            
            # Test the internal method that calculates market price
            estimated_price = service._get_estimated_market_price(product)
            self.stdout.write(f"   Estimated Market Price: R{estimated_price}")
            
            # Test the fallback calculation
            fallback_price = product.price * Decimal('0.7') if product.price else Decimal('10.00')
            self.stdout.write(f"   Fallback Price (70% of R{product.price}): R{fallback_price}")
            
            # Diagnose the issue
            if estimated_price == Decimal('70.00'):
                self.stdout.write(self.style.ERROR(f"   🚨 USING FALLBACK PRICING! (70% of product price)"))
                self.stdout.write("   REASON: Either no Fambri supplier product, or it's not available/has no stock")
            elif estimated_price == Decimal('100.00'):
                self.stdout.write(self.style.SUCCESS(f"   ✅ Using supplier pricing correctly"))
            else:
                self.stdout.write(self.style.WARNING(f"   🤔 Unexpected price: R{estimated_price}"))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"   ❌ Error testing service: {e}"))
        
        # 5. Check recent market procurement items
        self.stdout.write(f"\n5️⃣ RECENT MARKET PROCUREMENT ITEMS:")
        recent_items = MarketProcurementItem.objects.filter(
            product=product
        ).order_by('-recommendation__created_at')[:3]
        
        if recent_items.exists():
            for item in recent_items:
                self.stdout.write(f"   Date: {item.recommendation.created_at}")
                self.stdout.write(f"   Unit Price: R{item.estimated_unit_price}")
                self.stdout.write(f"   Supplier Unit Price: R{item.supplier_unit_price or 'N/A'}")
                self.stdout.write(f"   Preferred Supplier: {item.preferred_supplier.name if item.preferred_supplier else 'N/A'}")
                self.stdout.write(f"   ---")
        else:
            self.stdout.write(f"   No recent procurement items found for {product_name}")
        
        # 6. Provide recommendations
        self.stdout.write(f"\n6️⃣ RECOMMENDATIONS:")
        if fambri and not SupplierProduct.objects.filter(supplier=fambri, product=product).exists():
            self.stdout.write(self.style.WARNING(f"   • Create Fambri supplier product for {product_name}"))
        
        fambri_sp = SupplierProduct.objects.filter(supplier=fambri, product=product).first()
        if fambri_sp and not fambri_sp.is_available:
            self.stdout.write(self.style.WARNING(f"   • Set Fambri {product_name} as available"))
        
        if fambri_sp and fambri_sp.stock_quantity <= 0:
            self.stdout.write(self.style.WARNING(f"   • Update Fambri {product_name} stock quantity"))
        
        self.stdout.write(self.style.SUCCESS('\n✅ Debug completed!'))
