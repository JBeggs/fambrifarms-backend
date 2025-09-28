from django.test import TestCase
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.utils import timezone
from decimal import Decimal
from datetime import date, timedelta

from .models import (
    Recipe, RecipeIngredient, ProductionBatch, ProductionReservation, QualityCheck
)
from accounts.models import User
from products.models import Product, Department
from orders.models import Order, OrderItem


class RecipeModelTest(TestCase):
    """Test Recipe model functionality"""
    
    def setUp(self):
        self.department = Department.objects.create(name='Test Department')
        self.finished_product = Product.objects.create(
            name='Finished Product',
            price=Decimal('25.00'),
            unit='kg',
            department=self.department
        )
        
    def test_recipe_creation(self):
        """Test recipe is created correctly"""
        recipe = Recipe.objects.create(
            product=self.finished_product,
            name='Test Recipe',
            description='A test recipe for production',
            batch_size=10,
            production_time_minutes=120,
            yield_percentage=Decimal('95.00'),
            is_active=True,
            version='1.0'
        )
        
        self.assertEqual(recipe.product, self.finished_product)
        self.assertEqual(recipe.name, 'Test Recipe')
        self.assertEqual(recipe.batch_size, 10)
        self.assertEqual(recipe.production_time_minutes, 120)
        self.assertEqual(recipe.yield_percentage, Decimal('95.00'))
        self.assertTrue(recipe.is_active)
        self.assertEqual(recipe.version, '1.0')
        
    def test_recipe_str_representation(self):
        """Test recipe string representation"""
        recipe = Recipe.objects.create(
            product=self.finished_product,
            name='Test Recipe',
            version='2.1'
        )
        expected_str = f"Recipe: {self.finished_product.name} (v2.1)"
        self.assertEqual(str(recipe), expected_str)
        
    def test_recipe_default_values(self):
        """Test recipe default values"""
        recipe = Recipe.objects.create(
            product=self.finished_product,
            name='Default Recipe'
        )
        
        self.assertEqual(recipe.batch_size, 1)
        self.assertEqual(recipe.production_time_minutes, 60)
        self.assertEqual(recipe.yield_percentage, Decimal('100.00'))
        self.assertTrue(recipe.is_active)
        self.assertEqual(recipe.version, '1.0')


class RecipeIngredientModelTest(TestCase):
    """Test RecipeIngredient model functionality"""
    
    def setUp(self):
        self.department = Department.objects.create(name='Test Department')
        self.finished_product = Product.objects.create(
            name='Finished Product',
            price=Decimal('25.00'),
            unit='kg',
            department=self.department
        )
        self.raw_material = Product.objects.create(
            name='Raw Material',
            price=Decimal('10.00'),
            unit='kg',
            department=self.department
        )
        self.recipe = Recipe.objects.create(
            product=self.finished_product,
            name='Test Recipe'
        )
        
    def test_recipe_ingredient_creation(self):
        """Test recipe ingredient is created correctly"""
        ingredient = RecipeIngredient.objects.create(
            recipe=self.recipe,
            raw_material=self.raw_material,
            quantity=Decimal('5.000'),
            unit='kg',
            preparation_notes='Finely chopped',
            is_optional=False
        )
        
        self.assertEqual(ingredient.recipe, self.recipe)
        self.assertEqual(ingredient.raw_material, self.raw_material)
        self.assertEqual(ingredient.quantity, Decimal('5.000'))
        self.assertEqual(ingredient.unit, 'kg')
        self.assertEqual(ingredient.preparation_notes, 'Finely chopped')
        self.assertFalse(ingredient.is_optional)
        
    def test_recipe_ingredient_str_representation(self):
        """Test recipe ingredient string representation"""
        ingredient = RecipeIngredient.objects.create(
            recipe=self.recipe,
            raw_material=self.raw_material,
            quantity=Decimal('2.500'),
            unit='kg'
        )
        expected_str = f"{self.raw_material.name} (2.500 kg)"
        self.assertEqual(str(ingredient), expected_str)
        
    def test_recipe_ingredient_unique_constraint(self):
        """Test unique constraint on recipe and raw material"""
        # Create first ingredient
        RecipeIngredient.objects.create(
            recipe=self.recipe,
            raw_material=self.raw_material,
            quantity=Decimal('3.000')
        )
        
        # Try to create duplicate - should raise IntegrityError
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            RecipeIngredient.objects.create(
                recipe=self.recipe,
                raw_material=self.raw_material,
                quantity=Decimal('5.000')
            )


