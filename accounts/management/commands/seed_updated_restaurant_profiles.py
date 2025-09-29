from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth.models import Group
from accounts.models import User, RestaurantProfile
from inventory.models import PricingRule
from decimal import Decimal
import json
import os


class Command(BaseCommand):
    help = 'Seed restaurant profiles with updated data from current database state'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing restaurant profiles before importing',
        )
        parser.add_argument(
            '--seeding-dir',
            type=str,
            default='updated_seeding',
            help='Directory containing updated seeding files',
        )

    def handle(self, *args, **options):
        seeding_dir = options['seeding_dir']
        
        if options['clear']:
            self.stdout.write('Clearing existing restaurant profiles...')
            RestaurantProfile.objects.all().delete()
            User.objects.filter(user_type='restaurant').delete()
            self.stdout.write(self.style.SUCCESS('Existing restaurant data cleared.'))

        self.create_restaurant_profiles_from_data(seeding_dir)

        self.stdout.write(
            self.style.SUCCESS(
                f'\n🎉 UPDATED RESTAURANT PROFILES SEEDED SUCCESSFULLY!'
            )
        )

    def load_seeding_data(self, seeding_dir):
        """Load seeding data from JSON file"""
        file_path = os.path.join(seeding_dir, 'users_and_profiles.json')
        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f'Seeding file not found: {file_path}'))
            return None
        
        with open(file_path, 'r') as f:
            return json.load(f)

    def create_restaurant_profiles_from_data(self, seeding_dir):
        """Create restaurant profiles from updated seeding data"""
        data = self.load_seeding_data(seeding_dir)
        if not data:
            return
        
        users_data = data.get('users', [])
        restaurant_profiles_data = data.get('restaurant_profiles', [])
        
        self.stdout.write(f'Creating {len(users_data)} users and {len(restaurant_profiles_data)} restaurant profiles...')
        
        with transaction.atomic():
            # Create users first
            for user_data in users_data:
                if user_data['user_type'] == 'restaurant':
                    user, created = User.objects.get_or_create(
                        email=user_data['email'],
                        defaults={
                            'first_name': user_data.get('first_name', ''),
                            'last_name': user_data.get('last_name', ''),
                            'user_type': user_data['user_type'],
                            'phone': user_data.get('phone', ''),
                            'is_verified': user_data.get('is_verified', False),
                            'is_active': user_data.get('is_active', True),
                            'is_staff': user_data.get('is_staff', False),
                            'is_superuser': user_data.get('is_superuser', False),
                            'roles': user_data.get('roles', []),
                            'restaurant_roles': user_data.get('restaurant_roles', []),
                        }
                    )
                    if created:
                        # Set a default password for new users
                        user.set_password('defaultpassword123')
                        user.save()
                        self.stdout.write(f'  ✅ Created user: {user.email}')
            
            # Create restaurant profiles
            for profile_data in restaurant_profiles_data:
                try:
                    user = User.objects.get(email=profile_data['user_email'])
                    
                    # Get preferred pricing rule if specified
                    preferred_rule = None
                    if profile_data.get('preferred_pricing_rule'):
                        try:
                            preferred_rule = PricingRule.objects.get(name=profile_data['preferred_pricing_rule'])
                        except PricingRule.DoesNotExist:
                            self.stdout.write(self.style.WARNING(f'  Pricing rule not found: {profile_data["preferred_pricing_rule"]}'))
                    
                    profile, created = RestaurantProfile.objects.get_or_create(
                        user=user,
                        defaults={
                            'business_name': profile_data['business_name'],
                            'branch_name': profile_data.get('branch_name', ''),
                            'business_registration': profile_data.get('business_registration', ''),
                            'address': profile_data.get('address', ''),
                            'city': profile_data.get('city', ''),
                            'postal_code': profile_data.get('postal_code', ''),
                            'payment_terms': profile_data.get('payment_terms', 'Net 30'),
                            'is_private_customer': profile_data.get('is_private_customer', False),
                            'delivery_notes': profile_data.get('delivery_notes', ''),
                            'order_pattern': profile_data.get('order_pattern', ''),
                            'preferred_pricing_rule': preferred_rule,
                        }
                    )
                    if created:
                        self.stdout.write(f'  ✅ Created restaurant profile: {profile.business_name}')
                    else:
                        self.stdout.write(f'  ℹ️  Restaurant profile already exists: {profile.business_name}')
                        
                except User.DoesNotExist:
                    self.stdout.write(self.style.ERROR(f'  User not found: {profile_data["user_email"]}'))

        self.stdout.write(self.style.SUCCESS(f'✅ Restaurant profiles seeding completed'))
