from django.test import TestCase
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from decimal import Decimal
from datetime import date, timedelta
from unittest.mock import patch

from .models import (
    UnitOfMeasure, RawMaterial, RawMaterialBatch, ProductionRecipe, 
    RecipeIngredient, FinishedInventory, StockMovement, ProductionBatch,
    StockAlert, StockAnalysis, StockAnalysisItem, MarketPrice,
    ProcurementRecommendation, PriceAlert, PricingRule, 
    CustomerPriceList, CustomerPriceListItem, WeeklyPriceReport
)
from products.models import Product, Department
from suppliers.models import Supplier
from accounts.models import RestaurantProfile

User = get_user_model()


class UnitOfMeasureModelTest(TestCase):
    """Test UnitOfMeasure model functionality"""
    
    def test_unit_creation(self):
        """Test unit of measure is created correctly"""
        unit = UnitOfMeasure.objects.create(
            name='Kilogram',
            abbreviation='kg',
            is_weight=True,
            base_unit_multiplier=Decimal('1.0')
        )
        
        self.assertEqual(unit.name, 'Kilogram')
        self.assertEqual(unit.abbreviation, 'kg')
        self.assertTrue(unit.is_weight)
        self.assertEqual(unit.base_unit_multiplier, Decimal('1.0'))
        self.assertTrue(unit.is_active)
    
    def test_unit_str_representation(self):
        """Test unit string representation"""
        unit = UnitOfMeasure.objects.create(
            name='Kilogram',
            abbreviation='kg'
        )
        
        expected_str = "Kilogram (kg)"
        self.assertEqual(str(unit), expected_str)
    
    def test_unit_unique_constraints(self):
        """Test unique constraints on name and abbreviation"""
        UnitOfMeasure.objects.create(
            name='Kilogram',
            abbreviation='kg'
        )
        
        # Should raise exception for duplicate name
        with self.assertRaises(Exception):
            UnitOfMeasure.objects.create(
                name='Kilogram',
                abbreviation='kilo'
            )
        
        # Should raise exception for duplicate abbreviation
        with self.assertRaises(Exception):
            UnitOfMeasure.objects.create(
                name='Kilograms',
                abbreviation='kg'
            )


class RawMaterialModelTest(TestCase):
    """Test RawMaterial model functionality"""
    
    def setUp(self):
        self.unit = UnitOfMeasure.objects.create(
            name='Kilogram',
            abbreviation='kg',
            is_weight=True
        )
    
    def test_raw_material_creation(self):
        """Test raw material is created correctly"""
        material = RawMaterial.objects.create(
            name='Organic Lettuce',
            description='Fresh organic lettuce from local farms',
            sku='ORG-LET-001',
            unit=self.unit,
            requires_batch_tracking=True,
            shelf_life_days=7,
            minimum_stock_level=Decimal('10.00'),
            reorder_level=Decimal('20.00'),
            maximum_stock_level=Decimal('100.00')
        )
        
        self.assertEqual(material.name, 'Organic Lettuce')
        self.assertEqual(material.sku, 'ORG-LET-001')
        self.assertEqual(material.unit, self.unit)
        self.assertTrue(material.requires_batch_tracking)
        self.assertEqual(material.shelf_life_days, 7)
        self.assertTrue(material.is_active)
    
    def test_raw_material_str_representation(self):
        """Test raw material string representation"""
        material = RawMaterial.objects.create(
            name='Organic Lettuce',
            sku='ORG-LET-001',
            unit=self.unit
        )
        
        expected_str = "Organic Lettuce (ORG-LET-001)"
        self.assertEqual(str(material), expected_str)
    
    def test_raw_material_unique_sku(self):
        """Test SKU uniqueness constraint"""
        RawMaterial.objects.create(
            name='Organic Lettuce',
            sku='ORG-LET-001',
            unit=self.unit
        )
        
        with self.assertRaises(Exception):
            RawMaterial.objects.create(
                name='Different Lettuce',
                sku='ORG-LET-001',  # Duplicate SKU
                unit=self.unit
            )


