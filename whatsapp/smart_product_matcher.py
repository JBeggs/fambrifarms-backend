#!/usr/bin/env python3
"""
Smart Product Matcher - Database-Driven Approach
Dynamically analyzes message components instead of hardcoded regex patterns
"""

import re
import json
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass
from django.db.models import Q
from products.models import Product

@dataclass
class ParsedMessage:
    quantity: float
    unit: Optional[str]
    product_name: str
    extra_descriptions: List[str]
    original_message: str

@dataclass
class SmartMatchResult:
    product: Product
    quantity: float
    unit: str
    confidence_score: float
    match_details: Dict[str, any]

@dataclass
class SmartMatchSuggestions:
    best_match: Optional[SmartMatchResult]
    suggestions: List[SmartMatchResult]
    parsed_input: ParsedMessage
    total_candidates: int

class SmartProductMatcher:
    def __init__(self):
        """Initialize with dynamic database analysis"""
        # Initialize scoring weights
        self.scoring_weights = {
            'exact_name_match': 50,
            'partial_name_match': 30,
            'fuzzy_match': 15,
            'unit_match': 20,
            'weight_match': 15,
            'quantity_match': 10,
            'alias_match': 25
        }
        
        self._load_database_info()
        self._build_aliases()
    
    def _load_database_info(self):
        """Load and analyze all products from database and production data"""
        # Try to load production products first
        production_products = self._load_production_products()
        
        if production_products:
            print(f"Using production products data ({len(production_products)} products)")
            all_products_data = production_products
        else:
            print("Using local database products")
            # Fallback to local database
            all_products = Product.objects.all()
            all_products_data = [
                {
                    'id': p.id,
                    'name': p.name,
                    'unit': p.unit,
                    'price': float(p.price) if p.price else 0.0
                }
                for p in all_products
            ]
        
        # Extract all unique units
        self.valid_units = set()
        self.container_units = set()
        self.weight_units = set()
        
        # Extract product names and descriptions
        self.product_names = set()
        self.product_descriptions = {}  # product_name -> list of descriptions
        
        for product_data in all_products_data:
            unit = product_data['unit'].lower()
            
            # Add unit
            self.valid_units.add(unit)
            
            # Categorize units
            if unit in ['bag', 'packet', 'box', 'bunch', 'head', 'punnet', 'tray', 'pack']:
                self.container_units.add(unit)
            elif unit in ['kg', 'g', 'ml', 'l']:
                self.weight_units.add(unit)
            
            # Extract base product name and descriptions
            name = product_data['name']
            base_name, descriptions = self._extract_name_and_descriptions(name)
            
            self.product_names.add(base_name.lower())
            
            if base_name.lower() not in self.product_descriptions:
                self.product_descriptions[base_name.lower()] = set()
            
            for desc in descriptions:
                self.product_descriptions[base_name.lower()].add(desc.lower())
        
        print(f"Loaded {len(all_products_data)} products")
        print(f"Found {len(self.valid_units)} units: {sorted(self.valid_units)}")
        print(f"Found {len(self.container_units)} container units: {sorted(self.container_units)}")
        print(f"Found {len(self.product_names)} unique product names")
    
    def _load_production_products(self):
        """Load production products from JSON file"""
        import os
        import json
        
        # Try different possible locations for the production products file
        possible_paths = [
            'data/production_products_analysis.json',
            'production_products_analysis.json',
            'whatsapp/production_products_analysis.json',
            os.path.join(os.path.dirname(__file__), 'production_products_analysis.json'),
            os.path.join(os.path.dirname(__file__), '..', 'data', 'production_products_analysis.json'),
        ]
        
        for path in possible_paths:
            try:
                if os.path.exists(path):
                    with open(path, 'r') as f:
                        products = json.load(f)
                    print(f"✓ Loaded production products from: {path}")
                    return products
            except Exception as e:
                print(f"Failed to load from {path}: {e}")
                continue
        
        print("⚠ Production products file not found, using local database")
        return None
    
    def _extract_name_and_descriptions(self, product_name: str) -> Tuple[str, List[str]]:
        """Extract base name and descriptions from product name"""
        # Extract content in parentheses as descriptions
        descriptions = re.findall(r'\(([^)]+)\)', product_name)
        
        # Remove parentheses content to get base name
        base_name = re.sub(r'\s*\([^)]+\)', '', product_name).strip()
        
        return base_name, descriptions
    
    def _build_aliases(self):
        """Build aliases based on common variations"""
        self.aliases = {
            # Common misspellings
            'tomatoe': 'tomato',
            'potatoe': 'potato',
            'onion': 'onions',
            
            # Singular/plural variations
            'carrot': 'carrots',
            'pepper': 'peppers',
            'mushroom': 'mushrooms',
            
            # Alternative names
            'aubergine': 'aubergine',
            'eggplant': 'aubergine',
            'brinjal': 'aubergine',
            'cuke': 'cucumber',
            'cukes': 'cucumber',
            'avo': 'avocado',
            'avos': 'avocados',
            
            # Herb variations
            'coriander': 'coriander',
            'cilantro': 'coriander',
            'dhania': 'coriander',
            
            # Unit aliases
            'pkt': 'packet',
            'pckt': 'packet',
            'pk': 'packet',
            'pcs': 'piece',
            'pc': 'piece',
        }
    
    def parse_message(self, message: str) -> List[ParsedMessage]:
        """Parse message into components using space splitting"""
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
                
                parsed = self._parse_single_item(item)
                if parsed:
                    results.append(parsed)
        
        return results
    
    def _parse_single_item(self, item: str) -> Optional[ParsedMessage]:
        """Parse a single item using space splitting approach"""
        # Clean the item
        item = re.sub(r'[*×x]', ' ', item)  # Replace multipliers with spaces
        words = item.split()
        
        if not words:
            return None
        
        # Step 1: Find all numbers and their contexts
        numbers_found = []
        for i, word in enumerate(words):
            number_match = re.search(r'(\d+(?:\.\d+)?)', word)
            if number_match:
                numbers_found.append({
                    'value': float(number_match.group(1)),
                    'word': word,
                    'index': i,
                    'is_standalone': word == number_match.group(1)
                })
        
        # Step 2: Find unit/container words
        unit = None
        unit_word = None
        unit_index = -1
        
        for i, word in enumerate(words):
            # Check direct unit match
            if word in self.valid_units:
                unit = word
                unit_word = word
                unit_index = i
                break
            
            # Check unit aliases
            if word in self.aliases and self.aliases[word] in self.valid_units:
                unit = self.aliases[word]
                unit_word = word
                unit_index = i
                break
        
        # Step 3: Determine quantity and extra descriptions
        quantity = 1.0
        extra_descriptions = []
        words_to_remove = []
        
        if numbers_found:
            if len(numbers_found) == 1:
                num_info = numbers_found[0]
                
                # If we already found a unit (like "packet"), and this number is standalone, use it as quantity
                if unit_index != -1 and num_info['is_standalone']:
                    quantity = num_info['value']
                    words_to_remove.append(num_info['word'])
                
                # If the number is part of a word with unit (like "200g"), handle specially
                elif not num_info['is_standalone']:
                    # Check if this word contains a unit
                    found_unit_in_word = False
                    for valid_unit in self.valid_units:
                        if num_info['word'].endswith(valid_unit):
                            # If we don't have a unit yet, this becomes the unit
                            if unit_index == -1:
                                unit = valid_unit
                                quantity = num_info['value']
                                words_to_remove.append(num_info['word'])
                            else:
                                # We already have a unit, so this is a description
                                extra_descriptions.append(num_info['word'])
                                words_to_remove.append(num_info['word'])
                            found_unit_in_word = True
                            break
                    
                    # If no unit found in word, treat as regular quantity
                    if not found_unit_in_word:
                        quantity = num_info['value']
                        words_to_remove.append(num_info['word'])
                
                # Standalone number without existing unit
                else:
                    quantity = num_info['value']
                    words_to_remove.append(num_info['word'])
            else:
                # Multiple numbers - first standalone number is quantity, others are descriptions
                standalone_numbers = [n for n in numbers_found if n['is_standalone']]
                
                if standalone_numbers:
                    # Use first standalone number as quantity
                    quantity = standalone_numbers[0]['value']
                    words_to_remove.append(standalone_numbers[0]['word'])
                    
                    # Other numbers become descriptions
                    for num_info in numbers_found:
                        if num_info != standalone_numbers[0]:
                            extra_descriptions.append(num_info['word'])
                            words_to_remove.append(num_info['word'])
                else:
                    # No standalone numbers - use first number as quantity
                    quantity = numbers_found[0]['value']
                    words_to_remove.append(numbers_found[0]['word'])
                    
                    # Check if first number word contains unit
                    first_word = numbers_found[0]['word']
                    for valid_unit in self.valid_units:
                        if first_word.endswith(valid_unit) and unit_index == -1:
                            unit = valid_unit
                            extra_descriptions.append(first_word)
                            break
                    
                    # Other numbers become descriptions
                    for num_info in numbers_found[1:]:
                        extra_descriptions.append(num_info['word'])
                        words_to_remove.append(num_info['word'])
        
        # Step 4: Remove processed words
        if unit_word:
            words_to_remove.append(unit_word)
        
        remaining_words = [w for w in words if w not in words_to_remove]
        
        if not remaining_words:
            return None
        
        # Step 5: Build product name
        product_name = ' '.join(remaining_words)
        product_name = self._apply_aliases(product_name)
        
        return ParsedMessage(
            quantity=quantity,
            unit=unit,
            product_name=product_name,
            extra_descriptions=extra_descriptions,
            original_message=item
        )
    
    def _apply_aliases(self, product_name: str) -> str:
        """Apply aliases to product name"""
        # Handle special cases first
        if 'sweet potato' in product_name:
            return product_name  # Don't alias sweet potato
        
        # Apply word-level aliases (not substring replacement)
        words = product_name.split()
        result_words = []
        
        for word in words:
            if word in self.aliases:
                result_words.append(self.aliases[word])
            else:
                result_words.append(word)
        
        return ' '.join(result_words)
    
    def find_matches(self, parsed_message: ParsedMessage) -> List[SmartMatchResult]:
        """Find matching products using production data or Django Q queries"""
        product_name = parsed_message.product_name
        quantity = parsed_message.quantity
        unit = parsed_message.unit
        extra_descriptions = parsed_message.extra_descriptions
        
        # Try to use production data first
        production_products = self._load_production_products()
        
        if production_products:
            return self._find_matches_from_data(parsed_message, production_products)
        else:
            return self._find_matches_from_database(parsed_message)
    
    def _find_matches_from_data(self, parsed_message: ParsedMessage, products_data: List[Dict]) -> List[SmartMatchResult]:
        """Find matches from production data"""
        product_name = parsed_message.product_name
        quantity = parsed_message.quantity
        unit = parsed_message.unit
        extra_descriptions = parsed_message.extra_descriptions
        
        # Split product name into words for flexible matching
        name_words = product_name.split()
        
        candidates = []
        
        # Filter products based on name matching
        for product_data in products_data:
            product_name_lower = product_data['name'].lower()
            
            # Check if any word matches or full name matches
            name_match = False
            if product_name.lower() in product_name_lower or product_name_lower in product_name.lower():
                name_match = True
            else:
                for word in name_words:
                    if word.lower() in product_name_lower:
                        name_match = True
                        break
            
            if name_match:
                candidates.append(product_data)
        
        # Filter by unit if specified
        if unit and candidates:
            unit_candidates = [p for p in candidates if p['unit'].lower() == unit.lower()]
            if unit_candidates:
                candidates = unit_candidates
        
        # Filter by extra descriptions
        if extra_descriptions and candidates:
            for desc in extra_descriptions:
                desc_candidates = [p for p in candidates if desc.lower() in p['name'].lower()]
                if desc_candidates:
                    candidates = desc_candidates
                    break
        
        # Score and rank candidates
        results = []
        for product_data in candidates:
            score = self._calculate_score_from_data(product_data, parsed_message)
            if score > 0:
                # Create a mock product object for compatibility
                mock_product = type('MockProduct', (), {
                    'id': product_data['id'],
                    'name': product_data['name'],
                    'unit': product_data['unit'],
                    'price': product_data.get('price', 0)
                })()
                
                results.append(SmartMatchResult(
                    product=mock_product,
                    quantity=quantity,
                    unit=unit or product_data['unit'],
                    confidence_score=score,
                    match_details={
                        'parsed_name': product_name,
                        'matched_name': product_data['name'],
                        'unit_match': unit == product_data['unit'] if unit else False,
                        'description_matches': [d for d in extra_descriptions if d in product_data['name'].lower()],
                        'name_word_matches': [w for w in name_words if w in product_data['name'].lower()]
                    }
                ))
        
        # Sort by confidence score
        results.sort(key=lambda x: x.confidence_score, reverse=True)
        
        return results
    
    def _find_matches_from_database(self, parsed_message: ParsedMessage) -> List[SmartMatchResult]:
        """Find matches from Django database (fallback)"""
        product_name = parsed_message.product_name
        quantity = parsed_message.quantity
        unit = parsed_message.unit
        extra_descriptions = parsed_message.extra_descriptions
        
        # Build Q query for product name matching
        name_queries = Q()
        
        # Split product name into words for flexible matching
        name_words = product_name.split()
        
        # Add queries for each word in the product name
        for word in name_words:
            name_queries |= Q(name__icontains=word)
        
        # Add query for full product name
        name_queries |= Q(name__icontains=product_name)
        
        # Get initial candidates
        candidates = Product.objects.filter(name_queries)
        
        # Filter by unit if specified
        if unit:
            unit_candidates = candidates.filter(unit=unit)
            if unit_candidates.exists():
                candidates = unit_candidates
        
        # Filter by extra descriptions (like "200g", "large", etc.)
        if extra_descriptions:
            for desc in extra_descriptions:
                desc_candidates = candidates.filter(name__icontains=desc)
                if desc_candidates.exists():
                    candidates = desc_candidates
                    break  # Use first matching description
        
        # Score and rank candidates
        results = []
        for product in candidates:
            score = self._calculate_score(product, parsed_message)
            if score > 0:
                results.append(SmartMatchResult(
                    product=product,
                    quantity=quantity,
                    unit=unit or product.unit,
                    confidence_score=score,
                    match_details={
                        'parsed_name': product_name,
                        'matched_name': product.name,
                        'unit_match': unit == product.unit if unit else False,
                        'description_matches': [d for d in extra_descriptions if d in product.name.lower()],
                        'name_word_matches': [w for w in name_words if w in product.name.lower()]
                    }
                ))
        
        # Sort by confidence score
        results.sort(key=lambda x: x.confidence_score, reverse=True)
        
        return results
    
    def _calculate_score(self, product: Product, parsed_message: ParsedMessage) -> float:
        """Calculate confidence score for a product match"""
        score = 0
        product_name_lower = product.name.lower()
        parsed_name = parsed_message.product_name.lower()
        
        # Exact name match
        if parsed_name == product_name_lower:
            score += 50
        
        # Partial name match
        elif parsed_name in product_name_lower or product_name_lower in parsed_name:
            score += 30
        
        # Word-by-word matching
        parsed_words = set(parsed_name.split())
        product_words = set(product_name_lower.split())
        common_words = parsed_words.intersection(product_words)
        
        if common_words:
            word_match_ratio = len(common_words) / max(len(parsed_words), len(product_words))
            score += word_match_ratio * 25
        
        # Unit matching
        if parsed_message.unit:
            if parsed_message.unit == product.unit:
                score += 20
            elif self._compatible_units(parsed_message.unit, product.unit):
                score += 10
        
        # Extra description matching
        for desc in parsed_message.extra_descriptions:
            if desc in product_name_lower:
                score += 15
        
        # Penalize if no meaningful match
        if score < 10:
            return 0
        
        return min(score, 100)  # Cap at 100
    
    def _calculate_score_from_data(self, product_data: Dict, parsed_message: ParsedMessage) -> float:
        """Calculate confidence score for a product match from data"""
        score = 0
        product_name_lower = product_data['name'].lower()
        parsed_name = parsed_message.product_name.lower()
        
        # Name matching
        if parsed_name == product_name_lower:
            score += self.scoring_weights['exact_name_match']
        elif parsed_name in product_name_lower or product_name_lower in parsed_name:
            score += self.scoring_weights['partial_name_match']
        elif self._fuzzy_match(parsed_name, product_name_lower):
            score += self.scoring_weights['fuzzy_match']
        else:
            return 0  # No name match, skip
        
        # Unit matching
        if parsed_message.unit:
            if parsed_message.unit == product_data['unit']:
                score += self.scoring_weights['unit_match']
            elif self._compatible_units(parsed_message.unit, product_data['unit']):
                score += self.scoring_weights['unit_match'] * 0.7
        
        # Extra description matching
        for desc in parsed_message.extra_descriptions:
            if desc in product_name_lower:
                score += self.scoring_weights['weight_match']
        
        return min(score, 100)  # Cap at 100
    
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
    
    def match_message(self, message: str) -> List[SmartMatchResult]:
        """Main method to match a message to products"""
        parsed_messages = self.parse_message(message)
        all_results = []
        
        for parsed in parsed_messages:
            matches = self.find_matches(parsed)
            all_results.extend(matches)
        
        return all_results
    
    def get_suggestions(self, message: str, min_confidence: float = 10.0, max_suggestions: int = 5) -> SmartMatchSuggestions:
        """Get smart suggestions with multiple options when no good match is found"""
        parsed_messages = self.parse_message(message)
        
        if not parsed_messages:
            return SmartMatchSuggestions(
                best_match=None,
                suggestions=[],
                parsed_input=None,
                total_candidates=0
            )
        
        parsed = parsed_messages[0]  # Take first parsed result
        all_matches = self.find_matches(parsed)
        
        # Filter matches above minimum confidence
        valid_matches = [m for m in all_matches if m.confidence_score >= min_confidence]
        
        # Get best match (if confidence is high enough)
        best_match = None
        if valid_matches and valid_matches[0].confidence_score >= 50:
            best_match = valid_matches[0]
        
        # Get top suggestions (including lower confidence ones for suggestions)
        suggestions = valid_matches[:max_suggestions]
        
        # If we don't have enough suggestions, try fuzzy matching
        if len(suggestions) < max_suggestions:
            fuzzy_matches = self._get_fuzzy_suggestions(parsed, max_suggestions - len(suggestions))
            
            # Add fuzzy matches that aren't already in suggestions
            existing_ids = {s.product.id for s in suggestions}
            for fuzzy_match in fuzzy_matches:
                if fuzzy_match.product.id not in existing_ids:
                    suggestions.append(fuzzy_match)
        
        return SmartMatchSuggestions(
            best_match=best_match,
            suggestions=suggestions[:max_suggestions],
            parsed_input=parsed,
            total_candidates=len(all_matches)
        )
    
    def _get_fuzzy_suggestions(self, parsed_message: ParsedMessage, max_suggestions: int) -> List[SmartMatchResult]:
        """Get fuzzy suggestions when exact matching fails"""
        product_name = parsed_message.product_name
        quantity = parsed_message.quantity
        unit = parsed_message.unit
        
        # Try to use production data first
        production_products = self._load_production_products()
        
        if production_products:
            return self._get_fuzzy_suggestions_from_data(parsed_message, max_suggestions, production_products)
        else:
            return self._get_fuzzy_suggestions_from_database(parsed_message, max_suggestions)
    
    def _get_fuzzy_suggestions_from_data(self, parsed_message: ParsedMessage, max_suggestions: int, products_data: List[Dict]) -> List[SmartMatchResult]:
        """Get fuzzy suggestions from production data"""
        product_name = parsed_message.product_name
        quantity = parsed_message.quantity
        unit = parsed_message.unit
        
        fuzzy_matches = []
        
        # Strategy 1: Match individual words
        words = product_name.split()
        for word in words:
            if len(word) > 2:  # Skip short words
                word_matches = [p for p in products_data if word.lower() in p['name'].lower()][:10]
                for product_data in word_matches:
                    score = self._calculate_fuzzy_score_from_data(product_data, parsed_message, 'word_match')
                    if score > 0:
                        mock_product = type('MockProduct', (), {
                            'id': product_data['id'],
                            'name': product_data['name'],
                            'unit': product_data['unit'],
                            'price': product_data.get('price', 0)
                        })()
                        
                        fuzzy_matches.append(SmartMatchResult(
                            product=mock_product,
                            quantity=quantity,
                            unit=unit or product_data['unit'],
                            confidence_score=score,
                            match_details={
                                'strategy': 'word_match',
                                'matched_word': word,
                                'product_name': product_data['name']
                            }
                        ))
        
        # Strategy 2: Match by unit if specified
        if unit:
            unit_matches = [p for p in products_data if p['unit'].lower() == unit.lower()][:15]
            for product_data in unit_matches:
                score = self._calculate_fuzzy_score_from_data(product_data, parsed_message, 'unit_match')
                if score > 0:
                    mock_product = type('MockProduct', (), {
                        'id': product_data['id'],
                        'name': product_data['name'],
                        'unit': product_data['unit'],
                        'price': product_data.get('price', 0)
                    })()
                    
                    fuzzy_matches.append(SmartMatchResult(
                        product=mock_product,
                        quantity=quantity,
                        unit=unit,
                        confidence_score=score,
                        match_details={
                            'strategy': 'unit_match',
                            'matched_unit': unit,
                            'product_name': product_data['name']
                        }
                    ))
        
        # Strategy 3: Match by extra descriptions
        for desc in parsed_message.extra_descriptions:
            desc_matches = [p for p in products_data if desc.lower() in p['name'].lower()][:10]
            for product_data in desc_matches:
                score = self._calculate_fuzzy_score_from_data(product_data, parsed_message, 'description_match')
                if score > 0:
                    mock_product = type('MockProduct', (), {
                        'id': product_data['id'],
                        'name': product_data['name'],
                        'unit': product_data['unit'],
                        'price': product_data.get('price', 0)
                    })()
                    
                    fuzzy_matches.append(SmartMatchResult(
                        product=mock_product,
                        quantity=quantity,
                        unit=unit or product_data['unit'],
                        confidence_score=score,
                        match_details={
                            'strategy': 'description_match',
                            'matched_description': desc,
                            'product_name': product_data['name']
                        }
                    ))
        
        # Strategy 4: Similar sounding products (basic phonetic matching)
        if len(product_name) > 3:
            similar_matches = self._get_phonetic_matches_from_data(product_name, parsed_message, products_data)
            fuzzy_matches.extend(similar_matches)
        
        # Remove duplicates and sort by confidence
        seen_ids = set()
        unique_matches = []
        for match in fuzzy_matches:
            if match.product.id not in seen_ids:
                seen_ids.add(match.product.id)
                unique_matches.append(match)
        
        unique_matches.sort(key=lambda x: x.confidence_score, reverse=True)
        return unique_matches[:max_suggestions]
    
    def _get_fuzzy_suggestions_from_database(self, parsed_message: ParsedMessage, max_suggestions: int) -> List[SmartMatchResult]:
        """Get fuzzy suggestions from Django database (fallback)"""
        product_name = parsed_message.product_name
        quantity = parsed_message.quantity
        unit = parsed_message.unit
        
        # Try broader matching strategies
        fuzzy_matches = []
        
        # Strategy 1: Match individual words
        words = product_name.split()
        for word in words:
            if len(word) > 2:  # Skip short words
                word_matches = Product.objects.filter(name__icontains=word)[:10]
                for product in word_matches:
                    score = self._calculate_fuzzy_score(product, parsed_message, 'word_match')
                    if score > 0:
                        fuzzy_matches.append(SmartMatchResult(
                            product=product,
                            quantity=quantity,
                            unit=unit or product.unit,
                            confidence_score=score,
                            match_details={
                                'strategy': 'word_match',
                                'matched_word': word,
                                'product_name': product.name
                            }
                        ))
        
        # Strategy 2: Match by unit if specified
        if unit:
            unit_matches = Product.objects.filter(unit=unit)[:15]
            for product in unit_matches:
                score = self._calculate_fuzzy_score(product, parsed_message, 'unit_match')
                if score > 0:
                    fuzzy_matches.append(SmartMatchResult(
                        product=product,
                        quantity=quantity,
                        unit=unit,
                        confidence_score=score,
                        match_details={
                            'strategy': 'unit_match',
                            'matched_unit': unit,
                            'product_name': product.name
                        }
                    ))
        
        # Strategy 3: Match by extra descriptions
        for desc in parsed_message.extra_descriptions:
            desc_matches = Product.objects.filter(name__icontains=desc)[:10]
            for product in desc_matches:
                score = self._calculate_fuzzy_score(product, parsed_message, 'description_match')
                if score > 0:
                    fuzzy_matches.append(SmartMatchResult(
                        product=product,
                        quantity=quantity,
                        unit=unit or product.unit,
                        confidence_score=score,
                        match_details={
                            'strategy': 'description_match',
                            'matched_description': desc,
                            'product_name': product.name
                        }
                    ))
        
        # Strategy 4: Similar sounding products (basic phonetic matching)
        if len(product_name) > 3:
            similar_matches = self._get_phonetic_matches(product_name, parsed_message)
            fuzzy_matches.extend(similar_matches)
        
        # Remove duplicates and sort by confidence
        seen_ids = set()
        unique_matches = []
        for match in fuzzy_matches:
            if match.product.id not in seen_ids:
                seen_ids.add(match.product.id)
                unique_matches.append(match)
        
        unique_matches.sort(key=lambda x: x.confidence_score, reverse=True)
        return unique_matches[:max_suggestions]
    
    def _calculate_fuzzy_score(self, product: Product, parsed_message: ParsedMessage, strategy: str) -> float:
        """Calculate confidence score for fuzzy matches"""
        score = 0
        product_name_lower = product.name.lower()
        parsed_name = parsed_message.product_name.lower()
        
        # Base score depends on strategy
        if strategy == 'word_match':
            score = 25
        elif strategy == 'unit_match':
            score = 20
        elif strategy == 'description_match':
            score = 30
        elif strategy == 'phonetic_match':
            score = 15
        
        # Boost score for additional matches
        if parsed_name in product_name_lower or product_name_lower in parsed_name:
            score += 15
        
        # Unit matching bonus
        if parsed_message.unit and parsed_message.unit == product.unit:
            score += 10
        
        # Description matching bonus
        for desc in parsed_message.extra_descriptions:
            if desc in product_name_lower:
                score += 10
        
        # Penalize very long product names (less likely to be what user wants)
        if len(product.name) > 50:
            score -= 5
        
        return max(score, 0)
    
    def _get_phonetic_matches(self, product_name: str, parsed_message: ParsedMessage) -> List[SmartMatchResult]:
        """Get phonetically similar product matches"""
        matches = []
        
        # Simple phonetic matching - look for products with similar starting letters
        first_letters = product_name[:2].lower()
        
        phonetic_products = Product.objects.filter(name__istartswith=first_letters)[:10]
        
        for product in phonetic_products:
            # Calculate similarity based on common characters
            similarity = self._calculate_string_similarity(product_name.lower(), product.name.lower())
            
            if similarity > 0.3:  # At least 30% similarity
                score = similarity * 20  # Convert to confidence score
                matches.append(SmartMatchResult(
                    product=product,
                    quantity=parsed_message.quantity,
                    unit=parsed_message.unit or product.unit,
                    confidence_score=score,
                    match_details={
                        'strategy': 'phonetic_match',
                        'similarity': similarity,
                        'product_name': product.name
                    }
                ))
        
        return matches
    
    def _calculate_fuzzy_score_from_data(self, product_data: Dict, parsed_message: ParsedMessage, strategy: str) -> float:
        """Calculate confidence score for fuzzy matches from data"""
        score = 0
        product_name_lower = product_data['name'].lower()
        parsed_name = parsed_message.product_name.lower()
        
        # Base score depends on strategy
        if strategy == 'word_match':
            score = 15
        elif strategy == 'unit_match':
            score = 10
        elif strategy == 'description_match':
            score = 20
        elif strategy == 'phonetic_match':
            score = 8
        
        # Boost for better name matching
        if parsed_name in product_name_lower:
            score += 10
        elif any(word in product_name_lower for word in parsed_name.split()):
            score += 5
        
        # Unit compatibility
        if parsed_message.unit and parsed_message.unit == product_data['unit']:
            score += 8
        
        # Extra descriptions
        for desc in parsed_message.extra_descriptions:
            if desc in product_name_lower:
                score += 5
        
        return min(score, 50)  # Cap fuzzy scores lower
    
    def _get_phonetic_matches_from_data(self, product_name: str, parsed_message: ParsedMessage, products_data: List[Dict]) -> List[SmartMatchResult]:
        """Get phonetically similar product matches from data"""
        matches = []
        
        # Simple phonetic matching - look for products with similar starting letters
        first_letters = product_name[:2].lower()
        
        phonetic_products = [p for p in products_data if p['name'].lower().startswith(first_letters)][:10]
        
        for product_data in phonetic_products:
            # Calculate similarity based on common characters
            similarity = self._calculate_string_similarity(product_name.lower(), product_data['name'].lower())
            
            if similarity > 0.3:  # At least 30% similarity
                score = similarity * 20  # Convert to confidence score
                
                mock_product = type('MockProduct', (), {
                    'id': product_data['id'],
                    'name': product_data['name'],
                    'unit': product_data['unit'],
                    'price': product_data.get('price', 0)
                })()
                
                matches.append(SmartMatchResult(
                    product=mock_product,
                    quantity=parsed_message.quantity,
                    unit=parsed_message.unit or product_data['unit'],
                    confidence_score=score,
                    match_details={
                        'strategy': 'phonetic_match',
                        'similarity': similarity,
                        'product_name': product_data['name']
                    }
                ))
        
        return matches
    
    def _calculate_string_similarity(self, str1: str, str2: str) -> float:
        """Calculate simple string similarity (Jaccard similarity)"""
        set1 = set(str1.lower())
        set2 = set(str2.lower())
        
        intersection = set1.intersection(set2)
        union = set1.union(set2)
        
        if not union:
            return 0.0
        
        return len(intersection) / len(union)
    
    def _fuzzy_match(self, str1: str, str2: str) -> bool:
        """Check if two strings are fuzzy matches"""
        return self._calculate_string_similarity(str1, str2) > 0.4

