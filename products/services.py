"""
Intelligent Procurement Services for Fambri Farms
Handles market purchase predictions, buffer calculations, and recipe breakdowns
"""

from django.db.models import Sum, Q, F
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Tuple
import logging

from .models import Product, ProcurementBuffer, MarketProcurementRecommendation, MarketProcurementItem, Recipe
from orders.models import Order, OrderItem
from inventory.models import FinishedInventory, MarketPrice
from suppliers.models import Supplier

logger = logging.getLogger(__name__)

class ProcurementIntelligenceService:
    """
    Core service for intelligent market procurement recommendations
    """
    
    def __init__(self):
        self.tshwane_market = None
        try:
            # Ensure supplier exists or create it
            self.tshwane_market, created = Supplier.objects.get_or_create(
                name='Tshwane Fresh Produce Market',
                defaults={
                    'contact_person': 'Market Manager',
                    'phone': '+27 12 358 8000',
                    'email': 'info@tshwanemarket.co.za',
                    'address': 'Tshwane Fresh Produce Market, Pretoria',
                    'supplier_type': 'market',
                    'is_active': True
                }
            )
            if created:
                logger.info("Created Tshwane Fresh Produce Market supplier")
            else:
                logger.info("Using existing Tshwane Fresh Produce Market supplier")
        except Exception as e:
            logger.error(f"Error setting up Tshwane Market supplier: {e}")
            # Continue without supplier - system will still work but without supplier-specific features
    
    def generate_market_recommendation(self, for_date: datetime.date = None, use_historical_dates: bool = True) -> MarketProcurementRecommendation:
        """
        Generate intelligent market procurement recommendation based on:
        1. Current stock levels
        2. Pending orders (next 3-5 days)
        3. Historical patterns
        4. Recipe requirements
        5. Wastage/spoilage buffers
        
        Args:
            for_date: Target date for recommendation (defaults to today or earliest order date)
            use_historical_dates: If True, use order dates for historical analysis
        """
        if not for_date:
            if use_historical_dates:
                # Use earliest order date from recent orders for historical analysis
                from orders.models import Order
                recent_orders = Order.objects.filter(
                    status__in=['confirmed', 'processing', 'received']
                ).order_by('order_date')[:10]
                
                if recent_orders.exists():
                    for_date = recent_orders.first().order_date
                    logger.info(f"Using historical date from earliest order: {for_date}")
                else:
                    for_date = timezone.now().date()
                    logger.info(f"No orders found, using current date: {for_date}")
            else:
                for_date = timezone.now().date()
        
        logger.info(f"Generating market recommendation for {for_date}")
        
        # Create recommendation record
        recommendation = MarketProcurementRecommendation.objects.create(
            for_date=for_date,
            status='pending'
        )
        
        # Analyze requirements
        analysis_data = {
            'analysis_date': for_date.isoformat(),
            'upcoming_orders': [],
            'stock_analysis': {},
            'recipe_breakdowns': {},
            'buffer_calculations': {}
        }
        
        # 1. Get upcoming orders (next 5 days)
        upcoming_orders = self._get_upcoming_orders(for_date)
        analysis_data['upcoming_orders'] = [
            {
                'order_id': order.id,
                'customer': order.restaurant.get_full_name() if order.restaurant else 'Unknown Customer',
                'delivery_date': order.delivery_date.isoformat(),
                'total_value': float(order.total_amount)
            }
            for order in upcoming_orders
        ]
        
        # 2. Calculate product requirements
        product_requirements = self._calculate_product_requirements(upcoming_orders)
        
        # 3. Analyze current stock
        stock_analysis = self._analyze_current_stock(product_requirements)
        analysis_data['stock_analysis'] = stock_analysis
        
        # 4. Generate procurement items
        total_cost = Decimal('0.00')
        for product_id, requirement_data in product_requirements.items():
            try:
                product = Product.objects.get(id=product_id)
                
                # Get or create procurement buffer
                buffer, created = ProcurementBuffer.objects.get_or_create(
                    product=product,
                    defaults=self._get_default_buffer_settings(product)
                )
                
                # Calculate needed quantity
                needed_qty = float(requirement_data['total_needed'])
                current_stock = stock_analysis.get(str(product_id), {}).get('current_stock', 0)
                net_needed = max(0, needed_qty - current_stock)
                
                if net_needed > 0:
                    # Calculate market quantity with buffers
                    buffer_calc = buffer.calculate_market_quantity(net_needed)
                    
                    # Get estimated price
                    estimated_price = self._get_estimated_market_price(product)
                    item_cost = buffer_calc['market_quantity'] * float(estimated_price)
                    
                    # Create procurement item
                    procurement_item = MarketProcurementItem.objects.create(
                        recommendation=recommendation,
                        product=product,
                        needed_quantity=net_needed,
                        recommended_quantity=buffer_calc['market_quantity'],
                        estimated_unit_price=estimated_price,
                        estimated_total_cost=item_cost,
                        reasoning=self._generate_reasoning(requirement_data, buffer_calc, current_stock),
                        priority=self._determine_priority(current_stock, needed_qty, product),
                        source_orders=requirement_data['source_orders']
                    )
                    
                    total_cost += Decimal(str(item_cost))
                    
                    # Store buffer calculation in analysis
                    analysis_data['buffer_calculations'][str(product_id)] = {
                        'needed_quantity': float(net_needed),
                        'buffer_rate': float(buffer.total_buffer_rate),
                        'market_quantity': float(buffer_calc['market_quantity']),
                        'market_packs': buffer_calc['market_packs'],
                        'seasonal_multiplier': buffer_calc['seasonal_multiplier']
                    }
                    
            except Product.DoesNotExist:
                logger.error(f"Product {product_id} not found during procurement analysis")
                continue
        
        # Update recommendation totals
        recommendation.total_estimated_cost = total_cost
        recommendation.analysis_data = analysis_data
        recommendation.save()
        
        logger.info(f"Generated recommendation {recommendation.id} with {recommendation.items.count()} items, total cost R{total_cost}")
        
        return recommendation
    
    def _get_upcoming_orders(self, from_date: datetime.date, days_ahead: int = 5) -> List[Order]:
        """Get orders for the next few days or recent orders that need procurement"""
        end_date = from_date + timedelta(days=days_ahead)
        
        # First try to get future orders
        future_orders = Order.objects.filter(
            delivery_date__gte=from_date,
            delivery_date__lte=end_date,
            status__in=['confirmed', 'processing', 'received']  # Include received orderspython manage.py seed_whatsapp_messages --day Tuesday_27_08_2025python manage.py seed_whatsapp_messages --day Tuesday_27_08_2025
        ).prefetch_related('items__product')
        
        # If no future orders, get recent orders (last 30 days) for procurement planning
        if not future_orders.exists():
            recent_start = from_date - timedelta(days=30)
            recent_orders = Order.objects.filter(
                delivery_date__gte=recent_start,
                status__in=['confirmed', 'processing', 'received']
            ).prefetch_related('items__product')
            
            logger.info(f"No future orders found, using {recent_orders.count()} recent orders for procurement planning")
            return list(recent_orders)
        
        return list(future_orders)
    
    def _calculate_product_requirements(self, orders: List[Order]) -> Dict:
        """Calculate total product requirements from orders, including recipe breakdowns"""
        requirements = {}
        
        for order in orders:
            for item in order.items.all():
                product = item.product
                quantity_needed = item.quantity
                
                # Check if product has a recipe (composite product like veggie boxes)
                if hasattr(product, 'product_recipe'):
                    recipe = product.product_recipe
                    # Break down recipe into component ingredients
                    for ingredient_data in recipe.ingredients:
                        ingredient_id = ingredient_data.get('product_id')
                        ingredient_qty = Decimal(str(ingredient_data.get('quantity', 0)))
                        
                        # Calculate total ingredient needed (recipe qty * order qty)
                        total_ingredient_needed = ingredient_qty * quantity_needed
                        
                        if ingredient_id not in requirements:
                            requirements[ingredient_id] = {
                                'total_needed': Decimal('0'),
                                'source_orders': [],
                                'recipe_breakdown': []
                            }
                        
                        requirements[ingredient_id]['total_needed'] += total_ingredient_needed
                        requirements[ingredient_id]['source_orders'].append(order.id)
                        requirements[ingredient_id]['recipe_breakdown'].append({
                            'parent_product': product.name,
                            'order_id': order.id,
                            'recipe_qty': float(ingredient_qty),
                            'order_qty': float(quantity_needed),
                            'total_needed': float(total_ingredient_needed)
                        })
                else:
                    # Simple product - direct requirement
                    product_id = product.id
                    if product_id not in requirements:
                        requirements[product_id] = {
                            'total_needed': Decimal('0'),
                            'source_orders': [],
                            'recipe_breakdown': []
                        }
                    
                    requirements[product_id]['total_needed'] += quantity_needed
                    requirements[product_id]['source_orders'].append(order.id)
        
        return requirements
    
    def _analyze_current_stock(self, requirements: Dict) -> Dict:
        """Analyze current stock levels for required products"""
        stock_analysis = {}
        
        for product_id in requirements.keys():
            try:
                inventory = FinishedInventory.objects.get(product_id=product_id)
                stock_analysis[str(product_id)] = {
                    'current_stock': float(inventory.available_quantity or 0),
                    'minimum_stock': float(inventory.minimum_level or 0),
                    'is_low_stock': (inventory.available_quantity or 0) <= (inventory.minimum_level or 0),
                    'is_out_of_stock': (inventory.available_quantity or 0) <= 0
                }
            except FinishedInventory.DoesNotExist:
                stock_analysis[str(product_id)] = {
                    'current_stock': 0,
                    'minimum_stock': 0,
                    'is_low_stock': True,
                    'is_out_of_stock': True
                }
        
        return stock_analysis
    
    def _get_default_buffer_settings(self, product: Product) -> Dict:
        """Get default buffer settings based on product type"""
        # Default settings - can be customized per product
        defaults = {
            'spoilage_rate': Decimal('0.15'),  # 15% spoilage
            'cutting_waste_rate': Decimal('0.10'),  # 10% cutting waste
            'quality_rejection_rate': Decimal('0.05'),  # 5% quality rejection
            'market_pack_size': Decimal('5.0'),  # 5kg standard pack
            'market_pack_unit': 'kg'
        }
        
        # Adjust based on product department
        if product.department:
            dept_name = product.department.name.lower()
            if 'fruit' in dept_name:
                defaults['spoilage_rate'] = Decimal('0.20')  # Fruits spoil faster
                defaults['market_pack_size'] = Decimal('10.0')  # Larger packs
            elif 'herb' in dept_name or 'spice' in dept_name:
                defaults['spoilage_rate'] = Decimal('0.05')  # Herbs last longer
                defaults['cutting_waste_rate'] = Decimal('0.02')  # Less waste
                defaults['market_pack_size'] = Decimal('1.0')  # Smaller packs
            elif 'mushroom' in dept_name:
                defaults['spoilage_rate'] = Decimal('0.25')  # Mushrooms very perishable
                defaults['market_pack_size'] = Decimal('2.5')  # Small packs
        
        return defaults
    
    def _get_estimated_market_price(self, product: Product) -> Decimal:
        """Get estimated market price for product"""
        try:
            # Use product's base price with wholesale discount (70% of retail)
            if product.price:
                return product.price * Decimal('0.7')  # 30% wholesale discount
            
            # Fallback - estimate based on department
            return self._estimate_price_by_department(product)
            
        except Exception as e:
            logger.warning(f"Could not get market price for {product.name}: {e}")
            return Decimal('10.00')  # Safe fallback
    
    def _estimate_price_by_department(self, product: Product) -> Decimal:
        """Estimate price based on product department"""
        if not product.department:
            return Decimal('15.00')
        
        dept_name = product.department.name.lower()
        if 'vegetable' in dept_name:
            return Decimal('12.00')
        elif 'fruit' in dept_name:
            return Decimal('18.00')
        elif 'herb' in dept_name or 'spice' in dept_name:
            return Decimal('25.00')
        elif 'mushroom' in dept_name:
            return Decimal('35.00')
        else:
            return Decimal('15.00')
    
    def _generate_reasoning(self, requirement_data: Dict, buffer_calc: Dict, current_stock: float) -> str:
        """Generate human-readable reasoning for procurement recommendation"""
        needed = float(requirement_data['total_needed'])
        recommended = buffer_calc['market_quantity']
        buffer_rate = buffer_calc['buffer_rate']
        
        reasoning_parts = []
        
        # Stock situation
        if current_stock <= 0:
            reasoning_parts.append("🔴 OUT OF STOCK")
        elif current_stock < needed:
            shortage = needed - current_stock
            reasoning_parts.append(f"📉 Short by {shortage:.1f} units")
        
        # Order requirements
        if requirement_data['source_orders']:
            order_count = len(set(requirement_data['source_orders']))
            reasoning_parts.append(f"📋 {order_count} upcoming orders need {needed:.1f} units")
        
        # Buffer explanation
        if buffer_rate > 0:
            reasoning_parts.append(f"🛡️ {buffer_rate:.1%} buffer for spoilage/waste")
        
        # Market packs
        if buffer_calc.get('market_packs', 1) > 1:
            reasoning_parts.append(f"📦 {buffer_calc['market_packs']} market packs")
        
        # Seasonal adjustment
        if buffer_calc.get('seasonal_multiplier', 1.0) > 1.0:
            reasoning_parts.append(f"🌱 {buffer_calc['seasonal_multiplier']:.1f}x seasonal adjustment")
        
        return " • ".join(reasoning_parts)
    
    def _determine_priority(self, current_stock: float, needed_qty: Decimal, product: Product) -> str:
        """Determine priority level for procurement item"""
        if current_stock <= 0:
            return 'critical'
        elif current_stock < needed_qty:
            return 'high'
        elif hasattr(product, 'procurement_buffer') and current_stock <= product.minimum_stock:
            return 'medium'
        else:
            return 'low'

