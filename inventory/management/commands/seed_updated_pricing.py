from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth import get_user_model
from inventory.models import PricingRule
from decimal import Decimal
import json
import os

User = get_user_model()


class Command(BaseCommand):
    help = 'Seed pricing rules from updated seeding data with current database state'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing pricing rules before importing',
        )
        parser.add_argument(
            '--seeding-dir',
            type=str,
            default='updated_seeding',
            help='Directory containing updated seeding files',
        )

    def handle(self, *args, **options):
        seeding_dir = options['seeding_dir']
        
        if options['clear']:
            self.stdout.write('Clearing existing pricing rules...')
            PricingRule.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('Existing pricing rules cleared.'))

        self.create_pricing_rules_from_data(seeding_dir)

        self.stdout.write(
            self.style.SUCCESS(
                f'\n🎉 UPDATED PRICING RULES SEEDED SUCCESSFULLY!'
            )
        )

    def load_seeding_data(self, seeding_dir):
        """Load seeding data from JSON file"""
        file_path = os.path.join(seeding_dir, 'pricing_rules.json')
        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f'Seeding file not found: {file_path}'))
            return None
        
        with open(file_path, 'r') as f:
            return json.load(f)

    def create_pricing_rules_from_data(self, seeding_dir):
        """Create pricing rules from updated seeding data"""
        data = self.load_seeding_data(seeding_dir)
        if not data:
            return
        
        pricing_rules_data = data.get('pricing_rules', [])
        
        self.stdout.write(f'Creating {len(pricing_rules_data)} pricing rules...')
        
        # Get or create system user for created_by
        system_user, _ = User.objects.get_or_create(
            email='system@fambrifarms.co.za',
            defaults={
                'first_name': 'System',
                'last_name': 'Admin',
                'user_type': 'admin',
                'is_staff': True,
                'is_superuser': True,
            }
        )
        
        created_count = 0
        with transaction.atomic():
            for rule_data in pricing_rules_data:
                try:
                    rule, created = PricingRule.objects.get_or_create(
                        name=rule_data['name'],
                        defaults={
                            'description': rule_data.get('description', ''),
                            'customer_segment': rule_data.get('customer_segment', 'standard'),
                            'base_markup_percentage': Decimal(str(rule_data['base_markup_percentage'])),
                            'volatility_adjustment': Decimal(str(rule_data.get('volatility_adjustment', 0))),
                            'minimum_margin_percentage': Decimal(str(rule_data.get('minimum_margin_percentage', 5))),
                            'category_adjustments': rule_data.get('category_adjustments', {}),
                            'trend_multiplier': Decimal(str(rule_data.get('trend_multiplier', 1.0))),
                            'seasonal_adjustment': Decimal(str(rule_data.get('seasonal_adjustment', 0))),
                            'is_active': rule_data.get('is_active', True),
                            'effective_from': rule_data.get('effective_from'),
                            'effective_until': rule_data.get('effective_until'),
                            'created_by': system_user,
                        }
                    )
                    if created:
                        created_count += 1
                        self.stdout.write(f'  ✅ Created pricing rule: {rule.name} ({rule.base_markup_percentage}% markup)')
                    else:
                        self.stdout.write(f'  ℹ️  Pricing rule already exists: {rule.name}')
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'  Error creating pricing rule {rule_data["name"]}: {e}'))
        
        self.stdout.write(f'✅ Created {created_count} new pricing rules')
        
        # Show summary
        self.stdout.write('\n💰 Pricing Rules Summary:')
        for rule in PricingRule.objects.all().order_by('base_markup_percentage'):
            status = "Active" if rule.is_active else "Inactive"
            self.stdout.write(f'  - {rule.name}: {rule.base_markup_percentage}% markup ({rule.customer_segment}) - {status}')

        self.stdout.write(f'\n✅ Pricing rules seeding completed: {PricingRule.objects.count()} total rules')
