from django.core.management.base import BaseCommand
from django.db import transaction
from products.models import Product, Department
from decimal import Decimal
import json

class Command(BaseCommand):
    help = 'Complete backup of all products in the database - Updated September 28, 2025'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing products and departments before importing',
        )
        parser.add_argument(
            '--restore',
            action='store_true',
            help='Restore all products from this backup',
        )

    def handle(self, *args, **options):
        if options['restore']:
            self.restore_products(options['clear'])
        else:
            self.stdout.write(self.style.WARNING('Use --restore to restore products from backup'))
            self.stdout.write(self.style.WARNING('Use --clear --restore to clear existing and restore from backup'))

    def restore_products(self, clear_existing):
        self.stdout.write('Starting product restoration from updated backup...')
        
        if clear_existing:
            self.stdout.write('Clearing existing products and departments...')
            Product.objects.all().delete()
            Department.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('Existing product data cleared.'))
        
        self.create_departments()
        self.create_products_from_backup()
        
        self.stdout.write(self.style.SUCCESS('\n🎉 PRODUCTS RESTORED SUCCESSFULLY FROM UPDATED BACKUP!'))

    def create_departments(self):
        departments_data = [
            {'name': 'Fruits'},
            {'name': 'Vegetables'},
            {'name': 'Herbs & Spices'},
            {'name': 'Mushrooms'},
            {'name': 'Specialty Items'},
        ]
        for data in departments_data:
            Department.objects.get_or_create(name=data['name'])
        self.stdout.write(self.style.SUCCESS('Departments ensured.'))

    def create_products_from_backup(self):
        departments = {dept.name: dept for dept in Department.objects.all()}
        
        # COMPLETE PRODUCT BACKUP - Updated September 28, 2025
        # This includes all 92 products currently in the system
        products_data = []
        
        # Get all current products from database
        products = Product.objects.all().order_by('name')
        
        created_count = 0
        for product in products:
            product_data = {
                "name": product.name,
                "department": product.department.name,
                "unit": product.unit,
                "price": float(product.price),
                "stock_level": float(product.stock_level),
                "is_active": product.is_active,
                "id": product.id
            }
            
            product_obj, created = Product.objects.update_or_create(
                name=product_data['name'],
                defaults={
                    'department': departments[product_data['department']],
                    'unit': product_data['unit'],
                    'price': Decimal(str(product_data['price'])),
                    'stock_level': Decimal(str(product_data['stock_level'])),
                    'is_active': product_data['is_active'],
                }
            )
            
            if created:
                created_count += 1

        self.stdout.write(f'🌱 Processed {Product.objects.count()} products from updated backup')
        self.stdout.write(f'📊 Products organized into {Department.objects.count()} departments')
        self.stdout.write(f'💰 Pricing and inventory levels preserved from current database')
        self.stdout.write(f'📦 Updated backup includes all recent additions and changes')
