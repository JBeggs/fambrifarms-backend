# Generated migration for product supplier cost tracking

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0001_initial'),
        ('suppliers', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='supplier_cost',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text='Current cost from supplier',
                max_digits=10,
                null=True
            ),
        ),
        migrations.AddField(
            model_name='product',
            name='cost_unit',
            field=models.CharField(
                choices=[
                    ('per_kg', 'Per kilogram'),
                    ('per_unit', 'Per unit/each'),
                    ('per_package', 'Per package'),
                ],
                default='per_kg',
                max_length=20
            ),
        ),
        migrations.AddField(
            model_name='product',
            name='last_supplier',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='products_supplied',
                to='suppliers.supplier'
            ),
        ),
        migrations.AddField(
            model_name='product',
            name='last_cost_update',
            field=models.DateField(
                blank=True,
                help_text='Date of last supplier cost update',
                null=True
            ),
        ),
    ]

