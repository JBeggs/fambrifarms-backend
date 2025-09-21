from django.core.management.base import BaseCommand
from django.db import transaction
from settings.models import (
    SystemSetting, CustomerSegment, OrderStatus, 
    StockAdjustmentType, BusinessConfiguration
)


class Command(BaseCommand):
    help = 'Seed system settings for complete database integration'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing settings before seeding',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing existing settings...')
            SystemSetting.objects.all().delete()
            CustomerSegment.objects.all().delete()
            OrderStatus.objects.all().delete()
            StockAdjustmentType.objects.all().delete()
            BusinessConfiguration.objects.all().delete()

        with transaction.atomic():
            self.create_customer_segments()
            self.create_order_statuses()
            self.create_adjustment_types()
            self.create_business_configuration()
            self.create_system_settings()

        self.stdout.write(
            self.style.SUCCESS('Successfully seeded system settings for 100% database integration!')
        )

    def create_customer_segments(self):
        """Create customer segment definitions"""
        segments = [
            {
                'name': 'premium',
                'description': 'Premium customers with highest priority and best pricing',
                'default_markup': 1.15,
                'credit_limit_multiplier': 2.0,
                'payment_terms_days': 60,
            },
            {
                'name': 'standard',
                'description': 'Standard business customers',
                'default_markup': 1.25,
                'credit_limit_multiplier': 1.5,
                'payment_terms_days': 30,
            },
            {
                'name': 'budget',
                'description': 'Price-sensitive customers with basic service',
                'default_markup': 1.35,
                'credit_limit_multiplier': 1.0,
                'payment_terms_days': 14,
            },
            {
                'name': 'wholesale',
                'description': 'Bulk buyers with volume discounts',
                'default_markup': 1.10,
                'credit_limit_multiplier': 3.0,
                'payment_terms_days': 45,
            },
        ]

        for segment_data in segments:
            segment, created = CustomerSegment.objects.get_or_create(
                name=segment_data['name'],
                defaults=segment_data
            )
            if created:
                self.stdout.write(f'✅ Created customer segment: {segment.name}')

    def create_order_statuses(self):
        """Create order status definitions"""
        statuses = [
            {
                'name': 'pending',
                'display_name': 'Pending',
                'description': 'Order received, awaiting processing',
                'color': '#ffc107',
                'sort_order': 1,
            },
            {
                'name': 'confirmed',
                'display_name': 'Confirmed',
                'description': 'Order confirmed and being prepared',
                'color': '#17a2b8',
                'sort_order': 2,
            },
            {
                'name': 'preparing',
                'display_name': 'Preparing',
                'description': 'Order being prepared for delivery',
                'color': '#007bff',
                'sort_order': 3,
            },
            {
                'name': 'ready',
                'display_name': 'Ready for Delivery',
                'description': 'Order ready for pickup/delivery',
                'color': '#fd7e14',
                'sort_order': 4,
            },
            {
                'name': 'delivered',
                'display_name': 'Delivered',
                'description': 'Order successfully delivered',
                'color': '#28a745',
                'is_final': True,
                'sort_order': 5,
            },
            {
                'name': 'cancelled',
                'display_name': 'Cancelled',
                'description': 'Order cancelled by customer or system',
                'color': '#dc3545',
                'is_final': True,
                'sort_order': 6,
            },
        ]

        for status_data in statuses:
            status, created = OrderStatus.objects.get_or_create(
                name=status_data['name'],
                defaults=status_data
            )
            if created:
                self.stdout.write(f'✅ Created order status: {status.display_name}')

    def create_adjustment_types(self):
        """Create stock adjustment type definitions"""
        types = [
            {
                'name': 'increase',
                'display_name': 'Stock Increase',
                'description': 'Increase stock level (new deliveries, corrections)',
                'affects_cost': True,
                'requires_reason': True,
            },
            {
                'name': 'decrease',
                'display_name': 'Stock Decrease',
                'description': 'Decrease stock level (sales, usage)',
                'affects_cost': False,
                'requires_reason': True,
            },
            {
                'name': 'correction',
                'display_name': 'Stock Correction',
                'description': 'Correct stock count discrepancies',
                'affects_cost': False,
                'requires_reason': True,
            },
            {
                'name': 'damage',
                'display_name': 'Damaged Goods',
                'description': 'Remove damaged or spoiled items',
                'affects_cost': False,
                'requires_reason': True,
            },
            {
                'name': 'theft',
                'display_name': 'Theft/Loss',
                'description': 'Items lost due to theft or unknown causes',
                'affects_cost': False,
                'requires_reason': True,
            },
            {
                'name': 'expired',
                'display_name': 'Expired Items',
                'description': 'Remove expired or past-date items',
                'affects_cost': False,
                'requires_reason': False,
            },
            {
                'name': 'returned',
                'display_name': 'Customer Returns',
                'description': 'Items returned by customers',
                'affects_cost': False,
                'requires_reason': True,
            },
        ]

        for type_data in types:
            adj_type, created = StockAdjustmentType.objects.get_or_create(
                name=type_data['name'],
                defaults=type_data
            )
            if created:
                self.stdout.write(f'✅ Created adjustment type: {adj_type.display_name}')

    def create_business_configuration(self):
        """Create business configuration settings"""
        configs = [
            {
                'name': 'default_vat_rate',
                'display_name': 'Default VAT Rate',
                'value_type': 'decimal',
                'decimal_value': 0.15,
                'description': 'Default VAT rate for pricing calculations',
                'category': 'pricing',
            },
            {
                'name': 'default_base_markup',
                'display_name': 'Default Base Markup',
                'value_type': 'decimal',
                'decimal_value': 1.25,
                'description': 'Default markup multiplier for products',
                'category': 'pricing',
            },
            {
                'name': 'default_volatility_adjustment',
                'display_name': 'Default Volatility Adjustment',
                'value_type': 'decimal',
                'decimal_value': 0.15,
                'description': 'Default volatility adjustment for market prices',
                'category': 'pricing',
            },
            {
                'name': 'default_trend_multiplier',
                'display_name': 'Default Trend Multiplier',
                'value_type': 'decimal',
                'decimal_value': 1.10,
                'description': 'Default trend multiplier for price calculations',
                'category': 'pricing',
            },
            {
                'name': 'low_stock_threshold_percentage',
                'display_name': 'Low Stock Threshold %',
                'value_type': 'decimal',
                'decimal_value': 0.20,
                'description': 'Percentage of minimum stock to trigger low stock alerts',
                'category': 'inventory',
            },
            {
                'name': 'auto_reorder_enabled',
                'display_name': 'Auto Reorder Enabled',
                'value_type': 'boolean',
                'boolean_value': True,
                'description': 'Enable automatic reorder suggestions',
                'category': 'inventory',
            },
            {
                'name': 'default_credit_limit',
                'display_name': 'Default Credit Limit',
                'value_type': 'decimal',
                'decimal_value': 5000.00,
                'description': 'Default credit limit for new customers',
                'category': 'customers',
            },
            {
                'name': 'default_payment_terms',
                'display_name': 'Default Payment Terms (Days)',
                'value_type': 'integer',
                'integer_value': 30,
                'description': 'Default payment terms for new customers',
                'category': 'customers',
            },
        ]

        for config_data in configs:
            config, created = BusinessConfiguration.objects.get_or_create(
                name=config_data['name'],
                defaults=config_data
            )
            if created:
                self.stdout.write(f'✅ Created business config: {config.display_name}')

    def create_system_settings(self):
        """Create system-wide settings"""
        settings = [
            {
                'key': 'whatsapp_check_interval',
                'value': '30',
                'description': 'WhatsApp message check interval in seconds',
                'category': 'whatsapp',
            },
            {
                'key': 'api_timeout_seconds',
                'value': '30',
                'description': 'Default API timeout in seconds',
                'category': 'api',
            },
            {
                'key': 'max_retry_attempts',
                'value': '3',
                'description': 'Maximum retry attempts for failed operations',
                'category': 'api',
            },
            {
                'key': 'enable_debug_logging',
                'value': 'true',
                'description': 'Enable debug logging for development',
                'category': 'logging',
            },
            {
                'key': 'procurement_buffer_percentage',
                'value': '0.10',
                'description': 'Default buffer percentage for procurement calculations',
                'category': 'procurement',
            },
        ]

        for setting_data in settings:
            setting, created = SystemSetting.objects.get_or_create(
                key=setting_data['key'],
                defaults=setting_data
            )
            if created:
                self.stdout.write(f'✅ Created system setting: {setting.key}')
