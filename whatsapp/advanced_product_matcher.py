#!/usr/bin/env python3
"""
Advanced Product Matching System with Scoring
Analyzes WhatsApp messages and matches them to products with confidence scores
"""

import json
import re
from collections import defaultdict
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

@dataclass
class MatchResult:
    product_name: str
    quantity: float
    unit: str
    packaging: Optional[str]
    weight: Optional[str]
    confidence_score: float
    match_details: Dict[str, any]

class AdvancedProductMatcher:
    def __init__(self, products_file: str = 'local_products_analysis.json'):
        """Initialize with product database"""
        with open(products_file, 'r') as f:
            self.products = json.load(f)
        
        # Build search indices
        self._build_indices()
        
        # Define regex patterns with priorities
        self.patterns = self._build_regex_patterns()
        
        # Define scoring weights
        self.scoring_weights = {
            'exact_name_match': 40,
            'partial_name_match': 25,
            'packaging_match': 15,
            'weight_match': 15,
            'unit_match': 10,
            'alias_match': 20,
            'fuzzy_match': 5
        }
    
    def _build_indices(self):
        """Build search indices for faster matching"""
        self.name_index = {}
        self.packaging_index = defaultdict(list)
        self.weight_index = defaultdict(list)
        self.unit_index = defaultdict(list)
        
        # Common aliases
        self.aliases = {
            'porta': 'portabellini',
            'blueberry': 'blueberries',
            'blue berry': 'blueberries',
            'potato': 'potatoes',
            'potatos': 'potatoes',
            'potatoe': 'potatoes',
            'semi-ripe': 'semi ripe',
            'semi ripe': 'semi-ripe',
            'avo': 'avocado',
            'avos': 'avocados',
            'mint': 'mint',
            'basil': 'basil',
            'rocket': 'wild rocket'
        }
        
        for product in self.products:
            name = product['name'].lower()
            self.name_index[name] = product
            
            # Extract packaging
            packaging_words = ['bag', 'packet', 'box', 'bunch', 'head', 'punnet', 'bulk', 'tray']
            for pkg in packaging_words:
                if pkg in name:
                    self.packaging_index[pkg].append(product)
            
            # Extract weights
            weights = re.findall(r'(\d+(?:\.\d+)?)\s*(kg|g|ml|l)', name)
            for weight_val, weight_unit in weights:
                weight_key = f"{weight_val}{weight_unit}"
                self.weight_index[weight_key].append(product)
            
            # Index by unit
            self.unit_index[product['unit']].append(product)
    
    def _build_regex_patterns(self):
        """Build comprehensive regex patterns for parsing"""
        # Units pattern
        units = r'(?:kg|g|ml|l|pcs?|pieces?|boxes?|box|bags?|bag|bunches?|bunch|heads?|head|punnets?|punnet|pun|each|packet|packets?)'
        
        patterns = [
            # Pattern 1: "3 x mint packet 100g" - Specific packet with weight
            {
                'name': 'qty_x_product_packet_weight',
                'pattern': rf'(\d+(?:\.\d+)?)\s*[x×]\s*(.+?)\s+packet\s+(\d+(?:\.\d+)?)\s*(g|kg)',
                'groups': ['quantity', 'product', 'weight_val', 'weight_unit'],
                'priority': 10,
                'handler': self._handle_packet_weight
            },
            
            # Pattern 2: "3kg carrots" - No space between quantity and unit
            {
                'name': 'qty_unit_product_nospace',
                'pattern': rf'(\d+(?:\.\d+)?)({units})\s+(.+)',
                'groups': ['quantity', 'unit', 'product'],
                'priority': 9,
                'handler': self._handle_qty_unit_product
            },
            
            # Pattern 3: "Cucumber 2 each" - Product quantity unit
            {
                'name': 'product_qty_each',
                'pattern': rf'(.+?)\s+(\d+(?:\.\d+)?)\s+each',
                'groups': ['product', 'quantity', 'unit'],
                'priority': 8,
                'handler': self._handle_product_qty_unit
            },
            
            # Pattern 4: "Potato 6" - Product quantity (no unit)
            {
                'name': 'product_qty_nounit',
                'pattern': rf'(.+?)\s+(\d+(?:\.\d+)?)$',
                'groups': ['product', 'quantity'],
                'priority': 7,
                'handler': self._handle_product_qty_nounit
            },
            
            # Pattern 5: "3 x wild rocket 500g" - Quantity x product weight
            {
                'name': 'qty_x_product_weight',
                'pattern': rf'(\d+(?:\.\d+)?)\s*[x×]\s*(.+?)\s+(\d+(?:\.\d+)?)\s*(g|kg)',
                'groups': ['quantity', 'product', 'weight_val', 'weight_unit'],
                'priority': 6,
                'handler': self._handle_qty_product_weight
            },
            
            # Pattern 6: "2 bag red onions" - Quantity packaging product
            {
                'name': 'qty_packaging_product',
                'pattern': rf'(\d+(?:\.\d+)?)\s+(bag|packet|box|bunch|head|punnet)\s+(.+)',
                'groups': ['quantity', 'packaging', 'product'],
                'priority': 5,
                'handler': self._handle_qty_packaging_product
            },
            
            # Pattern 7: "3 carrots kg" - Quantity product unit
            {
                'name': 'qty_product_unit',
                'pattern': rf'(\d+(?:\.\d+)?)\s+(.+?)\s+({units})',
                'groups': ['quantity', 'product', 'unit'],
                'priority': 4,
                'handler': self._handle_qty_product_unit
            },
            
            # Pattern 8: "carrots 3kg" - Product quantity+unit
            {
                'name': 'product_qtyunit',
                'pattern': rf'(.+?)\s+(\d+(?:\.\d+)?)({units})',
                'groups': ['product', 'quantity', 'unit'],
                'priority': 3,
                'handler': self._handle_product_qtyunit
            },
            
            # Pattern 9: Generic "3 carrots" - Quantity product
            {
                'name': 'qty_product',
                'pattern': rf'(\d+(?:\.\d+)?)\s+(.+)',
                'groups': ['quantity', 'product'],
                'priority': 2,
                'handler': self._handle_qty_product
            },
            
            # Pattern 10: Just product name
            {
                'name': 'product_only',
                'pattern': rf'(.+)',
                'groups': ['product'],
                'priority': 1,
                'handler': self._handle_product_only
            }
        ]
        
        return sorted(patterns, key=lambda x: x['priority'], reverse=True)
    
    def parse_message(self, message: str) -> List[MatchResult]:
        """Parse a WhatsApp message and return potential matches with scores"""
        message = message.strip().lower()
        results = []
        
        # Split message into lines and items
        lines = [line.strip() for line in message.split('\n') if line.strip()]
        
        for line in lines:
            # Split by common separators
            items = re.split(r'[,;]', line)
            
            for item in items:
                item = item.strip()
                if not item:
                    continue
                
                # Try each pattern
                for pattern_info in self.patterns:
                    match = re.search(pattern_info['pattern'], item, re.IGNORECASE)
                    if match:
                        try:
                            result = pattern_info['handler'](match, pattern_info)
                            if result:
                                results.append(result)
                                break  # Use first matching pattern
                        except Exception as e:
                            print(f"Error processing pattern {pattern_info['name']}: {e}")
                            continue
        
        return results
    
    def _handle_packet_weight(self, match, pattern_info) -> Optional[MatchResult]:
        """Handle: 3 x mint packet 100g"""
        quantity = float(match.group(1))
        product_name = match.group(2).strip()
        weight_val = float(match.group(3))
        weight_unit = match.group(4)
        
        # For packet items, the weight is the actual quantity
        actual_quantity = weight_val
        unit = 'packet'
        weight = f"{weight_val}{weight_unit}"
        
        return self._find_best_match(product_name, actual_quantity, unit, 'packet', weight, pattern_info)
    
    def _handle_qty_unit_product(self, match, pattern_info) -> Optional[MatchResult]:
        """Handle: 3kg carrots"""
        quantity = float(match.group(1))
        unit = match.group(2)
        product_name = match.group(3).strip()
        
        return self._find_best_match(product_name, quantity, unit, None, None, pattern_info)
    
    def _handle_product_qty_unit(self, match, pattern_info) -> Optional[MatchResult]:
        """Handle: Cucumber 2 each"""
        product_name = match.group(1).strip()
        quantity = float(match.group(2))
        unit = 'each'
        
        return self._find_best_match(product_name, quantity, unit, None, None, pattern_info)
    
    def _handle_product_qty_nounit(self, match, pattern_info) -> Optional[MatchResult]:
        """Handle: Potato 6"""
        product_name = match.group(1).strip()
        quantity = float(match.group(2))
        
        # Smart unit detection
        individual_items = ['cucumber', 'pineapple', 'watermelon', 'avocado', 'potato', 'onion']
        unit = 'each' if any(item in product_name.lower() for item in individual_items) else 'piece'
        
        return self._find_best_match(product_name, quantity, unit, None, None, pattern_info)
    
    def _handle_qty_product_weight(self, match, pattern_info) -> Optional[MatchResult]:
        """Handle: 3 x wild rocket 500g"""
        quantity = float(match.group(1))
        product_name = match.group(2).strip()
        weight_val = float(match.group(3))
        weight_unit = match.group(4)
        
        weight = f"{weight_val}{weight_unit}"
        unit = 'g' if weight_unit == 'g' else weight_unit
        
        return self._find_best_match(product_name, weight_val, unit, None, weight, pattern_info)
    
    def _handle_qty_packaging_product(self, match, pattern_info) -> Optional[MatchResult]:
        """Handle: 2 bag red onions"""
        quantity = float(match.group(1))
        packaging = match.group(2)
        product_name = match.group(3).strip()
        
        return self._find_best_match(product_name, quantity, packaging, packaging, None, pattern_info)
    
    def _handle_qty_product_unit(self, match, pattern_info) -> Optional[MatchResult]:
        """Handle: 3 carrots kg"""
        quantity = float(match.group(1))
        product_name = match.group(2).strip()
        unit = match.group(3)
        
        return self._find_best_match(product_name, quantity, unit, None, None, pattern_info)
    
    def _handle_product_qtyunit(self, match, pattern_info) -> Optional[MatchResult]:
        """Handle: carrots 3kg"""
        product_name = match.group(1).strip()
        quantity = float(match.group(2))
        unit = match.group(3)
        
        return self._find_best_match(product_name, quantity, unit, None, None, pattern_info)
    
    def _handle_qty_product(self, match, pattern_info) -> Optional[MatchResult]:
        """Handle: 3 carrots"""
        quantity = float(match.group(1))
        product_name = match.group(2).strip()
        
        return self._find_best_match(product_name, quantity, 'piece', None, None, pattern_info)
    
    def _handle_product_only(self, match, pattern_info) -> Optional[MatchResult]:
        """Handle: carrots"""
        product_name = match.group(1).strip()
        
        return self._find_best_match(product_name, 1.0, 'piece', None, None, pattern_info)
    
    def _find_best_match(self, product_name: str, quantity: float, unit: str, 
                        packaging: Optional[str], weight: Optional[str], 
                        pattern_info: Dict) -> Optional[MatchResult]:
        """Find the best matching product with confidence score"""
        
        # Apply aliases
        normalized_name = self._apply_aliases(product_name.lower())
        
        candidates = []
        
        # 1. Exact name matches
        for product in self.products:
            score = self._calculate_match_score(
                product, normalized_name, quantity, unit, packaging, weight, pattern_info
            )
            if score > 0:
                candidates.append((product, score))
        
        if not candidates:
            return None
        
        # Sort by score and return best match
        candidates.sort(key=lambda x: x[1], reverse=True)
        best_product, best_score = candidates[0]
        
        # Only return matches above minimum threshold
        if best_score < 30:  # Minimum 30% confidence
            return None
        
        return MatchResult(
            product_name=best_product['name'],
            quantity=quantity,
            unit=unit,
            packaging=packaging,
            weight=weight,
            confidence_score=best_score,
            match_details={
                'pattern': pattern_info['name'],
                'original_input': product_name,
                'normalized_input': normalized_name,
                'matched_product_id': best_product['id'],
                'score_breakdown': self._get_score_breakdown(
                    best_product, normalized_name, quantity, unit, packaging, weight
                )
            }
        )
    
    def _apply_aliases(self, product_name: str) -> str:
        """Apply product name aliases"""
        # Handle special cases first
        if 'sweet potato' in product_name:
            return product_name  # Don't alias sweet potato
        
        for alias, canonical in self.aliases.items():
            if alias in product_name:
                product_name = product_name.replace(alias, canonical)
        
        return product_name
    
    def _calculate_match_score(self, product: Dict, normalized_name: str, 
                             quantity: float, unit: str, packaging: Optional[str], 
                             weight: Optional[str], pattern_info: Dict) -> float:
        """Calculate match confidence score (0-100)"""
        
        product_name_lower = product['name'].lower()
        score = 0
        
        # Name matching
        if normalized_name == product_name_lower:
            score += self.scoring_weights['exact_name_match']
        elif normalized_name in product_name_lower or product_name_lower in normalized_name:
            score += self.scoring_weights['partial_name_match']
        elif self._fuzzy_match(normalized_name, product_name_lower):
            score += self.scoring_weights['fuzzy_match']
        else:
            return 0  # No name match, skip
        
        # Unit matching
        if unit == product['unit']:
            score += self.scoring_weights['unit_match']
        elif self._compatible_units(unit, product['unit']):
            score += self.scoring_weights['unit_match'] * 0.7
        
        # Packaging matching
        if packaging:
            if packaging in product_name_lower:
                score += self.scoring_weights['packaging_match']
        
        # Weight matching
        if weight:
            if weight in product_name_lower:
                score += self.scoring_weights['weight_match']
            elif self._similar_weight(weight, product_name_lower):
                score += self.scoring_weights['weight_match'] * 0.8
        
        # Pattern priority bonus
        score += pattern_info['priority'] * 2
        
        return min(score, 100)  # Cap at 100
    
    def _fuzzy_match(self, name1: str, name2: str) -> bool:
        """Simple fuzzy matching"""
        words1 = set(name1.split())
        words2 = set(name2.split())
        
        # Check if at least 50% of words match
        if not words1 or not words2:
            return False
        
        intersection = words1.intersection(words2)
        return len(intersection) / max(len(words1), len(words2)) >= 0.5
    
    def _compatible_units(self, unit1: str, unit2: str) -> bool:
        """Check if units are compatible"""
        compatible_groups = [
            {'kg', 'g'},
            {'ml', 'l'},
            {'piece', 'each', 'pcs'},
            {'bag', 'packet'},
            {'box', 'tray'}
        ]
        
        for group in compatible_groups:
            if unit1 in group and unit2 in group:
                return True
        
        return unit1 == unit2
    
    def _similar_weight(self, weight: str, product_name: str) -> bool:
        """Check for similar weights in product name"""
        # Extract numbers from weight
        weight_nums = re.findall(r'\d+(?:\.\d+)?', weight)
        product_nums = re.findall(r'\d+(?:\.\d+)?', product_name)
        
        return bool(set(weight_nums).intersection(set(product_nums)))
    
    def _get_score_breakdown(self, product: Dict, normalized_name: str, 
                           quantity: float, unit: str, packaging: Optional[str], 
                           weight: Optional[str]) -> Dict:
        """Get detailed score breakdown for debugging"""
        breakdown = {}
        
        product_name_lower = product['name'].lower()
        
        if normalized_name == product_name_lower:
            breakdown['exact_name_match'] = self.scoring_weights['exact_name_match']
        elif normalized_name in product_name_lower or product_name_lower in normalized_name:
            breakdown['partial_name_match'] = self.scoring_weights['partial_name_match']
        
        if unit == product['unit']:
            breakdown['unit_match'] = self.scoring_weights['unit_match']
        
        if packaging and packaging in product_name_lower:
            breakdown['packaging_match'] = self.scoring_weights['packaging_match']
        
        if weight and weight in product_name_lower:
            breakdown['weight_match'] = self.scoring_weights['weight_match']
        
        return breakdown

def main():
    """Test the advanced matcher"""
    matcher = AdvancedProductMatcher()
    
    # Test cases
    test_messages = [
        "3kg carrots",
        "3 x mint packet 100g",
        "Cucumber 2 each",
        "Potato 6",
        "2 bag red onions",
        "wild rocket 500g",
        "porta mushrooms",
        "blueberry punnet",
        "semi-ripe avocados 3",
        "Red onions 2bag (18kg)"
    ]
    
    print("=== ADVANCED PRODUCT MATCHING TEST ===\n")
    
    for message in test_messages:
        print(f"Input: '{message}'")
        results = matcher.parse_message(message)
        
        if results:
            for result in results:
                print(f"  ✓ Match: {result.product_name}")
                print(f"    Quantity: {result.quantity} {result.unit}")
                print(f"    Confidence: {result.confidence_score:.1f}%")
                print(f"    Pattern: {result.match_details['pattern']}")
                if result.match_details['score_breakdown']:
                    print(f"    Score breakdown: {result.match_details['score_breakdown']}")
        else:
            print("  ✗ No matches found")
        
        print()

if __name__ == "__main__":
    main()
