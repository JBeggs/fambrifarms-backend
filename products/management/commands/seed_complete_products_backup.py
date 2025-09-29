from django.core.management.base import BaseCommand
from django.db import transaction
from products.models import Product, Department
from decimal import Decimal


class Command(BaseCommand):
    help = 'Complete backup of all products in the database - Generated automatically'

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
        if options['clear']:
            self.stdout.write('Clearing existing products and departments...')
            Product.objects.all().delete()
            Department.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('Existing product data cleared.'))

        if options['restore']:
            self.create_departments()
            self.restore_all_products()
            self.stdout.write(
                self.style.SUCCESS(
                    f'\n🎉 ALL PRODUCTS RESTORED FROM BACKUP!'
                )
            )
            self.stdout.write(f'📊 Total products restored: {len(self.get_complete_products_data())}')
        else:
            self.stdout.write('Use --restore to restore products from backup')
            self.stdout.write('Use --clear --restore to clear existing and restore from backup')

    def create_departments(self):
        """Create product departments"""
        departments_data = [
            {
                'name': 'Fruits',
                'description': 'Fresh fruits and citrus',
                'is_active': True
            },
            {
                'name': 'Vegetables', 
                'description': 'Fresh vegetables and produce',
                'is_active': True
            },
            {
                'name': 'Herbs & Spices',
                'description': 'Fresh herbs, spices and aromatics',
                'is_active': True
            },
            {
                'name': 'Mushrooms',
                'description': 'Fresh mushrooms and fungi',
                'is_active': True
            },
            {
                'name': 'Specialty Items',
                'description': 'Specialty and gourmet items',
                'is_active': True
            }
        ]
        
        for dept_data in departments_data:
            department, created = Department.objects.get_or_create(
                name=dept_data['name'],
                defaults={
                    'description': dept_data['description'],
                    'is_active': dept_data['is_active']
                }
            )
            if created:
                self.stdout.write(f'Created department: {department.name}')

    def restore_all_products(self):
        """Restore all products from backup data"""
        departments = {dept.name: dept for dept in Department.objects.all()}
        products_data = self.get_complete_products_data()
        
        created_count = 0
        updated_count = 0
        
        with transaction.atomic():
            for product_data in products_data:
                department = departments.get(product_data['department'])
                if not department:
                    self.stdout.write(
                        self.style.WARNING(f'Department not found: {product_data["department"]}')
                    )
                    continue
                
                product, created = Product.objects.get_or_create(
                    name=product_data['name'],
                    defaults={
                        'department': department,
                        'unit': product_data['unit'],
                        'price': Decimal(str(product_data['price'])),
                        'stock_level': Decimal(str(product_data['stock_level'])),
                        'is_active': product_data['is_active']
                    }
                )
                
                if created:
                    created_count += 1
                else:
                    # Update existing product
                    product.department = department
                    product.unit = product_data['unit']
                    product.price = Decimal(str(product_data['price']))
                    product.stock_level = Decimal(str(product_data['stock_level']))
                    product.is_active = product_data['is_active']
                    product.save()
                    updated_count += 1
        
        self.stdout.write(f'Products created: {created_count}')
        self.stdout.write(f'Products updated: {updated_count}')

    def get_complete_products_data(self):
        """Complete product backup - Updated September 28, 2025 - 92 products"""
        return [
            {
                "name": "Avocados (Hard)",
                "department": "Fruits",
                "unit": "box",
                "price": 100.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 30
            },
            {
                "name": "Avocados (Semi-Ripe)",
                "department": "Fruits",
                "unit": "box",
                "price": 110.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 31
            },
            {
                "name": "Avocados (Soft)",
                "department": "Fruits",
                "unit": "box",
                "price": 120.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 29
            },
            {
                "name": "Bananas",
                "department": "Fruits",
                "unit": "kg",
                "price": 20.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 32
            },
            {
                "name": "Black Grapes",
                "department": "Fruits",
                "unit": "kg",
                "price": 60.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 34
            },
            {
                "name": "Blueberries",
                "department": "Fruits",
                "unit": "punnet",
                "price": 35.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 33
            },
            {
                "name": "Box Pineapple",
                "department": "Fruits",
                "unit": "kg",
                "price": 25.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 73
            },
            {
                "name": "Grapefruit",
                "department": "Fruits",
                "unit": "kg",
                "price": 28.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 36
            },
            {
                "name": "Green Grapes",
                "department": "Fruits",
                "unit": "punnet",
                "price": 45.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 94
            },
            {
                "name": "Lemons",
                "department": "Fruits",
                "unit": "kg",
                "price": 30.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 37
            },
            {
                "name": "Naartjies",
                "department": "Fruits",
                "unit": "box",
                "price": 45.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 91
            },
            {
                "name": "Oranges",
                "department": "Fruits",
                "unit": "kg",
                "price": 25.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 38
            },
            {
                "name": "Papaya",
                "department": "Fruits",
                "unit": "punnet",
                "price": 30.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 92
            },
            {
                "name": "Paw Paw",
                "department": "Fruits",
                "unit": "punnet",
                "price": 25.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 39
            },
            {
                "name": "Pineapple",
                "department": "Fruits",
                "unit": "each",
                "price": 25.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 40
            },
            {
                "name": "Red Grapes",
                "department": "Fruits",
                "unit": "punnet",
                "price": 45.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 35
            },
            {
                "name": "Strawberries",
                "department": "Fruits",
                "unit": "punnet",
                "price": 25.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 41
            },
            {
                "name": "Sweet Melon",
                "department": "Fruits",
                "unit": "each",
                "price": 40.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 42
            },
            {
                "name": "Water Melon",
                "department": "Fruits",
                "unit": "each",
                "price": 50.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 43
            },
            {
                "name": "Watermelon",
                "department": "Fruits",
                "unit": "each",
                "price": 50.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 93
            },
            {
                "name": "Baby Spinach",
                "department": "Herbs & Spices",
                "unit": "kg",
                "price": 45.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 44
            },
            {
                "name": "Basil",
                "department": "Herbs & Spices",
                "unit": "bunch",
                "price": 15.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 45
            },
            {
                "name": "Coriander",
                "department": "Herbs & Spices",
                "unit": "bunch",
                "price": 8.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 46
            },
            {
                "name": "Crushed Garlic",
                "department": "Herbs & Spices",
                "unit": "kg",
                "price": 90.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 56
            },
            {
                "name": "Dill",
                "department": "Herbs & Spices",
                "unit": "bunch",
                "price": 15.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 47
            },
            {
                "name": "Garlic Cloves",
                "department": "Herbs & Spices",
                "unit": "kg",
                "price": 80.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 55
            },
            {
                "name": "Ginger",
                "department": "Herbs & Spices",
                "unit": "kg",
                "price": 150.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 48
            },
            {
                "name": "Green Chili",
                "department": "Herbs & Spices",
                "unit": "kg",
                "price": 45.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 79
            },
            {
                "name": "Mint",
                "department": "Herbs & Spices",
                "unit": "bunch",
                "price": 10.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 49
            },
            {
                "name": "Packets Mint",
                "department": "Herbs & Spices",
                "unit": "bunch",
                "price": 25.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 75
            },
            {
                "name": "Packets Rosemary",
                "department": "Herbs & Spices",
                "unit": "kg",
                "price": 25.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 70
            },
            {
                "name": "Packets Thyme",
                "department": "Herbs & Spices",
                "unit": "kg",
                "price": 25.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 71
            },
            {
                "name": "Parsley",
                "department": "Herbs & Spices",
                "unit": "bunch",
                "price": 8.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 50
            },
            {
                "name": "Red Chili",
                "department": "Herbs & Spices",
                "unit": "kg",
                "price": 80.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 78
            },
            {
                "name": "Rocket",
                "department": "Herbs & Spices",
                "unit": "kg",
                "price": 120.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 51
            },
            {
                "name": "Rosemary",
                "department": "Herbs & Spices",
                "unit": "bunch",
                "price": 12.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 52
            },
            {
                "name": "Thyme",
                "department": "Herbs & Spices",
                "unit": "bunch",
                "price": 12.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 53
            },
            {
                "name": "Turmeric",
                "department": "Herbs & Spices",
                "unit": "kg",
                "price": 150.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 54
            },
            {
                "name": "Brown Mushrooms",
                "department": "Mushrooms",
                "unit": "kg",
                "price": 80.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 58
            },
            {
                "name": "Button Mushrooms",
                "department": "Mushrooms",
                "unit": "punnet",
                "price": 25.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 57
            },
            {
                "name": "Portabellini Mushrooms",
                "department": "Mushrooms",
                "unit": "kg",
                "price": 90.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 59
            },
            {
                "name": "Cherry Tomatoes",
                "department": "Specialty Items",
                "unit": "punnet",
                "price": 20.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 61
            },
            {
                "name": "Edible Flowers",
                "department": "Specialty Items",
                "unit": "packet",
                "price": 35.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 63
            },
            {
                "name": "Large Veggie Box",
                "department": "Specialty Items",
                "unit": "box",
                "price": 320.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 65
            },
            {
                "name": "Micro Herbs",
                "department": "Specialty Items",
                "unit": "packet",
                "price": 25.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 62
            },
            {
                "name": "Small Veggie Box",
                "department": "Specialty Items",
                "unit": "box",
                "price": 180.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 64
            },
            {
                "name": "Baby Corn",
                "department": "Vegetables",
                "unit": "punnet",
                "price": 20.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 60
            },
            {
                "name": "Baby Marrow",
                "department": "Vegetables",
                "unit": "kg",
                "price": 35.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 25
            },
            {
                "name": "Beetroot",
                "department": "Vegetables",
                "unit": "kg",
                "price": 25.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 1
            },
            {
                "name": "Box Cucumber",
                "department": "Vegetables",
                "unit": "kg",
                "price": 25.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 80
            },
            {
                "name": "Box Mixed Lettuce",
                "department": "Vegetables",
                "unit": "head",
                "price": 25.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 74
            },
            {
                "name": "Broccoli",
                "department": "Vegetables",
                "unit": "head",
                "price": 35.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 8
            },
            {
                "name": "Brussels Sprouts",
                "department": "Vegetables",
                "unit": "kg",
                "price": 50.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 28
            },
            {
                "name": "Butternut",
                "department": "Vegetables",
                "unit": "kg",
                "price": 22.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 2
            },
            {
                "name": "Carrots (1kg Packed)",
                "department": "Vegetables",
                "unit": "kg",
                "price": 22.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 4
            },
            {
                "name": "Carrots (Loose)",
                "department": "Vegetables",
                "unit": "kg",
                "price": 20.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 3
            },
            {
                "name": "Cauliflower",
                "department": "Vegetables",
                "unit": "head",
                "price": 30.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 7
            },
            {
                "name": "Celery",
                "department": "Vegetables",
                "unit": "kg",
                "price": 40.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 27
            },
            {
                "name": "Cocktail Tomatoes",
                "department": "Vegetables",
                "unit": "punnet",
                "price": 18.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 23
            },
            {
                "name": "Crispy Lettuce",
                "department": "Vegetables",
                "unit": "box",
                "price": 40.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 89
            },
            {
                "name": "Cucumber",
                "department": "Vegetables",
                "unit": "each",
                "price": 8.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 9
            },
            {
                "name": "Deveined Spinach",
                "department": "Vegetables",
                "unit": "kg",
                "price": 25.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 66
            },
            {
                "name": "Eggplant",
                "department": "Vegetables",
                "unit": "kg",
                "price": 45.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 87
            },
            {
                "name": "Green Beans",
                "department": "Vegetables",
                "unit": "kg",
                "price": 45.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 26
            },
            {
                "name": "Green Cabbage",
                "department": "Vegetables",
                "unit": "head",
                "price": 20.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 5
            },
            {
                "name": "Green Chillies",
                "department": "Vegetables",
                "unit": "kg",
                "price": 75.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 10
            },
            {
                "name": "Green Peppers",
                "department": "Vegetables",
                "unit": "kg",
                "price": 50.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 12
            },
            {
                "name": "Iceberg Lettuce",
                "department": "Vegetables",
                "unit": "head",
                "price": 25.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 88
            },
            {
                "name": "Lettuce Head",
                "department": "Vegetables",
                "unit": "head",
                "price": 15.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 16
            },
            {
                "name": "Mixed Lettuce",
                "department": "Vegetables",
                "unit": "kg",
                "price": 35.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 15
            },
            {
                "name": "Packets Dill",
                "department": "Vegetables",
                "unit": "kg",
                "price": 25.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 76
            },
            {
                "name": "Packets Rocket",
                "department": "Vegetables",
                "unit": "kg",
                "price": 25.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 69
            },
            {
                "name": "Patty Pan",
                "department": "Vegetables",
                "unit": "each",
                "price": 8.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 90
            },
            {
                "name": "Potatoes",
                "department": "Vegetables",
                "unit": "bag",
                "price": 45.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 20
            },
            {
                "name": "Punnets Strawberries",
                "department": "Vegetables",
                "unit": "kg",
                "price": 25.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 77
            },
            {
                "name": "Red Cabbage",
                "department": "Vegetables",
                "unit": "head",
                "price": 25.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 6
            },
            {
                "name": "Red Chillies",
                "department": "Vegetables",
                "unit": "kg",
                "price": 80.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 11
            },
            {
                "name": "Red Onions",
                "department": "Vegetables",
                "unit": "bag",
                "price": 35.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 17
            },
            {
                "name": "Red Peppers",
                "department": "Vegetables",
                "unit": "kg",
                "price": 55.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 13
            },
            {
                "name": "Spring Onions",
                "department": "Vegetables",
                "unit": "kg",
                "price": 25.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 19
            },
            {
                "name": "Sweet Corn",
                "department": "Vegetables",
                "unit": "punnet",
                "price": 15.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 24
            },
            {
                "name": "Sweet Potatoes",
                "department": "Vegetables",
                "unit": "kg",
                "price": 28.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 21
            },
            {
                "name": "Tomatoes",
                "department": "Vegetables",
                "unit": "kg",
                "price": 25.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 22
            },
            {
                "name": "White Onions",
                "department": "Vegetables",
                "unit": "bag",
                "price": 30.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 18
            },
            {
                "name": "Wild Rocket",
                "department": "Vegetables",
                "unit": "kg",
                "price": 25.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 98
            },
            {
                "name": "Yellow Peppers",
                "department": "Vegetables",
                "unit": "kg",
                "price": 60.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 14
            }
        ]
