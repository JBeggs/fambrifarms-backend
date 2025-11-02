"""
Product Matching Service with Caching
Intelligent product matching for supplier invoice items
"""

from django.core.cache import cache
from django.db.models import Q, F
from django.utils import timezone
from typing import List, Dict, Optional
from decimal import Decimal
import logging

from products.models import Product
from suppliers.models import Supplier
from .models import SupplierProductMapping

logger = logging.getLogger(__name__)

PRODUCTS_CACHE_KEY = 'all_products_cached'
PRODUCTS_CACHE_TIMEOUT = 3600  # 1 hour


class ProductMatchingService:
    """
    Intelligent product matching with caching and learning
    """
    
    def __init__(self):
        self._products_cache = None
    
    def get_all_products(self) -> List[Product]:
        """
        Get all products with caching
        Uses Django cache to avoid repeated database queries
        """
        # Try memory cache first (within same request)
        if self._products_cache is not None:
            return self._products_cache
        
        # Try Django cache
        cached_products = cache.get(PRODUCTS_CACHE_KEY)
        if cached_products is not None:
            self._products_cache = cached_products
            return cached_products
        
        # Query database and cache
        products = list(Product.objects.select_related('department', 'last_supplier').all())
        cache.set(PRODUCTS_CACHE_KEY, products, PRODUCTS_CACHE_TIMEOUT)
        self._products_cache = products
        
        logger.info(f"Cached {len(products)} products")
        return products
    
    def invalidate_cache(self):
        """Invalidate product cache (call when products are updated)"""
        cache.delete(PRODUCTS_CACHE_KEY)
        self._products_cache = None
        logger.info("Product cache invalidated")
    
    def suggest_product_match(
        self, 
        supplier: Supplier, 
        description: str,
        quantity: Decimal = None,
        unit: str = None
    ) -> List[Dict]:
        """
        Multi-strategy product matching with confidence scoring
        
        Args:
            supplier: Supplier the product is from
            description: Product description from invoice
            quantity: Optional quantity for context
            unit: Optional unit for context
        
        Returns:
            List of suggestions sorted by confidence (highest first)
        """
        suggestions = []
        
        # Strategy 1: Exact previous mapping (highest confidence)
        previous_mapping = self._check_previous_mapping(supplier, description)
        if previous_mapping:
            suggestions.append({
                'product': previous_mapping.our_product,
                'product_id': previous_mapping.our_product.id,
                'product_name': previous_mapping.our_product.name,
                'department': previous_mapping.our_product.department.name,
                'confidence': 0.95,
                'reason': 'Previously mapped for this supplier',
                'times_used': previous_mapping.times_used,
                'last_cost': float(previous_mapping.our_product.supplier_cost) if previous_mapping.our_product.supplier_cost else None,
                'last_cost_unit': previous_mapping.our_product.cost_unit,
                'current_stock': float(previous_mapping.our_product.stock_level),
            })
        
        # Strategy 2: Fuzzy match on description
        fuzzy_matches = self._fuzzy_match_products(description)
        for product, score in fuzzy_matches:
            if any(s['product_id'] == product.id for s in suggestions):
                continue  # Skip duplicates
            
            suggestions.append({
                'product': product,
                'product_id': product.id,
                'product_name': product.name,
                'department': product.department.name,
                'confidence': score / 100,
                'reason': f'Name similarity: {score}%',
                'current_stock': float(product.stock_level),
                'last_cost': float(product.supplier_cost) if product.supplier_cost else None,
                'last_cost_unit': product.cost_unit,
            })
        
        # Strategy 3: Similar mappings from same supplier
        similar_mappings = self._check_similar_mappings(supplier, description)
        for mapping in similar_mappings:
            if any(s['product_id'] == mapping.our_product.id for s in suggestions):
                continue  # Skip duplicates
            
            suggestions.append({
                'product': mapping.our_product,
                'product_id': mapping.our_product.id,
                'product_name': mapping.our_product.name,
                'department': mapping.our_product.department.name,
                'confidence': 0.60,
                'reason': 'Similar product from this supplier',
                'current_stock': float(mapping.our_product.stock_level),
                'last_cost': float(mapping.our_product.supplier_cost) if mapping.our_product.supplier_cost else None,
                'last_cost_unit': mapping.our_product.cost_unit,
            })
        
        # Sort by confidence descending
        suggestions.sort(key=lambda x: x['confidence'], reverse=True)
        
        # Return top 5 suggestions
        return suggestions[:5]
    
    def _check_previous_mapping(
        self, 
        supplier: Supplier, 
        description: str
    ) -> Optional[SupplierProductMapping]:
        """Check for exact previous mapping"""
        return SupplierProductMapping.objects.filter(
            supplier=supplier,
            supplier_product_description__iexact=description,
            is_active=True
        ).select_related('our_product', 'our_product__department').first()
    
    def _fuzzy_match_products(self, description: str) -> List[tuple]:
        """
        Fuzzy match products using simple string similarity
        Returns list of (product, score) tuples
        """
        try:
            from fuzzywuzzy import fuzz
        except ImportError:
            logger.warning("fuzzywuzzy not installed, using simple matching")
            return self._simple_match_products(description)
        
        all_products = self.get_all_products()
        matches = []
        
        description_lower = description.lower()
        
        for product in all_products:
            if not product.is_active:
                continue
            
            # Calculate similarity score
            score = fuzz.partial_ratio(description_lower, product.name.lower())
            
            if score > 70:  # Only include good matches
                matches.append((product, score))
        
        # Sort by score descending
        matches.sort(key=lambda x: x[1], reverse=True)
        
        return matches[:10]  # Top 10 matches
    
    def _simple_match_products(self, description: str) -> List[tuple]:
        """
        Simple string matching (fallback if fuzzywuzzy not available)
        """
        all_products = self.get_all_products()
        matches = []
        
        description_lower = description.lower()
        words = description_lower.split()
        
        for product in all_products:
            if not product.is_active:
                continue
            
            product_name_lower = product.name.lower()
            
            # Count matching words
            matching_words = sum(1 for word in words if word in product_name_lower)
            
            if matching_words > 0:
                # Simple score: (matching_words / total_words) * 100
                score = int((matching_words / len(words)) * 100)
                matches.append((product, score))
        
        # Sort by score descending
        matches.sort(key=lambda x: x[1], reverse=True)
        
        return matches[:10]
    
    def _check_similar_mappings(
        self, 
        supplier: Supplier, 
        description: str
    ) -> List[SupplierProductMapping]:
        """Check for similar mappings from same supplier"""
        if not description:
            return []
        
        # Get first word of description for broad matching
        first_word = description.split()[0] if description.split() else description
        
        return list(SupplierProductMapping.objects.filter(
            supplier=supplier,
            supplier_product_description__icontains=first_word,
            is_active=True
        ).select_related('our_product', 'our_product__department')[:5])
    
    def record_mapping_usage(
        self, 
        mapping: SupplierProductMapping,
        actual_weight_kg: Decimal = None
    ):
        """
        Update mapping statistics when used
        Increases confidence with repeated successful use
        """
        mapping.times_used += 1
        mapping.last_used = timezone.now().date()
        
        # Update average weight if provided
        if actual_weight_kg:
            if mapping.average_weight_kg:
                # Running average
                mapping.average_weight_kg = (
                    (mapping.average_weight_kg * (mapping.times_used - 1) + actual_weight_kg) 
                    / mapping.times_used
                )
            else:
                mapping.average_weight_kg = actual_weight_kg
        
        # Increase confidence with repeated use
        if mapping.times_used > 10:
            mapping.confidence_score = min(Decimal('1.00'), mapping.confidence_score + Decimal('0.01'))
        
        mapping.save()
        
        logger.info(
            f"Updated mapping: {mapping.supplier_product_description} → "
            f"{mapping.our_product.name} (used {mapping.times_used} times, "
            f"confidence: {mapping.confidence_score})"
        )
    
    def create_or_update_mapping(
        self,
        supplier: Supplier,
        supplier_product_description: str,
        our_product: Product,
        pricing_strategy: str,
        created_by,
        package_size_kg: Decimal = None,
        units_per_package: int = None,
        notes: str = ""
    ) -> SupplierProductMapping:
        """
        Create or update a supplier product mapping
        """
        mapping, created = SupplierProductMapping.objects.update_or_create(
            supplier=supplier,
            supplier_product_description=supplier_product_description,
            defaults={
                'our_product': our_product,
                'pricing_strategy': pricing_strategy,
                'package_size_kg': package_size_kg,
                'units_per_package': units_per_package,
                'created_by': created_by,
                'notes': notes,
                'is_active': True,
                'times_used': 1 if created else F('times_used') + 1,
                'last_used': timezone.now().date(),
            }
        )
        
        if created:
            logger.info(f"Created new mapping: {supplier_product_description} → {our_product.name}")
        else:
            logger.info(f"Updated mapping: {supplier_product_description} → {our_product.name}")
        
        return mapping