class RecipeService:
    """
    Service for managing product recipes and ingredient breakdowns
    """
    
    @staticmethod
    def create_veggie_box_recipes():
        """Create sample recipes for veggie box products"""
        
        # Real veggie box recipes based on SHALLOME stock data
        veggie_box_recipes = [
            {
                'product_name': 'Small Veggie Box',
                'ingredients': [
                    # Core vegetables - good variety for small families
                    {'product_name': 'Potatoes', 'quantity': 1.0, 'unit': 'bag'},  # 1 bag potatoes
                    {'product_name': 'Carrots (1kg Packed)', 'quantity': 1.0, 'unit': 'kg'},  # 1kg carrots
                    {'product_name': 'White Onions', 'quantity': 0.5, 'unit': 'kg'},  # 500g onions
                    {'product_name': 'Tomatoes', 'quantity': 1.0, 'unit': 'kg'},  # 1kg tomatoes
                    {'product_name': 'Green Peppers', 'quantity': 0.5, 'unit': 'kg'},  # 500g peppers
                    {'product_name': 'Lettuce Head', 'quantity': 1.0, 'unit': 'head'},  # 1 lettuce head
                    {'product_name': 'Cucumber', 'quantity': 2.0, 'unit': 'each'},  # 2 cucumbers
                    {'product_name': 'Green Beans', 'quantity': 0.5, 'unit': 'kg'},  # 500g green beans
                    # Fresh herbs for flavor
                    {'product_name': 'Parsley', 'quantity': 1.0, 'unit': 'bunch'},  # 1 bunch parsley
                    {'product_name': 'Coriander', 'quantity': 1.0, 'unit': 'bunch'},  # 1 bunch coriander
                ],
                'instructions': 'Assemble fresh seasonal vegetables in small eco-friendly box. Perfect for 2-3 people for a week. Include variety card with storage tips.',
                'prep_time_minutes': 12,
                'yield_quantity': 1,
                'yield_unit': 'box'
            },
            {
                'product_name': 'Large Veggie Box',
                'ingredients': [
                    # Core vegetables - larger quantities for families
                    {'product_name': 'Potatoes', 'quantity': 2.0, 'unit': 'bag'},  # 2 bags potatoes
                    {'product_name': 'Carrots (1kg Packed)', 'quantity': 2.0, 'unit': 'kg'},  # 2kg carrots
                    {'product_name': 'White Onions', 'quantity': 1.0, 'unit': 'kg'},  # 1kg onions
                    {'product_name': 'Red Onions', 'quantity': 0.5, 'unit': 'kg'},  # 500g red onions
                    {'product_name': 'Tomatoes', 'quantity': 2.0, 'unit': 'kg'},  # 2kg tomatoes
                    {'product_name': 'Green Peppers', 'quantity': 0.5, 'unit': 'kg'},  # 500g green peppers
                    {'product_name': 'Red Peppers', 'quantity': 0.5, 'unit': 'kg'},  # 500g red peppers
                    {'product_name': 'Yellow Peppers', 'quantity': 0.5, 'unit': 'kg'},  # 500g yellow peppers
                    # Leafy greens and salads
                    {'product_name': 'Lettuce Head', 'quantity': 2.0, 'unit': 'head'},  # 2 lettuce heads
                    {'product_name': 'Mixed Lettuce', 'quantity': 1.0, 'unit': 'kg'},  # 1kg mixed lettuce
                    {'product_name': 'Baby Spinach', 'quantity': 0.5, 'unit': 'kg'},  # 500g baby spinach
                    # Additional vegetables
                    {'product_name': 'Cucumber', 'quantity': 4.0, 'unit': 'each'},  # 4 cucumbers
                    {'product_name': 'Green Beans', 'quantity': 1.0, 'unit': 'kg'},  # 1kg green beans
                    {'product_name': 'Baby Marrow', 'quantity': 1.0, 'unit': 'kg'},  # 1kg baby marrow
                    {'product_name': 'Broccoli', 'quantity': 1.0, 'unit': 'head'},  # 1 broccoli head
                    {'product_name': 'Cauliflower', 'quantity': 1.0, 'unit': 'head'},  # 1 cauliflower head
                    {'product_name': 'Green Cabbage', 'quantity': 1.0, 'unit': 'head'},  # 1 cabbage head
                    {'product_name': 'Sweet Potatoes', 'quantity': 1.0, 'unit': 'kg'},  # 1kg sweet potatoes
                    {'product_name': 'Beetroot', 'quantity': 0.5, 'unit': 'kg'},  # 500g beetroot
                    # Fresh herbs - generous portions
                    {'product_name': 'Parsley', 'quantity': 2.0, 'unit': 'bunch'},  # 2 bunches parsley
                    {'product_name': 'Coriander', 'quantity': 2.0, 'unit': 'bunch'},  # 2 bunches coriander
                    {'product_name': 'Basil', 'quantity': 1.0, 'unit': 'bunch'},  # 1 bunch basil
                    {'product_name': 'Spring Onions', 'quantity': 0.5, 'unit': 'kg'},  # 500g spring onions
                ],
                'instructions': 'Assemble premium selection of fresh seasonal vegetables in large eco-friendly box. Perfect for families of 4-6 people for a week. Include recipe suggestions and storage guide.',
                'prep_time_minutes': 20,
                'yield_quantity': 1,
                'yield_unit': 'box'
            }
        ]
        
        created_recipes = []
        
        for recipe_data in veggie_box_recipes:
            try:
                # Find the main product
                product = Product.objects.get(name=recipe_data['product_name'])
                
                # Convert ingredients to include product IDs
                ingredients_with_ids = []
                for ingredient in recipe_data['ingredients']:
                    try:
                        ingredient_product = Product.objects.get(name=ingredient['product_name'])
                        ingredients_with_ids.append({
                            'product_id': ingredient_product.id,
                            'product_name': ingredient_product.name,
                            'quantity': ingredient['quantity'],
                            'unit': ingredient['unit']
                        })
                    except Product.DoesNotExist:
                        logger.warning(f"Ingredient product '{ingredient['product_name']}' not found")
                        continue
                
                # Create or update recipe
                recipe, created = Recipe.objects.update_or_create(
                    product=product,
                    defaults={
                        'ingredients': ingredients_with_ids,
                        'instructions': recipe_data['instructions'],
                        'prep_time_minutes': recipe_data['prep_time_minutes'],
                        'yield_quantity': recipe_data['yield_quantity'],
                        'yield_unit': recipe_data['yield_unit']
                    }
                )
                
                created_recipes.append(recipe)
                logger.info(f"{'Created' if created else 'Updated'} recipe for {product.name}")
                
            except Product.DoesNotExist:
                logger.warning(f"Product '{recipe_data['product_name']}' not found for recipe creation")
                continue
        
        return created_recipes
