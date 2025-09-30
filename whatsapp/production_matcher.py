#!/usr/bin/env python3
"""
Production-Optimized Product Matcher
Specifically tuned for the 210 production products with enhanced scoring and aliases
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

class ProductionMatcher:
    def __init__(self):
        """Initialize with production products"""
        # Load production products
        try:
            with open('production_products_analysis.json', 'r') as f:
                self.products = json.load(f)
        except FileNotFoundError:
            # Fallback to local products if production file not found
            with open('local_products_analysis.json', 'r') as f:
                self.products = json.load(f)
        
        # Build search indices
        self._build_indices()
        
        # Define regex patterns with priorities
        self.patterns = self._build_regex_patterns()
        
        # Production-optimized scoring weights
        self.scoring_weights = {
            'exact_name_match': 45,
            'partial_name_match': 30,
            'packaging_match': 20,
            'weight_match': 20,
            'unit_match': 15,
            'alias_match': 25,
            'fuzzy_match': 10
        }
    
    def _build_indices(self):
        """Build search indices for faster matching"""
        self.name_index = {}
        self.packaging_index = defaultdict(list)
        self.weight_index = defaultdict(list)
        self.unit_index = defaultdict(list)
        
        # Production-optimized aliases based on analysis
        self.aliases = {
            # Basic aliases
            'porta': 'portabellini',
            'blueberry': 'blueberries',
            'blue berry': 'blueberries',
            'potato': 'potatoes',
            'potatos': 'potatoes',
            'potatoe': 'potatoes',
            'semi-ripe': 'semi ripe',
            'semi ripe': 'semi-ripe',
            'avo': 'avocados',
            'avos': 'avocados',
            
            # Production-specific aliases
            'aubergine': 'aubergine',
            'eggplant': 'aubergine',
            'brinjal': 'aubergine',
            'cuke': 'cucumber',
            'cukes': 'cucumber',
            'carrot': 'carrots',
            'coriander': 'coriander',
            'cilantro': 'coriander',
            'dhania': 'coriander',
            'hard avo': 'avocados (hard)',
            'ripe avo': 'avocados (soft)',
            'semi ripe avo': 'avocados (semi-ripe)',
            'egg': 'eggs',
            'large eggs': 'eggs (large)',
            'jumbo eggs': 'eggs (jumbo)',
            'tomatoe': 'tomatoes',
            'onion': 'onions',
            'mushroom': 'mushrooms',
            'pepper': 'peppers',
            'pkt': 'packet',
            'pckt': 'packet',
            'pk': 'packet',
        }
        
        for product in self.products:
            name = product['name'].lower()
            self.name_index[name] = product
            
            # Extract packaging
            packaging_words = ['bag', 'packet', 'box', 'bunch', 'head', 'punnet', 'bulk', 'tray', 'pack']
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
        units = r'(?:kg|g|ml|l|pcs?|pieces?|boxes?|box|bags?|bag|bunches?|bunch|heads?|head|punnets?|punnet|pun|each|packet|packets?|pack|packs?)'
        
        patterns = [
            # High priority patterns for production data
            {
                'name': 'qty_star_packet_product_weight',
                'pattern': rf'(\d+(?:\.\d+)?)\s*[*×x]\s*packet\s+(.+?)\s+(\d+(?:\.\d+)?)\s*(g|kg)',
                'groups': ['quantity', 'product', 'weight_val', 'weight_unit'],
                'priority': 11,
                'handler': self._handle_packet_weight
            },
            {
                'name': 'packet_product_weight',
                'pattern': rf'packet\s+(.+?)\s+(\d+(?:\.\d+)?)\s*(g|kg)',
                'groups': ['product', 'weight_val', 'weight_unit'],
                'priority': 10,
                'handler': self._handle_packet_product_weight
            },
            {
                'name': 'qty_x_product_packet_weight',
                'pattern': rf'(\d+(?:\.\d+)?)\s*[x×]\s*(.+?)\s+packet\s+(\d+(?:\.\d+)?)\s*(g|kg)',
                'groups': ['quantity', 'product', 'weight_val', 'weight_unit'],
                'priority': 9,
                'handler': self._handle_packet_weight
            },
            {
                'name': 'qty_unit_product_nospace',
                'pattern': rf'(\d+(?:\.\d+)?)({units})\s+(.+)',
                'groups': ['quantity', 'unit', 'product'],
                'priority': 9,
                'handler': self._handle_qty_unit_product
            },
            {
                'name': 'product_qty_each',
                'pattern': rf'(.+?)\s+(\d+(?:\.\d+)?)\s+each',
                'groups': ['product', 'quantity', 'unit'],
                'priority': 8,
                'handler': self._handle_product_qty_unit
            },
            {
                'name': 'product_qty_nounit',
                'pattern': rf'(.+?)\s+(\d+(?:\.\d+)?)$',
                'groups': ['product', 'quantity'],
                'priority': 7,
                'handler': self._handle_product_qty_nounit
            },
            {
                'name': 'qty_packaging_product',
                'pattern': rf'(\d+(?:\.\d+)?)\s+(bag|packet|box|bunch|head|punnet|pack)\s+(.+)',
                'groups': ['quantity', 'packaging', 'product'],
                'priority': 6,
                'handler': self._handle_qty_packaging_product
            },
            {
                'name': 'product_qtyunit',
                'pattern': rf'(.+?)\s+(\d+(?:\.\d+)?)({units})',
                'groups': ['product', 'quantity', 'unit'],
                'priority': 5,
                'handler': self._handle_product_qtyunit
            },
            {
                'name': 'qty_product_unit',
                'pattern': rf'(\d+(?:\.\d+)?)\s+(.+?)\s+({units})',
                'groups': ['quantity', 'product', 'unit'],
                'priority': 4,
                'handler': self._handle_qty_product_unit
            },
            {
                'name': 'qty_product',
                'pattern': rf'(\d+(?:\.\d+)?)\s+(.+)',
                'groups': ['quantity', 'product'],
                'priority': 3,
                'handler': self._handle_qty_product
            },
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
        # Format weight without decimal if it's a whole number
        if weight_val == int(weight_val):
            weight = f"{int(weight_val)}{weight_unit}"
        else:
            weight = f"{weight_val}{weight_unit}"
        
        return self._find_best_match(product_name, actual_quantity, unit, 'packet', weight, pattern_info)
    
    def _handle_packet_product_weight(self, match, pattern_info) -> Optional[MatchResult]:
        """Handle: packet rosemary 200g"""
        product_name = match.group(1).strip()
        weight_val = float(match.group(2))
        weight_unit = match.group(3)
        
        # For packet items, the weight is the actual quantity
        actual_quantity = weight_val
        unit = 'packet'
        # Format weight without decimal if it's a whole number
        if weight_val == int(weight_val):
            weight = f"{int(weight_val)}{weight_unit}"
        else:
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
        
        # Smart unit detection based on production data
        individual_items = ['cucumber', 'pineapple', 'watermelon', 'avocado', 'potato', 'onion', 'aubergine', 'egg']
        unit = 'each' if any(item in product_name.lower() for item in individual_items) else 'piece'
        
        return self._find_best_match(product_name, quantity, unit, None, None, pattern_info)
    
    def _handle_qty_packaging_product(self, match, pattern_info) -> Optional[MatchResult]:
        """Handle: 2 bag red onions"""
        quantity = float(match.group(1))
        packaging = match.group(2)
        product_name = match.group(3).strip()
        
        return self._find_best_match(product_name, quantity, packaging, packaging, None, pattern_info)
    
    def _handle_product_qtyunit(self, match, pattern_info) -> Optional[MatchResult]:
        """Handle: carrots 3kg"""
        product_name = match.group(1).strip()
        quantity = float(match.group(2))
        unit = match.group(3)
        
        return self._find_best_match(product_name, quantity, unit, None, None, pattern_info)
    
    def _handle_qty_product_unit(self, match, pattern_info) -> Optional[MatchResult]:
        """Handle: 3 carrots kg"""
        quantity = float(match.group(1))
        product_name = match.group(2).strip()
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
        
        # For packet products with specific weights, prioritize exact weight matches
        if unit == 'packet' and weight:
            # First, look for exact weight matches in packet products
            weight_candidates = []
            for product in self.products:
                if product['unit'] == 'packet' and weight in product['name'].lower():
                    if normalized_name in product['name'].lower() or product['name'].lower() in normalized_name:
                        score = self._calculate_match_score(
                            product, normalized_name, quantity, unit, packaging, weight, pattern_info
                        )
                        # Boost score for exact weight + packet matches
                        score += 25  # Extra boost for exact weight packet matches
                        weight_candidates.append((product, score))
            
            if weight_candidates:
                candidates.extend(weight_candidates)
        
        # Score all products (including non-weight matches)
        for product in self.products:
            score = self._calculate_match_score(
                product, normalized_name, quantity, unit, packaging, weight, pattern_info
            )
            if score > 0:
                # Avoid duplicates from weight matching above
                if not any(p[0]['id'] == product['id'] for p in candidates):
                    candidates.append((product, score))
        
        if not candidates:
            return None
        
        # Sort by score and return best match
        candidates.sort(key=lambda x: x[1], reverse=True)
        best_product, best_score = candidates[0]
        
        # Production threshold: 25% minimum (lower for better coverage)
        if best_score < 25:
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
        
        # Name matching (most important)
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
        if packaging and packaging in product_name_lower:
            score += self.scoring_weights['packaging_match']
        
        # Weight matching
        if weight and weight in product_name_lower:
            score += self.scoring_weights['weight_match']
        elif weight and self._similar_weight(weight, product_name_lower):
            score += self.scoring_weights['weight_match'] * 0.8
        
        # Pattern priority bonus
        score += pattern_info['priority'] * 2
        
        return min(score, 100)  # Cap at 100
    
    def _fuzzy_match(self, name1: str, name2: str) -> bool:
        """Simple fuzzy matching"""
        words1 = set(name1.split())
        words2 = set(name2.split())
        
        if not words1 or not words2:
            return False
        
        intersection = words1.intersection(words2)
        return len(intersection) / max(len(words1), len(words2)) >= 0.4  # Lower threshold for production
    
    def _compatible_units(self, unit1: str, unit2: str) -> bool:
        """Check if units are compatible"""
        compatible_groups = [
            {'kg', 'g'},
            {'ml', 'l'},
            {'piece', 'each', 'pcs'},
            {'bag', 'packet', 'pack'},
            {'box', 'tray'}
        ]
        
        for group in compatible_groups:
            if unit1 in group and unit2 in group:
                return True
        
        return unit1 == unit2
    
    def _similar_weight(self, weight: str, product_name: str) -> bool:
        """Check for similar weights in product name"""
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

# Global instance for use in Django
_production_matcher = None

def get_production_matcher():
    """Get singleton production matcher instance"""
    global _production_matcher
    if _production_matcher is None:
        _production_matcher = ProductionMatcher()
    return _production_matcher
