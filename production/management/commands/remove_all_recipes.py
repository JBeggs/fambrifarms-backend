#!/usr/bin/env python3
"""
Django management command to remove all recipes

This command allows you to remove all recipes from the system, useful if
something goes wrong and you need to start fresh.

Usage:
    # Dry run - preview what would be removed
    python manage.py remove_all_recipes --dry-run
    
    # Remove all recipes
    python manage.py remove_all_recipes
    
    # Remove only inactive recipes
    python manage.py remove_all_recipes --inactive-only
    
    # Remove recipes for specific products
    python manage.py remove_all_recipes --product-ids 123 456 789
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from production.models import Recipe, RecipeIngredient
from products.models import Product


class Command(BaseCommand):
    help = 'Remove all recipes from the system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview changes without actually removing recipes',
        )
        parser.add_argument(
            '--inactive-only',
            action='store_true',
            help='Only remove inactive recipes (is_active=False)',
        )
        parser.add_argument(
            '--product-ids',
            nargs='+',
            type=int,
            help='Remove recipes only for specific product IDs',
        )
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Skip confirmation prompt (use with caution)',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed output for each recipe',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        inactive_only = options['inactive_only']
        product_ids = options.get('product_ids')
        skip_confirm = options.get('confirm', False)
        verbose = options.get('verbose', False)

        if dry_run:
            self.stdout.write(self.style.WARNING('🔍 Running in DRY-RUN mode. No changes will be saved.'))

        # Build query
        recipes_query = Recipe.objects.all()
        
        if inactive_only:
            recipes_query = recipes_query.filter(is_active=False)
            self.stdout.write(self.style.WARNING('⚠️  Only removing INACTIVE recipes'))
        
        if product_ids:
            recipes_query = recipes_query.filter(product_id__in=product_ids)
            self.stdout.write(f'📋 Filtering to product IDs: {product_ids}')

        # Get recipes to remove
        recipes_to_remove = recipes_query.select_related('product').prefetch_related('ingredients')
        total_count = recipes_to_remove.count()

        if total_count == 0:
            self.stdout.write(self.style.SUCCESS('✅ No recipes found to remove.'))
            return

        # Display what will be removed
        self.stdout.write(self.style.WARNING(f'\n⚠️  Found {total_count} recipe(s) to remove:\n'))
        
        for recipe in recipes_to_remove[:20]:  # Show first 20
            ingredient_count = recipe.ingredients.count()
            status = 'INACTIVE' if not recipe.is_active else 'ACTIVE'
            self.stdout.write(f"  • {recipe.product.name} (ID: {recipe.product.id}) - {status} - {ingredient_count} ingredient(s)")
        
        if total_count > 20:
            self.stdout.write(f"  ... and {total_count - 20} more recipe(s)")
        
        # Show summary
        active_count = recipes_to_remove.filter(is_active=True).count()
        inactive_count = recipes_to_remove.filter(is_active=False).count()
        
        self.stdout.write(f'\n📊 Summary:')
        self.stdout.write(f"   • Total recipes: {total_count}")
        if not inactive_only:
            self.stdout.write(f"   • Active: {active_count}")
            self.stdout.write(f"   • Inactive: {inactive_count}")

        if dry_run:
            self.stdout.write(self.style.WARNING(f'\n🔍 DRY-RUN: Would remove {total_count} recipe(s).'))
            return

        # Confirm before proceeding
        if not skip_confirm:
            self.stdout.write(self.style.ERROR(f'\n⚠️  WARNING: This will PERMANENTLY DELETE {total_count} recipe(s)!'))
            if active_count > 0:
                self.stdout.write(self.style.ERROR(f'   ⚠️  This includes {active_count} ACTIVE recipe(s)!'))
            confirm = input("Type 'DELETE ALL RECIPES' to confirm: ")
            if confirm != 'DELETE ALL RECIPES':
                self.stdout.write(self.style.ERROR('❌ Operation cancelled'))
                return

        # Remove recipes
        removed_count = 0
        ingredient_count = 0
        
        with transaction.atomic():
            for recipe in recipes_to_remove:
                product_name = recipe.product.name
                ingredients = recipe.ingredients.count()
                
                # Delete ingredients first (foreign key constraint)
                deleted_ingredients = RecipeIngredient.objects.filter(recipe=recipe).delete()[0]
                ingredient_count += deleted_ingredients
                
                # Delete recipe
                recipe.delete()
                removed_count += 1
                
                if verbose:
                    self.stdout.write(f"✅ Removed recipe for {product_name} ({ingredients} ingredients)")

        self.stdout.write(self.style.SUCCESS(f'\n🎉 Successfully removed {removed_count} recipe(s)!'))
        self.stdout.write(f"   • Ingredients removed: {ingredient_count}")
        
        # Show remaining recipes
        remaining = Recipe.objects.count()
        if remaining > 0:
            self.stdout.write(f"   • Recipes remaining: {remaining}")
        else:
            self.stdout.write(self.style.SUCCESS(f"   • ✅ All recipes removed!"))

