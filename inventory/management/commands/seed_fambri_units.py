from django.core.management.base import BaseCommand
from django.db import transaction
from inventory.models import UnitOfMeasure


class Command(BaseCommand):
    help = 'Seed comprehensive units of measure based on real WhatsApp order data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing units before importing',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing existing units...')
            UnitOfMeasure.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('Existing units cleared.'))

        self.create_comprehensive_units()

        self.stdout.write(
            self.style.SUCCESS(
                f'\n🎉 FAMBRI UNITS SEEDED SUCCESSFULLY!'
            )
        )
        self.stdout.write(f'📏 Comprehensive unit system based on real WhatsApp orders')
        self.stdout.write(f'⚖️ Weight and count units with proper conversions')
        self.stdout.write(f'📦 Package units matching actual supplier formats')
        self.stdout.write(f'✅ Units system ready for accurate inventory management')

    def create_comprehensive_units(self):
        """Create comprehensive units based on real WhatsApp order patterns"""
        
        # Units extracted from actual WhatsApp messages and order patterns
        units_data = [
            # WEIGHT UNITS (Primary measurement system)
            {
                'name': 'Kilogram',
                'abbreviation': 'kg',
                'is_weight': True,
                'base_unit_multiplier': 1.0,
                'description': 'Primary weight unit - most vegetables, fruits, bulk items'
            },
            {
                'name': 'Gram',
                'abbreviation': 'g',
                'is_weight': True,
                'base_unit_multiplier': 0.001,
                'description': 'Small quantities - herbs like "200g Parsley", "100g Chives"'
            },
            
            # COUNT UNITS (Individual items)
            {
                'name': 'Each',
                'abbreviation': 'each',
                'is_weight': False,
                'base_unit_multiplier': 1.0,
                'description': 'Individual items - cucumbers, avocados, melons'
            },
            {
                'name': 'Piece',
                'abbreviation': 'piece',
                'is_weight': False,
                'base_unit_multiplier': 1.0,
                'description': 'Individual pieces - alternative to "each"'
            },
            
            # PRODUCE-SPECIFIC UNITS
            {
                'name': 'Head',
                'abbreviation': 'head',
                'is_weight': False,
                'base_unit_multiplier': 1.0,
                'description': 'Heads of vegetables - "10 heads broccoli", "10 heads cauliflower"'
            },
            {
                'name': 'Bunch',
                'abbreviation': 'bunch',
                'is_weight': False,
                'base_unit_multiplier': 1.0,
                'description': 'Bunched herbs and vegetables - basil, parsley, mint, rosemary'
            },
            
            # PACKAGE UNITS (Supplier/retail packaging)
            {
                'name': 'Box',
                'abbreviation': 'box',
                'is_weight': False,
                'base_unit_multiplier': 1.0,
                'description': 'Boxes - "1 box tomatoes", "Arthur box x2", "Lemon box"'
            },
            {
                'name': 'Bag',
                'abbreviation': 'bag',
                'is_weight': False,
                'base_unit_multiplier': 1.0,
                'description': 'Bags - "3-6 bags potatoes", "1-3 bags red onions"'
            },
            {
                'name': 'Punnet',
                'abbreviation': 'punnet',
                'is_weight': False,
                'base_unit_multiplier': 1.0,
                'description': 'Small containers - "4-6 punnets strawberries", "5-10 punnets cherry tomatoes"'
            },
            {
                'name': 'Packet',
                'abbreviation': 'packet',
                'is_weight': False,
                'base_unit_multiplier': 1.0,
                'description': 'Small packets - micro herbs, specialty items'
            },
            {
                'name': 'Crate',
                'abbreviation': 'crate',
                'is_weight': False,
                'base_unit_multiplier': 1.0,
                'description': 'Large containers for bulk produce'
            },
            
            # VOLUME UNITS (Less common but needed)
            {
                'name': 'Liter',
                'abbreviation': 'L',
                'is_weight': False,
                'base_unit_multiplier': 1.0,
                'description': 'Volume measurement for liquids'
            },
            {
                'name': 'Milliliter',
                'abbreviation': 'ml',
                'is_weight': False,
                'base_unit_multiplier': 0.001,
                'description': 'Small volume measurements'
            },
            
            # SPECIALTY UNITS (Farm-specific)
            {
                'name': 'Tray',
                'abbreviation': 'tray',
                'is_weight': False,
                'base_unit_multiplier': 1.0,
                'description': 'Seedling trays, herb trays'
            },
            {
                'name': 'Bundle',
                'abbreviation': 'bundle',
                'is_weight': False,
                'base_unit_multiplier': 1.0,
                'description': 'Bundled items - asparagus, green beans'
            },
        ]

        created_count = 0
        updated_count = 0

        with transaction.atomic():
            for unit_data in units_data:
                description = unit_data.pop('description', '')
                
                unit, created = UnitOfMeasure.objects.get_or_create(
                    abbreviation=unit_data['abbreviation'],
                    defaults=unit_data
                )
                
                if created:
                    created_count += 1
                    weight_type = "⚖️ Weight" if unit.is_weight else "🔢 Count"
                    self.stdout.write(f'✅ Created: {unit.name} ({unit.abbreviation}) - {weight_type}')
                    self.stdout.write(f'   📝 {description}')
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
                        self.stdout.write(f'🔄 Updated: {unit.name} ({unit.abbreviation})')
                    else:
                        self.stdout.write(f'⏭️  Exists: {unit.name} ({unit.abbreviation})')

        self.stdout.write(f'\n📊 UNITS SUMMARY:')
        self.stdout.write(f'✅ Created: {created_count} units')
        self.stdout.write(f'🔄 Updated: {updated_count} units')
        self.stdout.write(f'📏 Total units: {UnitOfMeasure.objects.count()}')

        # Display categorized units
        self.display_unit_categories()

    def display_unit_categories(self):
        """Display units organized by category"""
        
        weight_units = UnitOfMeasure.objects.filter(is_weight=True).order_by('base_unit_multiplier')
        count_units = UnitOfMeasure.objects.filter(is_weight=False).order_by('name')
        
        self.stdout.write(f'\n⚖️  WEIGHT UNITS:')
        for unit in weight_units:
            self.stdout.write(f'   {unit.name} ({unit.abbreviation}) - Multiplier: {unit.base_unit_multiplier}')
        
        self.stdout.write(f'\n🔢 COUNT/PACKAGE UNITS:')
        for unit in count_units:
            self.stdout.write(f'   {unit.name} ({unit.abbreviation})')
        
        # Show usage statistics if products exist
        try:
            from products.models import Product
            from collections import Counter
            
            if Product.objects.exists():
                units_used = Product.objects.values_list('unit', flat=True)
                unit_counts = Counter(units_used)
                
                self.stdout.write(f'\n📊 CURRENT PRODUCT USAGE:')
                for unit_abbr, count in unit_counts.most_common():
                    unit_obj = UnitOfMeasure.objects.filter(abbreviation=unit_abbr).first()
                    unit_name = unit_obj.name if unit_obj else unit_abbr
                    self.stdout.write(f'   {unit_name} ({unit_abbr}): {count} products')
                
        except ImportError:
            pass  # Products app not available
