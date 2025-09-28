"""
Unit tests for inventory management business logic
Tests stock operations, alerts, and inventory calculations
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from decimal import Decimal
from datetime import date, timedelta

from inventory.models import (
    FinishedInventory, StockMovement, StockAlert, RawMaterial, 
    RawMaterialBatch, UnitOfMeasure, ProductionRecipe, RecipeIngredient
)
from products.models import Product, Department
from suppliers.models import Supplier

User = get_user_model()


class FinishedInventoryTest(TestCase):
    """Test FinishedInventory stock management operations"""
    
    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(
            email='test@fambrifarms.com',
            password='testpass123',
            user_type='admin'
        )
        
        # Create test product
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
        
        # Create inventory record
        self.inventory, created = FinishedInventory.objects.get_or_create(
            product=self.product,
            defaults={
                'available_quantity': Decimal('100.00'),
                'reserved_quantity': Decimal('20.00'),
                'minimum_level': Decimal('10.00'),
                'reorder_level': Decimal('25.00'),
                'average_cost': Decimal('15.00')
            }
        )
    
    def test_total_quantity_calculation(self):
        """Test total_quantity property calculation"""
        expected_total = Decimal('100.00') + Decimal('20.00')
        self.assertEqual(self.inventory.total_quantity, expected_total)
    
    def test_needs_production_check(self):
        """Test needs_production property logic"""
        # Current available (100) > reorder level (25) = no production needed
        self.assertFalse(self.inventory.needs_production)
        
        # Reduce available quantity below reorder level
        self.inventory.available_quantity = Decimal('20.00')
        self.inventory.save()
        
        # Now production should be needed
        self.assertTrue(self.inventory.needs_production)
    
    def test_reserve_stock_success(self):
        """Test successful stock reservation"""
        initial_available = self.inventory.available_quantity
        initial_reserved = self.inventory.reserved_quantity
        reserve_quantity = Decimal('30.00')
        
        result = self.inventory.reserve_stock(reserve_quantity)
        
        self.assertTrue(result)
        self.assertEqual(
            self.inventory.available_quantity, 
            initial_available - reserve_quantity
        )
        self.assertEqual(
            self.inventory.reserved_quantity,
            initial_reserved + reserve_quantity
        )
    
    def test_reserve_stock_insufficient(self):
        """Test stock reservation with insufficient quantity"""
        reserve_quantity = Decimal('150.00')  # More than available (100)
        
        result = self.inventory.reserve_stock(reserve_quantity)
        
        self.assertFalse(result)
        # Quantities should remain unchanged
        self.assertEqual(self.inventory.available_quantity, Decimal('100.00'))
        self.assertEqual(self.inventory.reserved_quantity, Decimal('20.00'))
    
    def test_release_stock_success(self):
        """Test successful stock release"""
        initial_available = self.inventory.available_quantity
        initial_reserved = self.inventory.reserved_quantity
        release_quantity = Decimal('10.00')
        
        result = self.inventory.release_stock(release_quantity)
        
        self.assertTrue(result)
        self.assertEqual(
            self.inventory.available_quantity,
            initial_available + release_quantity
        )
        self.assertEqual(
            self.inventory.reserved_quantity,
            initial_reserved - release_quantity
        )
    
    def test_release_stock_insufficient_reserved(self):
        """Test stock release with insufficient reserved quantity"""
        release_quantity = Decimal('30.00')  # More than reserved (20)
        
        result = self.inventory.release_stock(release_quantity)
        
        self.assertFalse(result)
        # Quantities should remain unchanged
        self.assertEqual(self.inventory.available_quantity, Decimal('100.00'))
        self.assertEqual(self.inventory.reserved_quantity, Decimal('20.00'))
    
    def test_sell_stock_success(self):
        """Test successful stock sale"""
        initial_reserved = self.inventory.reserved_quantity
        sell_quantity = Decimal('15.00')
        
        result = self.inventory.sell_stock(sell_quantity)
        
        self.assertTrue(result)
        self.assertEqual(
            self.inventory.reserved_quantity,
            initial_reserved - sell_quantity
        )
        # Available quantity should remain unchanged in sell operation
        self.assertEqual(self.inventory.available_quantity, Decimal('100.00'))
    
    def test_sell_stock_insufficient_reserved(self):
        """Test stock sale with insufficient reserved quantity"""
        sell_quantity = Decimal('30.00')  # More than reserved (20)
        
        result = self.inventory.sell_stock(sell_quantity)
        
        self.assertFalse(result)
        # Quantities should remain unchanged
        self.assertEqual(self.inventory.reserved_quantity, Decimal('20.00'))


class RawMaterialBatchTest(TestCase):
    """Test RawMaterialBatch business logic"""
    
    def setUp(self):
        # Create test data
        self.supplier = Supplier.objects.create(
            name='Test Supplier',
            supplier_type='external'
        )
        
        self.unit = UnitOfMeasure.objects.create(
            name='Kilogram',
            abbreviation='kg',
            is_weight=True
        )
        
        self.raw_material = RawMaterial.objects.create(
            name='Test Raw Material',
            sku='TRM001',
            unit=self.unit,
            shelf_life_days=30
        )
    
    def test_batch_number_auto_generation(self):
        """Test automatic batch number generation"""
        batch = RawMaterialBatch.objects.create(
            raw_material=self.raw_material,
            supplier=self.supplier,
            received_quantity=Decimal('50.00'),
            unit_cost=Decimal('10.00'),
            quality_grade='A'
        )
        
        self.assertIsNotNone(batch.batch_number)
        self.assertTrue(batch.batch_number.startswith('RM-'))
        # Format: RM-YYYYMMDD-XXXX
        self.assertEqual(len(batch.batch_number), 15)
    
    def test_available_quantity_default(self):
        """Test that available_quantity defaults to received_quantity"""
        batch = RawMaterialBatch.objects.create(
            raw_material=self.raw_material,
            supplier=self.supplier,
            received_quantity=Decimal('50.00'),
            unit_cost=Decimal('10.00'),
            quality_grade='A'
        )
        
        self.assertEqual(batch.available_quantity, batch.received_quantity)
    
    def test_total_cost_calculation(self):
        """Test automatic total_cost calculation"""
        received_qty = Decimal('50.00')
        unit_cost = Decimal('10.00')
        
        batch = RawMaterialBatch.objects.create(
            raw_material=self.raw_material,
            supplier=self.supplier,
            received_quantity=received_qty,
            unit_cost=unit_cost,
            quality_grade='A'
        )
        
        expected_total = received_qty * unit_cost
        self.assertEqual(batch.total_cost, expected_total)
    
    def test_is_expired_property(self):
        """Test is_expired property logic"""
        # Create batch with expiry date in the past
        past_date = date.today() - timedelta(days=5)
        batch = RawMaterialBatch.objects.create(
            raw_material=self.raw_material,
            supplier=self.supplier,
            received_quantity=Decimal('50.00'),
            unit_cost=Decimal('10.00'),
            quality_grade='A',
            expiry_date=past_date
        )
        
        self.assertTrue(batch.is_expired)
        
        # Create batch with future expiry date
        future_date = date.today() + timedelta(days=5)
        batch.expiry_date = future_date
        batch.save()
        
        self.assertFalse(batch.is_expired)
    
    def test_days_until_expiry_property(self):
        """Test days_until_expiry calculation"""
        # Test future expiry
        future_date = date.today() + timedelta(days=10)
        batch = RawMaterialBatch.objects.create(
            raw_material=self.raw_material,
            supplier=self.supplier,
            received_quantity=Decimal('50.00'),
            unit_cost=Decimal('10.00'),
            quality_grade='A',
            expiry_date=future_date
        )
        
        self.assertEqual(batch.days_until_expiry, 10)
        
        # Test past expiry (negative days)
        past_date = date.today() - timedelta(days=5)
        batch.expiry_date = past_date
        batch.save()
        
        self.assertEqual(batch.days_until_expiry, -5)


class ProductionRecipeTest(TestCase):
    """Test ProductionRecipe calculations"""
    
    def setUp(self):
        # Create test data
        self.user = User.objects.create_user(
            email='test@fambrifarms.com',
            password='testpass123',
            user_type='admin'
        )
        
        self.department = Department.objects.create(name='Test Products')
        self.product = Product.objects.create(
            name='Test Finished Product',
            department=self.department,
            price=Decimal('50.00'),
            unit='piece'
        )
        
        self.unit = UnitOfMeasure.objects.create(
            name='Piece',
            abbreviation='pcs',
            is_weight=False
        )
        
        self.recipe = ProductionRecipe.objects.create(
            product=self.product,
            version='1.0',
            output_quantity=Decimal('10.00'),
            output_unit=self.unit,
            created_by=self.user
        )
        
        # Create raw materials and ingredients
        self.raw_material1 = RawMaterial.objects.create(
            name='Ingredient 1',
            sku='ING001',
            unit=self.unit
        )
        
        self.raw_material2 = RawMaterial.objects.create(
            name='Ingredient 2', 
            sku='ING002',
            unit=self.unit
        )
        
        # Create recipe ingredients
        self.ingredient1 = RecipeIngredient.objects.create(
            recipe=self.recipe,
            raw_material=self.raw_material1,
            quantity=Decimal('5.00')
        )
        
        self.ingredient2 = RecipeIngredient.objects.create(
            recipe=self.recipe,
            raw_material=self.raw_material2,
            quantity=Decimal('3.00')
        )
        
        # Create batches for cost calculation
        supplier = Supplier.objects.create(name='Test Supplier')
        
        RawMaterialBatch.objects.create(
            raw_material=self.raw_material1,
            supplier=supplier,
            received_quantity=Decimal('100.00'),
            unit_cost=Decimal('2.00'),
            quality_grade='A'
        )
        
        RawMaterialBatch.objects.create(
            raw_material=self.raw_material2,
            supplier=supplier,
            received_quantity=Decimal('100.00'),
            unit_cost=Decimal('3.00'),
            quality_grade='A'
        )
    
    def test_total_raw_material_cost(self):
        """Test total raw material cost calculation"""
        # Ingredient 1: 5.00 * 2.00 = 10.00
        # Ingredient 2: 3.00 * 3.00 = 9.00
        # Total: 19.00
        expected_cost = Decimal('19.00')
        self.assertEqual(self.recipe.total_raw_material_cost, expected_cost)
    
    def test_cost_per_unit(self):
        """Test cost per unit calculation"""
        # Total cost: 19.00, Output quantity: 10.00
        # Cost per unit: 19.00 / 10.00 = 1.90
        expected_cost_per_unit = Decimal('1.90')
        self.assertEqual(self.recipe.cost_per_unit, expected_cost_per_unit)
    
    def test_cost_per_unit_zero_output(self):
        """Test cost per unit with zero output quantity"""
        self.recipe.output_quantity = Decimal('0.00')
        self.recipe.save()
        
        self.assertEqual(self.recipe.cost_per_unit, Decimal('0.00'))


class RecipeIngredientTest(TestCase):
    """Test RecipeIngredient cost calculations"""
    
    def setUp(self):
        # Create minimal test data
        self.user = User.objects.create_user(
            email='test@fambrifarms.com',
            password='testpass123'
        )
        
        self.department = Department.objects.create(name='Test')
        self.product = Product.objects.create(
            name='Test Product',
            department=self.department,
            price=Decimal('10.00')
        )
        
        self.unit = UnitOfMeasure.objects.create(
            name='Kilogram',
            abbreviation='kg'
        )
        
        self.recipe = ProductionRecipe.objects.create(
            product=self.product,
            version='1.0',
            output_quantity=Decimal('1.00'),
            output_unit=self.unit,
            created_by=self.user
        )
        
        self.raw_material = RawMaterial.objects.create(
            name='Test Raw Material',
            sku='TRM001',
            unit=self.unit
        )
        
        self.ingredient = RecipeIngredient.objects.create(
            recipe=self.recipe,
            raw_material=self.raw_material,
            quantity=Decimal('5.00')
        )
    
    def test_estimated_cost_with_batch(self):
        """Test estimated cost calculation with available batch"""
        supplier = Supplier.objects.create(name='Test Supplier')
        
        # Create batch with unit cost
        RawMaterialBatch.objects.create(
            raw_material=self.raw_material,
            supplier=supplier,
            received_quantity=Decimal('100.00'),
            unit_cost=Decimal('2.50'),
            quality_grade='A'
        )
        
        # Expected cost: 5.00 * 2.50 = 12.50
        expected_cost = Decimal('12.50')
        self.assertEqual(self.ingredient.estimated_cost, expected_cost)
    
    def test_estimated_cost_no_batch(self):
        """Test estimated cost when no batch is available"""
        # No batches created, should return 0.00
        self.assertEqual(self.ingredient.estimated_cost, Decimal('0.00'))
    
    def test_total_cost_property(self):
        """Test that total_cost returns estimated_cost"""
        supplier = Supplier.objects.create(name='Test Supplier')
        
        RawMaterialBatch.objects.create(
            raw_material=self.raw_material,
            supplier=supplier,
            received_quantity=Decimal('100.00'),
            unit_cost=Decimal('3.00'),
            quality_grade='A'
        )
        
        self.assertEqual(self.ingredient.total_cost, self.ingredient.estimated_cost)
