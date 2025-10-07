from django.core.management.base import BaseCommand
from settings.models import (
    UnitOfMeasure, MessageType, UserType, SupplierType,
    InvoiceStatus, PaymentMethod, ProductionStatus,
    QualityGrade, PriorityLevel, WhatsAppPattern,
    ProductVariation, CompanyAlias, OrderStatus
)


class Command(BaseCommand):
    help = 'Seed configuration data with current hardcoded values'

    def handle(self, *args, **options):
        self.stdout.write('Seeding configuration data...')
        
        # Seed Units of Measure
        self.seed_units_of_measure()
        
        # Seed Message Types
        self.seed_message_types()
        
        # Seed User Types
        self.seed_user_types()
        
        # Seed Supplier Types
        self.seed_supplier_types()
        
        # Seed Invoice Statuses
        self.seed_invoice_statuses()
        
        # Seed Payment Methods
        self.seed_payment_methods()
        
        # Seed Production Statuses
        self.seed_production_statuses()
        
        # Seed Quality Grades
        self.seed_quality_grades()
        
        # Seed Priority Levels
        self.seed_priority_levels()
        
        # Seed WhatsApp Patterns
        self.seed_whatsapp_patterns()
        
        # Seed Product Variations
        self.seed_product_variations()
        
        # Seed Company Aliases
        self.seed_company_aliases()
        
        # Seed Order Statuses
        self.seed_order_statuses()
        
        self.stdout.write(
            self.style.SUCCESS('Successfully seeded all configuration data')
        )

    def seed_units_of_measure(self):
        """Seed units of measure from Product.UNIT_CHOICES"""
        units_data = [
            ('kg', 'Kilogram', 'Weight measurement', 'weight', 1),
            ('g', 'Gram', 'Weight measurement', 'weight', 2),
            ('piece', 'Piece', 'Individual item count', 'count', 3),
            ('each', 'Each', 'Individual item count', 'count', 4),
            ('head', 'Head', 'Individual item count', 'count', 5),
            ('bunch', 'Bunch', 'Group of items', 'count', 6),
            ('box', 'Box', 'Container count', 'count', 7),
            ('bag', 'Bag', 'Container count', 'count', 8),
            ('punnet', 'Punnet', 'Small container', 'count', 9),
            ('packet', 'Packet', 'Packaged item', 'count', 10),
            ('crate', 'Crate', 'Large container', 'count', 11),
            ('tray', 'Tray', 'Flat container', 'count', 12),
            ('bundle', 'Bundle', 'Group of items', 'count', 13),
            ('L', 'Liter', 'Volume measurement', 'volume', 14),
            ('ml', 'Milliliter', 'Volume measurement', 'volume', 15),
        ]
        
        for name, display_name, description, category, sort_order in units_data:
            UnitOfMeasure.objects.get_or_create(
                name=name,
                defaults={
                    'display_name': display_name,
                    'description': description,
                    'category': category,
                    'sort_order': sort_order,
                    'is_active': True
                }
            )
        
        self.stdout.write('✓ Seeded units of measure')

    def seed_message_types(self):
        """Seed message types from WhatsAppMessage.MESSAGE_TYPES"""
        types_data = [
            ('order', 'Customer Order', 'Order placed by customer', '#28a745', 1),
            ('stock', 'Stock Update', 'Stock level update from SHALLOME', '#17a2b8', 2),
            ('instruction', 'Instruction/Note', 'General instruction or note', '#ffc107', 3),
            ('demarcation', 'Order Day Demarcation', 'Order day boundary marker', '#6c757d', 4),
            ('image', 'Image Message', 'Image attachment', '#6f42c1', 5),
            ('voice', 'Voice Message', 'Voice recording', '#e83e8c', 6),
            ('video', 'Video Message', 'Video attachment', '#fd7e14', 7),
            ('document', 'Document Message', 'Document attachment', '#20c997', 8),
            ('sticker', 'Sticker Message', 'Sticker/emoji', '#6c757d', 9),
            ('other', 'Other', 'Unclassified message', '#6c757d', 10),
        ]
        
        for name, display_name, description, color, sort_order in types_data:
            MessageType.objects.get_or_create(
                name=name,
                defaults={
                    'display_name': display_name,
                    'description': description,
                    'color': color,
                    'sort_order': sort_order,
                    'is_active': True
                }
            )
        
        self.stdout.write('✓ Seeded message types')

    def seed_user_types(self):
        """Seed user types from accounts.models"""
        types_data = [
            ('restaurant', 'Restaurant', 'Restaurant customer', ['view_orders', 'create_orders'], 1),
            ('private', 'Private Customer', 'Private individual customer', ['view_orders'], 2),
            ('farm_manager', 'Farm Manager', 'Internal farm manager', ['view_all', 'manage_production'], 3),
            ('stock_taker', 'Stock Taker', 'Stock management staff', ['view_inventory', 'update_stock'], 4),
            ('admin', 'Admin', 'System administrator', ['all_permissions'], 5),
            ('staff', 'Staff', 'General staff member', ['view_orders', 'view_inventory'], 6),
        ]
        
        for name, display_name, description, permissions, sort_order in types_data:
            UserType.objects.get_or_create(
                name=name,
                defaults={
                    'display_name': display_name,
                    'description': description,
                    'permissions': permissions,
                    'sort_order': sort_order,
                    'is_active': True
                }
            )
        
        self.stdout.write('✓ Seeded user types')

    def seed_supplier_types(self):
        """Seed supplier types"""
        types_data = [
            ('internal', 'Internal Farm', 'Internal farm production', 1),
            ('external', 'External Supplier', 'External supplier/vendor', 2),
        ]
        
        for name, display_name, description, sort_order in types_data:
            SupplierType.objects.get_or_create(
                name=name,
                defaults={
                    'display_name': display_name,
                    'description': description,
                    'sort_order': sort_order,
                    'is_active': True
                }
            )
        
        self.stdout.write('✓ Seeded supplier types')

    def seed_invoice_statuses(self):
        """Seed invoice statuses"""
        statuses_data = [
            ('draft', 'Draft', 'Draft invoice', '#6c757d', False, 1),
            ('sent', 'Sent', 'Invoice sent to customer', '#17a2b8', False, 2),
            ('paid', 'Paid', 'Invoice paid', '#28a745', True, 3),
            ('overdue', 'Overdue', 'Invoice overdue', '#dc3545', False, 4),
            ('cancelled', 'Cancelled', 'Invoice cancelled', '#6c757d', True, 5),
        ]
        
        for name, display_name, description, color, is_final, sort_order in statuses_data:
            InvoiceStatus.objects.get_or_create(
                name=name,
                defaults={
                    'display_name': display_name,
                    'description': description,
                    'color': color,
                    'is_final': is_final,
                    'sort_order': sort_order,
                    'is_active': True
                }
            )
        
        self.stdout.write('✓ Seeded invoice statuses')

    def seed_payment_methods(self):
        """Seed payment methods"""
        methods_data = [
            ('cash', 'Cash', 'Cash payment', False, 1),
            ('bank_transfer', 'Bank Transfer', 'Bank transfer payment', True, 2),
            ('credit_card', 'Credit Card', 'Credit card payment', True, 3),
            ('eft', 'EFT', 'Electronic funds transfer', True, 4),
        ]
        
        for name, display_name, description, requires_reference, sort_order in methods_data:
            PaymentMethod.objects.get_or_create(
                name=name,
                defaults={
                    'display_name': display_name,
                    'description': description,
                    'requires_reference': requires_reference,
                    'sort_order': sort_order,
                    'is_active': True
                }
            )
        
        self.stdout.write('✓ Seeded payment methods')

    def seed_production_statuses(self):
        """Seed production statuses"""
        statuses_data = [
            ('planned', 'Planned', 'Production planned', '#17a2b8', False, 1),
            ('in_progress', 'In Progress', 'Production in progress', '#ffc107', False, 2),
            ('completed', 'Completed', 'Production completed', '#28a745', True, 3),
            ('cancelled', 'Cancelled', 'Production cancelled', '#dc3545', True, 4),
        ]
        
        for name, display_name, description, color, is_final, sort_order in statuses_data:
            ProductionStatus.objects.get_or_create(
                name=name,
                defaults={
                    'display_name': display_name,
                    'description': description,
                    'color': color,
                    'is_final': is_final,
                    'sort_order': sort_order,
                    'is_active': True
                }
            )
        
        self.stdout.write('✓ Seeded production statuses')

    def seed_quality_grades(self):
        """Seed quality grades"""
        grades_data = [
            ('A', 'Grade A - Premium', 'Premium quality grade', '#28a745', 1),
            ('B', 'Grade B - Standard', 'Standard quality grade', '#ffc107', 2),
            ('C', 'Grade C - Basic', 'Basic quality grade', '#fd7e14', 3),
        ]
        
        for name, display_name, description, color, sort_order in grades_data:
            QualityGrade.objects.get_or_create(
                name=name,
                defaults={
                    'display_name': display_name,
                    'description': description,
                    'color': color,
                    'sort_order': sort_order,
                    'is_active': True
                }
            )
        
        self.stdout.write('✓ Seeded quality grades')

    def seed_priority_levels(self):
        """Seed priority levels"""
        levels_data = [
            ('low', 'Low', 'Low priority', '#28a745', 1, 1),
            ('medium', 'Medium', 'Medium priority', '#ffc107', 2, 2),
            ('high', 'High', 'High priority', '#fd7e14', 3, 3),
            ('critical', 'Critical', 'Critical priority', '#dc3545', 4, 4),
        ]
        
        for name, display_name, description, color, numeric_value, sort_order in levels_data:
            PriorityLevel.objects.get_or_create(
                name=name,
                defaults={
                    'display_name': display_name,
                    'description': description,
                    'color': color,
                    'numeric_value': numeric_value,
                    'sort_order': sort_order,
                    'is_active': True
                }
            )
        
        self.stdout.write('✓ Seeded priority levels')

    def seed_whatsapp_patterns(self):
        """Seed WhatsApp patterns from services.py"""
        patterns_data = [
            # Stock header patterns
            ('stock_header', 'STOCK AS AT', 'Standard stock header', False, 1),
            ('stock_header', 'STOKE AS AT', 'Common typo for stock header', False, 2),
            ('stock_header', 'TOCK AS AT', 'Missing S typo', False, 3),
            ('stock_header', 'STOCK AT', 'Missing AS', False, 4),
            ('stock_header', 'STOK AS AT', 'Another typo', False, 5),
            
            # Demarcation patterns
            ('demarcation', 'ORDERS STARTS HERE', 'Order day demarcation', False, 1),
            ('demarcation', '👇👇👇', 'Order day demarcation emoji', False, 2),
            ('demarcation', 'THURSDAY ORDERS STARTS HERE', 'Thursday orders', False, 3),
            ('demarcation', 'TUESDAY ORDERS STARTS HERE', 'Tuesday orders', False, 4),
            ('demarcation', 'MONDAY ORDERS STARTS HERE', 'Monday orders', False, 5),
            
            # Order keywords
            ('order_keyword', 'ORDER', 'Order keyword', False, 1),
            ('order_keyword', 'NEED', 'Need keyword', False, 2),
            ('order_keyword', 'WANT', 'Want keyword', False, 3),
            ('order_keyword', 'REQUIRE', 'Require keyword', False, 4),
            ('order_keyword', 'REQUEST', 'Request keyword', False, 5),
            
            # Stock keywords
            ('stock_keyword', 'STOCK', 'Stock keyword', False, 1),
            ('stock_keyword', 'AVAILABLE', 'Available keyword', False, 2),
            ('stock_keyword', 'INVENTORY', 'Inventory keyword', False, 3),
            ('stock_keyword', 'SUPPLY', 'Supply keyword', False, 4),
            ('stock_keyword', 'STOKE', 'Stock typo', False, 5),
        ]
        
        for pattern_type, pattern_value, description, is_regex, sort_order in patterns_data:
            WhatsAppPattern.objects.get_or_create(
                pattern_type=pattern_type,
                pattern_value=pattern_value,
                defaults={
                    'description': description,
                    'is_regex': is_regex,
                    'sort_order': sort_order,
                    'is_active': True
                }
            )
        
        self.stdout.write('✓ Seeded WhatsApp patterns')

    def seed_product_variations(self):
        """Seed product variations from services.py"""
        variations_data = [
            ('tomatos', 'tomatoes'),
            ('tomatoe', 'tomatoes'),
            ('onion', 'onions'),
            ('potato', 'potatoes'),
            ('potatos', 'potatoes'),
            ('mushroom', 'mushrooms'),
            ('carrot', 'carrots'),
        ]
        
        for original_name, normalized_name in variations_data:
            ProductVariation.objects.get_or_create(
                original_name=original_name,
                normalized_name=normalized_name,
                defaults={
                    'description': f'Normalize {original_name} to {normalized_name}',
                    'is_active': True
                }
            )
        
        self.stdout.write('✓ Seeded product variations')

    def seed_company_aliases(self):
        """Seed company aliases from company_extractor.py"""
        aliases_data = [
            ('mugg and bean', 'Mugg and Bean'),
            ('mugg bean', 'Mugg and Bean'),
            ('mugg', 'Mugg and Bean'),
            ('maltos', 'Maltos'),
            ('valley', 'Valley'),
            ('order valley', 'Valley'),
            ('barchef', 'Barchef Entertainment'),
            ('barchef entertainment', 'Barchef Entertainment'),
            ('casa bella', 'Casa Bella'),
            ('casabella', 'Casa Bella'),
            ('debonairs', 'Debonairs Pizza'),
            ('debonair', 'Debonairs Pizza'),
            ('debonair pizza', 'Debonairs Pizza'),
            ('wimpy', 'Wimpy Mooikloof'),
            ('wimpy mooikloof', 'Wimpy Mooikloof'),
            ('wimpy mooinooi', 'Wimpy Mooikloof'),
            ('t-junction', 'T-junction'),
            ('t junction', 'T-junction'),
            ('tjunction', 'T-junction'),
            ('venue', 'Venue'),
            ('revue', 'Revue Bar'),
            ('revue bar', 'Revue Bar'),
            ('pecanwood', 'Pecanwood Golf Estate'),
            ('pecanwood golf', 'Pecanwood Golf Estate'),
            ('culinary', 'Culinary Institute'),
            ('culinary institute', 'Culinary Institute'),
            ('marco', 'Marco'),
            ('sylvia', 'Sylvia'),
            ('arthur', 'Arthur'),
            ('shallome', 'SHALLOME'),
            ('hazvinei', 'SHALLOME'),
            ('luma', 'Luma'),
            ('shebeen', 'Shebeen'),
        ]
        
        for alias, company_name in aliases_data:
            CompanyAlias.objects.get_or_create(
                alias=alias,
                company_name=company_name,
                defaults={
                    'description': f'Alias for {company_name}',
                    'is_active': True
                }
            )
        
        self.stdout.write('✓ Seeded company aliases')

    def seed_order_statuses(self):
        """Seed order statuses from Order.STATUS_CHOICES"""
        statuses_data = [
            ('received', 'Received via WhatsApp', 'Order received via WhatsApp', '#17a2b8', False, 1),
            ('parsed', 'AI Parsed', 'Order parsed by AI system', '#ffc107', False, 2),
            ('confirmed', 'Manager Confirmed', 'Order confirmed by manager', '#28a745', False, 3),
            ('po_sent', 'PO Sent to Sales Rep', 'Purchase order sent to sales rep', '#6f42c1', False, 4),
            ('po_confirmed', 'Sales Rep Confirmed', 'Purchase order confirmed by sales rep', '#20c997', False, 5),
            ('delivered', 'Delivered to Customer', 'Order delivered to customer', '#28a745', True, 6),
            ('cancelled', 'Cancelled', 'Order cancelled', '#dc3545', True, 7),
        ]
        
        for name, display_name, description, color, is_final, sort_order in statuses_data:
            OrderStatus.objects.get_or_create(
                name=name,
                defaults={
                    'display_name': display_name,
                    'description': description,
                    'color': color,
                    'is_final': is_final,
                    'sort_order': sort_order,
                    'is_active': True
                }
            )
        
        self.stdout.write('✓ Seeded order statuses')
