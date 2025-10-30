# Generated to fix production migration conflicts
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0018_add_enable_buffer_calculations'),
    ]

    operations = [
        # Fix enable_buffer_calculations column if missing (MySQL compatible)
        migrations.RunSQL(
            """
            SET @col_exists = (
                SELECT COUNT(*) FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'products_businesssettings' 
                AND COLUMN_NAME = 'enable_buffer_calculations'
            );
            
            SET @sql = IF(@col_exists = 0, 
                'ALTER TABLE products_businesssettings ADD COLUMN enable_buffer_calculations BOOLEAN DEFAULT TRUE', 
                'SELECT "enable_buffer_calculations already exists"'
            );
            
            PREPARE stmt FROM @sql;
            EXECUTE stmt;
            DEALLOCATE PREPARE stmt;
            """,
            reverse_sql="""
            ALTER TABLE products_businesssettings 
            DROP COLUMN enable_buffer_calculations;
            """
        ),
        # Fix procurement_supplier_id column if missing (MySQL compatible)
        migrations.RunSQL(
            """
            SET @col_exists = (
                SELECT COUNT(*) FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'products_product' 
                AND COLUMN_NAME = 'procurement_supplier_id'
            );
            
            SET @sql = IF(@col_exists = 0, 
                'ALTER TABLE products_product ADD COLUMN procurement_supplier_id INT NULL', 
                'SELECT "procurement_supplier_id already exists"'
            );
            
            PREPARE stmt FROM @sql;
            EXECUTE stmt;
            DEALLOCATE PREPARE stmt;
            """,
            reverse_sql="""
            ALTER TABLE products_product 
            DROP COLUMN procurement_supplier_id;
            """
        ),
        # Add foreign key constraint if it doesn't exist
        migrations.RunSQL(
            """
            SET @constraint_exists = (
                SELECT COUNT(*) FROM information_schema.KEY_COLUMN_USAGE 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'products_product' 
                AND CONSTRAINT_NAME = 'products_product_procurement_supplier_id_fk'
            );
            
            SET @sql = IF(@constraint_exists = 0, 
                'ALTER TABLE products_product ADD CONSTRAINT products_product_procurement_supplier_id_fk FOREIGN KEY (procurement_supplier_id) REFERENCES suppliers_supplier(id)', 
                'SELECT "Foreign key already exists"'
            );
            
            PREPARE stmt FROM @sql;
            EXECUTE stmt;
            DEALLOCATE PREPARE stmt;
            """,
            reverse_sql="""
            ALTER TABLE products_product 
            DROP FOREIGN KEY IF EXISTS products_product_procurement_supplier_id_fk;
            """
        ),
    ]
