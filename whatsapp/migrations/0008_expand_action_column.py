# Generated migration to fix action column size

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('whatsapp', '0007_whatsappmessage_processing_notes'),
    ]

    operations = [
        migrations.AlterField(
            model_name='messageprocessinglog',
            name='action',
            field=models.CharField(
                choices=[
                    ('classified', 'Message Classified'),
                    ('parsed', 'Items Parsed'),
                    ('order_created', 'Order Created'),
                    ('stock_updated', 'Stock Updated'),
                    ('edited', 'Message Edited'),
                    ('error', 'Processing Error'),
                    ('dynamic_pricing_applied', 'Dynamic Pricing Applied'),
                    ('product_created', 'Product Auto-Created'),
                    ('customer_assigned', 'Customer Assigned'),
                    ('validation_failed', 'Validation Failed'),
                    ('partial_rejected', 'Partial Processing Rejected'),
                    ('unparsed_as_notes', 'Unparsed Lines Added as Notes'),
                    ('note_item_created', 'Note Item Created for Unparsed'),
                    ('manual_company_preserved', 'Manual Company Preserved'),
                    ('context_company_changed', 'Context Company Changed'),
                    ('company_updated', 'Company Assignment Updated'),
                    ('type_updated', 'Message Type Updated'),
                ],
                max_length=50  # Increased from 20 to 50
            ),
        ),
    ]