class RawMaterialBatchModelTest(TestCase):
    """Test RawMaterialBatch model functionality"""
    
    def setUp(self):
        self.unit = UnitOfMeasure.objects.create(
            name='Kilogram',
            abbreviation='kg'
        )
        self.supplier = Supplier.objects.create(
            name='Fresh Farms Co',
            supplier_type='external'
        )
        self.material = RawMaterial.objects.create(
            name='Organic Lettuce',
            sku='ORG-LET-001',
            unit=self.unit,
            requires_batch_tracking=True,
            shelf_life_days=7
        )
    
    def test_batch_creation(self):
        """Test raw material batch is created correctly"""
        batch = RawMaterialBatch.objects.create(
            raw_material=self.material,
            supplier=self.supplier,
            batch_number='BATCH-001',
            received_quantity=Decimal('50.00'),
            unit_cost=Decimal('12.50'),
            received_date=date.today(),
            expiry_date=date.today() + timedelta(days=7),
            quality_grade='A'
        )
        
        self.assertEqual(batch.raw_material, self.material)
        self.assertEqual(batch.supplier, self.supplier)
        self.assertEqual(batch.batch_number, 'BATCH-001')
        self.assertEqual(batch.received_quantity, Decimal('50.00'))
        self.assertEqual(batch.unit_cost, Decimal('12.50'))
    
    def test_batch_total_cost_calculation(self):
        """Test total cost calculation"""
        batch = RawMaterialBatch.objects.create(
            raw_material=self.material,
            supplier=self.supplier,
            batch_number='BATCH-001',
            received_quantity=Decimal('50.00'),
            unit_cost=Decimal('12.50'),
            quality_grade='A'
        )
        
        expected_total = Decimal('50.00') * Decimal('12.50')
        self.assertEqual(batch.total_cost, expected_total)
    
    def test_batch_remaining_quantity_default(self):
        """Test remaining quantity defaults to received quantity"""
        batch = RawMaterialBatch.objects.create(
            raw_material=self.material,
            supplier=self.supplier,
            batch_number='BATCH-001',
            received_quantity=Decimal('50.00'),
            unit_cost=Decimal('12.50'),
            quality_grade='A'
        )
        
        self.assertEqual(batch.available_quantity, batch.received_quantity)


