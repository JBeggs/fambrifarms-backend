# Generated manually to convert StockUpdate items from product names to product IDs

from django.db import migrations
from django.db.models import Q


def convert_stockupdate_items_to_product_ids(apps, schema_editor):
    """
    Convert existing StockUpdate.items from:
    {"product_name": {"quantity": X, "unit": "kg"}}
    
    To:
    {"product_id": {"quantity": X, "unit": "kg", "product_name": "name"}}
    """
    StockUpdate = apps.get_model('whatsapp', 'StockUpdate')
    Product = apps.get_model('products', 'Product')
    
    # Get all products for name-to-ID mapping
    products_by_name = {}
    for product in Product.objects.all():
        products_by_name[product.name.lower().strip()] = product
    
    updated_count = 0
    failed_count = 0
    
    for stock_update in StockUpdate.objects.all():
        if not stock_update.items:
            continue
            
        new_items = {}
        has_changes = False
        
        for key, data in stock_update.items.items():
            # Check if this is already in the new format (key is numeric)
            try:
                int(key)
                # Already in new format, keep as is
                new_items[key] = data
                continue
            except ValueError:
                # Old format (product name), need to convert
                pass
            
            # Try to find product by name
            product_name_key = key.lower().strip()
            product = products_by_name.get(product_name_key)
            
            if product:
                # Convert to new format
                new_items[str(product.id)] = {
                    'quantity': data.get('quantity', 0),
                    'unit': data.get('unit', ''),
                    'product_name': product.name,
                    'original_line': data.get('original_line', key)
                }
                has_changes = True
            else:
                # Product not found, keep original but log it
                print(f"Warning: Product '{key}' not found for StockUpdate {stock_update.id}")
                # Keep in old format for manual review
                new_items[key] = data
                failed_count += 1
        
        if has_changes:
            stock_update.items = new_items
            stock_update.save()
            updated_count += 1
    
    print(f"Converted {updated_count} StockUpdate records to product ID format")
    if failed_count > 0:
        print(f"Warning: {failed_count} items could not be converted (product names not found)")


def reverse_stockupdate_items_to_product_names(apps, schema_editor):
    """
    Reverse conversion: Convert back from product IDs to product names
    """
    StockUpdate = apps.get_model('whatsapp', 'StockUpdate')
    Product = apps.get_model('products', 'Product')
    
    # Get all products for ID-to-name mapping
    products_by_id = {}
    for product in Product.objects.all():
        products_by_id[product.id] = product
    
    updated_count = 0
    
    for stock_update in StockUpdate.objects.all():
        if not stock_update.items:
            continue
            
        new_items = {}
        has_changes = False
        
        for key, data in stock_update.items.items():
            # Check if this is in the new format (key is numeric)
            try:
                product_id = int(key)
                # New format, convert back to old format
                product = products_by_id.get(product_id)
                if product:
                    new_items[product.name] = {
                        'quantity': data.get('quantity', 0),
                        'unit': data.get('unit', ''),
                        'original_line': data.get('original_line', product.name)
                    }
                    has_changes = True
                else:
                    # Product not found, keep as is
                    new_items[key] = data
            except ValueError:
                # Old format, keep as is
                new_items[key] = data
        
        if has_changes:
            stock_update.items = new_items
            stock_update.save()
            updated_count += 1
    
    print(f"Reverted {updated_count} StockUpdate records to product name format")


class Migration(migrations.Migration):

    dependencies = [
        ('whatsapp', '0010_alter_whatsappmessage_options'),
        ('products', '0021_product_supplier_cost_fields'),
    ]

    operations = [
        migrations.RunPython(
            convert_stockupdate_items_to_product_ids,
            reverse_stockupdate_items_to_product_names,
        ),
    ]
