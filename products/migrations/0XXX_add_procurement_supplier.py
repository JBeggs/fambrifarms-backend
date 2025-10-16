# Generated migration for procurement supplier assignment

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0001_initial'),  # Replace with actual last migration
        ('suppliers', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='procurement_supplier',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='procured_products',
                to='suppliers.supplier',
                help_text='Primary supplier for market procurement. NULL = use Fambri garden/no procurement needed.'
            ),
        ),
    ]
