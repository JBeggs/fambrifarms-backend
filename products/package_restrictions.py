"""
Utility functions for restaurant package size restrictions
"""
from typing import List, Optional, Set
from decimal import Decimal
import re
from .models import Product, RestaurantPackageRestriction, Department
from accounts.models import RestaurantProfile


def extract_package_size_grams(product_name: str) -> Optional[int]:
    """
    Extract package size in grams from product name
    
    Examples:
        "Basil (100g)" -> 100
        "Basil (150g packet)" -> 150
        "Tomatoes (5kg)" -> 5000
        "Parsley (100g)" -> 100
        "Carrots" -> None (no package size)
    
    Returns:
        Package size in grams, or None if not found
    """
    # Pattern to match package sizes: (100g), (150g packet), (5kg), etc.
    pattern = r'\((\d+(?:\.\d+)?)\s*(kg|g|ml|l)\s*(?:bag|box|packet|punnet)?\)'
    match = re.search(pattern, product_name, re.IGNORECASE)
    
    if match:
        size_value = float(match.group(1))
        unit = match.group(2).lower()
        
        # Convert to grams
        if unit == 'kg':
            return int(size_value * 1000)
        elif unit == 'g':
            return int(size_value)
        elif unit in ['l', 'ml']:
            # For liquids, assume 1:1 ratio with grams for simplicity
            if unit == 'ml':
                return int(size_value)
            else:  # liters
                return int(size_value * 1000)
    
    return None


def get_restricted_package_sizes(restaurant: RestaurantProfile, department: Department) -> Optional[List[int]]:
    """
    Get allowed package sizes for a restaurant-department combination
    
    Args:
        restaurant: RestaurantProfile instance
        department: Department instance
        
    Returns:
        List of allowed package sizes in grams, or None if no restrictions (all sizes allowed)
    """
    try:
        restriction = RestaurantPackageRestriction.objects.get(
            restaurant=restaurant,
            department=department
        )
        # Empty list means all sizes allowed (fallback behavior)
        if not restriction.allowed_package_sizes:
            return None
        return restriction.allowed_package_sizes
    except RestaurantPackageRestriction.DoesNotExist:
        # No restriction = all sizes allowed
        return None


def is_product_allowed_for_restaurant(product: Product, restaurant: Optional[RestaurantProfile]) -> bool:
    """
    Check if a product is allowed for a restaurant based on package size restrictions
    
    Args:
        product: Product instance
        restaurant: RestaurantProfile instance or None
        
    Returns:
        True if product is allowed, False otherwise
        If restaurant is None, always returns True (no restrictions)
    """
    # If no restaurant specified, allow all products (backward compatible)
    if not restaurant:
        return True
    
    # Extract package size from product name
    package_size_grams = extract_package_size_grams(product.name)
    
    # If product has no package size, it's always allowed
    if package_size_grams is None:
        return True
    
    # Get restrictions for this restaurant-department combination
    allowed_sizes = get_restricted_package_sizes(restaurant, product.department)
    
    # If no restrictions exist, allow all products (fallback)
    if allowed_sizes is None:
        return True
    
    # Check if product's package size is in allowed list
    return package_size_grams in allowed_sizes


def filter_products_by_restaurant(
    products: List[Product], 
    restaurant: Optional[RestaurantProfile]
) -> List[Product]:
    """
    Filter a list of products based on restaurant package size restrictions
    
    Args:
        products: List of Product instances
        restaurant: RestaurantProfile instance or None
        
    Returns:
        Filtered list of products that are allowed for the restaurant
    """
    if not restaurant:
        return products
    
    filtered = []
    for product in products:
        if is_product_allowed_for_restaurant(product, restaurant):
            filtered.append(product)
    
    return filtered


def get_allowed_products_for_restaurant(
    restaurant: Optional[RestaurantProfile],
    department: Optional[Department] = None,
    queryset: Optional[Product.objects] = None
) -> Product.objects:
    """
    Get a queryset of products allowed for a restaurant, filtered by restrictions
    
    Args:
        restaurant: RestaurantProfile instance or None
        department: Optional Department to filter by
        queryset: Optional base Product queryset (defaults to Product.objects.all())
        
    Returns:
        Filtered Product queryset
    """
    if queryset is None:
        queryset = Product.objects.all()
    
    # If no restaurant, return all products (backward compatible)
    if not restaurant:
        if department:
            return queryset.filter(department=department)
        return queryset
    
    # Get all restrictions for this restaurant
    restrictions = RestaurantPackageRestriction.objects.filter(
        restaurant=restaurant
    ).select_related('department')
    
    # If no restrictions exist, return all products (fallback)
    if not restrictions.exists():
        if department:
            return queryset.filter(department=department)
        return queryset
    
    # Build a set of allowed package sizes per department
    department_allowed_sizes = {}
    for restriction in restrictions:
        if restriction.allowed_package_sizes:
            department_allowed_sizes[restriction.department_id] = set(restriction.allowed_package_sizes)
    
    # If no restrictions with sizes, return all products
    if not department_allowed_sizes:
        if department:
            return queryset.filter(department=department)
        return queryset
    
    # Filter by department if specified
    if department:
        queryset = queryset.filter(department=department)
        # Check if this department has restrictions
        if department.id in department_allowed_sizes:
            allowed_sizes = department_allowed_sizes[department.id]
            # We need to filter by package size extracted from name
            # This is complex in SQL, so we'll do it in Python for now
            # TODO: Could optimize with database function if needed
            products = list(queryset)
            filtered = [
                p for p in products
                if extract_package_size_grams(p.name) is None or
                   extract_package_size_grams(p.name) in allowed_sizes
            ]
            # Return a queryset with filtered IDs
            product_ids = [p.id for p in filtered]
            return queryset.filter(id__in=product_ids)
        else:
            # No restrictions for this department, return all
            return queryset
    else:
        # Filter all departments
        products = list(queryset)
        filtered = []
        for product in products:
            product_size = extract_package_size_grams(product.name)
            # If product has no package size, it's always allowed
            if product_size is None:
                filtered.append(product)
            # If product's department has restrictions, check them
            elif product.department_id in department_allowed_sizes:
                allowed_sizes = department_allowed_sizes[product.department_id]
                if product_size in allowed_sizes:
                    filtered.append(product)
            # If product's department has no restrictions, allow it
            else:
                filtered.append(product)
        
        # Return queryset with filtered IDs
        product_ids = [p.id for p in filtered]
        return queryset.filter(id__in=product_ids)

