from django.core.management.base import BaseCommand
from inventory.models import UnitOfMeasure

class Command(BaseCommand):
    help = 'Populate UnitOfMeasure data for the inventory system'

    def handle(self, *args, **options):
        # Define standard units for the farm business
        units_data = [
            # Weight units
            {'name': 'Kilogram', 'abbreviation': 'kg', 'is_weight': True, 'base_unit_multiplier': 1.0},
            {'name': 'Gram', 'abbreviation': 'g', 'is_weight': True, 'base_unit_multiplier': 0.001},
            {'name': 'Pound', 'abbreviation': 'lb', 'is_weight': True, 'base_unit_multiplier': 0.453592},
            
            # Count units
            {'name': 'Piece', 'abbreviation': 'piece', 'is_weight': False, 'base_unit_multiplier': 1.0},
            {'name': 'Pieces', 'abbreviation': 'pieces', 'is_weight': False, 'base_unit_multiplier': 1.0},
            {'name': 'Bunch', 'abbreviation': 'bunch', 'is_weight': False, 'base_unit_multiplier': 1.0},
            {'name': 'Bunches', 'abbreviation': 'bunches', 'is_weight': False, 'base_unit_multiplier': 1.0},
            
            # Package units (common for suppliers)
            {'name': 'Packet', 'abbreviation': 'pkt', 'is_weight': False, 'base_unit_multiplier': 1.0},
            {'name': 'Packets', 'abbreviation': 'pkts', 'is_weight': False, 'base_unit_multiplier': 1.0},
            {'name': 'Box', 'abbreviation': 'box', 'is_weight': False, 'base_unit_multiplier': 1.0},
            {'name': 'Boxes', 'abbreviation': 'boxes', 'is_weight': False, 'base_unit_multiplier': 1.0},
            {'name': 'Bag', 'abbreviation': 'bag', 'is_weight': False, 'base_unit_multiplier': 1.0},
            {'name': 'Bags', 'abbreviation': 'bags', 'is_weight': False, 'base_unit_multiplier': 1.0},
            {'name': 'Crate', 'abbreviation': 'crate', 'is_weight': False, 'base_unit_multiplier': 1.0},
            {'name': 'Crates', 'abbreviation': 'crates', 'is_weight': False, 'base_unit_multiplier': 1.0},
            
            # Produce-specific units
            {'name': 'Head', 'abbreviation': 'head', 'is_weight': False, 'base_unit_multiplier': 1.0},
            {'name': 'Heads', 'abbreviation': 'heads', 'is_weight': False, 'base_unit_multiplier': 1.0},
            
            # Volume units (for liquids/bulk)
            {'name': 'Liter', 'abbreviation': 'l', 'is_weight': False, 'base_unit_multiplier': 1.0},
            {'name': 'Liters', 'abbreviation': 'L', 'is_weight': False, 'base_unit_multiplier': 1.0},
            {'name': 'Milliliter', 'abbreviation': 'ml', 'is_weight': False, 'base_unit_multiplier': 0.001},
        ]

        self.stdout.write("Populating UnitOfMeasure data...")

        created_count = 0
        updated_count = 0

        for unit_data in units_data:
            unit, created = UnitOfMeasure.objects.get_or_create(
                abbreviation=unit_data['abbreviation'],
                defaults=unit_data
            )
            
            if created:
                created_count += 1
                self.stdout.write(f"✅ Created: {unit.name} ({unit.abbreviation})")
            else:
                # Update existing unit if needed
                updated = False
                for field, value in unit_data.items():
                    if getattr(unit, field) != value:
                        setattr(unit, field, value)
                        updated = True
                
                if updated:
                    unit.save()
                    updated_count += 1
                    self.stdout.write(f"🔄 Updated: {unit.name} ({unit.abbreviation})")
                else:
                    self.stdout.write(f"⏭️  Exists: {unit.name} ({unit.abbreviation})")

        self.stdout.write(f"\n📊 Summary:")
        self.stdout.write(f"Created: {created_count} units")
        self.stdout.write(f"Updated: {updated_count} units")
        self.stdout.write(f"Total units: {UnitOfMeasure.objects.count()}")

        # Display all units
        self.stdout.write(f"\n📋 All Units:")
        for unit in UnitOfMeasure.objects.all().order_by('is_weight', 'name'):
            weight_type = "Weight" if unit.is_weight else "Count"
            self.stdout.write(f"  {unit.name} ({unit.abbreviation}) - {weight_type} - Multiplier: {unit.base_unit_multiplier}")

        self.stdout.write(self.style.SUCCESS("\n✅ UnitOfMeasure population complete!"))
