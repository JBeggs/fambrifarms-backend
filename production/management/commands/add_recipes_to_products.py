#!/usr/bin/env python3
"""
Django management command to add recipes to products

This command allows you to add recipes to products, which enables automatic
stock deduction from recipe ingredients when the product is ordered.

Usage:
    # Dry run - preview what would be created
    python manage.py add_recipes_to_products --dry-run
    
    # Add recipes from JSON file
    python manage.py add_recipes_to_products --from-json recipes.json
    
    # Add recipe to specific product
    python manage.py add_recipes_to_products --product-id 123 --ingredients-json '[{"product_id": 456, "quantity": 0.3, "unit": "kg"}]'
    
    # Add recipes to all products matching pattern
    python manage.py add_recipes_to_products --name-pattern "Mixed Lettuce" --auto-ingredients
    
    # List products that could have recipes
    python manage.py add_recipes_to_products --list-candidates
"""

import json
import os
from decimal import Decimal
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q
from products.models import Product
from production.models import Recipe, RecipeIngredient


class Command(BaseCommand):
    help = 'Add recipes to products for automatic ingredient stock deduction'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview changes without actually creating recipes',
        )
        parser.add_argument(
            '--from-json',
            type=str,
            help='Load recipes from JSON file (format: [{"product_id": 123, "name": "...", "batch_size": 1, "ingredients": [...]}, ...])',
        )
        parser.add_argument(
            '--product-id',
            type=int,
            help='Add recipe to specific product by ID',
        )
        parser.add_argument(
            '--name-pattern',
            type=str,
            help='Add recipes to products matching name pattern (e.g., "Mixed Lettuce")',
        )
        parser.add_argument(
            '--ingredients-json',
            type=str,
            help='JSON array of ingredients for single product recipe (format: [{"product_id": 456, "quantity": 0.3, "unit": "kg"}, ...])',
        )
        parser.add_argument(
            '--auto-ingredients',
            action='store_true',
            help='Automatically find ingredient products based on product name patterns (experimental)',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=1,
            help='Batch size for recipe (default: 1)',
        )
        parser.add_argument(
            '--list-candidates',
            action='store_true',
            help='List products that might need recipes (products with "Mixed", "Box", etc. in name)',
        )
        parser.add_argument(
            '--skip-existing',
            action='store_true',
            help='Skip products that already have recipes',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed output for each recipe',
        )
        parser.add_argument(
            '--auto-match-kg',
            action='store_true',
            help='Automatically match box/bag/packet products to their kg versions and create recipes',
        )

    def find_ingredient_products(self, product_name, product_unit):
        """
        Attempt to find ingredient products based on product name patterns
        
        Examples:
            "Mixed Lettuce" -> Find "Romaine Lettuce", "Butter Lettuce", "Arugula"
            "Tomatoes (kg)" -> Find "Tomatoes (5kg box)"
        """
        ingredients = []
        
        # Pattern 1: Mixed products
        if 'mixed' in product_name.lower():
            # Try to find individual lettuce types
            base_name = product_name.lower().replace('mixed', '').replace('lettuce', '').strip()
            if 'lettuce' in product_name.lower():
                # Look for individual lettuce products
                lettuce_types = ['romaine', 'butter', 'arugula', 'iceberg', 'green leaf', 'red leaf']
                for lettuce_type in lettuce_types:
                    search_name = f"{lettuce_type} lettuce"
                    try:
                        ingredient = Product.objects.filter(
                            name__icontains=search_name,
                            is_active=True
                        ).first()
                        if ingredient:
                            # Default to equal parts (can be adjusted)
                            ingredients.append({
                                'product': ingredient,
                                'quantity': Decimal('0.33'),  # 1/3 for 3 ingredients
                                'unit': product_unit,
                            })
                    except:
                        pass
        
        # Pattern 2: Kg products that might need box ingredients
        if product_unit.lower() == 'kg' and 'box' not in product_name.lower():
            # Look for box version of same product
            base_name = product_name.lower().replace('(kg)', '').replace('kg', '').strip()
            try:
                box_product = Product.objects.filter(
                    Q(name__icontains=base_name) & Q(name__icontains='box'),
                    is_active=True
                ).first()
                if box_product:
                    # Extract box size from name or packaging_size
                    box_size = self._extract_box_size(box_product)
                    if box_size:
                        ingredients.append({
                            'product': box_product,
                            'quantity': Decimal('1'),  # 1 box = X kg
                            'unit': 'box',
                        })
            except:
                pass
        
        return ingredients

    def _extract_box_size(self, product):
        """Extract box size in kg from product name or packaging_size"""
        if product.packaging_size:
            # Try to parse packaging_size (e.g., "5kg")
            import re
            match = re.search(r'(\d+(?:\.\d+)?)\s*kg', product.packaging_size, re.IGNORECASE)
            if match:
                return Decimal(match.group(1))
            
            # Try grams (convert to kg)
            match = re.search(r'(\d+(?:\.\d+)?)\s*g', product.packaging_size, re.IGNORECASE)
            if match:
                return Decimal(match.group(1)) / Decimal('1000')
        
        # Try to extract from name
        import re
        match = re.search(r'(\d+(?:\.\d+)?)\s*kg', product.name, re.IGNORECASE)
        if match:
            return Decimal(match.group(1))
        
        # Try grams in name (convert to kg)
        match = re.search(r'(\d+(?:\.\d+)?)\s*g', product.name, re.IGNORECASE)
        if match:
            return Decimal(match.group(1)) / Decimal('1000')
        
        return None

    def _extract_base_product_name(self, product_name):
        """
        Extract base product name by removing packaging information
        
        Examples:
            "Tomatoes (5kg box)" -> "Tomatoes"
            "Carrots (2kg bag)" -> "Carrots"
            "Basil (100g packet)" -> "Basil"
        """
        import re
        # Remove parentheses content
        base_name = re.sub(r'\s*\([^)]*\)', '', product_name)
        # Remove packaging words
        packaging_words = ['box', 'bag', 'packet', 'punnet', 'bunch', 'head', 'each', 'piece']
        for word in packaging_words:
            base_name = re.sub(r'\b' + word + r'\b', '', base_name, flags=re.IGNORECASE)
        # Remove weight units
        base_name = re.sub(r'\b\d+(?:\.\d+)?\s*(kg|g|ml|l)\b', '', base_name, flags=re.IGNORECASE)
        # Clean up whitespace
        base_name = re.sub(r'\s+', ' ', base_name).strip()
        return base_name

    def _find_kg_product_for_package(self, package_product):
        """
        Find the kg version of a package product
        
        Args:
            package_product: Product with unit in ['box', 'bag', 'packet', 'punnet']
        
        Returns:
            Matching kg Product or None
        """
        base_name = self._extract_base_product_name(package_product.name)
        
        # Try to find kg product with same base name
        # Pattern 1: "{base_name} (kg)"
        kg_product = Product.objects.filter(
            name__iexact=f"{base_name} (kg)",
            unit='kg',
            is_active=True
        ).first()
        
        if kg_product:
            return kg_product
        
        # Pattern 2: "{base_name} kg" (without parentheses)
        kg_product = Product.objects.filter(
            name__iexact=f"{base_name} kg",
            unit='kg',
            is_active=True
        ).first()
        
        if kg_product:
            return kg_product
        
        # Pattern 3: Name contains base name and unit is kg
        kg_products = Product.objects.filter(
            name__icontains=base_name,
            unit='kg',
            is_active=True
        ).exclude(name__icontains='box').exclude(name__icontains='bag').exclude(name__icontains='packet')
        
        # Prefer exact match
        for kg_product in kg_products:
            kg_base = self._extract_base_product_name(kg_product.name)
            if kg_base.lower() == base_name.lower():
                return kg_product
        
        # Return first match if any
        return kg_products.first()

    def auto_match_kg_products(self, skip_existing=False, verbose=False):
        """
        Automatically match box/bag/packet products to their kg versions and create recipes
        
        Strategy:
        1. Find all products with units: box, bag, packet, punnet
        2. Check if they have packaging_size set
        3. Find matching kg product
        4. Create recipe: kg product uses package product as ingredient
        5. Batch size = packaging_size in kg
        """
        recipes_to_create = []
        
        # Find all package products (box, bag, packet, punnet)
        package_units = ['box', 'bag', 'packet', 'punnet']
        package_products = Product.objects.filter(
            unit__in=package_units,
            is_active=True
        ).exclude(packaging_size__isnull=True).exclude(packaging_size='')
        
        self.stdout.write(f"\n🔍 Found {package_products.count()} package products with packaging_size")
        
        matched_count = 0
        skipped_count = 0
        no_kg_count = 0
        no_size_count = 0
        
        for package_product in package_products:
            # Extract packaging size in kg
            packaging_size_kg = self._extract_box_size(package_product)
            
            if not packaging_size_kg:
                no_size_count += 1
                if verbose:
                    self.stdout.write(f"⚠️  {package_product.name}: Could not extract packaging size")
                continue
            
            # Find matching kg product
            kg_product = self._find_kg_product_for_package(package_product)
            
            if not kg_product:
                no_kg_count += 1
                if verbose:
                    self.stdout.write(f"⚠️  {package_product.name}: No matching kg product found")
                continue
            
            # Check if kg product already has recipe
            if skip_existing and hasattr(kg_product, 'recipe') and kg_product.recipe:
                skipped_count += 1
                if verbose:
                    self.stdout.write(f"⏭️  {kg_product.name}: Already has recipe")
                continue
            
            # Create recipe data
            # Recipe: kg product uses package product as ingredient
            # Batch size = packaging_size_kg (e.g., if box is 5kg, batch_size = 5)
            # Ingredient: 1 package = packaging_size_kg kg
            recipes_to_create.append({
                'product': kg_product,
                'name': f'Recipe for {kg_product.name}',
                'description': f'Auto-generated: 1 {package_product.unit} = {packaging_size_kg}kg',
                'batch_size': int(packaging_size_kg),  # Batch size in kg
                'ingredients': [{
                    'product': package_product,
                    'quantity': Decimal('1'),  # 1 package
                    'unit': package_product.unit,
                }],
            })
            
            matched_count += 1
            if verbose:
                self.stdout.write(f"✅ Matched: {package_product.name} ({packaging_size_kg}kg) -> {kg_product.name}")
        
        self.stdout.write(f"\n📊 Matching Summary:")
        self.stdout.write(f"   ✅ Matched: {matched_count}")
        self.stdout.write(f"   ⏭️  Skipped (has recipe): {skipped_count}")
        self.stdout.write(f"   ⚠️  No kg product: {no_kg_count}")
        self.stdout.write(f"   ⚠️  No packaging size: {no_size_count}")
        
        return recipes_to_create

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        json_file = options.get('from_json')
        product_id = options.get('product_id')
        name_pattern = options.get('name_pattern')
        ingredients_json = options.get('ingredients_json')
        auto_ingredients = options.get('auto_ingredients', False)
        batch_size = options.get('batch_size', 1)
        list_candidates = options.get('list_candidates', False)
        skip_existing = options.get('skip_existing', False)
        verbose = options.get('verbose', False)
        auto_match_kg = options.get('auto_match_kg', False)

        if dry_run:
            self.stdout.write(self.style.WARNING('🔍 Running in DRY-RUN mode. No changes will be saved.'))

        # Auto-match kg products mode
        if auto_match_kg:
            recipes_to_create = self.auto_match_kg_products(skip_existing=skip_existing, verbose=verbose)
            
            if not recipes_to_create:
                self.stdout.write(self.style.WARNING('\n⚠️  No recipes to create from auto-matching.'))
                return
            
            # Display what will be created
            self.stdout.write(self.style.SUCCESS(f'\n📋 Found {len(recipes_to_create)} recipes to create:\n'))
            
            for recipe_data in recipes_to_create:
                product = recipe_data['product']
                ingredients = recipe_data['ingredients']
                
                self.stdout.write(f"🔸 {product.name} (ID: {product.id})")
                self.stdout.write(f"   Batch size: {recipe_data['batch_size']} kg")
                self.stdout.write(f"   Ingredients ({len(ingredients)}):")
                
                for ing in ingredients:
                    ing_product = ing['product']
                    ing_qty = ing['quantity']
                    ing_unit = ing.get('unit', ing_product.unit)
                    
                    self.stdout.write(f"     • {ing_product.name}: {ing_qty} {ing_unit}")
                
                self.stdout.write('')
            
            if dry_run:
                self.stdout.write(self.style.WARNING(f'\n🔍 DRY-RUN: Would create {len(recipes_to_create)} recipes.'))
                return
            
            # Confirm before proceeding
            self.stdout.write(self.style.WARNING(f'\n⚠️  This will create {len(recipes_to_create)} recipes!'))
            confirm = input("Type 'yes' to proceed: ")
            if confirm.lower() != 'yes':
                self.stdout.write(self.style.ERROR('❌ Operation cancelled'))
                return
            
            # Create recipes (reuse existing creation logic)
            created_count = 0
            skipped_count = 0
            
            with transaction.atomic():
                for recipe_data in recipes_to_create:
                    product = recipe_data['product']
                    
                    # Check if recipe already exists
                    if hasattr(product, 'recipe') and product.recipe:
                        if skip_existing:
                            skipped_count += 1
                            continue
                        else:
                            # Update existing recipe
                            recipe = product.recipe
                            recipe.name = recipe_data['name']
                            recipe.description = recipe_data['description']
                            recipe.batch_size = recipe_data['batch_size']
                            recipe.is_active = True
                            recipe.save()
                            
                            # Clear existing ingredients
                            RecipeIngredient.objects.filter(recipe=recipe).delete()
                    else:
                        # Create new recipe
                        recipe = Recipe.objects.create(
                            product=product,
                            name=recipe_data['name'],
                            description=recipe_data['description'],
                            batch_size=recipe_data['batch_size'],
                            is_active=True,
                        )
                    
                    # Add ingredients
                    for ing in recipe_data['ingredients']:
                        ing_product = ing['product']
                        ing_qty = ing['quantity']
                        ing_unit = ing.get('unit', ing_product.unit)
                        
                        RecipeIngredient.objects.create(
                            recipe=recipe,
                            raw_material=ing_product,
                            quantity=ing_qty,
                            unit=ing_unit,
                        )
                    
                    created_count += 1
                    
                    if verbose:
                        self.stdout.write(f"✅ Created recipe for {product.name} with {len(recipe_data['ingredients'])} ingredients")
            
            self.stdout.write(self.style.SUCCESS(f'\n🎉 Successfully created {created_count} recipes!'))
            if skipped_count > 0:
                self.stdout.write(f"   ⏭️  Skipped {skipped_count} products (already have recipes)")
            
            return

        # List candidates mode
        if list_candidates:
            self.stdout.write(self.style.SUCCESS('\n📋 Products that might need recipes:\n'))
            
            # Find products with "Mixed" in name
            mixed_products = Product.objects.filter(
                name__icontains='mixed',
                is_active=True
            ).exclude(recipe__isnull=False).order_by('name')
            
            if mixed_products.exists():
                self.stdout.write(f'\n🔸 Mixed Products ({mixed_products.count()}):')
                for product in mixed_products:
                    self.stdout.write(f"  • {product.name} (ID: {product.id}, unit: {product.unit})")
            
            # Find kg products that might have box versions
            kg_products = Product.objects.filter(
                unit='kg',
                is_active=True
            ).exclude(name__icontains='box').exclude(recipe__isnull=False).order_by('name')[:20]
            
            if kg_products.exists():
                self.stdout.write(f'\n🔸 Kg Products (showing first 20):')
                for product in kg_products:
                    # Check if box version exists
                    box_exists = Product.objects.filter(
                        Q(name__icontains=product.name.split('(')[0].strip()) & Q(name__icontains='box'),
                        is_active=True
                    ).exists()
                    if box_exists:
                        self.stdout.write(f"  • {product.name} (ID: {product.id}) - has box version")
            
            # Find package products that could be auto-matched
            package_units = ['box', 'bag', 'packet', 'punnet']
            package_products = Product.objects.filter(
                unit__in=package_units,
                is_active=True
            ).exclude(packaging_size__isnull=True).exclude(packaging_size='')
            
            auto_matchable = []
            for package_product in package_products:
                packaging_size_kg = self._extract_box_size(package_product)
                if packaging_size_kg:
                    kg_product = self._find_kg_product_for_package(package_product)
                    if kg_product and not (hasattr(kg_product, 'recipe') and kg_product.recipe):
                        auto_matchable.append((package_product, kg_product, packaging_size_kg))
            
            if auto_matchable:
                self.stdout.write(f'\n🔸 Auto-Matchable Products ({len(auto_matchable)}):')
                self.stdout.write(f'   (Use --auto-match-kg to create recipes automatically)')
                for package_product, kg_product, size_kg in auto_matchable[:20]:
                    self.stdout.write(f"  • {package_product.name} ({package_product.packaging_size}) -> {kg_product.name} (1 {package_product.unit} = {size_kg}kg)")
            
            self.stdout.write('')
            return

        recipes_to_create = []

        # Load from JSON file
        if json_file:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    recipes_data = json.load(f)
                    
                for recipe_data in recipes_data:
                    try:
                        product = Product.objects.get(id=recipe_data['product_id'])
                        
                        # Check if recipe already exists
                        if skip_existing and hasattr(product, 'recipe'):
                            if verbose:
                                self.stdout.write(f"⏭️  Skipping {product.name} - already has recipe")
                            continue
                        
                        recipes_to_create.append({
                            'product': product,
                            'name': recipe_data.get('name', f'Recipe for {product.name}'),
                            'description': recipe_data.get('description', ''),
                            'batch_size': recipe_data.get('batch_size', 1),
                            'ingredients': recipe_data.get('ingredients', []),
                        })
                    except Product.DoesNotExist:
                        self.stdout.write(self.style.ERROR(f"❌ Product ID {recipe_data['product_id']} not found"))
            except FileNotFoundError:
                raise CommandError(f"JSON file not found: {json_file}")
            except json.JSONDecodeError as e:
                raise CommandError(f"Invalid JSON file: {e}")

        # Single product mode
        elif product_id:
            try:
                product = Product.objects.get(id=product_id)
                
                # Check if recipe already exists
                if skip_existing and hasattr(product, 'recipe'):
                    self.stdout.write(self.style.WARNING(f"⏭️  Product {product.name} already has a recipe. Use --skip-existing to skip."))
                    return
                
                ingredients = []
                
                # Load ingredients from JSON
                if ingredients_json:
                    try:
                        ingredients_data = json.loads(ingredients_json)
                        for ing_data in ingredients_data:
                            try:
                                ing_product = Product.objects.get(id=ing_data['product_id'])
                                ingredients.append({
                                    'product': ing_product,
                                    'quantity': Decimal(str(ing_data['quantity'])),
                                    'unit': ing_data.get('unit', ing_product.unit),
                                })
                            except Product.DoesNotExist:
                                self.stdout.write(self.style.ERROR(f"❌ Ingredient product ID {ing_data['product_id']} not found"))
                    except json.JSONDecodeError as e:
                        raise CommandError(f"Invalid ingredients JSON: {e}")
                
                # Auto-find ingredients
                elif auto_ingredients:
                    ingredients = self.find_ingredient_products(product.name, product.unit)
                    if not ingredients:
                        self.stdout.write(self.style.WARNING(f"⚠️  Could not auto-find ingredients for {product.name}"))
                        return
                
                else:
                    raise CommandError("Must provide --ingredients-json or --auto-ingredients for single product")
                
                recipes_to_create.append({
                    'product': product,
                    'name': f'Recipe for {product.name}',
                    'description': '',
                    'batch_size': batch_size,
                    'ingredients': ingredients,
                })
            except Product.DoesNotExist:
                raise CommandError(f"Product with ID {product_id} not found")

        # Pattern matching mode
        elif name_pattern:
            products = Product.objects.filter(
                name__icontains=name_pattern,
                is_active=True
            )
            
            if not products.exists():
                self.stdout.write(self.style.WARNING(f"⚠️  No products found matching pattern: {name_pattern}"))
                return
            
            self.stdout.write(f"Found {products.count()} products matching '{name_pattern}'")
            
            for product in products:
                # Check if recipe already exists
                if skip_existing and hasattr(product, 'recipe'):
                    if verbose:
                        self.stdout.write(f"⏭️  Skipping {product.name} - already has recipe")
                    continue
                
                ingredients = []
                
                if auto_ingredients:
                    ingredients = self.find_ingredient_products(product.name, product.unit)
                    if not ingredients:
                        if verbose:
                            self.stdout.write(f"⚠️  Could not auto-find ingredients for {product.name}")
                        continue
                else:
                    raise CommandError("Must provide --auto-ingredients or use --from-json for pattern matching")
                
                recipes_to_create.append({
                    'product': product,
                    'name': f'Recipe for {product.name}',
                    'description': '',
                    'batch_size': batch_size,
                    'ingredients': ingredients,
                })

        else:
            raise CommandError("Must provide --from-json, --product-id, or --name-pattern")

        if not recipes_to_create:
            self.stdout.write(self.style.WARNING('No recipes to create.'))
            return

        # Display what will be created
        self.stdout.write(self.style.SUCCESS(f'\n📋 Found {len(recipes_to_create)} recipes to create:\n'))
        
        for recipe_data in recipes_to_create:
            product = recipe_data['product']
            ingredients = recipe_data['ingredients']
            
            self.stdout.write(f"🔸 {product.name} (ID: {product.id})")
            self.stdout.write(f"   Batch size: {recipe_data['batch_size']}")
            self.stdout.write(f"   Ingredients ({len(ingredients)}):")
            
            for ing in ingredients:
                if isinstance(ing, dict):
                    ing_product = ing['product']
                    ing_qty = ing['quantity']
                    ing_unit = ing.get('unit', ing_product.unit)
                else:
                    # Handle JSON format
                    ing_product = Product.objects.get(id=ing['product_id'])
                    ing_qty = Decimal(str(ing['quantity']))
                    ing_unit = ing.get('unit', ing_product.unit)
                
                self.stdout.write(f"     • {ing_product.name}: {ing_qty} {ing_unit}")
            
            self.stdout.write('')

        if dry_run:
            self.stdout.write(self.style.WARNING(f'\n🔍 DRY-RUN: Would create {len(recipes_to_create)} recipes.'))
            return

        # Confirm before proceeding
        self.stdout.write(self.style.WARNING(f'\n⚠️  This will create {len(recipes_to_create)} recipes!'))
        confirm = input("Type 'yes' to proceed: ")
        if confirm.lower() != 'yes':
            self.stdout.write(self.style.ERROR('❌ Operation cancelled'))
            return

        # Create recipes
        created_count = 0
        skipped_count = 0
        
        with transaction.atomic():
            for recipe_data in recipes_to_create:
                product = recipe_data['product']
                
                # Check if recipe already exists
                if hasattr(product, 'recipe') and product.recipe:
                    if skip_existing:
                        skipped_count += 1
                        if verbose:
                            self.stdout.write(f"⏭️  Skipping {product.name} - already has recipe")
                        continue
                    else:
                        # Update existing recipe
                        recipe = product.recipe
                        recipe.name = recipe_data['name']
                        recipe.description = recipe_data['description']
                        recipe.batch_size = recipe_data['batch_size']
                        recipe.is_active = True
                        recipe.save()
                        
                        # Clear existing ingredients
                        RecipeIngredient.objects.filter(recipe=recipe).delete()
                else:
                    # Create new recipe
                    recipe = Recipe.objects.create(
                        product=product,
                        name=recipe_data['name'],
                        description=recipe_data['description'],
                        batch_size=recipe_data['batch_size'],
                        is_active=True,
                    )
                
                # Add ingredients
                for ing in recipe_data['ingredients']:
                    if isinstance(ing, dict) and 'product' in ing:
                        # Already processed format
                        ing_product = ing['product']
                        ing_qty = ing['quantity']
                        ing_unit = ing.get('unit', ing_product.unit)
                    else:
                        # JSON format
                        ing_product = Product.objects.get(id=ing['product_id'])
                        ing_qty = Decimal(str(ing['quantity']))
                        ing_unit = ing.get('unit', ing_product.unit)
                    
                    RecipeIngredient.objects.create(
                        recipe=recipe,
                        raw_material=ing_product,
                        quantity=ing_qty,
                        unit=ing_unit,
                    )
                
                created_count += 1
                
                if verbose:
                    self.stdout.write(f"✅ Created recipe for {product.name} with {len(recipe_data['ingredients'])} ingredients")

        self.stdout.write(self.style.SUCCESS(f'\n🎉 Successfully created {created_count} recipes!'))
        if skipped_count > 0:
            self.stdout.write(f"   ⏭️  Skipped {skipped_count} products (already have recipes)")

