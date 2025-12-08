# Generated migration for adding weight_kg field to RecipeIngredient

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('production', '0004_alter_recipe_batch_size_alter_recipe_is_active_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='recipeingredient',
            name='weight_kg',
            field=models.DecimalField(
                blank=True,
                decimal_places=3,
                help_text='Weight in kg (required for non-kg products, e.g., boxes, bags)',
                max_digits=10,
                null=True
            ),
        ),
    ]