def test_smart_matcher():
    """Test the smart matcher"""
    matcher = SmartProductMatcher()
    
    test_cases = [
        "1 * packet rosemary 200g",
        "packet rosemary 200g",
        "3kg carrots",
        "cucumber 5 each",
        "potato 10",
        "2 bag red onions",
        "wild rocket 500g",
        "aubergine box",
        "large eggs 2",
        "cherry tomatoes punnet"
    ]
    
    print("=== SMART MATCHER TEST ===\n")
    
    for test_case in test_cases:
        print(f"Input: '{test_case}'")
        
        # Parse message
        parsed_messages = matcher.parse_message(test_case)
        for parsed in parsed_messages:
            print(f"  Parsed: quantity={parsed.quantity}, unit={parsed.unit}, "
                  f"product='{parsed.product_name}', extras={parsed.extra_descriptions}")
            
            # Find matches
            matches = matcher.find_matches(parsed)
            if matches:
                best_match = matches[0]
                print(f"  ✓ Best match: {best_match.product.name}")
                print(f"    Confidence: {best_match.confidence_score:.1f}%")
                print(f"    Details: {best_match.match_details}")
            else:
                print(f"  ✗ No matches found")
        
        print()

if __name__ == "__main__":
    import os
    import django
    
    # Setup Django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'familyfarms_api.settings')
    django.setup()
    
    test_smart_matcher()
