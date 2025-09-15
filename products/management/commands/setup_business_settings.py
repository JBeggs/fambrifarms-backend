from django.core.management.base import BaseCommand
from products.models import BusinessSettings, Department
from inventory.models import UnitOfMeasure
from suppliers.models import Supplier

class Command(BaseCommand):
    help = 'Setup BusinessSettings with sensible defaults'

    def handle(self, *args, **options):
        self.stdout.write("Setting up BusinessSettings...")
        
        # Get or create the business settings
        settings, created = BusinessSettings.objects.get_or_create(pk=1)
        
        if created:
            self.stdout.write("✅ Created new BusinessSettings with defaults")
        else:
            self.stdout.write("🔄 BusinessSettings already exists, updating with current defaults")
        
        # Set default units if they exist
        try:
            kg_unit = UnitOfMeasure.objects.get(abbreviation='kg')
            settings.default_weight_unit = kg_unit
            self.stdout.write(f"✅ Set default weight unit: {kg_unit}")
        except UnitOfMeasure.DoesNotExist:
            self.stdout.write("⚠️  Warning: 'kg' unit not found. Run 'populate_units' first.")
        
        try:
            piece_unit = UnitOfMeasure.objects.get(abbreviation='piece')
            settings.default_count_unit = piece_unit
            self.stdout.write(f"✅ Set default count unit: {piece_unit}")
        except UnitOfMeasure.DoesNotExist:
            self.stdout.write("⚠️  Warning: 'piece' unit not found. Run 'populate_units' first.")
        
        # Set default department if one exists
        try:
            first_department = Department.objects.filter(is_active=True).first()
            if first_department:
                settings.default_department = first_department
                self.stdout.write(f"✅ Set default department: {first_department}")
            else:
                self.stdout.write("⚠️  Warning: No active departments found.")
        except Department.DoesNotExist:
            self.stdout.write("⚠️  Warning: No departments found.")
        
        # Set default supplier if one exists
        try:
            first_supplier = Supplier.objects.filter(is_active=True).first()
            if first_supplier:
                settings.default_supplier = first_supplier
                self.stdout.write(f"✅ Set default supplier: {first_supplier}")
            else:
                self.stdout.write("⚠️  Warning: No active suppliers found.")
        except Supplier.DoesNotExist:
            self.stdout.write("⚠️  Warning: No suppliers found.")
        
        # Save the settings
        settings.save()
        
        # Display current settings
        self.stdout.write("\n📋 Current Business Settings:")
        self.stdout.write(f"  Default minimum level: {settings.default_minimum_level}")
        self.stdout.write(f"  Default reorder level: {settings.default_reorder_level}")
        self.stdout.write(f"  Default maximum level: {settings.default_maximum_level}")
        self.stdout.write(f"  Default order quantity: {settings.default_order_quantity}")
        self.stdout.write(f"  Max price variance: {settings.max_price_variance_percent}%")
        self.stdout.write(f"  Require batch tracking: {settings.require_batch_tracking}")
        self.stdout.write(f"  Require expiry dates: {settings.require_expiry_dates}")
        self.stdout.write(f"  Require quality grades: {settings.require_quality_grades}")
        self.stdout.write(f"  Default weight unit: {settings.default_weight_unit}")
        self.stdout.write(f"  Default count unit: {settings.default_count_unit}")
        self.stdout.write(f"  Default department: {settings.default_department}")
        self.stdout.write(f"  Default supplier: {settings.default_supplier}")
        self.stdout.write(f"  Min phone digits: {settings.min_phone_digits}")
        self.stdout.write(f"  Allow negative inventory: {settings.allow_negative_inventory}")
        
        self.stdout.write(self.style.SUCCESS("\n✅ BusinessSettings setup complete!"))