class ProductionBatchModelTest(TestCase):
    """Test ProductionBatch model functionality"""
    
    def setUp(self):
        self.user = User.objects.create_user(email='producer@example.com')
        self.department = Department.objects.create(name='Test Department')
        self.finished_product = Product.objects.create(
            name='Finished Product',
            price=Decimal('25.00'),
            unit='kg',
            department=self.department
        )
        self.recipe = Recipe.objects.create(
            product=self.finished_product,
            name='Test Recipe'
        )
        
    def test_production_batch_creation(self):
        """Test production batch is created correctly"""
        start_date = timezone.now()
        end_date = start_date + timedelta(hours=4)
        
        batch = ProductionBatch.objects.create(
            recipe=self.recipe,
            planned_quantity=50,
            actual_quantity=48,
            status='completed',
            planned_start_date=start_date,
            planned_end_date=end_date,
            actual_start_date=start_date,
            actual_end_date=end_date,
            produced_by=self.user,
            notes='Test production batch',
            quality_notes='Good quality output'
        )
        
        self.assertEqual(batch.recipe, self.recipe)
        self.assertEqual(batch.planned_quantity, 50)
        self.assertEqual(batch.actual_quantity, 48)
        self.assertEqual(batch.status, 'completed')
        self.assertEqual(batch.produced_by, self.user)
        self.assertIsNotNone(batch.batch_number)
        
    def test_production_batch_str_representation(self):
        """Test production batch string representation"""
        batch = ProductionBatch.objects.create(
            recipe=self.recipe,
            planned_quantity=25,
            planned_start_date=timezone.now(),
            planned_end_date=timezone.now() + timedelta(hours=3)
        )
        expected_str = f"Batch {batch.batch_number} - {self.finished_product.name}"
        self.assertEqual(str(batch), expected_str)
        
    def test_batch_number_generation(self):
        """Test automatic batch number generation"""
        start_date = timezone.now()
        end_date = start_date + timedelta(hours=2)
        
        batch1 = ProductionBatch.objects.create(
            recipe=self.recipe,
            planned_quantity=10,
            planned_start_date=start_date,
            planned_end_date=end_date
        )
        batch2 = ProductionBatch.objects.create(
            recipe=self.recipe,
            planned_quantity=20,
            planned_start_date=start_date,
            planned_end_date=end_date
        )
        
        self.assertIsNotNone(batch1.batch_number)
        self.assertIsNotNone(batch2.batch_number)
        self.assertNotEqual(batch1.batch_number, batch2.batch_number)
        
        # Both should start with 'B' and today's date
        today_str = timezone.now().date().strftime('%Y%m%d')
        self.assertTrue(batch1.batch_number.startswith(f'B{today_str}'))
        self.assertTrue(batch2.batch_number.startswith(f'B{today_str}'))
        
    def test_yield_percentage_property(self):
        """Test yield percentage calculation"""
        batch = ProductionBatch.objects.create(
            recipe=self.recipe,
            planned_quantity=100,
            actual_quantity=85,
            planned_start_date=timezone.now(),
            planned_end_date=timezone.now() + timedelta(hours=4)
        )
        
        expected_yield = 85.0  # (85/100) * 100
        self.assertEqual(batch.yield_percentage, expected_yield)
        
        # Test with zero planned quantity
        batch_zero = ProductionBatch.objects.create(
            recipe=self.recipe,
            planned_quantity=0,
            planned_start_date=timezone.now(),
            planned_end_date=timezone.now() + timedelta(hours=1)
        )
        self.assertEqual(batch_zero.yield_percentage, 0)


