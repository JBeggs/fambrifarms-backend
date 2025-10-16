"""
Fambri Staff Users Sync Command
===============================
Syncs only the Fambri staff users without touching products, customers, or suppliers.
Perfect for user management on production without full system reset.

Usage:
    python manage.py sync_fambri_users
    python manage.py sync_fambri_users --clear-users
    python manage.py sync_fambri_users --dry-run
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth import get_user_model
from accounts.models import FarmProfile

User = get_user_model()


class Command(BaseCommand):
    help = 'Sync Fambri staff users only (admin, karl, hazvinei, stock, info)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear-users',
            action='store_true',
            help='Clear all non-superuser users before syncing staff',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without actually creating it',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('👥 FAMBRI STAFF USERS SYNC'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        
        dry_run = options.get('dry_run', False)
        clear_users = options.get('clear_users', False)
        
        if dry_run:
            self.stdout.write(self.style.WARNING('🔍 DRY RUN MODE - No changes will be made'))
        
        # Clear users if requested
        if clear_users and not dry_run:
            self.clear_non_superuser_users()
        
        # Get Fambri staff users data
        staff_users = self.get_fambri_staff_users()
        
        self.stdout.write(f'\n📊 STAFF SYNC SUMMARY:')
        self.stdout.write(f'   Staff users to sync: {len(staff_users)}')
        
        # Sync staff users
        self.sync_staff_users(staff_users, dry_run)
        
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('🎉 FAMBRI STAFF SYNC COMPLETE!'))
        self.stdout.write(self.style.SUCCESS('=' * 60))

    def clear_non_superuser_users(self):
        """Clear all non-superuser users and their profiles"""
        self.stdout.write(self.style.WARNING('🗑️  CLEARING NON-SUPERUSER USERS...'))
        
        try:
            # Clear profiles first (foreign key dependencies)
            from accounts.models import RestaurantProfile, PrivateCustomerProfile
            
            restaurant_count = RestaurantProfile.objects.count()
            private_count = PrivateCustomerProfile.objects.count()
            farm_count = FarmProfile.objects.count()
            
            RestaurantProfile.objects.all().delete()
            PrivateCustomerProfile.objects.all().delete()
            FarmProfile.objects.all().delete()
            
            self.stdout.write(f'    🗑️  Cleared {restaurant_count} restaurant profiles')
            self.stdout.write(f'    🗑️  Cleared {private_count} private customer profiles')
            self.stdout.write(f'    🗑️  Cleared {farm_count} farm profiles')
            
            # Clear non-superuser users
            user_count = User.objects.filter(is_superuser=False).count()
            if user_count > 0:
                User.objects.filter(is_superuser=False).delete()
                self.stdout.write(f'    🗑️  Cleared {user_count} users (kept superusers)')
            else:
                self.stdout.write(f'    ✅ No non-superuser users to clear')
                
        except Exception as e:
            self.stdout.write(f'    ❌ Error clearing users: {str(e)[:50]}...')

    def get_fambri_staff_users(self):
        """Get Fambri staff users data"""
        self.stdout.write('📄 Defining Fambri staff users...')
        
        staff_users = [
            {
                'email': 'admin@fambrifarms.co.za',
                'first_name': 'Admin',
                'last_name': 'User',
                'user_type': 'staff',
                'phone': '+27 76 655 4873',
                'is_verified': True,
                'is_active': True,
                'is_staff': True,
                'is_superuser': True,
                'password': 'defaultpassword123'
            },
            {
                'email': 'system@fambrifarms.co.za',
                'first_name': 'System',
                'last_name': 'Admin',
                'user_type': 'admin',
                'phone': '+27 76 655 4873',
                'is_verified': True,
                'is_active': True,
                'is_staff': True,
                'is_superuser': True,
                'password': 'defaultpassword123'
            },
            {
                'email': 'karl@fambrifarms.co.za',
                'first_name': 'Karl',
                'last_name': 'Farm Manager',
                'user_type': 'farm_manager',
                'phone': '+27 76 655 4873',
                'is_verified': True,
                'is_active': True,
                'is_staff': True,
                'is_superuser': False,
                'password': 'defaultpassword123'
            },
            {
                'email': 'hazvinei@fambrifarms.co.za',
                'first_name': 'Hazvinei',
                'last_name': 'Stock Controller',
                'user_type': 'stock_taker',
                'phone': '+27 61 674 9368',
                'is_verified': True,
                'is_active': True,
                'is_staff': True,
                'is_superuser': False,
                'password': 'defaultpassword123'
            },
            {
                'email': 'stock@fambrifarms.co.za',
                'first_name': 'SHALLOME',
                'last_name': 'Stock Operations',
                'user_type': 'stock_manager',
                'phone': '+27 61 674 9368',
                'is_verified': True,
                'is_active': True,
                'is_staff': True,
                'is_superuser': False,
                'password': 'defaultpassword123'
            },
            {
                'email': 'info@fambrifarms.co.za',
                'first_name': 'Fambri Farms',
                'last_name': 'General Info',
                'user_type': 'info_desk',
                'phone': '+27 84 504 8586',
                'is_verified': True,
                'is_active': True,
                'is_staff': True,
                'is_superuser': False,
                'password': 'defaultpassword123'
            },
        ]
        
        self.stdout.write(f'    ✅ Defined {len(staff_users)} staff users:')
        for user in staff_users:
            self.stdout.write(f'       - {user["email"]} ({user["user_type"]}) - {user["first_name"]} {user["last_name"]}')
        
        return staff_users

    def sync_staff_users(self, staff_users, dry_run):
        """Sync staff users with farm profiles"""
        self.stdout.write('👥 Syncing staff users...')
        
        if dry_run:
            self.stdout.write(f'    Would create/update {len(staff_users)} staff users:')
            for user in staff_users:
                self.stdout.write(f'    - {user["email"]} ({user["user_type"]}) - {user["first_name"]} {user["last_name"]}')
            return
        
        created_count = 0
        updated_count = 0
        profile_count = 0
        error_count = 0
        
        with transaction.atomic():
            for user_data in staff_users:
                try:
                    # Create or update user
                    user, user_created = User.objects.get_or_create(
                        email=user_data['email'],
                        defaults={
                            'first_name': user_data.get('first_name', ''),
                            'last_name': user_data.get('last_name', ''),
                            'user_type': user_data.get('user_type', 'staff'),
                            'phone': user_data.get('phone', ''),
                            'is_active': user_data.get('is_active', True),
                            'is_staff': user_data.get('is_staff', True),
                            'is_superuser': user_data.get('is_superuser', False),
                            'is_verified': user_data.get('is_verified', True),
                        }
                    )
                    
                    if user_created:
                        # Set password for new users
                        password = user_data.get('password', 'defaultpassword123')
                        user.set_password(password)
                        user.save()
                        created_count += 1
                        self.stdout.write(f'    ✅ Created: {user_data["email"]} - {user_data["first_name"]} {user_data["last_name"]}')
                    else:
                        # Update existing user
                        user.first_name = user_data.get('first_name', user.first_name)
                        user.last_name = user_data.get('last_name', user.last_name)
                        user.user_type = user_data.get('user_type', user.user_type)
                        user.phone = user_data.get('phone', user.phone)
                        user.is_active = user_data.get('is_active', user.is_active)
                        user.is_staff = user_data.get('is_staff', user.is_staff)
                        user.is_verified = user_data.get('is_verified', user.is_verified)
                        user.save()
                        updated_count += 1
                        self.stdout.write(f'    🔄 Updated: {user_data["email"]} - {user_data["first_name"]} {user_data["last_name"]}')
                    
                    # Create farm profile for staff users
                    if user_data.get('user_type') in ['staff', 'farm_manager', 'stock_taker', 'stock_manager', 'info_desk', 'admin']:
                        # Set access level and position based on user type
                        if user_data.get('is_superuser'):
                            access_level = 'admin'
                            position = 'Administrator'
                        elif user_data.get('user_type') == 'farm_manager':
                            access_level = 'manager'
                            position = 'Farm Manager'
                        elif user_data.get('user_type') == 'stock_taker':
                            access_level = 'staff'
                            position = 'Stock Controller'
                        elif user_data.get('user_type') == 'stock_manager':
                            access_level = 'manager'
                            position = 'Stock Operations Manager'
                        elif user_data.get('user_type') == 'info_desk':
                            access_level = 'staff'
                            position = 'Information Desk'
                        else:
                            access_level = 'manager'
                            position = 'Manager'
                        
                        farm_profile, profile_created = FarmProfile.objects.get_or_create(
                            user=user,
                            defaults={
                                'employee_id': f'{user_data.get("user_type", "STAFF").upper()}-{user.id:03d}',
                                'department': 'Operations',
                                'position': position,
                                'whatsapp_number': user_data.get('phone', ''),
                                'access_level': access_level,
                                'notes': f'Fambri staff {user_data.get("user_type", "staff")} profile',
                                'can_manage_inventory': user_data.get('user_type') not in ['info_desk'],
                                'can_approve_orders': user_data.get('user_type') not in ['stock_taker', 'info_desk'],
                                'can_manage_customers': user_data.get('user_type') not in ['stock_taker'],
                                'can_view_reports': True,
                            }
                        )
                        
                        if profile_created:
                            profile_count += 1
                            self.stdout.write(f'        📋 Created farm profile: {position}')
                        else:
                            # Update existing profile
                            farm_profile.position = position
                            farm_profile.access_level = access_level
                            farm_profile.whatsapp_number = user_data.get('phone', farm_profile.whatsapp_number)
                            farm_profile.save()
                            self.stdout.write(f'        📋 Updated farm profile: {position}')
                        
                except Exception as e:
                    error_count += 1
                    self.stdout.write(f'    ❌ Error syncing {user_data["email"]}: {e}')
        
        self.stdout.write(self.style.SUCCESS(f'\n📊 SYNC RESULTS:'))
        self.stdout.write(f'   ✅ Created: {created_count} users')
        self.stdout.write(f'   🔄 Updated: {updated_count} users')
        self.stdout.write(f'   📋 Farm profiles: {profile_count} created')
        self.stdout.write(f'   ❌ Errors: {error_count} users')
        self.stdout.write(f'   📱 Total: {created_count + updated_count} users synced')
        
        if error_count == 0:
            self.stdout.write(self.style.SUCCESS('🎉 All Fambri staff synced successfully!'))
