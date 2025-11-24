# Generated migration for adding packaging_size field to Product model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0101_restaurantpackagerestriction'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='packaging_size',
            field=models.CharField(
                blank=True,
                help_text='Packaging size (e.g., "100g", "1kg", "500g"). Used for stock calculations when unit is discrete (packet, bag, box, etc.).',
                max_length=50,
                null=True
            ),
        ),
    ]

