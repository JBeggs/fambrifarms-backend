# Generated migration for adding performance indexes

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0102_product_packaging_size'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='product',
            index=models.Index(fields=['is_active'], name='products_pr_is_acti_idx'),
        ),
        migrations.AddIndex(
            model_name='product',
            index=models.Index(fields=['department', 'is_active'], name='products_pr_departm_idx'),
        ),
    ]