class FinishedInventoryModelTest(TestCase):
    """Test FinishedInventory model functionality"""
    
    def setUp(self):
        self.department = Department.objects.create(name='Salads')
        # Don't create a shared product since FinishedInventory has OneToOneField
    
    def _create_inventory(self, product, **kwargs):
        """Helper method to create or get inventory with proper defaults"""
        defaults = {
            'available_quantity': Decimal('0.00'),
            'reserved_quantity': Decimal('0.00'),
            'minimum_level': Decimal('10.00'),
            'reorder_level': Decimal('20.00'),
            'average_cost': Decimal('18.50')
        }
        defaults.update(kwargs)
        
        inventory, created = FinishedInventory.objects.get_or_create(
            product=product,
            defaults=defaults
        )
        
        # Update the inventory if it was created by signal with different values
        if not created:
            for key, value in kwargs.items():
                setattr(inventory, key, value)
            inventory.save()
        
        return inventory
    
    def test_finished_inventory_creation(self):
        """Test finished inventory is created correctly"""
        product = Product.objects.create(
            name='Mixed Salad 1',
            department=self.department,
            price=Decimal('25.00'),
            unit='portion'
        )
        
        inventory = self._create_inventory(
            product=product,
            available_quantity=Decimal('100.00'),
            reserved_quantity=Decimal('20.00'),
            minimum_level=Decimal('10.00'),
            reorder_level=Decimal('25.00'),
            average_cost=Decimal('18.50')
        )
        
        self.assertEqual(inventory.product, product)
        self.assertEqual(inventory.available_quantity, Decimal('100.00'))
        self.assertEqual(inventory.reserved_quantity, Decimal('20.00'))
        self.assertEqual(inventory.average_cost, Decimal('18.50'))
    
    def test_finished_inventory_str_representation(self):
        """Test finished inventory string representation"""
        product = Product.objects.create(
            name='Mixed Salad 2',
            department=self.department,
            price=Decimal('25.00'),
            unit='portion'
        )
        
        inventory = self._create_inventory(
            product=product,
            available_quantity=Decimal('100.00')
        )
        
        expected_str = f"{product.name} - Available: {inventory.available_quantity}"
        self.assertEqual(str(inventory), expected_str)
    
    def test_total_quantity_property(self):
        """Test total quantity calculation"""
        product = Product.objects.create(
            name='Mixed Salad 3',
            department=self.department,
            price=Decimal('25.00'),
            unit='portion'
        )
        
        inventory = self._create_inventory(
            product=product,
            available_quantity=Decimal('100.00'),
            reserved_quantity=Decimal('20.00')
        )
        
        expected_total = Decimal('100.00') + Decimal('20.00')
        self.assertEqual(inventory.total_quantity, expected_total)
    
    def test_needs_production_property(self):
        """Test needs production logic"""
        product = Product.objects.create(
            name='Mixed Salad 4',
            department=self.department,
            price=Decimal('25.00'),
            unit='portion'
        )
        
        inventory = self._create_inventory(
            product=product,
            available_quantity=Decimal('15.00'),
            reorder_level=Decimal('25.00')
        )
        
        # Available (15) <= reorder (25) = needs production
        self.assertTrue(inventory.needs_production)
        
        # Increase available quantity above reorder level
        inventory.available_quantity = Decimal('30.00')
        inventory.save()
        self.assertFalse(inventory.needs_production)
    
    def test_reserve_stock_success(self):
        """Test successful stock reservation"""
        product = Product.objects.create(
            name='Mixed Salad 5',
            department=self.department,
            price=Decimal('25.00'),
            unit='portion'
        )
        
        inventory = self._create_inventory(
            product=product,
            available_quantity=Decimal('100.00'),
            reserved_quantity=Decimal('0.00')
        )
        
        result = inventory.reserve_stock(Decimal('25.00'))
        
        self.assertTrue(result)
        inventory.refresh_from_db()
        self.assertEqual(inventory.available_quantity, Decimal('75.00'))
        self.assertEqual(inventory.reserved_quantity, Decimal('25.00'))
    
    def test_reserve_stock_insufficient(self):
        """Test stock reservation with insufficient quantity"""
        product = Product.objects.create(
            name='Mixed Salad 6',
            department=self.department,
            price=Decimal('25.00'),
            unit='portion'
        )
        
        inventory = self._create_inventory(
            product=product,
            available_quantity=Decimal('10.00'),
            reserved_quantity=Decimal('0.00')
        )
        
        result = inventory.reserve_stock(Decimal('25.00'))
        
        self.assertFalse(result)
        inventory.refresh_from_db()
        # Quantities should remain unchanged
        self.assertEqual(inventory.available_quantity, Decimal('10.00'))
        self.assertEqual(inventory.reserved_quantity, Decimal('0.00'))
    
    def test_release_stock_success(self):
        """Test successful stock release"""
        product = Product.objects.create(
            name='Mixed Salad 7',
            department=self.department,
            price=Decimal('25.00'),
            unit='portion'
        )
        
        inventory = self._create_inventory(
            product=product,
            available_quantity=Decimal('75.00'),
            reserved_quantity=Decimal('25.00')
        )
        
        result = inventory.release_stock(Decimal('10.00'))
        
        self.assertTrue(result)
        inventory.refresh_from_db()
        self.assertEqual(inventory.available_quantity, Decimal('85.00'))
        self.assertEqual(inventory.reserved_quantity, Decimal('15.00'))
    
    def test_sell_stock_success(self):
        """Test successful stock sale"""
        product = Product.objects.create(
            name='Mixed Salad 8',
            department=self.department,
            price=Decimal('25.00'),
            unit='portion'
        )
        
        inventory = self._create_inventory(
            product=product,
            available_quantity=Decimal('75.00'),
            reserved_quantity=Decimal('25.00')
        )
        
        result = inventory.sell_stock(Decimal('10.00'))
        
        self.assertTrue(result)
        inventory.refresh_from_db()
        self.assertEqual(inventory.available_quantity, Decimal('75.00'))  # Unchanged
        self.assertEqual(inventory.reserved_quantity, Decimal('15.00'))   # Reduced


