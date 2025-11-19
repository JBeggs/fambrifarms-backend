from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth import get_user_model
from accounts.models import PrivateCustomerProfile
from decimal import Decimal

User = get_user_model()


class Command(BaseCommand):
    help = 'Add a private customer to the database (generic command for adding private customers)'

    def add_arguments(self, parser):
        parser.add_argument(
            'name',
            type=str,
            help='Name of the private customer (e.g., "Rusty Feather")',
        )
        parser.add_argument(
            '--email',
            type=str,
            help='Email address (defaults to name-based email if not provided)',
        )
        parser.add_argument(
            '--phone',
            type=str,
            default='',
            help='Phone number (optional)',
        )
        parser.add_argument(
            '--whatsapp',
            type=str,
            default='',
            help='WhatsApp number (optional)',
        )
        parser.add_argument(
            '--address',
            type=str,
            default='Address to be provided',
            help='Delivery address (defaults to placeholder)',
        )
        parser.add_argument(
            '--customer-type',
            type=str,
            choices=['household', 'small_business', 'personal'],
            default='household',
            help='Customer type (default: household)',
        )
        parser.add_argument(
            '--delivery-day',
            type=str,
            choices=['tuesday', 'thursday', 'any'],
            default='tuesday',
            help='Preferred delivery day (default: tuesday)',
        )
        parser.add_argument(
            '--credit-limit',
            type=float,
            default=1000.00,
            help='Credit limit (default: 1000.00)',
        )
        parser.add_argument(
            '--delivery-instructions',
            type=str,
            default='',
            help='Delivery instructions (optional)',
        )
        parser.add_argument(
            '--order-notes',
            type=str,
            default='',
            help='Order notes/patterns (optional)',
        )

    def handle(self, *args, **options):
        name = options['name']
        email = options.get('email')
        phone = options.get('phone', '')
        whatsapp = options.get('whatsapp', '')
        address = options.get('address', 'Address to be provided')
        customer_type = options.get('customer_type', 'household')
        delivery_day = options.get('delivery_day', 'tuesday')
        credit_limit = Decimal(str(options.get('credit_limit', 1000.00)))
        delivery_instructions = options.get('delivery_instructions', '')
        order_notes = options.get('order_notes', '')

        # Generate email from name if not provided
        if not email:
            # Convert name to email format: "Rusty Feather" -> "rusty.feather@fambri.co.za"
            email_name = name.lower().replace(' ', '.').replace("'", '').replace('-', '.')
            email = f'{email_name}@fambri.co.za'

        # Split name into first and last name
        name_parts = name.strip().split()
        first_name = name_parts[0] if name_parts else name
        last_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else ''

        with transaction.atomic():
            # Check if customer already exists
            existing_user = User.objects.filter(email=email).first()
            if existing_user:
                if hasattr(existing_user, 'privatecustomerprofile'):
                    self.stdout.write(
                        self.style.WARNING(
                            f'Private customer with email {email} already exists: {existing_user.privatecustomerprofile.user.get_full_name()}'
                        )
                    )
                    return
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f'User with email {email} exists but has no private customer profile. Creating profile...'
                        )
                    )
                    user = existing_user
                    # Update user type if needed
                    if user.user_type != 'private':
                        user.user_type = 'private'
                        user.save()
            else:
                # Create user
                user = User.objects.create_user(
                    email=email,
                    password='changeme123',  # Default password - should be changed
                    first_name=first_name,
                    last_name=last_name,
                    phone=phone if phone else '',
                    user_type='private',
                    is_active=True,
                )
                self.stdout.write(self.style.SUCCESS(f'Created user: {email}'))

            # Create or update private customer profile
            profile, created = PrivateCustomerProfile.objects.get_or_create(
                user=user,
                defaults={
                    'customer_type': customer_type,
                    'delivery_address': address,
                    'delivery_instructions': delivery_instructions,
                    'preferred_delivery_day': delivery_day,
                    'whatsapp_number': whatsapp if whatsapp else phone,
                    'credit_limit': credit_limit,
                    'order_notes': order_notes,
                }
            )

            if created:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✅ Successfully created private customer: {name}\n'
                        f'   Email: {email}\n'
                        f'   Phone: {phone if phone else "Not provided"}\n'
                        f'   WhatsApp: {whatsapp if whatsapp else phone if phone else "Not provided"}\n'
                        f'   Address: {address}\n'
                        f'   Customer Type: {customer_type}\n'
                        f'   Preferred Delivery Day: {delivery_day}\n'
                        f'   Credit Limit: R{credit_limit}'
                    )
                )
            else:
                # Update existing profile
                profile.customer_type = customer_type
                profile.delivery_address = address
                profile.delivery_instructions = delivery_instructions
                profile.preferred_delivery_day = delivery_day
                profile.whatsapp_number = whatsapp if whatsapp else phone
                profile.credit_limit = credit_limit
                profile.order_notes = order_notes
                profile.save()
                
                # Update user name if changed
                user.first_name = first_name
                user.last_name = last_name
                if phone:
                    user.phone = phone
                user.save()
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✅ Updated private customer: {name}\n'
                        f'   Email: {email}\n'
                        f'   Phone: {phone if phone else "Not provided"}\n'
                        f'   WhatsApp: {whatsapp if whatsapp else phone if phone else "Not provided"}\n'
                        f'   Address: {address}\n'
                        f'   Customer Type: {customer_type}\n'
                        f'   Preferred Delivery Day: {delivery_day}\n'
                        f'   Credit Limit: R{credit_limit}'
                    )
                )

