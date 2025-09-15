from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from datetime import date, timedelta
from decimal import Decimal
import random

from inventory.models import (
    MarketPrice, PricingRule, CustomerPriceList, CustomerPriceListItem,
    ProcurementRecommendation, StockAnalysis
)
from suppliers.models import Supplier, SupplierProduct
from products.models import Product, Department
from accounts.models import User


class Command(BaseCommand):
    help = 'Seed comprehensive pricing intelligence system with real WhatsApp-based data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing pricing data before importing',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing existing pricing data...')
            CustomerPriceListItem.objects.all().delete()
            CustomerPriceList.objects.all().delete()
            ProcurementRecommendation.objects.all().delete()
            PricingRule.objects.all().delete()
            MarketPrice.objects.all().delete()
            SupplierProduct.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('Existing pricing data cleared.'))

        self.create_market_prices()
        self.create_pricing_rules()
        self.create_supplier_products()
        self.create_customer_price_lists()
        self.create_procurement_recommendations()

        self.stdout.write(
            self.style.SUCCESS(
                f'\n🎉 FAMBRI PRICING INTELLIGENCE SEEDED SUCCESSFULLY!'
            )
        )
        self.stdout.write(f'💰 Market-driven pricing with real supplier variations')
        self.stdout.write(f'🎯 Customer-specific pricing rules and segments')
        self.stdout.write(f'📊 Intelligent procurement recommendations')
        self.stdout.write(f'🔄 Dynamic pricing based on stock levels and demand')
        self.stdout.write(f'✅ Phase 6 Complete: Pricing intelligence system operational')

    def create_market_prices(self):
        """Create realistic market prices based on SHALLOME stock data"""
        products = Product.objects.all()
        suppliers = ['Tshwane Market', 'Johannesburg Market', 'Pretoria Fresh Market']
        
        created_count = 0
        for product in products:
            # Create market prices for the last 30 days with realistic variations
            for days_ago in range(0, 30, 3):  # Every 3 days
                price_date = date.today() - timedelta(days=days_ago)
                
                for supplier_name in suppliers:
                    # Base price from product with market variations
                    base_price = product.price
                    
                    # Market-specific variations
                    if supplier_name == 'Tshwane Market':
                        variation = Decimal(str(random.uniform(0.85, 1.05)))  # -15% to +5%
                    elif supplier_name == 'Johannesburg Market':
                        variation = Decimal(str(random.uniform(0.90, 1.10)))  # -10% to +10%
                    else:  # Pretoria Fresh Market
                        variation = Decimal(str(random.uniform(0.95, 1.15)))  # -5% to +15%
                    
                    # Seasonal variations (higher prices for out-of-season items)
                    if product.department.name in ['Fruits', 'Specialty Items']:
                        seasonal_factor = Decimal(str(random.uniform(1.0, 1.3)))
                    else:
                        seasonal_factor = Decimal(str(random.uniform(0.95, 1.1)))
                    
                    # Stock level impact (from SHALLOME data)
                    stock_factor = Decimal('1.0')
                    if product.stock_level < product.minimum_stock:
                        stock_factor = Decimal(str(random.uniform(1.1, 1.4)))  # Higher prices for low stock
                    elif product.stock_level > (product.minimum_stock * 3):
                        stock_factor = Decimal(str(random.uniform(0.9, 1.0)))  # Lower prices for high stock
                    
                    market_price = (base_price * variation * seasonal_factor * stock_factor).quantize(Decimal('0.01'))
                    vat_amount = (market_price * Decimal('0.15')).quantize(Decimal('0.01'))
                    
                    market_price_record, created = MarketPrice.objects.get_or_create(
                        supplier_name=supplier_name,
                        invoice_date=price_date,
                        product_name=product.name,
                        defaults={
                            'matched_product': product,
                            'unit_price_excl_vat': market_price,
                            'vat_amount': vat_amount,
                            'unit_price_incl_vat': market_price + vat_amount,
                            'quantity_unit': product.unit,
                            'invoice_reference': f'INV-{price_date.strftime("%Y%m%d")}-{random.randint(1000, 9999)}'
                        }
                    )
                    
                    if created:
                        created_count += 1

        self.stdout.write(f'💰 Created {created_count} market price records with realistic variations')
        self.stdout.write(f'📊 Market data spans 30 days across 3 major suppliers')

    def create_pricing_rules(self):
        """Create intelligent pricing rules based on customer segments from WhatsApp data"""
        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            admin_user = User.objects.filter(user_type='admin').first()
        
        if not admin_user:
            self.stdout.write(self.style.WARNING('No admin user found for pricing rules'))
            return

        pricing_rules_data = [
            {
                'name': 'Premium Restaurants',
                'description': 'High-end restaurants like Casa Bella, Pecanwood Golf Estate - premium quality, premium pricing',
                'customer_segment': 'premium',
                'base_markup_percentage': Decimal('35.00'),  # 35% markup
                'volatility_adjustment': Decimal('5.00'),    # +5% for volatile items
                'minimum_margin_percentage': Decimal('25.00'), # Minimum 25% margin
                'category_adjustments': {
                    'herbs & spices': 15,  # +15% for premium herbs
                    'specialty items': 20,  # +20% for specialty items
                    'mushrooms': 10        # +10% for mushrooms
                },
                'trend_multiplier': Decimal('1.10'),         # +10% for trending items
                'seasonal_adjustment': Decimal('5.00'),      # +5% seasonal adjustment
            },
            {
                'name': 'Standard Restaurants',
                'description': 'Regular restaurants like Maltos, T-junction, Venue - standard quality and pricing',
                'customer_segment': 'standard',
                'base_markup_percentage': Decimal('25.00'),  # 25% markup
                'volatility_adjustment': Decimal('3.00'),    # +3% for volatile items
                'minimum_margin_percentage': Decimal('18.00'), # Minimum 18% margin
                'category_adjustments': {
                    'herbs & spices': 8,   # +8% for herbs
                    'specialty items': 12, # +12% for specialty items
                    'vegetables': 2        # +2% for vegetables
                },
                'trend_multiplier': Decimal('1.05'),         # +5% for trending items
                'seasonal_adjustment': Decimal('2.00'),      # +2% seasonal adjustment
            },
            {
                'name': 'Budget Establishments',
                'description': 'Budget-conscious establishments like Debonair, Wimpy - competitive pricing',
                'customer_segment': 'budget',
                'base_markup_percentage': Decimal('18.00'),  # 18% markup
                'volatility_adjustment': Decimal('2.00'),    # +2% for volatile items
                'minimum_margin_percentage': Decimal('12.00'), # Minimum 12% margin
                'category_adjustments': {
                    'vegetables': -2,      # -2% discount on vegetables
                    'fruits': 0,           # No adjustment on fruits
                    'herbs & spices': 5    # +5% on herbs (still needed)
                },
                'trend_multiplier': Decimal('1.02'),         # +2% for trending items
                'seasonal_adjustment': Decimal('0.00'),      # No seasonal adjustment
            },
            {
                'name': 'Private Customers',
                'description': 'Private customers like Sylvia, Marco, Arthur - household-friendly pricing',
                'customer_segment': 'retail',
                'base_markup_percentage': Decimal('15.00'),  # 15% markup
                'volatility_adjustment': Decimal('1.00'),    # +1% for volatile items
                'minimum_margin_percentage': Decimal('10.00'), # Minimum 10% margin
                'category_adjustments': {
                    'vegetables': -3,      # -3% discount on vegetables
                    'fruits': -2,          # -2% discount on fruits
                    'herbs & spices': 3    # +3% on herbs
                },
                'trend_multiplier': Decimal('1.00'),         # No trend multiplier
                'seasonal_adjustment': Decimal('-2.00'),     # -2% seasonal discount
            },
            {
                'name': 'Institutional Wholesale',
                'description': 'Large institutions like Culinary Institute - bulk pricing',
                'customer_segment': 'wholesale',
                'base_markup_percentage': Decimal('12.00'),  # 12% markup
                'volatility_adjustment': Decimal('1.50'),    # +1.5% for volatile items
                'minimum_margin_percentage': Decimal('8.00'), # Minimum 8% margin
                'category_adjustments': {
                    'vegetables': -5,      # -5% bulk discount on vegetables
                    'fruits': -3,          # -3% bulk discount on fruits
                    'herbs & spices': 0    # No adjustment on herbs
                },
                'trend_multiplier': Decimal('1.00'),         # No trend multiplier
                'seasonal_adjustment': Decimal('-3.00'),     # -3% bulk seasonal discount
            },
        ]

        created_count = 0
        for rule_data in pricing_rules_data:
            pricing_rule, created = PricingRule.objects.get_or_create(
                name=rule_data['name'],
                defaults={
                    **rule_data,
                    'effective_from': date.today(),
                    'effective_until': date.today() + timedelta(days=365),  # 1 year validity
                    'created_by': admin_user,
                    'is_active': True
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(f'🎯 Created pricing rule: {pricing_rule.name} ({pricing_rule.base_markup_percentage}% base markup)')

        self.stdout.write(f'📋 Created {created_count} intelligent pricing rules based on customer segments')

    def create_supplier_products(self):
        """Create supplier-specific product pricing based on real supplier characteristics"""
        suppliers = Supplier.objects.all()
        products = Product.objects.all()
        
        created_count = 0
        for supplier in suppliers:
            # Determine supplier pricing strategy based on name and characteristics
            if 'Fambri Farms Internal' in supplier.name:
                # Internal supplier - base cost pricing
                price_multiplier = Decimal('0.70')  # 70% of retail (cost price)
                availability_rate = 0.95  # 95% availability
            elif 'Tania' in supplier.name:
                # Emergency supplier - premium pricing but high availability
                price_multiplier = Decimal('1.15')  # 115% of retail (premium for quick delivery)
                availability_rate = 0.90  # 90% availability
            elif 'Mumbai' in supplier.name:
                # Specialty supplier - varied pricing based on product type
                price_multiplier = Decimal('1.05')  # 105% of retail
                availability_rate = 0.85  # 85% availability
            else:
                # Default supplier pricing
                price_multiplier = Decimal('0.85')
                availability_rate = 0.80

            # Select products based on supplier specialty
            if 'Fambri Farms Internal' in supplier.name:
                # Internal farm - all fresh produce
                supplier_products = products.filter(
                    department__name__in=['Vegetables', 'Fruits', 'Herbs & Spices']
                )
            elif 'Tania' in supplier.name:
                # Tania - herbs and emergency vegetables
                supplier_products = products.filter(
                    department__name__in=['Herbs & Spices', 'Vegetables']
                )[:30]  # Limit to 30 products
            elif 'Mumbai' in supplier.name:
                # Mumbai - spices, specialty items, exotic vegetables
                spice_products = products.filter(
                    department__name__in=['Herbs & Spices', 'Specialty Items']
                )
                pepper_products = products.filter(name__icontains='pepper')
                chilli_products = products.filter(name__icontains='chilli')
                
                # Combine manually to avoid union ordering issues
                supplier_products = list(spice_products) + list(pepper_products) + list(chilli_products)
                # Remove duplicates
                seen_ids = set()
                supplier_products = [p for p in supplier_products if not (p.id in seen_ids or seen_ids.add(p.id))]
            else:
                # Default - random selection
                supplier_products = random.sample(list(products), min(20, len(products)))

            for product in supplier_products:
                # Calculate supplier-specific pricing
                base_price = product.price * price_multiplier
                
                # Add product-specific adjustments
                if product.department.name == 'Herbs & Spices' and 'Mumbai' in supplier.name:
                    base_price *= Decimal('1.20')  # 20% premium for Mumbai spices
                elif product.department.name == 'Vegetables' and 'Fambri' in supplier.name:
                    base_price *= Decimal('0.90')  # 10% discount for internal vegetables
                
                # Random availability based on supplier characteristics
                is_available = random.random() < availability_rate
                stock_quantity = random.randint(10, 100) if is_available else 0
                
                supplier_product, created = SupplierProduct.objects.get_or_create(
                    supplier=supplier,
                    product=product,
                    defaults={
                        'supplier_product_code': f'{supplier.name[:3].upper()}-{product.id:04d}',
                        'supplier_product_name': product.name,
                        'supplier_category_code': product.department.name[:3].upper(),
                        'supplier_price': base_price.quantize(Decimal('0.01')),
                        'currency': 'ZAR',
                        'is_available': is_available,
                        'stock_quantity': stock_quantity,
                        'minimum_order_quantity': random.randint(1, 5),
                        'lead_time_days': supplier.lead_time_days,
                        'quality_rating': Decimal(str(random.uniform(3.5, 5.0))).quantize(Decimal('0.1'))
                    }
                )
                
                if created:
                    created_count += 1

        self.stdout.write(f'🏭 Created {created_count} supplier-product relationships with realistic pricing')
        self.stdout.write(f'💡 Fambri Internal: Cost pricing, Tania: Premium emergency, Mumbai: Specialty spices')

    def create_customer_price_lists(self):
        """Create customer-specific price lists based on their segments and order patterns"""
        # Get customers and their appropriate pricing rules
        customer_segments = {
            'premium': ['Casa Bella', 'Pecanwood Golf Estate', 'Culinary Institute'],
            'standard': ['Maltos', 'T-junction', 'Venue', 'Mugg and Bean'],
            'budget': ['Debonair Pizza', 'Wimpy Mooikloof', 'Barchef Entertainment'],
            'retail': ['Marco', 'Sylvia', 'Arthur']
        }
        
        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            admin_user = User.objects.filter(user_type='admin').first()
        
        created_lists = 0
        created_items = 0
        
        for segment, customer_names in customer_segments.items():
            # Get the pricing rule for this segment
            if segment == 'retail':
                pricing_rule = PricingRule.objects.filter(customer_segment='retail').first()
            else:
                pricing_rule = PricingRule.objects.filter(customer_segment=segment).first()
            
            if not pricing_rule:
                continue
                
            for customer_name in customer_names:
                # Find customer user
                customer_user = User.objects.filter(
                    restaurantprofile__business_name__icontains=customer_name
                ).first()
                
                if not customer_user:
                    customer_user = User.objects.filter(
                        first_name__icontains=customer_name.split()[0]
                    ).first()
                
                if not customer_user:
                    continue
                
                # Create weekly price list
                price_list, created = CustomerPriceList.objects.get_or_create(
                    customer=customer_user,
                    effective_from=date.today(),
                    defaults={
                        'pricing_rule': pricing_rule,
                        'list_name': f'Weekly Price List - {customer_name} - {date.today().strftime("%Y-%m-%d")}',
                        'effective_until': date.today() + timedelta(days=7),
                        'generated_by': admin_user,
                        'based_on_market_data': date.today(),
                        'market_data_source': 'Tshwane Market',
                        'status': 'active'
                    }
                )
                
                if created:
                    created_lists += 1
                    
                    # Create price list items for relevant products
                    products = Product.objects.all()
                    
                    # Filter products based on customer type and order patterns
                    if segment == 'retail':
                        # Private customers - household basics
                        relevant_products = products.filter(
                            department__name__in=['Vegetables', 'Fruits']
                        )[:20]  # Limit to 20 household items
                    elif 'Casa Bella' in customer_name:
                        # Italian restaurant - premium ingredients
                        relevant_products = products.filter(
                            department__name__in=['Herbs & Spices', 'Vegetables', 'Specialty Items']
                        )[:35]
                    elif 'Pecanwood' in customer_name:
                        # Golf estate - bulk institutional items
                        relevant_products = products.all()[:50]  # Large variety
                    else:
                        # Standard restaurants - general produce
                        relevant_products = products.filter(
                            department__name__in=['Vegetables', 'Fruits', 'Herbs & Spices']
                        )[:30]
                    
                    total_list_value = Decimal('0.00')
                    markup_percentages = []
                    
                    for product in relevant_products:
                        # Get latest market price
                        latest_market_price = MarketPrice.objects.filter(
                            matched_product=product
                        ).order_by('-invoice_date').first()
                        
                        if not latest_market_price:
                            continue
                        
                        # Calculate markup using pricing rule
                        markup_percentage = pricing_rule.calculate_markup(
                            product, 
                            latest_market_price.unit_price_excl_vat,
                            volatility_level='stable'  # Simplified for seeding
                        )
                        
                        # Calculate customer price
                        market_price_excl = latest_market_price.unit_price_excl_vat
                        customer_price_excl = market_price_excl * (1 + markup_percentage / 100)
                        customer_price_incl = customer_price_excl * Decimal('1.15')  # Add VAT
                        
                        # Create price list item
                        CustomerPriceListItem.objects.create(
                            price_list=price_list,
                            product=product,
                            market_price_excl_vat=market_price_excl,
                            market_price_incl_vat=latest_market_price.unit_price_incl_vat,
                            market_price_date=latest_market_price.invoice_date,
                            markup_percentage=markup_percentage,
                            customer_price_excl_vat=customer_price_excl.quantize(Decimal('0.01')),
                            customer_price_incl_vat=customer_price_incl.quantize(Decimal('0.01')),
                            unit_of_measure=product.unit,
                            product_category=product.department.name,
                            is_volatile=product.department.name in ['Fruits', 'Specialty Items'],
                            is_seasonal=product.department.name == 'Fruits',
                            is_premium=segment == 'premium'
                        )
                        
                        created_items += 1
                        total_list_value += customer_price_incl
                        markup_percentages.append(markup_percentage)
                    
                    # Update price list statistics
                    if markup_percentages:
                        price_list.total_products = len(markup_percentages)
                        price_list.average_markup_percentage = sum(markup_percentages) / len(markup_percentages)
                        price_list.total_list_value = total_list_value
                        price_list.save()
                    
                    self.stdout.write(f'📋 Created price list for {customer_name}: {len(markup_percentages)} items, avg markup {price_list.average_markup_percentage:.1f}%')

        self.stdout.write(f'💰 Created {created_lists} customer price lists with {created_items} total items')
        self.stdout.write(f'🎯 Segment-based pricing: Premium (35%), Standard (25%), Budget (18%), Retail (15%)')

    def create_procurement_recommendations(self):
        """Create intelligent procurement recommendations based on stock levels and demand"""
        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            admin_user = User.objects.filter(user_type='admin').first()
        
        if not admin_user:
            return
        
        # Create a mock stock analysis for procurement recommendations
        stock_analysis = StockAnalysis.objects.create(
            order_period_start=date.today(),
            order_period_end=date.today() + timedelta(days=3),
            total_orders_value=Decimal('15000.00'),
            total_stock_value=Decimal('12000.00'),
            fulfillment_percentage=Decimal('80.00'),
            status='completed',
            created_by=admin_user,
            notes='Automated analysis for procurement recommendations'
        )
        
        # Find products that need procurement (low stock or high demand)
        low_stock_products = []
        for product in Product.objects.all():
            if product.stock_level < product.minimum_stock:
                low_stock_products.append(product)
                if len(low_stock_products) >= 10:
                    break
        
        created_count = 0
        for product in low_stock_products:
            # Get best supplier for this product
            best_supplier_product = SupplierProduct.objects.filter(
                product=product,
                is_available=True
            ).order_by('supplier_price').first()
            
            if not best_supplier_product:
                continue
            
            # Calculate recommended quantity (2x minimum stock)
            recommended_qty = max(product.minimum_stock * 2, Decimal('10.0'))
            
            # Get market price trend
            recent_prices = MarketPrice.objects.filter(
                matched_product=product
            ).order_by('-invoice_date')[:7]  # Last 7 prices
            
            if len(recent_prices) >= 2:
                recent_prices_list = list(recent_prices)
                price_trend = 'rising' if recent_prices_list[0].unit_price_incl_vat > recent_prices_list[-1].unit_price_incl_vat else 'falling'
            else:
                price_trend = 'stable'
            
            # Determine urgency based on stock level
            stock_ratio = product.stock_level / product.minimum_stock if product.minimum_stock > 0 else 0
            if stock_ratio <= 0.2:
                urgency = 'urgent'
            elif stock_ratio <= 0.5:
                urgency = 'high'
            elif stock_ratio <= 0.8:
                urgency = 'medium'
            else:
                urgency = 'low'
            
            # Calculate recommended order date based on urgency and lead time
            if urgency == 'urgent':
                order_date = date.today()
            elif urgency == 'high':
                order_date = date.today() + timedelta(days=1)
            else:
                order_date = date.today() + timedelta(days=3)
            
            expected_delivery = order_date + timedelta(days=best_supplier_product.get_effective_lead_time())
            
            ProcurementRecommendation.objects.create(
                stock_analysis=stock_analysis,
                product=product,
                recommended_quantity=recommended_qty,
                recommended_supplier=best_supplier_product.supplier,
                current_market_price=best_supplier_product.supplier_price,
                average_market_price_30d=best_supplier_product.supplier_price * Decimal('1.05'),  # Simulated average
                price_trend=price_trend,
                urgency_level=urgency,
                recommended_order_date=order_date,
                expected_delivery_date=expected_delivery,
                estimated_total_cost=recommended_qty * best_supplier_product.supplier_price,
                potential_savings=Decimal('0.00'),  # Could calculate vs other suppliers
                status='pending',
                created_by=admin_user,
                notes=f'Auto-generated recommendation: {product.name} stock level ({product.stock_level}) below minimum ({product.minimum_stock})'
            )
            
            created_count += 1

        self.stdout.write(f'🔄 Created {created_count} intelligent procurement recommendations')
        self.stdout.write(f'⚡ Urgency levels: Urgent (same day), High (1 day), Medium (3 days)')
        self.stdout.write(f'🎯 Recommendations based on stock levels, supplier pricing, and lead times')


# Import Django's F expression for database queries
from django.db import models