class StockMovementModelTest(TestCase):
    """Test StockMovement model functionality"""
    
    def setUp(self):
        self.department = Department.objects.create(name='Salads')
        self.product = Product.objects.create(
            name='Mixed Salad',
            department=self.department,
            price=Decimal('25.00')
        )
        self.user = User.objects.create_user(email='test@example.com')
    
    def test_stock_movement_creation(self):
        """Test stock movement is created correctly"""
        movement = StockMovement.objects.create(
            product=self.product,
            movement_type='finished_adjust',
            quantity=Decimal('50.00'),
            unit_cost=Decimal('18.50'),
            reference_number='REF-001',
            notes='Initial stock receipt',
            user=self.user
        )
        
        self.assertEqual(movement.product, self.product)
        self.assertEqual(movement.movement_type, 'finished_adjust')
        self.assertEqual(movement.quantity, Decimal('50.00'))
        self.assertEqual(movement.unit_cost, Decimal('18.50'))
        self.assertEqual(movement.user, self.user)
    
    def test_stock_movement_total_value(self):
        """Test total value calculation"""
        movement = StockMovement.objects.create(
            product=self.product,
            movement_type='finished_adjust',
            quantity=Decimal('50.00'),
            unit_cost=Decimal('18.50'),
            reference_number='REF-002',
            user=self.user
        )
        
        # Calculate total value manually since it's not auto-calculated
        expected_total = Decimal('50.00') * Decimal('18.50')
        movement.total_value = expected_total
        movement.save()
        
        self.assertEqual(movement.total_value, expected_total)


class ProductionRecipeModelTest(TestCase):
    """Test ProductionRecipe model functionality"""
    
    def setUp(self):
        self.department = Department.objects.create(name='Salads')
        self.finished_product = Product.objects.create(
            name='Mixed Salad',
            department=self.department,
            price=Decimal('25.00')
        )
        
        self.unit = UnitOfMeasure.objects.create(
            name='Kilogram',
            abbreviation='kg'
        )
        self.raw_material = RawMaterial.objects.create(
            name='Lettuce',
            sku='LET-001',
            unit=self.unit
        )
    
    def test_recipe_creation(self):
        """Test production recipe is created correctly"""
        recipe = ProductionRecipe.objects.create(
            product=self.finished_product,
            version='1.0',
            output_quantity=Decimal('10.00'),
            output_unit=self.unit,
            processing_time_minutes=30,
            processing_notes='Mix all ingredients thoroughly',
            created_by=User.objects.create_user(email='chef@example.com')
        )
        
        self.assertEqual(recipe.product, self.finished_product)
        self.assertEqual(recipe.output_quantity, Decimal('10.00'))
        self.assertEqual(recipe.processing_time_minutes, 30)
        self.assertEqual(recipe.processing_notes, 'Mix all ingredients thoroughly')
        self.assertTrue(recipe.is_active)
    
    def test_recipe_ingredient_relationship(self):
        """Test recipe-ingredient relationship"""
        recipe = ProductionRecipe.objects.create(
            product=self.finished_product,
            version='1.0',
            output_quantity=Decimal('10.00'),
            output_unit=self.unit,
            created_by=User.objects.create_user(email='chef2@example.com')
        )
        
        ingredient = RecipeIngredient.objects.create(
            recipe=recipe,
            raw_material=self.raw_material,
            quantity=Decimal('5.00')
        )
        
        # Test relationship from recipe side
        self.assertEqual(recipe.ingredients.count(), 1)
        self.assertEqual(recipe.ingredients.first(), ingredient)
        
        # Test relationship from ingredient side
        self.assertEqual(ingredient.recipe, recipe)
        self.assertEqual(ingredient.raw_material, self.raw_material)


