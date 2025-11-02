# Generated migration for invoice product matching system

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0001_initial'),
        ('products', '0001_initial'),
        ('suppliers', '0001_initial'),
        ('procurement', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Extend InvoicePhoto model
        migrations.AddField(
            model_name='invoicephoto',
            name='purchase_order',
            field=models.ForeignKey(
                blank=True,
                help_text='Link to purchase order being fulfilled',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='invoice_photos',
                to='procurement.purchaseorder'
            ),
        ),
        migrations.AddField(
            model_name='invoicephoto',
            name='receipt_number',
            field=models.CharField(
                blank=True,
                help_text="Supplier's receipt/invoice number",
                max_length=100
            ),
        ),
        
        # Extend ExtractedInvoiceData model
        migrations.AddField(
            model_name='extractedinvoicedata',
            name='matched_product',
            field=models.ForeignKey(
                blank=True,
                help_text='Our product that this line maps to',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to='products.product'
            ),
        ),
        migrations.AddField(
            model_name='extractedinvoicedata',
            name='pricing_strategy',
            field=models.CharField(
                blank=True,
                choices=[
                    ('per_kg', 'Cost per kg'),
                    ('per_unit', 'Cost per unit'),
                    ('per_package', 'Cost per package'),
                ],
                max_length=20,
                null=True
            ),
        ),
        migrations.AddField(
            model_name='extractedinvoicedata',
            name='calculated_cost_per_kg',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text='Auto-calculated: line_total / actual_weight_kg',
                max_digits=10,
                null=True
            ),
        ),
        migrations.AddField(
            model_name='extractedinvoicedata',
            name='po_item',
            field=models.ForeignKey(
                blank=True,
                help_text='PO item this fulfills',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to='procurement.purchaseorderitem'
            ),
        ),
        migrations.AddField(
            model_name='extractedinvoicedata',
            name='quantity_variance',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text='Difference between ordered and received',
                max_digits=10,
                null=True
            ),
        ),
        migrations.AddField(
            model_name='extractedinvoicedata',
            name='has_discrepancy',
            field=models.BooleanField(
                default=False,
                help_text="Flag if quantity/product doesn't match PO"
            ),
        ),
        migrations.AddField(
            model_name='extractedinvoicedata',
            name='discrepancy_notes',
            field=models.TextField(
                blank=True,
                help_text='Notes about any discrepancies'
            ),
        ),
        
        # Enhance SupplierProductMapping model
        migrations.AddField(
            model_name='supplierproductmapping',
            name='times_used',
            field=models.PositiveIntegerField(
                default=0,
                help_text='How many times this mapping has been used'
            ),
        ),
        migrations.AddField(
            model_name='supplierproductmapping',
            name='last_used',
            field=models.DateField(
                blank=True,
                help_text='Last time this mapping was used',
                null=True
            ),
        ),
        migrations.AddField(
            model_name='supplierproductmapping',
            name='confidence_score',
            field=models.DecimalField(
                decimal_places=2,
                default=1.00,
                help_text='0.00-1.00 confidence in this mapping',
                max_digits=3
            ),
        ),
        migrations.AddField(
            model_name='supplierproductmapping',
            name='average_weight_kg',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text='Average weight per package for this supplier product',
                max_digits=10,
                null=True
            ),
        ),
    ]

