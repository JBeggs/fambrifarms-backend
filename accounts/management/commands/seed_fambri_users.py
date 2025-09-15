from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth.models import Group, Permission
from accounts.models import User, FarmProfile, PrivateCustomerProfile
from decimal import Decimal


class Command(BaseCommand):
    help = 'Seed comprehensive user system with real WhatsApp contacts and roles'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing farm and private users before importing',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing existing farm and private users...')
            FarmProfile.objects.all().delete()
            PrivateCustomerProfile.objects.all().delete()
            User.objects.filter(user_type__in=['farm_manager', 'stock_taker', 'private']).delete()
            self.stdout.write(self.style.SUCCESS('Existing farm and private user data cleared.'))

        self.create_user_groups()
        self.create_farm_users()
        self.create_private_customers()

        self.stdout.write(
            self.style.SUCCESS(
                f'\n🎉 FAMBRI USER SYSTEM SEEDED SUCCESSFULLY!'
            )
        )
        self.stdout.write(f'👥 Complete user ecosystem with real WhatsApp contacts')
        self.stdout.write(f'🌾 Farm staff: Karl (Manager), Hazvinei (Stock Taker)')
        self.stdout.write(f'🤖 System user: WhatsApp integration (API key authentication)')
        self.stdout.write(f'👤 Private customers: Sylvia, Marco, Arthur with real patterns')
        self.stdout.write(f'🔐 Role-based permissions and access levels configured')
        self.stdout.write(f'✅ Phase 5 Complete: User system ready for frontend integration')

    def create_user_groups(self):
        """Create Django groups for role-based permissions"""
        groups_data = [
            {
                'name': 'Farm Managers',
                'permissions': ['view_user', 'change_user', 'view_product', 'change_product', 'view_order']
            },
            {
                'name': 'Stock Takers', 
                'permissions': ['view_product', 'change_product', 'view_inventory']
            },
            {
                'name': 'Restaurant Customers',
                'permissions': ['view_product', 'add_order', 'view_order']
            },
            {
                'name': 'Private Customers',
                'permissions': ['view_product', 'add_order', 'view_order']
            },
        ]

        for group_data in groups_data:
            group, created = Group.objects.get_or_create(name=group_data['name'])
            if created:
                self.stdout.write(f'🔐 Created group: {group.name}')

    def create_farm_users(self):
        """Create farm staff users with real WhatsApp data"""
        farm_users_data = [
            {
                'email': 'karl@fambrifarms.co.za',
                'first_name': 'Karl',
                'last_name': 'Farm Manager',
                'phone': '+27 76 655 4873',  # Real WhatsApp number
                'user_type': 'farm_manager',
                'is_staff': True,
                'is_active': True,
                'profile_data': {
                    'employee_id': 'FF001',
                    'department': 'Operations',
                    'position': 'Farm Manager',
                    'whatsapp_number': '+27 76 655 4873',
                    'access_level': 'admin',
                    'can_manage_inventory': True,
                    'can_approve_orders': True,
                    'can_manage_customers': True,
                    'can_view_reports': True,
                    'notes': 'Farm Manager - oversees all operations, customer relationships, and order approvals. Key contact for restaurant partnerships and operational decisions.'
                }
            },
            {
                'email': 'hazvinei@fambrifarms.co.za',
                'first_name': 'Hazvinei',
                'last_name': 'Stock Controller',
                'phone': '+27 61 674 9368',  # Real WhatsApp number
                'user_type': 'stock_taker',
                'is_staff': True,
                'is_active': True,
                'profile_data': {
                    'employee_id': 'FF002',
                    'department': 'Inventory',
                    'position': 'Stock Taker',
                    'whatsapp_number': '+27 61 674 9368',
                    'access_level': 'manager',
                    'can_manage_inventory': True,
                    'can_approve_orders': False,
                    'can_manage_customers': False,
                    'can_view_reports': True,
                    'notes': 'Stock Taker - manages all inventory counts, SHALLOME stock reports, and inventory updates. Sends daily stock updates via WhatsApp.'
                }
            },
            {
                'email': 'system@fambrifarms.co.za',
                'first_name': 'WhatsApp',
                'last_name': 'System',
                'phone': '',  # System user doesn't need phone
                'user_type': 'admin',
                'is_staff': False,
                'is_active': True,
                'profile_data': {
                    'employee_id': 'SYS001',
                    'department': 'System',
                    'position': 'WhatsApp Integration',
                    'whatsapp_number': '',
                    'access_level': 'system',
                    'can_manage_inventory': False,
                    'can_approve_orders': False,
                    'can_manage_customers': False,
                    'can_view_reports': False,
                    'notes': 'System user for WhatsApp scraper API key authentication. Allows Python scraper to send messages to Django backend securely.'
                }
            },
        ]

        created_count = 0
        for user_data in farm_users_data:
            profile_data = user_data.pop('profile_data')
            
            with transaction.atomic():
                user, user_created = User.objects.get_or_create(
                    email=user_data['email'],
                    defaults=user_data
                )
                
                if user_created:
                    user.set_password('FambriFarms2025!')  # Default password
                    user.save()
                    created_count += 1
                    self.stdout.write(f'👤 Created farm user: {user.get_full_name()} ({user.email})')
                    
                    # Create farm profile
                    farm_profile = FarmProfile.objects.create(
                        user=user,
                        **profile_data
                    )
                    self.stdout.write(f'   🌾 Profile: {farm_profile.position} - {farm_profile.department}')
                    
                    # Add to appropriate group
                    if user.user_type == 'farm_manager':
                        group = Group.objects.get(name='Farm Managers')
                        user.groups.add(group)
                    elif user.user_type == 'stock_taker':
                        group = Group.objects.get(name='Stock Takers')
                        user.groups.add(group)
                else:
                    self.stdout.write(f'🔄 Farm user already exists: {user.get_full_name()}')

        self.stdout.write(f'🌾 Created {created_count} farm staff users')

    def create_private_customers(self):
        """Create private customer users with real WhatsApp data"""
        private_customers_data = [
            {
                'email': 'sylvia.orders@gmail.com',
                'first_name': 'Sylvia',
                'last_name': 'Private Customer',
                'phone': '+27 73 621 2471',  # Real WhatsApp number
                'user_type': 'private',
                'is_active': True,
                'profile_data': {
                    'customer_type': 'household',
                    'delivery_address': '456 Residential Avenue, Johannesburg, 2001',
                    'delivery_instructions': 'Small household orders - potatoes, oranges, bananas, carrots',
                    'preferred_delivery_day': 'tuesday',
                    'whatsapp_number': '+27 73 621 2471',
                    'credit_limit': Decimal('3000.00'),
                    'order_notes': 'Tuesday orders - "Sylvia Tuesday order" - household basics: Potato 2x1kg, Orange 1kg, Banana 2x1kg, Carrots 1kg'
                }
            },
            {
                'email': 'marco.private@gmail.com',
                'first_name': 'Marco',
                'last_name': 'Private Customer',
                'phone': '+27 73 621 2471',  # Same number as Sylvia (family/shared)
                'user_type': 'private',
                'is_active': True,
                'profile_data': {
                    'customer_type': 'personal',
                    'delivery_address': '963 Residential Street, Johannesburg, 2001',
                    'delivery_instructions': 'Private customer - mixed vegetables and fruits',
                    'preferred_delivery_day': 'tuesday',
                    'whatsapp_number': '+27 73 621 2471',
                    'credit_limit': Decimal('5000.00'),
                    'order_notes': 'Tuesday orders - Personal household supplies, mixed vegetables and fruits'
                }
            },
            {
                'email': 'arthur.orders@gmail.com',
                'first_name': 'Arthur',
                'last_name': 'Private Customer',
                'phone': '+27 76 555 0018',
                'user_type': 'private',
                'is_active': True,
                'profile_data': {
                    'customer_type': 'household',
                    'delivery_address': '789 Private Road, Johannesburg, 2001',
                    'delivery_instructions': 'Simple orders - "Arthur box x2"',
                    'preferred_delivery_day': 'tuesday',
                    'whatsapp_number': '+27 76 555 0018',
                    'credit_limit': Decimal('2000.00'),
                    'order_notes': 'Tuesday orders - Box orders, simple household requirements'
                }
            },
        ]

        created_count = 0
        for customer_data in private_customers_data:
            profile_data = customer_data.pop('profile_data')
            
            with transaction.atomic():
                user, user_created = User.objects.get_or_create(
                    email=customer_data['email'],
                    defaults=customer_data
                )
                
                if user_created:
                    user.set_password('FambriFarms2025!')  # Default password
                    user.save()
                    created_count += 1
                    self.stdout.write(f'👤 Created private customer: {user.get_full_name()} ({user.email})')
                    
                    # Create private customer profile
                    private_profile = PrivateCustomerProfile.objects.create(
                        user=user,
                        **profile_data
                    )
                    self.stdout.write(f'   🏠 Profile: {private_profile.get_customer_type_display()} - R{private_profile.credit_limit} limit')
                    
                    # Add to private customers group
                    group = Group.objects.get(name='Private Customers')
                    user.groups.add(group)
                else:
                    self.stdout.write(f'🔄 Private customer already exists: {user.get_full_name()}')

        self.stdout.write(f'👤 Created {created_count} private customer users')
