# Generated to fix production migration conflict
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0018_add_enable_buffer_calculations'),
    ]

    operations = [
        # This migration ensures enable_buffer_calculations exists
        # If it already exists, this will be a no-op
        migrations.RunSQL(
            """
            ALTER TABLE products_businesssettings 
            ADD COLUMN IF NOT EXISTS enable_buffer_calculations BOOLEAN DEFAULT TRUE;
            """,
            reverse_sql="""
            ALTER TABLE products_businesssettings 
            DROP COLUMN IF EXISTS enable_buffer_calculations;
            """
        ),
    ]