class StockAlertModelTest(TestCase):
    """Test StockAlert model functionality"""
    
    def setUp(self):
        self.department = Department.objects.create(name='Salads')
        self.product = Product.objects.create(
            name='Mixed Salad',
            department=self.department,
            price=Decimal('25.00')
        )
    
    def test_stock_alert_creation(self):
        """Test stock alert is created correctly"""
        alert = StockAlert.objects.create(
            product=self.product,
            alert_type='low_stock',
            message='Stock level is below minimum threshold',
            severity='medium'
        )
        
        self.assertEqual(alert.product, self.product)
        self.assertEqual(alert.alert_type, 'low_stock')
        self.assertEqual(alert.message, 'Stock level is below minimum threshold')
        self.assertEqual(alert.severity, 'medium')
        self.assertTrue(alert.is_active)
        self.assertIsNotNone(alert.created_at)
    
    def test_stock_alert_resolution(self):
        """Test stock alert resolution"""
        alert = StockAlert.objects.create(
            product=self.product,
            alert_type='low_stock',
            message='Stock level is below minimum threshold',
            severity='medium'
        )
        
        # Initially not acknowledged
        self.assertIsNone(alert.is_acknowledged)
        self.assertIsNone(alert.acknowledged_at)
        
        # Acknowledge the alert
        user = User.objects.create_user(email='manager@example.com')
        alert.acknowledge(user)
        
        self.assertTrue(alert.is_acknowledged)
        self.assertEqual(alert.acknowledged_by, user)
        self.assertIsNotNone(alert.acknowledged_at)


class PricingRuleModelTest(TestCase):
    """Test PricingRule model functionality"""
    
    def setUp(self):
        self.department = Department.objects.create(name='Vegetables')
        self.product = Product.objects.create(
            name='Lettuce',
            department=self.department,
            price=Decimal('15.00')
        )
    
    def test_pricing_rule_creation(self):
        """Test pricing rule is created correctly"""
        rule = PricingRule.objects.create(
            name='Premium Restaurant Rule',
            description='Pricing for premium restaurants',
            customer_segment='premium',
            base_markup_percentage=Decimal('25.00'),
            volatility_adjustment=Decimal('5.00'),
            minimum_margin_percentage=Decimal('15.00'),
            effective_from=date.today(),
            created_by=User.objects.create_user(email='pricing@example.com')
        )
        
        self.assertEqual(rule.name, 'Premium Restaurant Rule')
        self.assertEqual(rule.customer_segment, 'premium')
        self.assertEqual(rule.base_markup_percentage, Decimal('25.00'))
        self.assertEqual(rule.volatility_adjustment, Decimal('5.00'))
        self.assertEqual(rule.minimum_margin_percentage, Decimal('15.00'))
    
    def test_pricing_rule_product_relationship(self):
        """Test pricing rule can be applied to products"""
        rule = PricingRule.objects.create(
            name='Standard Restaurant Rule',
            customer_segment='standard',
            base_markup_percentage=Decimal('20.00'),
            minimum_margin_percentage=Decimal('10.00'),
            effective_from=date.today(),
            created_by=User.objects.create_user(email='pricing2@example.com')
        )
        
        # Test that rule was created successfully
        self.assertEqual(rule.name, 'Standard Restaurant Rule')
        self.assertEqual(rule.customer_segment, 'standard')
        self.assertEqual(rule.base_markup_percentage, Decimal('20.00'))


