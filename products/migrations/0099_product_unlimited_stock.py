# Generated manually for unlimited stock feature

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0021_product_supplier_cost_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='unlimited_stock',
            field=models.BooleanField(
                default=False,
                help_text='Product is always available (e.g., garden-grown). Orders will not reserve stock.'
            ),
        ),
    ]

