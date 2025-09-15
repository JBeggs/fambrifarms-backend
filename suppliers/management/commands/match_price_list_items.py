from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q
from suppliers.models import SupplierPriceList, SupplierPriceListItem
from products.models import Product
from difflib import SequenceMatcher
import re


class Command(BaseCommand):
    help = 'Match supplier price list items to existing products using fuzzy matching'

    def add_arguments(self, parser):
        parser.add_argument(
            '--price-list-id',
            type=int,
            help='Match items for a specific price list ID',
        )
        parser.add_argument(
            '--min-confidence',
            type=float,
            default=0.7,
            help='Minimum confidence score for automatic matching (0.0-1.0, default: 0.7)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show matches without saving them',
        )

    def handle(self, *args, **options):
        min_confidence = options['min_confidence']
        dry_run = options['dry_run']
        price_list_id = options.get('price_list_id')

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be saved'))

        # Get price lists to process
        if price_list_id:
            try:
                price_lists = [SupplierPriceList.objects.get(id=price_list_id)]
            except SupplierPriceList.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'Price list with ID {price_list_id} not found'))
                return
        else:
            price_lists = SupplierPriceList.objects.filter(is_processed=False)

        if not price_lists:
            self.stdout.write(self.style.WARNING('No unprocessed price lists found'))
            return

        # Get all products for matching
        products = list(Product.objects.all().select_related('department'))
        self.stdout.write(f'Loaded {len(products)} products for matching')

        total_matched = 0
        total_items = 0

        for price_list in price_lists:
            self.stdout.write(f'\nProcessing price list: {price_list}')
            
            items = price_list.items.filter(matched_product__isnull=True)
            matched_count = 0
            
            with transaction.atomic():
                for item in items:
                    total_items += 1
                    
                    # Find best match
                    best_match, confidence = self.find_best_match(item, products)
                    
                    if best_match and confidence >= min_confidence:
                        if not dry_run:
                            item.matched_product = best_match
                            item.match_confidence = round(confidence * 100, 2)
                            item.match_method = 'automatic_fuzzy'
                            item.save()
                        
                        matched_count += 1
                        total_matched += 1
                        
                        self.stdout.write(
                            f'  ✓ "{item.product_description}" → "{best_match.name}" '
                            f'(confidence: {confidence:.2%})'
                        )
                    else:
                        if not dry_run:
                            item.needs_review = True
                            item.save()
                        
                        self.stdout.write(
                            f'  ? "{item.product_description}" - No good match found '
                            f'(best: {confidence:.2%} - {best_match.name if best_match else "None"})'
                        )

            # Update price list statistics
            if not dry_run:
                self.update_price_list_stats(price_list)
            
            self.stdout.write(f'  Matched {matched_count}/{len(items)} items for this price list')

        self.stdout.write(
            self.style.SUCCESS(
                f'\nMatching complete: {total_matched}/{total_items} items matched '
                f'({total_matched/total_items:.1%} success rate)' if total_items > 0 else '\nNo items to process'
            )
        )

    def find_best_match(self, price_list_item, products):
        """Find the best matching product for a price list item"""
        description = price_list_item.product_description.lower().strip()
        
        # Clean the description
        cleaned_description = self.clean_product_description(description)
        
        best_match = None
        best_confidence = 0.0
        
        for product in products:
            confidence = self.calculate_match_confidence(cleaned_description, product)
            
            if confidence > best_confidence:
                best_confidence = confidence
                best_match = product
        
        return best_match, best_confidence

    def clean_product_description(self, description):
        """Clean product description for better matching"""
        # Remove common prefixes/suffixes that might interfere with matching
        description = re.sub(r'^\d+\s*[xX×]\s*', '', description)  # Remove quantity prefixes like "5x"
        description = re.sub(r'^\d+\s*(kg|g|ml|l|pcs?|pieces?|box|boxes?|bag|bags?)\s+', '', description, flags=re.IGNORECASE)
        description = re.sub(r'\s+\d+\s*(kg|g|ml|l|pcs?|pieces?|box|boxes?|bag|bags?)$', '', description, flags=re.IGNORECASE)
        
        # Remove extra whitespace
        description = ' '.join(description.split())
        
        return description

    def calculate_match_confidence(self, description, product):
        """Calculate confidence score for matching a description to a product"""
        product_name = product.name.lower().strip()
        
        # Exact match gets highest score
        if description == product_name:
            return 1.0
        
        # Check common names if available
        if hasattr(product, 'common_names') and product.common_names:
            for common_name in product.common_names:
                if description == common_name.lower().strip():
                    return 0.95
        
        # Use sequence matcher for fuzzy matching
        base_confidence = SequenceMatcher(None, description, product_name).ratio()
        
        # Boost confidence for partial word matches
        description_words = set(description.split())
        product_words = set(product_name.split())
        
        if description_words and product_words:
            word_overlap = len(description_words.intersection(product_words))
            word_boost = word_overlap / max(len(description_words), len(product_words))
            base_confidence = max(base_confidence, word_boost * 0.8)
        
        # Boost confidence if key words match
        key_words = ['tomato', 'onion', 'potato', 'carrot', 'lettuce', 'mushroom', 
                    'pepper', 'cucumber', 'spinach', 'broccoli', 'cauliflower',
                    'lemon', 'avocado', 'strawberry', 'pineapple', 'mint', 'parsley']
        
        for key_word in key_words:
            if key_word in description and key_word in product_name:
                base_confidence += 0.1
                break
        
        # Penalize if category codes don't match (if available)
        if hasattr(product, 'category') and price_list_item.category_code:
            # This would need to be implemented based on your category system
            pass
        
        return min(base_confidence, 1.0)

    def update_price_list_stats(self, price_list):
        """Update statistics for a price list"""
        items = price_list.items.all()
        total_items = items.count()
        matched_items = items.filter(matched_product__isnull=False).count()
        unmatched_items = total_items - matched_items
        
        price_list.total_items = total_items
        price_list.matched_items = matched_items
        price_list.unmatched_items = unmatched_items
        
        # Mark as processed if all items are either matched or flagged for review
        unprocessed_items = items.filter(
            matched_product__isnull=True,
            needs_review=False
        ).count()
        
        if unprocessed_items == 0:
            price_list.is_processed = True
        
        price_list.save()