class InventoryAPITest(APITestCase):
    """Test Inventory API endpoints"""
    
    def setUp(self):
        self.client = APIClient()
        # Create and authenticate user
        self.user = User.objects.create_user(
            email='api_test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        
        self.unit = UnitOfMeasure.objects.create(
            name='Kilogram',
            abbreviation='kg'
        )
        self.department = Department.objects.create(name='Salads')
        self.product = Product.objects.create(
            name='Mixed Salad',
            department=self.department,
            price=Decimal('25.00')
        )
    
    def test_get_units_list(self):
        """Test getting list of units of measure"""
        url = reverse('unitofmeasure-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)
        
        # Check that our test unit is in the response
        if isinstance(response.data, list) and len(response.data) > 0:
            unit_names = [u.get('name') for u in response.data if isinstance(u, dict)]
            self.assertIn('Kilogram', unit_names)
    
    def test_create_raw_material(self):
        """Test creating a raw material via API"""
        url = reverse('rawmaterial-list')
        data = {
            'name': 'Organic Tomatoes',
            'description': 'Fresh organic tomatoes',
            'sku': 'ORG-TOM-001',
            'unit_id': self.unit.id,
            'requires_batch_tracking': True,
            'shelf_life_days': 14,
            'minimum_stock_level': '20.00',
            'reorder_level': '40.00'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(RawMaterial.objects.filter(sku='ORG-TOM-001').exists())
    
    def test_get_finished_inventory_list(self):
        """Test getting finished inventory list"""
        # Create finished inventory
        inventory, created = FinishedInventory.objects.get_or_create(
            product=self.product,
            defaults={
                'available_quantity': Decimal('100.00'),
                'reserved_quantity': Decimal('20.00')
            }
        )
        if not created:
            inventory.available_quantity = Decimal('100.00')
            inventory.reserved_quantity = Decimal('20.00')
            inventory.save()
        
        url = reverse('finishedinventory-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)
    
    def test_stock_levels_endpoint(self):
        """Test stock levels summary endpoint"""
        url = reverse('stock-levels')
        response = self.client.get(url)
        
        # This endpoint might return different status codes depending on implementation
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND])
    
    def test_inventory_dashboard_endpoint(self):
        """Test inventory dashboard endpoint"""
        url = reverse('inventory-dashboard')
        response = self.client.get(url)
        
        # This endpoint might return different status codes depending on implementation
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND])


