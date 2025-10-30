# Production schema fix - handles existing columns gracefully
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0019_fix_enable_buffer_calculations'),
    ]

    operations = [
        # Mark existing migrations as applied without running them
        # This is a no-op migration to sync production state
    ]