class ProductionReservationModelTest(TestCase):
    """Test ProductionReservation model functionality"""
    
    def setUp(self):
        self.user = User.objects.create_user(email='customer@example.com')
        self.department = Department.objects.create(name='Test Department')
        self.finished_product = Product.objects.create(
            name='Finished Product',
            price=Decimal('25.00'),
            unit='kg',
            department=self.department
        )
        self.raw_material = Product.objects.create(
            name='Raw Material',
            price=Decimal('10.00'),
            unit='kg',
            department=self.department
        )
        self.recipe = Recipe.objects.create(
            product=self.finished_product,
            name='Test Recipe'
        )
        self.batch = ProductionBatch.objects.create(
            recipe=self.recipe,
            planned_quantity=20,
            planned_start_date=timezone.now(),
            planned_end_date=timezone.now() + timedelta(hours=2)
        )
        
        # Create an order and order item for testing
        self.order = Order.objects.create(
            restaurant=self.user,
            order_date=date.today(),
            delivery_date=date.today() + timedelta(days=1),
            status='pending'
        )
        self.order_item = OrderItem.objects.create(
            order=self.order,
            product=self.finished_product,
            quantity=5,
            unit='kg',
            price=Decimal('25.00')
        )
        
    def test_production_reservation_creation(self):
        """Test production reservation is created correctly"""
        reservation = ProductionReservation.objects.create(
            batch=self.batch,
            raw_material=self.raw_material,
            order_item=self.order_item,
            quantity_reserved=Decimal('10.000'),
            quantity_used=Decimal('9.500'),
            is_consumed=True
        )
        
        self.assertEqual(reservation.batch, self.batch)
        self.assertEqual(reservation.raw_material, self.raw_material)
        self.assertEqual(reservation.order_item, self.order_item)
        self.assertEqual(reservation.quantity_reserved, Decimal('10.000'))
        self.assertEqual(reservation.quantity_used, Decimal('9.500'))
        self.assertTrue(reservation.is_consumed)
        
    def test_production_reservation_str_representation(self):
        """Test production reservation string representation"""
        reservation = ProductionReservation.objects.create(
            batch=self.batch,
            raw_material=self.raw_material,
            quantity_reserved=Decimal('5.000')
        )
        expected_str = f"{self.raw_material.name} reserved for {self.batch.batch_number}"
        self.assertEqual(str(reservation), expected_str)
        
    def test_quantity_remaining_property(self):
        """Test quantity remaining calculation"""
        reservation = ProductionReservation.objects.create(
            batch=self.batch,
            raw_material=self.raw_material,
            quantity_reserved=Decimal('15.000'),
            quantity_used=Decimal('12.000')
        )
        
        expected_remaining = Decimal('3.000')
        self.assertEqual(reservation.quantity_remaining, expected_remaining)
        
        # Test with no quantity used - create a different raw material to avoid unique constraint
        raw_material2 = Product.objects.create(
            name='Raw Material 2',
            price=Decimal('8.00'),
            unit='kg',
            department=Department.objects.create(name='Test Department 2')
        )
        reservation_unused = ProductionReservation.objects.create(
            batch=self.batch,
            raw_material=raw_material2,
            quantity_reserved=Decimal('8.000'),
            quantity_used=Decimal('0.000')
        )
        # quantity_used is 0, so remaining should be reserved amount
        self.assertEqual(reservation_unused.quantity_remaining, Decimal('8.000'))


class QualityCheckModelTest(TestCase):
    """Test QualityCheck model functionality"""
    
    def setUp(self):
        self.user = User.objects.create_user(email='quality@example.com')
        self.department = Department.objects.create(name='Test Department')
        self.finished_product = Product.objects.create(
            name='Finished Product',
            price=Decimal('25.00'),
            unit='kg',
            department=self.department
        )
        self.recipe = Recipe.objects.create(
            product=self.finished_product,
            name='Test Recipe'
        )
        self.batch = ProductionBatch.objects.create(
            recipe=self.recipe,
            planned_quantity=30,
            planned_start_date=timezone.now(),
            planned_end_date=timezone.now() + timedelta(hours=2)
        )
        
    def test_quality_check_creation(self):
        """Test quality check is created correctly"""
        check_date = timezone.now()
        quality_check = QualityCheck.objects.create(
            batch=self.batch,
            check_type='visual_inspection',
            result='pass',
            score=Decimal('92.50'),
            notes='Good color and texture',
            checked_by=self.user,
            check_date=check_date
        )
        
        self.assertEqual(quality_check.batch, self.batch)
        self.assertEqual(quality_check.check_type, 'visual_inspection')
        self.assertEqual(quality_check.result, 'pass')
        self.assertEqual(quality_check.score, Decimal('92.50'))
        self.assertEqual(quality_check.notes, 'Good color and texture')
        self.assertEqual(quality_check.checked_by, self.user)
        self.assertEqual(quality_check.check_date, check_date)
        
    def test_quality_check_str_representation(self):
        """Test quality check string representation"""
        quality_check = QualityCheck.objects.create(
            batch=self.batch,
            check_type='taste_test',
            result='conditional'
        )
        expected_str = f"taste_test - conditional ({self.batch.batch_number})"
        self.assertEqual(str(quality_check), expected_str)
        
    def test_quality_check_result_choices(self):
        """Test quality check result choices"""
        # Test all valid result choices
        valid_results = ['pass', 'fail', 'conditional']
        
        for result in valid_results:
            quality_check = QualityCheck.objects.create(
                batch=self.batch,
                check_type=f'test_{result}',
                result=result
            )
            self.assertEqual(quality_check.result, result)