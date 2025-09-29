"""
Complete Database Seeding Update
Updates all seeding files with current database state to eliminate duplicates
and ensure consistency for production deployment
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from accounts.models import User, RestaurantProfile, FarmProfile, PrivateCustomerProfile
from products.models import Product, Department
from suppliers.models import Supplier, SalesRep, SupplierProduct
from inventory.models import PricingRule
import json
import os

class Command(BaseCommand):
    help = 'Update all seeding files with current database state'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output-dir',
            type=str,
            default='updated_seeding',
            help='Directory to output updated seeding files',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without creating files',
        )

    def handle(self, *args, **options):
        output_dir = options['output_dir']
        dry_run = options['dry_run']
        
        if not dry_run:
            os.makedirs(output_dir, exist_ok=True)
        
        self.stdout.write(self.style.SUCCESS('=== UPDATING COMPLETE DATABASE SEEDING ==='))
        
        # Update each component
        self.update_users_and_profiles(output_dir, dry_run)
        self.update_products_and_departments(output_dir, dry_run)
        self.update_suppliers_and_products(output_dir, dry_run)
        self.update_pricing_rules(output_dir, dry_run)
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - No files were created'))
        else:
            self.stdout.write(self.style.SUCCESS(f'✅ Updated seeding files in {output_dir}/'))

    def update_users_and_profiles(self, output_dir, dry_run):
        """Update users and customer profiles seeding"""
        self.stdout.write('\n📧 Updating Users and Profiles...')
        
        # Get all users with profiles
        users_data = []
        restaurant_profiles_data = []
        farm_profiles_data = []
        private_profiles_data = []
        
        for user in User.objects.all():
            user_data = {
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'user_type': user.user_type,
                'phone': user.phone,
                'is_verified': user.is_verified,
                'is_active': user.is_active,
                'is_staff': user.is_staff,
                'is_superuser': user.is_superuser,
                'roles': user.roles,
                'restaurant_roles': user.restaurant_roles,
            }
            users_data.append(user_data)
            
            # Add profile data
            if hasattr(user, 'restaurantprofile'):
                profile = user.restaurantprofile
                restaurant_profiles_data.append({
                    'user_email': user.email,
                    'business_name': profile.business_name,
                    'branch_name': profile.branch_name,
                    'business_registration': profile.business_registration,
                    'address': profile.address,
                    'city': profile.city,
                    'postal_code': profile.postal_code,
                    'payment_terms': profile.payment_terms,
                    'is_private_customer': profile.is_private_customer,
                    'delivery_notes': profile.delivery_notes,
                    'order_pattern': profile.order_pattern,
                    'preferred_pricing_rule': profile.preferred_pricing_rule.name if profile.preferred_pricing_rule else None,
                })
            
            if hasattr(user, 'farmprofile'):
                profile = user.farmprofile
                farm_profiles_data.append({
                    'user_email': user.email,
                    'employee_id': profile.employee_id,
                    'department': profile.department,
                    'position': profile.position,
                    'whatsapp_number': profile.whatsapp_number,
                    'access_level': profile.access_level,
                    'can_manage_inventory': profile.can_manage_inventory,
                    'can_approve_orders': profile.can_approve_orders,
                    'can_manage_customers': profile.can_manage_customers,
                    'can_view_reports': profile.can_view_reports,
                    'notes': profile.notes,
                })
            
            if hasattr(user, 'privatecustomerprofile'):
                profile = user.privatecustomerprofile
                private_profiles_data.append({
                    'user_email': user.email,
                    'customer_type': profile.customer_type,
                    'delivery_address': profile.delivery_address,
                    'delivery_instructions': profile.delivery_instructions,
                    'preferred_delivery_day': profile.preferred_delivery_day,
                    'whatsapp_number': profile.whatsapp_number,
                    'credit_limit': float(profile.credit_limit),
                    'order_notes': profile.order_notes,
                })
        
        # Output data
        seeding_data = {
            'users': users_data,
            'restaurant_profiles': restaurant_profiles_data,
            'farm_profiles': farm_profiles_data,
            'private_profiles': private_profiles_data,
        }
        
        self.stdout.write(f'  Users: {len(users_data)}')
        self.stdout.write(f'  Restaurant Profiles: {len(restaurant_profiles_data)}')
        self.stdout.write(f'  Farm Profiles: {len(farm_profiles_data)}')
        self.stdout.write(f'  Private Profiles: {len(private_profiles_data)}')
        
        if not dry_run:
            with open(f'{output_dir}/users_and_profiles.json', 'w') as f:
                json.dump(seeding_data, f, indent=2, default=str)

    def update_products_and_departments(self, output_dir, dry_run):
        """Update products and departments seeding"""
        self.stdout.write('\n🛍️ Updating Products and Departments...')
        
        # Departments
        departments_data = []
        for dept in Department.objects.all():
            departments_data.append({
                'name': dept.name,
                'description': dept.description,
            })
        
        # Products
        products_data = []
        for product in Product.objects.all():
            products_data.append({
                'name': product.name,
                'description': product.description,
                'department': product.department.name,
                'price': float(product.price),
                'unit': product.unit,
                'stock_level': float(product.stock_level),
                'minimum_stock': float(product.minimum_stock),
                'is_active': product.is_active,
                'needs_setup': product.needs_setup,
            })
        
        seeding_data = {
            'departments': departments_data,
            'products': products_data,
        }
        
        self.stdout.write(f'  Departments: {len(departments_data)}')
        self.stdout.write(f'  Products: {len(products_data)}')
        
        if not dry_run:
            with open(f'{output_dir}/products_and_departments.json', 'w') as f:
                json.dump(seeding_data, f, indent=2, default=str)

    def update_suppliers_and_products(self, output_dir, dry_run):
        """Update suppliers and supplier products seeding"""
        self.stdout.write('\n🏢 Updating Suppliers and Products...')
        
        # Suppliers
        suppliers_data = []
        for supplier in Supplier.objects.all():
            suppliers_data.append({
                'name': supplier.name,
                'contact_person': supplier.contact_person,
                'phone': supplier.phone,
                'email': supplier.email,
                'address': supplier.address,
                'description': supplier.description,
                'supplier_type': supplier.supplier_type,
                'registration_number': supplier.registration_number,
                'tax_number': supplier.tax_number,
                'payment_terms_days': supplier.payment_terms_days,
                'lead_time_days': supplier.lead_time_days,
                'minimum_order_value': float(supplier.minimum_order_value) if supplier.minimum_order_value else None,
                'is_active': supplier.is_active,
            })
        
        # Sales Reps
        sales_reps_data = []
        for rep in SalesRep.objects.all():
            sales_reps_data.append({
                'name': rep.name,
                'supplier': rep.supplier.name,
                'phone': rep.phone,
                'email': rep.email,
                'position': rep.position,
                'is_active': rep.is_active,
                'is_primary': rep.is_primary,
                'total_orders': rep.total_orders,
                'last_contact_date': rep.last_contact_date.isoformat() if rep.last_contact_date else None,
            })
        
        # Supplier Products
        supplier_products_data = []
        for sp in SupplierProduct.objects.all():
            supplier_products_data.append({
                'supplier': sp.supplier.name,
                'product': sp.product.name,
                'supplier_product_code': sp.supplier_product_code,
                'supplier_product_name': sp.supplier_product_name,
                'supplier_category_code': sp.supplier_category_code,
                'supplier_price': float(sp.supplier_price),
                'currency': sp.currency,
                'is_available': sp.is_available,
                'stock_quantity': sp.stock_quantity,
                'minimum_order_quantity': sp.minimum_order_quantity,
                'lead_time_days': sp.lead_time_days,
                'quality_rating': float(sp.quality_rating) if sp.quality_rating else None,
                'last_order_date': sp.last_order_date.isoformat() if sp.last_order_date else None,
            })
        
        seeding_data = {
            'suppliers': suppliers_data,
            'sales_reps': sales_reps_data,
            'supplier_products': supplier_products_data,
        }
        
        self.stdout.write(f'  Suppliers: {len(suppliers_data)}')
        self.stdout.write(f'  Sales Reps: {len(sales_reps_data)}')
        self.stdout.write(f'  Supplier Products: {len(supplier_products_data)}')
        
        if not dry_run:
            with open(f'{output_dir}/suppliers_and_products.json', 'w') as f:
                json.dump(seeding_data, f, indent=2, default=str)

    def update_pricing_rules(self, output_dir, dry_run):
        """Update pricing rules seeding"""
        self.stdout.write('\n💰 Updating Pricing Rules...')
        
        pricing_rules_data = []
        for rule in PricingRule.objects.all():
            pricing_rules_data.append({
                'name': rule.name,
                'description': rule.description,
                'customer_segment': rule.customer_segment,
                'base_markup_percentage': float(rule.base_markup_percentage),
                'volatility_adjustment': float(rule.volatility_adjustment),
                'minimum_margin_percentage': float(rule.minimum_margin_percentage),
                'category_adjustments': rule.category_adjustments,
                'trend_multiplier': float(rule.trend_multiplier),
                'seasonal_adjustment': float(rule.seasonal_adjustment),
                'is_active': rule.is_active,
                'effective_from': rule.effective_from.isoformat() if rule.effective_from else None,
                'effective_until': rule.effective_until.isoformat() if rule.effective_until else None,
            })
        
        seeding_data = {
            'pricing_rules': pricing_rules_data,
        }
        
        self.stdout.write(f'  Pricing Rules: {len(pricing_rules_data)}')
        
        if not dry_run:
            with open(f'{output_dir}/pricing_rules.json', 'w') as f:
                json.dump(seeding_data, f, indent=2, default=str)