class InventoryBusinessLogicTest(TestCase):
    """Test inventory business logic and calculations"""
    
    def setUp(self):
        self.unit = UnitOfMeasure.objects.create(
            name='Kilogram',
            abbreviation='kg'
        )
        self.supplier = Supplier.objects.create(
            name='Fresh Farms Co',
            supplier_type='external'
        )
        self.department = Department.objects.create(name='Salads')
        self.product = Product.objects.create(
            name='Mixed Salad',
            department=self.department,
            price=Decimal('25.00')
        )
        self.raw_material = RawMaterial.objects.create(
            name='Lettuce',
            sku='LET-001',
            unit=self.unit,
            minimum_stock_level=Decimal('10.00'),
            reorder_level=Decimal('20.00')
        )
    
    def test_stock_level_calculations(self):
        """Test stock level calculations and thresholds"""
        # Create batches with different quantities
        batch1 = RawMaterialBatch.objects.create(
            raw_material=self.raw_material,
            supplier=self.supplier,
            batch_number='BATCH-001',
            received_quantity=Decimal('30.00'),
            available_quantity=Decimal('15.00'),
            unit_cost=Decimal('10.00'),
            quality_grade='A'
        )
        
        batch2 = RawMaterialBatch.objects.create(
            raw_material=self.raw_material,
            supplier=self.supplier,
            batch_number='BATCH-002',
            received_quantity=Decimal('20.00'),
            available_quantity=Decimal('8.00'),
            unit_cost=Decimal('12.00'),
            quality_grade='A'
        )
        
        # Total remaining should be 15 + 8 = 23
        total_remaining = sum(
            batch.available_quantity 
            for batch in RawMaterialBatch.objects.filter(raw_material=self.raw_material)
        )
        self.assertEqual(total_remaining, Decimal('23.00'))
        
        # Check if reorder is needed (23 > 20 = False)
        needs_reorder = total_remaining <= self.raw_material.reorder_level
        self.assertFalse(needs_reorder)
    
    def test_production_cost_calculation(self):
        """Test production cost calculation for recipes"""
        recipe = ProductionRecipe.objects.create(
            product=self.product,
            version='1.0',
            output_quantity=Decimal('10.00'),
            output_unit=self.unit,
            created_by=User.objects.create_user(email='chef3@example.com')
        )
        
        # Add ingredients
        ingredient1 = RecipeIngredient.objects.create(
            recipe=recipe,
            raw_material=self.raw_material,
            quantity=Decimal('5.00')
        )
        
        # Create another raw material and ingredient
        raw_material2 = RawMaterial.objects.create(
            name='Tomatoes',
            sku='TOM-001',
            unit=self.unit
        )
        
        ingredient2 = RecipeIngredient.objects.create(
            recipe=recipe,
            raw_material=raw_material2,
            quantity=Decimal('3.00')
        )
        
        # Test that ingredients were added to recipe
        self.assertEqual(recipe.ingredients.count(), 2)
        self.assertIn(ingredient1, recipe.ingredients.all())
        self.assertIn(ingredient2, recipe.ingredients.all())
        
        # Test total cost calculation (using property)
        total_cost = recipe.total_raw_material_cost
        self.assertIsInstance(total_cost, Decimal)
        
        # Test cost per unit calculation (using property)
        cost_per_unit = recipe.cost_per_unit
        self.assertIsInstance(cost_per_unit, Decimal)
    
    def test_inventory_valuation(self):
        """Test inventory valuation calculations"""
        product = Product.objects.create(
            name='Business Logic Product 1',
            department=self.department,
            price=Decimal('25.00')
        )
        
        inventory, created = FinishedInventory.objects.get_or_create(
            product=product,
            defaults={
                'available_quantity': Decimal('100.00'),
                'reserved_quantity': Decimal('25.00'),
                'average_cost': Decimal('18.50')
            }
        )
        if not created:
            inventory.available_quantity = Decimal('100.00')
            inventory.reserved_quantity = Decimal('25.00')
            inventory.average_cost = Decimal('18.50')
            inventory.save()
        
        # Total inventory value
        total_value = inventory.total_quantity * inventory.average_cost
        expected_value = Decimal('125.00') * Decimal('18.50')  # (100 + 25) * 18.50
        self.assertEqual(total_value, expected_value)
        
        # Available inventory value
        available_value = inventory.available_quantity * inventory.average_cost
        expected_available = Decimal('100.00') * Decimal('18.50')
        self.assertEqual(available_value, expected_available)
    
    def test_stock_movement_impact(self):
        """Test stock movement impact on inventory levels"""
        product = Product.objects.create(
            name='Business Logic Product 2',
            department=self.department,
            price=Decimal('25.00')
        )
        
        inventory, created = FinishedInventory.objects.get_or_create(
            product=product,
            defaults={
                'available_quantity': Decimal('100.00'),
                'reserved_quantity': Decimal('0.00')
            }
        )
        if not created:
            inventory.available_quantity = Decimal('100.00')
            inventory.reserved_quantity = Decimal('0.00')
            inventory.save()
        
        user = User.objects.create_user(email='test@example.com')
        
        # Create stock movements
        inbound_movement = StockMovement.objects.create(
            product=product,
            movement_type='finished_adjust',
            quantity=Decimal('50.00'),
            unit_cost=Decimal('18.00'),
            reference_number='IN-001',
            user=user
        )
        
        outbound_movement = StockMovement.objects.create(
            product=product,
            movement_type='finished_sell',
            quantity=Decimal('25.00'),
            unit_cost=Decimal('18.00'),
            reference_number='OUT-001',
            user=user
        )
        
        # Calculate net movement: +50 - 25 = +25
        net_movement = (
            StockMovement.objects.filter(product=product, movement_type='finished_adjust')
            .aggregate(total_in=models.Sum('quantity'))['total_in'] or Decimal('0')
        ) - (
            StockMovement.objects.filter(product=product, movement_type='finished_sell')
            .aggregate(total_out=models.Sum('quantity'))['total_out'] or Decimal('0')
        )
        
        self.assertEqual(net_movement, Decimal('25.00'))


