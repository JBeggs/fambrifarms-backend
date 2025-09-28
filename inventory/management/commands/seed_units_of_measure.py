from django.core.management.base import BaseCommand
from inventory.models import UnitOfMeasure


class Command(BaseCommand):
    help = 'Seeds basic units of measure for the inventory system'

    def handle(self, *args, **options):
        units_data = [
            # Weight-based units
            {'name': 'Kilogram', 'abbreviation': 'kg', 'is_weight': True, 'base_unit_multiplier': 1.0},
            {'name': 'Gram', 'abbreviation': 'g', 'is_weight': True, 'base_unit_multiplier': 0.001},
            {'name': 'Pound', 'abbreviation': 'lb', 'is_weight': True, 'base_unit_multiplier': 0.453592},
            
            # Count-based units
            {'name': 'Piece', 'abbreviation': 'pcs', 'is_weight': False, 'base_unit_multiplier': 1.0},
            {'name': 'Each', 'abbreviation': 'each', 'is_weight': False, 'base_unit_multiplier': 1.0},
            {'name': 'Dozen', 'abbreviation': 'doz', 'is_weight': False, 'base_unit_multiplier': 12.0},
            
            # Volume-based units
            {'name': 'Liter', 'abbreviation': 'L', 'is_weight': False, 'base_unit_multiplier': 1.0},
            {'name': 'Milliliter', 'abbreviation': 'mL', 'is_weight': False, 'base_unit_multiplier': 0.001},
            
            # Agricultural units
            {'name': 'Bunch', 'abbreviation': 'bunch', 'is_weight': False, 'base_unit_multiplier': 1.0},
            {'name': 'Head', 'abbreviation': 'head', 'is_weight': False, 'base_unit_multiplier': 1.0},
            {'name': 'Bag', 'abbreviation': 'bag', 'is_weight': False, 'base_unit_multiplier': 1.0},
            {'name': 'Box', 'abbreviation': 'box', 'is_weight': False, 'base_unit_multiplier': 1.0},
            {'name': 'Crate', 'abbreviation': 'crate', 'is_weight': False, 'base_unit_multiplier': 1.0},
            {'name': 'Tray', 'abbreviation': 'tray', 'is_weight': False, 'base_unit_multiplier': 1.0},
        ]

        created_count = 0
        updated_count = 0

        for unit_data in units_data:
            unit, created = UnitOfMeasure.objects.get_or_create(
                abbreviation=unit_data['abbreviation'],
                defaults=unit_data
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Created unit: {unit.name} ({unit.abbreviation})')
                )
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
                    self.stdout.write(
                        self.style.WARNING(f'🔄 Updated unit: {unit.name} ({unit.abbreviation})')
                    )
                else:
                    self.stdout.write(f'⏭️  Unit already exists: {unit.name} ({unit.abbreviation})')

        self.stdout.write(
            self.style.SUCCESS(
                f'\n🎉 Units seeding completed!\n'
                f'   Created: {created_count} units\n'
                f'   Updated: {updated_count} units\n'
                f'   Total units in database: {UnitOfMeasure.objects.count()}'
            )
        )
