"""
Unit tests for customer pricing system
Tests dynamic pricing rules, customer price lists, and price calculations
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from decimal import Decimal
from datetime import date, timedelta

from inventory.models import (
    PricingRule, CustomerPriceList, CustomerPriceListItem, MarketPrice
)
from products.models import Product, Department
from accounts.models import User, RestaurantProfile

User = get_user_model()


class PricingRuleTest(TestCase):
    """Test PricingRule calculations and logic"""
    
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
            name='Vegetables',
            description='Fresh vegetables'
        )
        
        self.product = Product.objects.create(
            name='Lettuce',
            department=self.department,
            price=Decimal('25.00'),
            unit='kg'
        )
        
        # Create test pricing rule
        self.pricing_rule = PricingRule.objects.create(
            name='Premium Restaurant Rule',
            customer_segment='premium',
            base_markup_percentage=Decimal('35.00'),
            volatility_adjustment=Decimal('5.00'),
            minimum_margin_percentage=Decimal('25.00'),
            category_adjustments={'vegetables': 10},
            trend_multiplier=Decimal('1.20'),
            seasonal_adjustment=Decimal('2.50'),
            effective_from=date.today(),
            created_by=self.admin_user
        )
    
    def test_is_effective_current_date(self):
        """Test that rule is effective on current date"""
        self.assertTrue(self.pricing_rule.is_effective())
        self.assertTrue(self.pricing_rule.is_effective(date.today()))
    
    def test_is_effective_future_date(self):
        """Test rule effectiveness with future dates"""
        future_date = date.today() + timedelta(days=10)
        
        # Rule without end date should be effective in future
        self.assertTrue(self.pricing_rule.is_effective(future_date))
        
        # Rule with end date before future date should not be effective
        self.pricing_rule.effective_until = date.today() + timedelta(days=5)
        self.pricing_rule.save()
        
        self.assertFalse(self.pricing_rule.is_effective(future_date))
    
    def test_is_effective_past_date(self):
        """Test rule effectiveness with past dates"""
        past_date = date.today() - timedelta(days=10)
        
        # Rule effective from today should not be effective in past
        self.assertFalse(self.pricing_rule.is_effective(past_date))
    
    def test_is_effective_inactive_rule(self):
        """Test that inactive rules are never effective"""
        self.pricing_rule.is_active = False
        self.pricing_rule.save()
        
        self.assertFalse(self.pricing_rule.is_effective())
    
    def test_calculate_markup_base_case(self):
        """Test basic markup calculation"""
        market_price = Decimal('20.00')
        
        markup = self.pricing_rule.calculate_markup(
            self.product, 
            market_price, 
            'stable'
        )
        
        # Base: 35% + Category: 10% = 45%
        # Trend multiplier: 45% * 1.20 = 54%
        # Seasonal: 54% + 2.5% = 56.5%
        expected_markup = Decimal('56.50')
        self.assertEqual(markup, expected_markup)
    
    def test_calculate_markup_volatile_market(self):
        """Test markup calculation with volatile market conditions"""
        market_price = Decimal('20.00')
        
        markup = self.pricing_rule.calculate_markup(
            self.product,
            market_price,
            'volatile'
        )
        
        # Base: 35% + Volatility: 5% + Category: 10% = 50%
        # Trend multiplier: 50% * 1.20 = 60%
        # Seasonal: 60% + 2.5% = 62.5%
        expected_markup = Decimal('62.50')
        self.assertEqual(markup, expected_markup)
    
    def test_calculate_markup_minimum_margin_enforcement(self):
        """Test that minimum margin is enforced"""
        # Create rule with high minimum margin
        rule = PricingRule.objects.create(
            name='High Minimum Rule',
            customer_segment='budget',
            base_markup_percentage=Decimal('10.00'),  # Low base
            minimum_margin_percentage=Decimal('30.00'),  # High minimum
            effective_from=date.today(),
            created_by=self.admin_user
        )
        
        markup = rule.calculate_markup(self.product, Decimal('20.00'), 'stable')
        
        # Should return minimum margin (30%) instead of calculated (10%)
        self.assertEqual(markup, Decimal('30.00'))
    
    def test_calculate_markup_no_category_adjustment(self):
        """Test markup calculation for product without category adjustment"""
        # Create product in department not in category_adjustments
        other_department = Department.objects.create(name='Fruits')
        fruit_product = Product.objects.create(
            name='Apple',
            department=other_department,
            price=Decimal('15.00'),
            unit='kg'
        )
        
        markup = self.pricing_rule.calculate_markup(
            fruit_product,
            Decimal('20.00'),
            'stable'
        )
        
        # Base: 35% + Category: 0% = 35%
        # Trend multiplier: 35% * 1.20 = 42%
        # Seasonal: 42% + 2.5% = 44.5%
        expected_markup = Decimal('44.50')
        self.assertEqual(markup, expected_markup)


class CustomerPriceListTest(TestCase):
    """Test CustomerPriceList functionality"""
    
    def setUp(self):
        # Create test users
        self.admin_user = User.objects.create_user(
            email='admin@test.com',
            password='testpass123',
            user_type='admin'
        )
        
        self.customer = User.objects.create_user(
            email='customer@restaurant.com',
            password='testpass123',
            user_type='restaurant'
        )
        
        # Create restaurant profile
        RestaurantProfile.objects.create(
            user=self.customer,
            business_name='Test Restaurant',
            address='123 Test St',
            city='Test City',
            postal_code='12345'
        )
        
        # Create pricing rule
        self.pricing_rule = PricingRule.objects.create(
            name='Standard Rule',
            customer_segment='standard',
            base_markup_percentage=Decimal('25.00'),
            minimum_margin_percentage=Decimal('15.00'),
            effective_from=date.today(),
            created_by=self.admin_user
        )
        
        # Create price list
        self.price_list = CustomerPriceList.objects.create(
            customer=self.customer,
            pricing_rule=self.pricing_rule,
            list_name='Weekly Price List - Test',
            effective_from=date.today(),
            effective_until=date.today() + timedelta(days=7),
            generated_by=self.admin_user,
            based_on_market_data=date.today(),
            status='active'
        )
    
    def test_is_current_property(self):
        """Test is_current property logic"""
        # Current price list should be current
        self.assertTrue(self.price_list.is_current)
        
        # Past price list should not be current
        self.price_list.effective_until = date.today() - timedelta(days=1)
        self.price_list.save()
        
        self.assertFalse(self.price_list.is_current)
        
        # Future price list should not be current
        self.price_list.effective_from = date.today() + timedelta(days=1)
        self.price_list.effective_until = date.today() + timedelta(days=8)
        self.price_list.save()
        
        self.assertFalse(self.price_list.is_current)
    
    def test_days_until_expiry_property(self):
        """Test days_until_expiry calculation"""
        # Price list expires in 7 days
        self.assertEqual(self.price_list.days_until_expiry, 7)
        
        # Price list expires tomorrow
        self.price_list.effective_until = date.today() + timedelta(days=1)
        self.price_list.save()
        
        self.assertEqual(self.price_list.days_until_expiry, 1)
        
        # Expired price list
        self.price_list.effective_until = date.today() - timedelta(days=1)
        self.price_list.save()
        
        self.assertEqual(self.price_list.days_until_expiry, -1)
    
    def test_activate_method(self):
        """Test price list activation"""
        # Create another active price list for same customer
        other_price_list = CustomerPriceList.objects.create(
            customer=self.customer,
            pricing_rule=self.pricing_rule,
            list_name='Other Price List',
            effective_from=date.today() - timedelta(days=1),
            effective_until=date.today() + timedelta(days=6),
            generated_by=self.admin_user,
            based_on_market_data=date.today(),
            status='active'
        )
        
        # Activate new price list
        self.price_list.activate()
        
        # Check that new list is active and old list is expired
        self.price_list.refresh_from_db()
        other_price_list.refresh_from_db()
        
        self.assertEqual(self.price_list.status, 'active')
        self.assertEqual(other_price_list.status, 'expired')


class CustomerPriceListItemTest(TestCase):
    """Test CustomerPriceListItem calculations"""
    
    def setUp(self):
        # Create test data
        self.admin_user = User.objects.create_user(
            email='admin@test.com',
            password='testpass123',
            user_type='admin'
        )
        
        self.customer = User.objects.create_user(
            email='customer@restaurant.com',
            password='testpass123',
            user_type='restaurant'
        )
        
        self.department = Department.objects.create(name='Vegetables')
        self.product = Product.objects.create(
            name='Lettuce',
            department=self.department,
            price=Decimal('25.00'),
            unit='kg'
        )
        
        self.pricing_rule = PricingRule.objects.create(
            name='Test Rule',
            customer_segment='standard',
            base_markup_percentage=Decimal('25.00'),
            minimum_margin_percentage=Decimal('15.00'),
            effective_from=date.today(),
            created_by=self.admin_user
        )
        
        self.price_list = CustomerPriceList.objects.create(
            customer=self.customer,
            pricing_rule=self.pricing_rule,
            list_name='Test Price List',
            effective_from=date.today(),
            effective_until=date.today() + timedelta(days=7),
            generated_by=self.admin_user,
            based_on_market_data=date.today(),
            status='active'
        )
        
        # Create price list item
        self.price_item = CustomerPriceListItem.objects.create(
            price_list=self.price_list,
            product=self.product,
            market_price_excl_vat=Decimal('20.00'),
            market_price_incl_vat=Decimal('23.00'),
            market_price_date=date.today(),
            markup_percentage=Decimal('25.00'),
            customer_price_excl_vat=Decimal('25.00'),
            customer_price_incl_vat=Decimal('28.75'),
            previous_price=Decimal('27.00'),
            unit_of_measure='kg'
        )
    
    def test_margin_amount_calculation(self):
        """Test margin amount calculation"""
        # Customer price excl VAT (25.00) - Market price excl VAT (20.00) = 5.00
        expected_margin = Decimal('5.00')
        self.assertEqual(self.price_item.margin_amount, expected_margin)
    
    def test_is_price_increase_property(self):
        """Test price increase detection"""
        # Current: 28.75, Previous: 27.00 = increase
        self.price_item.price_change_percentage = Decimal('6.48')  # Positive change
        self.assertTrue(self.price_item.is_price_increase)
        
        # Test price decrease
        self.price_item.price_change_percentage = Decimal('-5.00')  # Negative change
        self.assertFalse(self.price_item.is_price_increase)
    
    def test_is_significant_change_property(self):
        """Test significant price change detection"""
        # 15% change is significant (>10%)
        self.price_item.price_change_percentage = Decimal('15.00')
        self.assertTrue(self.price_item.is_significant_change)
        
        # 5% change is not significant (<10%)
        self.price_item.price_change_percentage = Decimal('5.00')
        self.assertFalse(self.price_item.is_significant_change)
        
        # -15% change is significant (absolute value >10%)
        self.price_item.price_change_percentage = Decimal('-15.00')
        self.assertTrue(self.price_item.is_significant_change)


class ProductCustomerPriceTest(TestCase):
    """Test Product.get_customer_price() method"""
    
    def setUp(self):
        # Create test data
        self.admin_user = User.objects.create_user(
            email='admin@test.com',
            password='testpass123',
            user_type='admin'
        )
        
        self.customer = User.objects.create_user(
            email='customer@restaurant.com',
            password='testpass123',
            user_type='restaurant'
        )
        
        self.department = Department.objects.create(name='Vegetables')
        self.product = Product.objects.create(
            name='Lettuce',
            department=self.department,
            price=Decimal('25.00'),  # Base price
            unit='kg'
        )
    
    def test_get_customer_price_with_active_price_list(self):
        """Test customer price retrieval with active price list"""
        # Create pricing rule and price list
        pricing_rule = PricingRule.objects.create(
            name='Test Rule',
            customer_segment='standard',
            base_markup_percentage=Decimal('25.00'),
            minimum_margin_percentage=Decimal('15.00'),
            effective_from=date.today(),
            created_by=self.admin_user
        )
        
        price_list = CustomerPriceList.objects.create(
            customer=self.customer,
            pricing_rule=pricing_rule,
            list_name='Test Price List',
            effective_from=date.today(),
            effective_until=date.today() + timedelta(days=7),
            generated_by=self.admin_user,
            based_on_market_data=date.today(),
            status='active'
        )
        
        # Create price list item with customer-specific price
        CustomerPriceListItem.objects.create(
            price_list=price_list,
            product=self.product,
            market_price_excl_vat=Decimal('20.00'),
            market_price_incl_vat=Decimal('23.00'),
            market_price_date=date.today(),
            markup_percentage=Decimal('30.00'),
            customer_price_excl_vat=Decimal('26.00'),
            customer_price_incl_vat=Decimal('29.90'),  # Customer-specific price
            unit_of_measure='kg'
        )
        
        # Should return customer-specific price
        customer_price = self.product.get_customer_price(self.customer)
        self.assertEqual(customer_price, Decimal('29.90'))
    
    def test_get_customer_price_fallback_to_base_price(self):
        """Test fallback to base price when no customer price list exists"""
        # No price list exists, should return base product price
        customer_price = self.product.get_customer_price(self.customer)
        self.assertEqual(customer_price, self.product.price)
    
    def test_get_customer_price_with_expired_price_list(self):
        """Test fallback when price list is expired"""
        # Create expired price list
        pricing_rule = PricingRule.objects.create(
            name='Test Rule',
            customer_segment='standard',
            base_markup_percentage=Decimal('25.00'),
            minimum_margin_percentage=Decimal('15.00'),
            effective_from=date.today() - timedelta(days=10),
            created_by=self.admin_user
        )
        
        price_list = CustomerPriceList.objects.create(
            customer=self.customer,
            pricing_rule=pricing_rule,
            list_name='Expired Price List',
            effective_from=date.today() - timedelta(days=10),
            effective_until=date.today() - timedelta(days=1),  # Expired
            generated_by=self.admin_user,
            based_on_market_data=date.today() - timedelta(days=10),
            status='expired'
        )
        
        CustomerPriceListItem.objects.create(
            price_list=price_list,
            product=self.product,
            customer_price_incl_vat=Decimal('35.00'),
            market_price_excl_vat=Decimal('20.00'),
            market_price_incl_vat=Decimal('23.00'),
            market_price_date=date.today() - timedelta(days=10),
            markup_percentage=Decimal('30.00'),
            customer_price_excl_vat=Decimal('30.43'),
            unit_of_measure='kg'
        )
        
        # Should fallback to base price since price list is expired
        customer_price = self.product.get_customer_price(self.customer)
        self.assertEqual(customer_price, self.product.price)
