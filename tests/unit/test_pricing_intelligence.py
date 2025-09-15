"""
Unit tests for the pricing intelligence system
Tests individual components of the dynamic pricing system
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from decimal import Decimal
from datetime import date, timedelta

from inventory.models import PricingRule, MarketPrice, CustomerPriceList, CustomerPriceListItem
from products.models import Product, Department
from accounts.models import User

User = get_user_model()


class PricingRuleTest(TestCase):
    """Test pricing rule calculations and logic"""
    
    def setUp(self):
        # Create test user
        self.admin_user = User.objects.create_user(
            email='admin@test.com',
            password='testpass123',
            user_type='admin',
            is_staff=True
        )
        
        # Create test department and product
        self.department = Department.objects.create(
            name='Test Vegetables',
            description='Test department'
        )
        
        self.product = Product.objects.create(
            name='Test Lettuce',
            department=self.department,
            price=Decimal('25.00'),
            unit='kg'
        )
        
        # Create test pricing rule
        self.pricing_rule = PricingRule.objects.create(
            name='Test Premium Rule',
            customer_segment='premium',
            base_markup_percentage=Decimal('35.00'),
            volatility_adjustment=Decimal('5.00'),
            minimum_margin_percentage=Decimal('25.00'),
            category_adjustments={'vegetables': 10},
            trend_multiplier=Decimal('1.10'),
            seasonal_adjustment=Decimal('5.00'),
            effective_from=date.today(),
            created_by=self.admin_user
        )

    def test_pricing_rule_creation(self):
        """Test that pricing rules are created correctly"""
        self.assertEqual(self.pricing_rule.name, 'Test Premium Rule')
        self.assertEqual(self.pricing_rule.customer_segment, 'premium')
        self.assertEqual(self.pricing_rule.base_markup_percentage, Decimal('35.00'))

    def test_pricing_rule_effectiveness(self):
        """Test pricing rule effectiveness validation"""
        # Current rule should be effective
        self.assertTrue(self.pricing_rule.is_effective())
        
        # Future rule should not be effective yet
        future_rule = PricingRule.objects.create(
            name='Future Rule',
            customer_segment='standard',
            base_markup_percentage=Decimal('25.00'),
            minimum_margin_percentage=Decimal('15.00'),
            effective_from=date.today() + timedelta(days=30),
            created_by=self.admin_user
        )
        self.assertFalse(future_rule.is_effective())
        
        # Expired rule should not be effective
        expired_rule = PricingRule.objects.create(
            name='Expired Rule',
            customer_segment='budget',
            base_markup_percentage=Decimal('18.00'),
            minimum_margin_percentage=Decimal('12.00'),
            effective_from=date.today() - timedelta(days=60),
            effective_until=date.today() - timedelta(days=30),
            created_by=self.admin_user
        )
        self.assertFalse(expired_rule.is_effective())

    def test_markup_calculation_base(self):
        """Test basic markup calculation"""
        market_price = Decimal('20.00')
        
        # Base calculation without adjustments
        markup = self.pricing_rule.calculate_markup(
            self.product, 
            market_price, 
            volatility_level='stable'
        )
        
        # Should be base (35%) + category adjustment (10%) * trend multiplier (1.10) + seasonal (5%)
        # (35 + 10) * 1.10 + 5 = 49.5 + 5 = 54.5
        expected_markup = Decimal('54.50')
        self.assertEqual(markup, expected_markup)

    def test_markup_calculation_with_volatility(self):
        """Test markup calculation with volatility adjustment"""
        market_price = Decimal('20.00')
        
        markup = self.pricing_rule.calculate_markup(
            self.product, 
            market_price, 
            volatility_level='volatile'
        )
        
        # Should include volatility adjustment: (35 + 5 + 10) * 1.10 + 5 = 55 + 5 = 60
        expected_markup = Decimal('60.00')
        self.assertEqual(markup, expected_markup)

    def test_minimum_margin_enforcement(self):
        """Test that minimum margin is enforced"""
        # Create a rule with very low base markup
        low_markup_rule = PricingRule.objects.create(
            name='Low Markup Rule',
            customer_segment='wholesale',
            base_markup_percentage=Decimal('5.00'),
            minimum_margin_percentage=Decimal('15.00'),
            effective_from=date.today(),
            created_by=self.admin_user
        )
        
        market_price = Decimal('20.00')
        markup = low_markup_rule.calculate_markup(self.product, market_price)
        
        # Should enforce minimum margin of 15%
        self.assertEqual(markup, Decimal('15.00'))


class MarketPriceTest(TestCase):
    """Test market price tracking and analysis"""
    
    def setUp(self):
        self.department = Department.objects.create(
            name='Test Fruits',
            description='Test department'
        )
        
        self.product = Product.objects.create(
            name='Test Oranges',
            department=self.department,
            price=Decimal('30.00'),
            unit='kg'
        )

    def test_market_price_creation(self):
        """Test market price record creation"""
        market_price = MarketPrice.objects.create(
            supplier_name='Test Market',
            invoice_date=date.today(),
            product_name='Test Oranges',
            matched_product=self.product,
            unit_price_excl_vat=Decimal('25.00'),
            vat_amount=Decimal('3.75'),
            quantity_unit='kg'
        )
        
        self.assertEqual(market_price.supplier_name, 'Test Market')
        self.assertEqual(market_price.unit_price_incl_vat, Decimal('28.75'))

    def test_vat_calculation(self):
        """Test automatic VAT calculation"""
        market_price = MarketPrice.objects.create(
            supplier_name='Test Market',
            invoice_date=date.today(),
            product_name='Test Oranges',
            unit_price_excl_vat=Decimal('20.00'),
            vat_amount=Decimal('3.00'),
            quantity_unit='kg'
        )
        
        # VAT percentage should be 15%
        self.assertEqual(market_price.vat_percentage, Decimal('15.00'))

    def test_price_trend_analysis(self):
        """Test price trend analysis over time"""
        # Create price history
        base_date = date.today() - timedelta(days=30)
        
        prices = [
            (base_date, Decimal('20.00')),
            (base_date + timedelta(days=7), Decimal('22.00')),
            (base_date + timedelta(days=14), Decimal('25.00')),
            (base_date + timedelta(days=21), Decimal('24.00')),
            (base_date + timedelta(days=28), Decimal('26.00')),
        ]
        
        for price_date, price in prices:
            MarketPrice.objects.create(
                supplier_name='Test Market',
                invoice_date=price_date,
                product_name='Test Oranges',
                matched_product=self.product,
                unit_price_excl_vat=price,
                vat_amount=price * Decimal('0.15'),
                quantity_unit='kg'
            )
        
        # Test price retrieval
        latest_price = MarketPrice.objects.filter(
            matched_product=self.product
        ).order_by('-invoice_date').first()
        
        self.assertEqual(latest_price.unit_price_excl_vat, Decimal('26.00'))
        
        # Test price history count
        price_count = MarketPrice.objects.filter(matched_product=self.product).count()
        self.assertEqual(price_count, 5)


class CustomerPriceListTest(TestCase):
    """Test customer-specific price list generation"""
    
    def setUp(self):
        # Create test users
        self.admin_user = User.objects.create_user(
            email='admin@test.com',
            password='testpass123',
            user_type='admin'
        )
        
        self.customer_user = User.objects.create_user(
            email='customer@test.com',
            password='testpass123',
            user_type='restaurant'
        )
        
        # Create test product
        self.department = Department.objects.create(name='Test Vegetables')
        self.product = Product.objects.create(
            name='Test Carrots',
            department=self.department,
            price=Decimal('20.00'),
            unit='kg'
        )
        
        # Create pricing rule
        self.pricing_rule = PricingRule.objects.create(
            name='Test Standard Rule',
            customer_segment='standard',
            base_markup_percentage=Decimal('25.00'),
            minimum_margin_percentage=Decimal('15.00'),
            effective_from=date.today(),
            created_by=self.admin_user
        )

    def test_customer_price_list_creation(self):
        """Test customer price list creation"""
        price_list = CustomerPriceList.objects.create(
            customer=self.customer_user,
            pricing_rule=self.pricing_rule,
            list_name='Test Price List',
            effective_from=date.today(),
            effective_until=date.today() + timedelta(days=7),
            generated_by=self.admin_user,
            based_on_market_data=date.today(),
            status='active'
        )
        
        self.assertEqual(price_list.customer, self.customer_user)
        self.assertTrue(price_list.is_current)

    def test_price_list_item_calculation(self):
        """Test price list item price calculation"""
        # Create price list
        price_list = CustomerPriceList.objects.create(
            customer=self.customer_user,
            pricing_rule=self.pricing_rule,
            list_name='Test Price List',
            effective_from=date.today(),
            effective_until=date.today() + timedelta(days=7),
            generated_by=self.admin_user,
            based_on_market_data=date.today(),
            status='active'
        )
        
        # Create price list item
        market_price = Decimal('18.00')
        markup_percentage = Decimal('25.00')
        
        price_item = CustomerPriceListItem.objects.create(
            price_list=price_list,
            product=self.product,
            market_price_excl_vat=market_price,
            market_price_incl_vat=market_price * Decimal('1.15'),
            market_price_date=date.today(),
            markup_percentage=markup_percentage,
            customer_price_excl_vat=market_price * (1 + markup_percentage / 100),
            customer_price_incl_vat=market_price * (1 + markup_percentage / 100) * Decimal('1.15'),
            unit_of_measure='kg'
        )
        
        # Test calculations
        expected_customer_price_excl = Decimal('22.50')  # 18.00 * 1.25
        expected_customer_price_incl = Decimal('25.88')  # 22.50 * 1.15
        
        self.assertEqual(price_item.customer_price_excl_vat, expected_customer_price_excl)
        self.assertEqual(price_item.customer_price_incl_vat, expected_customer_price_incl)
        
        # Test margin calculation
        expected_margin = Decimal('4.50')  # 22.50 - 18.00
        self.assertEqual(price_item.margin_amount, expected_margin)

    def test_price_change_tracking(self):
        """Test price change tracking between price lists"""
        # Create price list
        price_list = CustomerPriceList.objects.create(
            customer=self.customer_user,
            pricing_rule=self.pricing_rule,
            list_name='Test Price List',
            effective_from=date.today(),
            effective_until=date.today() + timedelta(days=7),
            generated_by=self.admin_user,
            based_on_market_data=date.today(),
            status='active'
        )
        
        # Create price item with previous price
        price_item = CustomerPriceListItem.objects.create(
            price_list=price_list,
            product=self.product,
            market_price_excl_vat=Decimal('18.00'),
            market_price_incl_vat=Decimal('20.70'),
            market_price_date=date.today(),
            markup_percentage=Decimal('25.00'),
            customer_price_excl_vat=Decimal('22.50'),
            customer_price_incl_vat=Decimal('25.88'),
            previous_price=Decimal('24.00'),  # Previous was higher
            unit_of_measure='kg'
        )
        
        # Test price change calculation
        expected_change = ((Decimal('25.88') - Decimal('24.00')) / Decimal('24.00')) * 100
        self.assertEqual(price_item.price_change_percentage, expected_change.quantize(Decimal('0.01')))
        
        # Test price increase detection
        self.assertTrue(price_item.is_price_increase)
        
        # Test significant change detection (should be False for small changes)
        self.assertFalse(price_item.is_significant_change)
