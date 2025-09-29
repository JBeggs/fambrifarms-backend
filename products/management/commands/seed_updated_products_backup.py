from django.core.management.base import BaseCommand
from django.db import transaction
from products.models import Product, Department
from decimal import Decimal


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
        products_data = [
            {
                "name": "Artichokes",
                "department": "Vegetables",
                "unit": "kg",
                "price": 45.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 104
            },
            {
                "name": "Aubergine",
                "department": "Vegetables",
                "unit": "kg",
                "price": 55.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 105
            },
            {
                "name": "Aubergine box",
                "department": "Vegetables",
                "unit": "box",
                "price": 120.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 106
            },
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
                "name": "Baby Potatoes",
                "department": "Vegetables",
                "unit": "kg",
                "price": 30.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 99
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
                "name": "Bananas",
                "department": "Fruits",
                "unit": "kg",
                "price": 20.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 32
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
                "name": "Beetroot",
                "department": "Vegetables",
                "unit": "kg",
                "price": 25.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 1
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
                "name": "Box Mixed Lettuce",
                "department": "Vegetables",
                "unit": "head",
                "price": 25.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 74
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
                "name": "Broccoli",
                "department": "Vegetables",
                "unit": "head",
                "price": 35.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 8
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
                "name": "Button Mushrooms",
                "department": "Mushrooms",
                "unit": "punnet",
                "price": 25.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 57
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
                "name": "Cherry Tomatoes",
                "department": "Specialty Items",
                "unit": "punnet",
                "price": 20.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 61
            },
            {
                "name": "Chives",
                "department": "Herbs & Spices",
                "unit": "piece",
                "price": 35.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 100
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
                "name": "Coriander",
                "department": "Herbs & Spices",
                "unit": "bunch",
                "price": 8.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 46
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
                "name": "Crushed Garlic",
                "department": "Herbs & Spices",
                "unit": "kg",
                "price": 90.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 56
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
                "name": "Cucumber Box",
                "department": "Vegetables",
                "unit": "box",
                "price": 25.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 80
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
                "name": "Dill",
                "department": "Herbs & Spices",
                "unit": "bunch",
                "price": 15.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 47
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
                "name": "Eggplant",
                "department": "Vegetables",
                "unit": "kg",
                "price": 45.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 87
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
                "name": "Grapefruit",
                "department": "Fruits",
                "unit": "kg",
                "price": 28.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 36
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
                "name": "Green Grapes",
                "department": "Fruits",
                "unit": "punnet",
                "price": 45.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 94
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
                "name": "Large Veggie Box",
                "department": "Specialty Items",
                "unit": "box",
                "price": 320.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 65
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
                "name": "Lemons box",
                "department": "Fruits",
                "unit": "box",
                "price": 34.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 107
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
                "name": "Micro Herbs",
                "department": "Specialty Items",
                "unit": "packet",
                "price": 25.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 62
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
                "name": "Mixed Lettuce",
                "department": "Vegetables",
                "unit": "kg",
                "price": 35.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 15
            },
            {
                "name": "Mixed Peppers",
                "department": "Vegetables",
                "unit": "kg",
                "price": 50.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 102
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
                "name": "Packets Dill",
                "department": "Vegetables",
                "unit": "kg",
                "price": 25.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 76
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
                "name": "Packets Rocket",
                "department": "Vegetables",
                "unit": "kg",
                "price": 25.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 69
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
                "name": "Papaya",
                "department": "Fruits",
                "unit": "punnet",
                "price": 30.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 92
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
                "name": "Patty Pan",
                "department": "Vegetables",
                "unit": "each",
                "price": 8.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 90
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
                "unit": "piece",
                "price": 25.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 40
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
                "name": "Red Apples",
                "department": "Fruits",
                "unit": "kg",
                "price": 35.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 103
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
                "name": "Red Grapes",
                "department": "Fruits",
                "unit": "punnet",
                "price": 45.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 35
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
                "name": "Small Veggie Box",
                "department": "Specialty Items",
                "unit": "box",
                "price": 180.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 64
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
                "name": "Strawberries",
                "department": "Fruits",
                "unit": "punnet",
                "price": 25.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 41
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
                "name": "Sweet Melon",
                "department": "Fruits",
                "unit": "piece",
                "price": 40.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 42
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
                "name": "Thyme",
                "department": "Herbs & Spices",
                "unit": "bunch",
                "price": 12.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 53
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
                "name": "Turmeric",
                "department": "Herbs & Spices",
                "unit": "kg",
                "price": 150.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 54
            },
            {
                "name": "Water Melon",
                "department": "Fruits",
                "unit": "piece",
                "price": 50.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 43
            },
            {
                "name": "Watermelon",
                "department": "Fruits",
                "unit": "piece",
                "price": 50.0,
                "stock_level": 0.0,
                "is_active": True,
                "id": 93
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
            },
        ]
        
        created_count = 0
        for product_data in products_data:
            product, created = Product.objects.update_or_create(
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

        self.stdout.write(f'🌱 Created/Updated {len(products_data)} products from updated backup')
        self.stdout.write(f'📊 Products organized into {Department.objects.count()} departments')
        self.stdout.write(f'💰 Total products in database: {Product.objects.count()}')
        self.stdout.write(f'📦 Updated backup includes all recent additions and changes')
        self.stdout.write(f'✨ New products include: Artichokes, Aubergine box, Lemons box, Mixed Peppers, Red Apples, Baby Potatoes, Chives, Wild Rocket')
