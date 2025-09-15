"""
Django management command to seed procurement intelligence data
Creates buffer settings, sample recommendations, and veggie box recipes
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from decimal import Decimal
import logging

from products.models import Product, ProcurementBuffer, MarketProcurementRecommendation
from products.services import ProcurementIntelligenceService, RecipeService

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Seed procurement intelligence data: buffers, recommendations, and recipes'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing procurement data before seeding',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🧠 SEEDING PROCUREMENT INTELLIGENCE DATA...')
        )

        if options['clear']:
            self.clear_existing_data()

        with transaction.atomic():
            # 1. Create procurement buffers for all products
            buffers_created = self.create_procurement_buffers()
            
            # 2. Create veggie box recipes
            recipes_created = self.create_veggie_box_recipes()
            
            # 3. Generate sample market recommendation
            recommendation = self.generate_sample_recommendation()

        self.stdout.write(
            self.style.SUCCESS(
                f'\n✅ PROCUREMENT INTELLIGENCE SEEDING COMPLETE!\n'
                f'📊 Created {buffers_created} procurement buffers\n'
                f'📝 Created {recipes_created} product recipes\n'
                f'🛒 Generated sample market recommendation: {recommendation.id if recommendation else "None"}\n'
                f'\n🎯 Karl can now:\n'
                f'   • View intelligent market recommendations\n'
                f'   • Adjust buffer settings per product\n'
                f'   • Track recipe breakdowns for veggie boxes\n'
                f'   • Optimize procurement based on orders + waste\n'
            )
        )

    def clear_existing_data(self):
        """Clear existing procurement data"""
        self.stdout.write('🧹 Clearing existing procurement data...')
        
        ProcurementBuffer.objects.all().delete()
        MarketProcurementRecommendation.objects.all().delete()
        
        self.stdout.write(self.style.WARNING('   Cleared procurement buffers and recommendations'))

    def create_procurement_buffers(self):
        """Create intelligent procurement buffers for all products"""
        self.stdout.write('📊 Creating procurement buffers...')
        
        # Buffer settings by product department
        department_buffers = {
            'Vegetables': {
                'spoilage_rate': Decimal('0.15'),  # 15% spoilage
                'cutting_waste_rate': Decimal('0.12'),  # 12% cutting waste
                'quality_rejection_rate': Decimal('0.08'),  # 8% quality rejection
                'market_pack_size': Decimal('5.0'),  # 5kg boxes
                'market_pack_unit': 'kg',
                'is_seasonal': True,
                'peak_season_months': [11, 12, 1, 2, 3],  # Summer season
                'peak_season_buffer_multiplier': Decimal('1.3')
            },
            'Fruits': {
                'spoilage_rate': Decimal('0.20'),  # 20% spoilage (more perishable)
                'cutting_waste_rate': Decimal('0.08'),  # 8% cutting waste
                'quality_rejection_rate': Decimal('0.12'),  # 12% quality rejection
                'market_pack_size': Decimal('10.0'),  # 10kg boxes
                'market_pack_unit': 'kg',
                'is_seasonal': True,
                'peak_season_months': [10, 11, 12, 1, 2],  # Fruit season
                'peak_season_buffer_multiplier': Decimal('1.4')
            },
            'Herbs & Spices': {
                'spoilage_rate': Decimal('0.08'),  # 8% spoilage (longer lasting)
                'cutting_waste_rate': Decimal('0.05'),  # 5% cutting waste
                'quality_rejection_rate': Decimal('0.03'),  # 3% quality rejection
                'market_pack_size': Decimal('1.0'),  # 1kg bundles
                'market_pack_unit': 'kg',
                'is_seasonal': False,
                'peak_season_months': [],
                'peak_season_buffer_multiplier': Decimal('1.0')
            },
            'Mushrooms': {
                'spoilage_rate': Decimal('0.25'),  # 25% spoilage (very perishable)
                'cutting_waste_rate': Decimal('0.15'),  # 15% cutting waste
                'quality_rejection_rate': Decimal('0.10'),  # 10% quality rejection
                'market_pack_size': Decimal('2.5'),  # 2.5kg boxes
                'market_pack_unit': 'kg',
                'is_seasonal': False,
                'peak_season_months': [],
                'peak_season_buffer_multiplier': Decimal('1.0')
            },
            'Specialty Items': {
                'spoilage_rate': Decimal('0.12'),  # 12% spoilage
                'cutting_waste_rate': Decimal('0.08'),  # 8% cutting waste
                'quality_rejection_rate': Decimal('0.05'),  # 5% quality rejection
                'market_pack_size': Decimal('3.0'),  # 3kg mixed
                'market_pack_unit': 'kg',
                'is_seasonal': False,
                'peak_season_months': [],
                'peak_season_buffer_multiplier': Decimal('1.0')
            }
        }
        
        # Default buffer for products without department
        default_buffer = {
            'spoilage_rate': Decimal('0.15'),
            'cutting_waste_rate': Decimal('0.10'),
            'quality_rejection_rate': Decimal('0.05'),
            'market_pack_size': Decimal('5.0'),
            'market_pack_unit': 'kg',
            'is_seasonal': False,
            'peak_season_months': [],
            'peak_season_buffer_multiplier': Decimal('1.0')
        }
        
        created_count = 0
        
        for product in Product.objects.all():
            # Get buffer settings based on department
            if product.department and product.department.name in department_buffers:
                buffer_settings = department_buffers[product.department.name]
            else:
                buffer_settings = default_buffer
            
            # Create or update procurement buffer
            buffer, created = ProcurementBuffer.objects.get_or_create(
                product=product,
                defaults=buffer_settings
            )
            
            if created:
                created_count += 1
                self.stdout.write(f'   ✓ {product.name} ({product.department.name if product.department else "No Dept"})')
        
        self.stdout.write(self.style.SUCCESS(f'   Created {created_count} procurement buffers'))
        return created_count

    def create_veggie_box_recipes(self):
        """Create veggie box recipes using the RecipeService"""
        self.stdout.write('📝 Creating veggie box recipes...')
        
        try:
            created_recipes = RecipeService.create_veggie_box_recipes()
            
            for recipe in created_recipes:
                self.stdout.write(f'   ✓ {recipe.product.name} ({len(recipe.ingredients)} ingredients)')
            
            self.stdout.write(self.style.SUCCESS(f'   Created {len(created_recipes)} recipes'))
            return len(created_recipes)
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'   Error creating recipes: {e}'))
            return 0

    def generate_sample_recommendation(self):
        """Generate a sample market recommendation"""
        self.stdout.write('🛒 Generating sample market recommendation...')
        
        try:
            service = ProcurementIntelligenceService()
            recommendation = service.generate_market_recommendation()
            
            if recommendation:
                items_count = recommendation.items.count()
                total_cost = recommendation.total_estimated_cost
                
                self.stdout.write(
                    f'   ✓ Recommendation {recommendation.id}: {items_count} items, R{total_cost:.2f}'
                )
                
                # Show top 5 items
                top_items = recommendation.items.order_by('-estimated_total_cost')[:5]
                for item in top_items:
                    self.stdout.write(
                        f'     • {item.product.name}: {item.recommended_quantity}kg @ R{item.estimated_unit_price}/kg = R{item.estimated_total_cost:.2f}'
                    )
            
            return recommendation
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'   Error generating recommendation: {e}'))
            return None