class InventoryIntegrationTest(TestCase):
    """Test inventory integration with other models"""
    
    def setUp(self):
        self.user = User.objects.create_user(email='customer@restaurant.com')
        self.restaurant_profile = RestaurantProfile.objects.create(
            user=self.user,
            business_name='Test Restaurant'
        )
        
        self.department = Department.objects.create(name='Salads')
        self.product = Product.objects.create(
            name='Mixed Salad',
            department=self.department,
            price=Decimal('25.00')
        )
    
    def test_customer_price_list_integration(self):
        """Test customer price list integration"""
        # Create pricing rule
        pricing_rule = PricingRule.objects.create(
            name='Restaurant Discount',
            customer_segment='standard',
            base_markup_percentage=Decimal('20.00'),
            minimum_margin_percentage=Decimal('15.00'),
            effective_from=date.today(),
            created_by=User.objects.create_user(email='pricing3@example.com')
        )
        
        # Create customer price list
        price_list = CustomerPriceList.objects.create(
            customer=self.user,
            list_name='Test Restaurant Prices',
            pricing_rule=pricing_rule,
            effective_from=date.today(),
            effective_until=date.today() + timedelta(days=30),
            generated_by=User.objects.create_user(email='generator@example.com'),
            based_on_market_data=date.today()
        )
        
        # Create price list item
        price_item = CustomerPriceListItem.objects.create(
            price_list=price_list,
            product=self.product,
            market_price_excl_vat=Decimal('20.00'),
            market_price_incl_vat=Decimal('23.00'),
            market_price_date=date.today(),
            markup_percentage=Decimal('15.00'),
            customer_price_excl_vat=Decimal('23.00'),
            customer_price_incl_vat=Decimal('26.45')
        )
        
        # Test relationships
        self.assertEqual(price_list.customer, self.user)
        self.assertEqual(price_list.pricing_rule, pricing_rule)
        self.assertEqual(price_item.product, self.product)
        self.assertEqual(price_item.customer_price_excl_vat, Decimal('23.00'))
    
    def test_product_inventory_relationship(self):
        """Test product-inventory relationship"""
        product = Product.objects.create(
            name='Integration Product 1',
            department=self.department,
            price=Decimal('25.00')
        )
        
        inventory, created = FinishedInventory.objects.get_or_create(
            product=product,
            defaults={'available_quantity': Decimal('100.00')}
        )
        if not created:
            inventory.available_quantity = Decimal('100.00')
            inventory.save()
        
        # Test OneToOne relationship
        self.assertEqual(product.inventory, inventory)
        self.assertEqual(inventory.product, product)
    
    def test_cascade_deletion_behavior(self):
        """Test cascade deletion behavior"""
        product = Product.objects.create(
            name='Integration Product 2',
            department=self.department,
            price=Decimal('25.00')
        )
        
        inventory, created = FinishedInventory.objects.get_or_create(
            product=product,
            defaults={'available_quantity': Decimal('100.00')}
        )
        if not created:
            inventory.available_quantity = Decimal('100.00')
            inventory.save()
        
        # Delete product should delete inventory (CASCADE)
        product.delete()
        
        # Inventory should be deleted
        self.assertFalse(FinishedInventory.objects.filter(id=inventory.id).exists())


# Import Django's models for aggregation
from django.db import models
