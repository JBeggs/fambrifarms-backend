# Generated manually for multiple source products feature

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0006_order_locked_at_order_locked_by'),
    ]

    operations = [
        migrations.AddField(
            model_name='orderitem',
            name='source_products',
            field=models.JSONField(
                blank=True,
                default=list,
                help_text='Array of source products for mixed products. Format: [{"product_id": 123, "quantity": 3.0, "unit": "kg"}, ...]',
                null=True
            ),
        ),
    ]

