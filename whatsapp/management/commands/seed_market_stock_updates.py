#!/usr/bin/env python3
"""
Django management command to create stock updates based on market purchases
Correlates with supplier pricing data from market invoices

Usage:
    python manage.py seed_market_stock_updates [--dry-run] [--date YYYY-MM-DD]
"""

import json
import os
from datetime import datetime, timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from products.models import Product
from inventory.models import StockMovement


class Command(BaseCommand):
    help = 'Create stock updates based on market purchase data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without making changes',
        )
        parser.add_argument(
            '--date',
            type=str,
            help='Date for stock updates (YYYY-MM-DD). Defaults to both market dates.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        target_date = options.get('date')
        
        self.stdout.write(f"{'🔍 DRY RUN: ' if dry_run else ''}Creating stock updates from market purchases")
        
        # Load supplier pricing data
        supplier_file = os.path.join('data', 'supplier_pricing_data.json')
        if not os.path.exists(supplier_file):
            self.stdout.write(self.style.ERROR(f'Supplier pricing file not found: {supplier_file}'))
            return
        
        with open(supplier_file, 'r', encoding='utf-8') as f:
            supplier_data = json.load(f)
        
        # Get market purchases
        market_data = supplier_data['suppliers']['tshwane_market']['invoices']
        
        # Filter by date if specified
        if target_date:
            if target_date in market_data:
                invoices_to_process = {target_date: market_data[target_date]}
            else:
                self.stdout.write(self.style.ERROR(f'No market data found for date: {target_date}'))
                return
        else:
            invoices_to_process = market_data
        
        self.stdout.write(f"📊 Processing {len(invoices_to_process)} market invoices")
        
        total_movements = 0
        total_value = 0
        
        for date_str, invoice in invoices_to_process.items():
            self.stdout.write(f"\n📅 Processing market purchase for {date_str}")
            self.stdout.write(f"   Invoice: {invoice.get('receipt_number', 'N/A')}")
            self.stdout.write(f"   Total: R{invoice['total_amount']:,.2f}")
            self.stdout.write(f"   Weight: {invoice['total_weight_kg']:,.1f}kg")
            
            purchase_date = datetime.strptime(date_str, '%Y-%m-%d')
            movements_created = 0
            
            for product_key, product_data in invoice['products'].items():
                if not dry_run:
                    with transaction.atomic():
                        # Try to find matching product
                        product_name = product_data['description']
                        unit = product_data['unit_type']
                        quantity = Decimal(str(product_data['actual_weight_kg']))
                        unit_price = Decimal(str(product_data['price_per_kg']))
                        
                        # Map unit types
                        unit_mapping = {
                            'each': 'piece',
                            'pack': 'packet',
                            'punnet': 'punnet',
                            'bag': 'bag',
                            'box': 'box',
                            'head': 'head',
                            'bunch': 'bunch'
                        }
                        mapped_unit = unit_mapping.get(unit, unit)
                        
                        # Try to find or create product
                        try:
                            # First, try exact name match
                            product = Product.objects.filter(
                                name__icontains=product_name.split()[0],  # Use first word
                                unit__in=[mapped_unit, 'kg']  # Accept kg or original unit
                            ).first()
                            
                            if not product:
                                # Create new product if not found
                                self.stdout.write(f"   🆕 Creating product: {product_name}")
                                # Determine department based on product name
                                dept_name = self._get_department_from_name(product_name)
                                from products.models import Department
                                department, _ = Department.objects.get_or_create(
                                    name=dept_name,
                                    defaults={'description': f'{dept_name} products'}
                                )
                                
                                product = Product.objects.create(
                                    name=product_name,
                                    department=department,
                                    price=unit_price,
                                    unit='kg',  # Market purchases are by weight
                                    stock_level=Decimal('0.00'),
                                    needs_setup=True
                                )
                            
                            # Create stock movement (purchase)
                            movement = StockMovement.objects.create(
                                product=product,
                                movement_type='purchase',
                                quantity=quantity,
                                unit=product.unit,
                                unit_cost=unit_price,
                                total_cost=quantity * unit_price,
                                movement_date=purchase_date,
                                reference=f"Market Purchase - {invoice.get('receipt_number', 'N/A')}",
                                notes=f"Tshwane Market purchase - {product_data['description']}",
                                created_by_system=True
                            )
                            
                            # Update product stock level
                            product.stock_level += quantity
                            product.save()
                            
                            movements_created += 1
                            total_value += float(quantity * unit_price)
                            
                        except Exception as e:
                            self.stdout.write(f"   ⚠️  Error processing {product_name}: {e}")
                            continue
                else:
                    # Dry run - just show what would be created
                    self.stdout.write(f"   📦 Would add stock: {product_data['description']}")
                    self.stdout.write(f"      Quantity: {product_data['actual_weight_kg']}kg")
                    self.stdout.write(f"      Unit Price: R{product_data['price_per_kg']:.2f}/kg")
                    movements_created += 1
            
            total_movements += movements_created
            self.stdout.write(f"   ✅ {'Would create' if dry_run else 'Created'} {movements_created} stock movements")
        
        if not dry_run:
            self.stdout.write(self.style.SUCCESS(f'\n🎉 Stock updates completed!'))
            self.stdout.write(f"   • Total movements created: {total_movements}")
            self.stdout.write(f"   • Total value added: R{total_value:,.2f}")
        else:
            self.stdout.write(self.style.WARNING('\n🔍 DRY RUN COMPLETE - No changes made'))
            self.stdout.write(f"   • Would create: {total_movements} stock movements")
        
        # Show next steps
        self.stdout.write(f"\n📋 Next Steps:")
        self.stdout.write(f"   1. Review created products with needs_setup=True")
        self.stdout.write(f"   2. Adjust product names and departments as needed")
        self.stdout.write(f"   3. Update product pricing rules")
        self.stdout.write(f"   4. Verify stock levels are correct")
        
        self.stdout.write(f"\n✅ Command completed!")
    
    def _get_department_from_name(self, product_name):
        """Determine department based on product name"""
        name_lower = product_name.lower()
        
        if any(fruit in name_lower for fruit in ['apple', 'orange', 'grape', 'lemon', 'pineapple', 'strawber', 'kiwi', 'avocado', 'banana', 'papino', 'musk', 'sweet melon', 'blueberr']):
            return 'Fruits'
        elif any(veg in name_lower for veg in ['potato', 'onion', 'tomato', 'pepper', 'carrot', 'cabbage', 'lettuce', 'celery', 'cucumber', 'broccoli', 'cauliflower', 'spinach', 'chilli', 'butternut', 'marrow', 'leek']):
            return 'Vegetables'
        elif any(herb in name_lower for herb in ['herb', 'parsley', 'basil', 'rocket', 'mint', 'dill', 'chive', 'coriander', 'rosemary', 'thyme']):
            return 'Herbs'
        elif 'mushroom' in name_lower:
            return 'Mushrooms'
        else:
            return 'Vegetables'  # Default
