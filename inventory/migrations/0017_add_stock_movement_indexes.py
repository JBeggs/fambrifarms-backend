# Generated migration for adding performance indexes to StockMovement

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0016_stockmovement_weight_and_more'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='stockmovement',
            index=models.Index(fields=['reference_number'], name='inventory_st_referen_idx'),
        ),
        migrations.AddIndex(
            model_name='stockmovement',
            index=models.Index(fields=['movement_type', 'timestamp'], name='inventory_st_movemen_idx'),
        ),
        migrations.AddIndex(
            model_name='stockmovement',
            index=models.Index(fields=['product', 'timestamp'], name='inventory_st_product_idx'),
        ),
    ]

