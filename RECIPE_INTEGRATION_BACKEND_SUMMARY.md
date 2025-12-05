# Recipe Integration - Backend Implementation Summary

## Overview

Backend implementation for recipe-based stock management in order creation. Recipes automatically handle stock deduction from multiple ingredients, eliminating the need for manual source product selection when recipes exist.

## Changes Made

### 1. Production App Serializers (`backend/production/serializers.py`)
- **RecipeIngredientSerializer**: Serializes recipe ingredients with product details
- **RecipeSerializer**: Serializes recipes with nested ingredients

### 2. Product Serializer Enhancement (`backend/products/serializers.py`)
- Added optional `recipe` field to `ProductSerializer`
- Returns recipe data (with ingredients) if product has an active recipe
- Uses production app's Recipe model

### 3. Recipe API Endpoints (`backend/production/views.py` & `urls.py`)
- **GET `/api/production/products/<product_id>/recipe/`**: Get recipe for a specific product
  - Returns recipe with ingredients if exists
  - Returns `null` if no recipe (not an error)
  - Public endpoint (AllowAny) for order creation flow
  
- **GET `/api/production/recipes/`**: List all active recipes (admin endpoint)

### 4. Order Creation Integration (`backend/whatsapp/views.py`)
- **Recipe Detection**: Checks if product has an active recipe before processing
- **Recipe-Based Stock Deduction**:
  - Calculates required quantities for each ingredient based on order quantity
  - Formula: `(order_quantity / recipe.batch_size) * ingredient.quantity`
  - Reserves stock from ALL recipe ingredients automatically
  - Stores recipe source products in `OrderItem.source_products` JSONField
- **Fallback to Source Product**: If no recipe exists, uses existing single source product flow
- **Logging**: Comprehensive logging for recipe detection and stock operations

## How It Works

### Flow for Products WITH Recipe:
1. Order item created with product (e.g., "Mixed Lettuce")
2. System checks for active recipe
3. If recipe exists:
   - Calculate ingredient quantities based on order quantity
   - Reserve stock from each ingredient product
   - Store recipe source products in `source_products` JSONField
   - **No manual source product selection needed**

### Flow for Products WITHOUT Recipe:
1. Order item created with product
2. No recipe found
3. Uses existing source product flow:
   - User manually selects source product (if needed)
   - Single source product stored in `source_product` and `source_quantity` fields

## Database Fields Used

- **OrderItem.source_products** (JSONField): Array of source products from recipe
  - Format: `[{"product_id": 123, "quantity": 0.5, "unit": "kg", "name": "Romaine Lettuce"}, ...]`
- **OrderItem.source_product** (ForeignKey): Single source product (fallback, no recipe)
- **OrderItem.source_quantity** (DecimalField): Single source quantity (fallback, no recipe)

## API Endpoints

### Get Product Recipe
```
GET /api/production/products/{product_id}/recipe/
Response: {
  "status": "success",
  "recipe": {
    "id": 1,
    "product_id": 123,
    "product_name": "Mixed Lettuce",
    "name": "Mixed Lettuce Recipe",
    "batch_size": 1,
    "ingredients": [
      {
        "id": 1,
        "raw_material_id": 456,
        "raw_material_name": "Romaine Lettuce",
        "quantity": 0.1,
        "unit": "kg"
      },
      ...
    ]
  }
}
```

## Testing

To test recipe integration:
1. Create a Recipe for "Mixed Lettuce" product in production app
2. Add RecipeIngredient records (e.g., Romaine: 100g, Butter Lettuce: 100g)
3. Create an order with "Mixed Lettuce"
4. Verify stock is deducted from all ingredients automatically
5. Check `OrderItem.source_products` contains recipe ingredients

## Next Steps

1. **Frontend Integration**: 
   - Fetch recipe data when product selected
   - Show recipe ingredients in UI
   - Hide source product selector when recipe exists
   - Display recipe breakdown

2. **Data Setup**:
   - Create recipes for "Mixed Lettuce" and "Green Mixed Lettuce"
   - Add all required ingredients with quantities
   - Test with real orders

## Notes

- Recipes take precedence over manual source product selection
- If recipe exists, `source_product_id` in request is ignored
- Recipe-based flow is automatic - no UI changes needed for basic functionality
- Backward compatible - products without recipes work exactly as before

