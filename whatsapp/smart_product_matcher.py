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
    packaging_size: Optional[str] = None

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
    # Class-level cache to share across instances
    _products_cache = None
    _name_index = None
    _last_cache_time = None
    _cache_timeout = 3600  # 1 hour cache timeout
    
    def __init__(self):
        """Initialize with dynamic database analysis and caching"""
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
        
        self._load_database_info_cached()
        # COMMENTED OUT FOR TESTING: self._build_aliases()
        # Initialize empty aliases dict to prevent errors
        self.aliases = {}
    
    def _load_database_info_cached(self):
        """Load database info with caching for performance"""
        import time
        
        # Check if cache is valid
        current_time = time.time()
        if (self._products_cache is not None and 
            self._last_cache_time is not None and 
            current_time - self._last_cache_time < self._cache_timeout):
            # Use cached data
            self._use_cached_data()
            return
        
        # Load fresh data with optimized queries
        self._load_database_info_fresh()
        self._last_cache_time = current_time
    
    def _use_cached_data(self):
        """Use cached product data"""
        self.all_products_data = self._products_cache
        self.name_index = self._name_index
        self._extract_metadata_from_cache()
    
    def _load_database_info_fresh(self):
        """Load fresh data from database with optimizations"""
        # OPTIMIZATION: Use select_related and prefetch_related for efficient loading
        all_products = Product.objects.select_related('department').prefetch_related('supplier_products').all()
        
        # Convert to optimized data structure
        all_products_data = []
        name_index = {}  # word -> list of product indices
        
        for i, p in enumerate(all_products):
            product_data = {
                'id': p.id,
                'name': p.name,
                'unit': p.unit,
                'price': float(p.price) if p.price else 0.0,
                'department': p.department.name if p.department else '',
                'common_names': getattr(p, 'common_names', '') or '',
                'django_object': p  # Keep reference to Django object
            }
            all_products_data.append(product_data)
            
            # Build search index for O(1) lookups
            words = p.name.lower().split()
            for word in words:
                if word not in name_index:
                    name_index[word] = []
                name_index[word].append(i)
                
                # Add plural/singular variants to index for better matching
                # This allows "lemon" to find "Lemons" and vice versa
                singular_form = self._get_singular(word)
                plural_form = self._get_plural(word)
                
                if singular_form != word:
                    if singular_form not in name_index:
                        name_index[singular_form] = []
                    if i not in name_index[singular_form]:  # Avoid duplicates
                        name_index[singular_form].append(i)
                
                if plural_form != word:
                    if plural_form not in name_index:
                        name_index[plural_form] = []
                    if i not in name_index[plural_form]:  # Avoid duplicates
                        name_index[plural_form].append(i)
        
        # Cache the data
        self._products_cache = all_products_data
        self._name_index = name_index
        
        # Set instance variables
        self.all_products_data = all_products_data
        self.name_index = name_index
        
        self._extract_metadata_from_cache()
    
    def _extract_metadata_from_cache(self):
        """Extract metadata from cached product data"""
        
        # Extract all unique units
        self.valid_units = set()
        self.container_units = set()
        self.weight_units = set()
        
        # Extract product names and descriptions
        self.product_names = set()
        self.product_descriptions = {}  # product_name -> list of descriptions
        
        for product_data in self.all_products_data:
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
            'packets': 'packet',
            'pcs': 'piece',
            'pc': 'piece',
            'pieces': 'piece',
            'bo': 'box',
            'boxes': 'box',
            'pun': 'punnet',
            'punnet': 'punnet',
            'punnets': 'punnet',
            'bags': 'bag',
            'bunches': 'bunch',
            'heads': 'head',
            'trays': 'tray',
            
            # Color variations
            'red onion': 'red onions',
            'white onion': 'white onions',
            'spring onion': 'spring onions',
            'red pepper': 'red peppers',
            'green pepper': 'green peppers',
            'yellow pepper': 'yellow peppers',
            'brown mushroom': 'brown mushrooms',
            'portabellini mushroom': 'portabellini mushrooms',
            'cherry tomato': 'cherry tomatoes',
            'cocktail tomato': 'cocktail tomatoes',
            'sweet potato': 'sweet potatoes',
            'baby marrow': 'baby marrow',
            'wild rocket': 'rocket',
            'mi ed lettuce': 'lettuce',
            'mixed lettuce': 'lettuce',
        }
    
    def parse_message(self, message: str) -> List[ParsedMessage]:
        """Parse message into components using space splitting"""
        message = message.strip().lower()
        results = []
        
        # Split message into lines and items
        lines = [line.strip() for line in message.split('\n') if line.strip()]
        
        # Skip the first line if it looks like a company name
        # Common patterns: "Restaurant Name", "Company Ltd", etc.
        if len(lines) > 1:
            first_line = lines[0]
            # Skip if first line contains typical company indicators
            company_indicators = ['restaurant', 'bar', 'cafe', 'hotel', 'ltd', 'pty', 'inc', 'co.']
            if any(indicator in first_line for indicator in company_indicators):
                lines = lines[1:]  # Skip first line
        
        for line in lines:
            # Skip lines that are clearly not product descriptions
            if self._is_non_product_line(line):
                continue
                
            # First try standard separators (commas, semicolons)
            items = re.split(r'[,;]', line)
            
            # If no separators found, treat the entire line as one item
            if len(items) == 1:
                    items = [line]
            
            for item in items:
                item = item.strip()
                if not item:
                    continue
                
                parsed = self._parse_single_item(item)
                if parsed:
                    results.append(parsed)
        
        return results
    
    def _is_non_product_line(self, line: str) -> bool:
        """Check if a line is clearly not a product description"""
        line_lower = line.lower().strip()
        
        # Skip empty lines
        if not line_lower:
            return True
            
        # Skip lines that are clearly greetings or headers
        non_product_patterns = [
            r'^(hi|hello|hey|good morning|good afternoon|good evening)',
            r'^(here is|here\'s) my order',
            r'^(please|plz|pls) send',
            r'^(thanks|thank you)',
            r'^(regards|best regards)',
            r'^(order|order for)',
            r'^(for|to) \w+$',  # Lines like "for John" or "to Mary"
            r'^\w+ and \w+$',  # Lines like "Mugg and Bean"
            r'^\d+$',  # Just numbers
            r'^confirmed order:',  # Order confirmation headers
            r'^original message:',  # Original message headers
            # Removed the overly broad pattern that was catching product names
        ]
        
        for pattern in non_product_patterns:
            if re.match(pattern, line_lower):
                return True
                
        # Skip lines that don't contain any numbers or product indicators
        has_number = bool(re.search(r'\d', line_lower))
        has_product_indicators = any(word in line_lower for word in [
            'kg', 'g', 'ml', 'l', 'box', 'bag', 'packet', 'punnet', 'bunch', 'head', 'each', 'piece',
            'x', '*', '×', 'tomato', 'onion', 'pepper', 'mushroom', 'lettuce', 'cucumber', 'carrot', 
            'potato', 'spinach', 'broccoli', 'cauliflower', 'cabbage', 'avocado', 'lemon', 'lime', 
            'orange', 'apple', 'grape', 'strawberry', 'banana', 'pineapple', 'herb', 'mint', 'parsley',
            'rosemary', 'thyme', 'basil', 'dill', 'coriander', 'rocket'
        ])
        
        # Allow single words to pass through for suggestions (they might be product names)
        # Only skip multi-word lines that clearly aren't products
        if not has_number and not has_product_indicators and len(line_lower.split()) > 2:
            return True
            
        return False
    
    def _parse_single_item(self, item: str) -> Optional[ParsedMessage]:
        """Parse a single item using space splitting approach"""
        # Store original item before cleaning
        original_item = item
        
        # Clean the item - replace multipliers and handle number+x patterns
        item = re.sub(r'[*×]', ' ', item)  # Replace multipliers with spaces
        
        # Handle specific patterns like "3×5kgTomato" -> "3 5kg Tomato"
        # Match: number + space + number + unit + product name
        item = re.sub(r'(\d+)\s+(\d+)(kg|g|ml|l|box|bag|packet|punnet|bunch|head|each|piece)([a-zA-Z]+)', r'\1 \2\3 \4', item)
        
        # Handle patterns like "x10bunches" -> "x 10bunches" (x + number + unit, keep together)
        item = re.sub(r'x(\d+)(kg|g|ml|l|box|bag|packet|punnet|bunch|head|each|piece)s?', r'x \1\2', item)
        
        # Handle patterns like "5kgTomato" -> "5kg Tomato" (number + unit + product name)
        item = re.sub(r'(\d+)(kg|g|ml|l|box|bag|packet|punnet|bunch|head|each|piece)([a-zA-Z]+)', r'\1\2 \3', item)
        
        item = re.sub(r'(\w+)x(\d+)', r'\1 \2', item)  # Handle patterns like "melonx1" -> "melon 1"
        item = re.sub(r'\bx\b', ' ', item)  # Replace standalone 'x' with space
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
        
        # DEBUG: Log what we're parsing in SmartProductMatcher
        if 'tomato' in original_item.lower() or 'mushroom' in original_item.lower():
            print(f"🧠 SMART_MATCHER DEBUG: '{original_item}'")
        
        # Step 2: Find unit/container words - look for number+unit combinations first
        unit = None
        unit_word = None
        unit_index = -1
        
        # First check for container units in the text (highest priority)
        container_units = ['box', 'bag', 'punnet', 'packet', 'bunch', 'head', 'tray']
        for i, word in enumerate(words):
            if word in container_units:
                unit = word
                unit_word = word 
                unit_index = i
                break
        
        # If no container unit found, then check for number+unit combinations (like "5kg", "200g")  
        if not unit:
            # Sort units by length (longest first) to prioritize "kg" over "g"
            sorted_units = sorted(self.valid_units, key=len, reverse=True)
            for i, word in enumerate(words):
                for valid_unit in sorted_units:
                    # Check if word ends with unit AND starts with a number
                    if word.endswith(valid_unit) and len(word) > len(valid_unit):
                        # Verify it actually starts with a number
                        number_match = re.search(r'^(\d+(?:\.\d+)?)', word)
                        if number_match:
                            # For weight units, only use if no containers present
                            if valid_unit in ['kg', 'g']:
                                if not any(c in original_item.lower() for c in ['box', 'bag', 'punnet', 'packet']):
                                    unit = valid_unit
                                    unit_word = word
                                    unit_index = i
                                    break
                            else:
                                # This word contains a number + unit
                                unit = valid_unit
                                unit_word = word
                                unit_index = i
                                break
                if unit:
                    break
        
        # COMMENTED OUT FOR TESTING: If still no unit found, check container aliases
        # if not unit:
        #     for i, word in enumerate(words):
        #         if word in self.aliases and self.aliases[word] in container_units:
        #             unit = self.aliases[word]
        #             unit_word = word
        #             unit_index = i
        #             break
        
        # If no container found, look for any standalone units
        if not unit:
            for i, word in enumerate(words):
                # Check direct unit match
                if word in self.valid_units:
                    unit = word
                    unit_word = word
                    unit_index = i
                    break
                
                # COMMENTED OUT FOR TESTING: Check unit aliases
                # if word in self.aliases and self.aliases[word] in self.valid_units:
                #     unit = self.aliases[word]
                #     unit_word = word
                #     unit_index = i
                #     break
            
        # Step 3: Extract packaging size (e.g., "5kg", "2kg", "10kg", "(10kg)")
        packaging_size = None
        packaging_size_word = None
        
        # First, look for packaging sizes in parentheses (e.g., "(10kg)", "(5kg)")
        for i, word in enumerate(words):
            if word.startswith('(') and word.endswith(')'):
                # Extract content inside parentheses
                content = word[1:-1]  # Remove parentheses
                for valid_unit in self.valid_units:
                    if content.endswith(valid_unit) and len(content) > len(valid_unit):
                        # Check if this looks like a packaging size (number + unit)
                        number_match = re.search(r'^(\d+(?:\.\d+)?)', content)
                        if number_match:
                            packaging_size = content  # Store without parentheses (e.g., "10kg")
                            packaging_size_word = word
                            break
                if packaging_size:
                    break
            
        # If no packaging size found in parentheses, look for direct format (like "5kg", "2kg", "10kg")
        if not packaging_size:
            for i, word in enumerate(words):
                for valid_unit in self.valid_units:
                    if word.endswith(valid_unit) and len(word) > len(valid_unit):
                        # Check if this looks like a packaging size (number + unit)
                        number_match = re.search(r'^(\d+(?:\.\d+)?)', word)
                        if number_match:
                            packaging_size = word  # Store the full packaging size (e.g., "5kg")
                            packaging_size_word = word
                            break
                if packaging_size:
                    break
        
        # Step 3.5: Preserve individual packaging size for product matching
        # We should match products based on individual package size, not calculated total
        # For "3 x 5kg Tomato box", we want to match "Tomatoes (5kg box)", not "Tomatoes (15kg)"
        # The packaging_size should remain as the individual package size (e.g., "5kg")
        # The quantity will handle the multiplier (3)
        
        # Store the original packaging size for product matching
        individual_packaging_size = packaging_size
            
        # Step 4: Determine quantity using GOLDEN RULE: First standalone number = quantity
        quantity = 1.0
        extra_descriptions = []
        words_to_remove = []
        
        if numbers_found:
            # GOLDEN RULE: Find first standalone number and use as quantity
            standalone_numbers = [n for n in numbers_found if n['is_standalone']]
            if standalone_numbers:
                # Use first standalone number as quantity (Golden Rule)
                first_standalone = standalone_numbers[0]
                quantity = first_standalone['value']
                words_to_remove.append(first_standalone['word'])
            elif len(numbers_found) == 1:
                num_info = numbers_found[0]
                
                # If we already found a unit (like "packet"), and this number is standalone, use it as quantity
                if unit_index != -1 and num_info['is_standalone']:
                    quantity = num_info['value']
                    words_to_remove.append(num_info['word'])
                
                # If the number is part of a word with unit (like "200g"), handle specially
                elif not num_info['is_standalone']:
                    # Check if this word contains a unit
                    found_unit_in_word = False
                    # Sort units by length (longest first) to prioritize "kg" over "g"
                    sorted_units = sorted(self.valid_units, key=len, reverse=True)
                    for valid_unit in sorted_units:
                        if num_info['word'].endswith(valid_unit):
                            # This is a packaging size (like "10kg"), not a quantity
                            # Quantity should remain 1.0 unless there's an explicit multiplier
                            # The packaging size is already captured in the packaging_size variable
                            
                            # Explicitly keep quantity as 1.0 for packaging sizes
                            # Do NOT set quantity = num_info['value'] for packaging sizes
                            
                            # If we don't have a unit yet, this becomes the unit
                            if unit_index == -1:
                                unit = valid_unit
                                words_to_remove.append(num_info['word'])
                            else:
                                # We already have a unit, so this is a description
                                # But don't add it to extra_descriptions if it's a packaging size
                                if num_info['word'] != packaging_size:
                                    extra_descriptions.append(num_info['word'])
                                words_to_remove.append(num_info['word'])
                            found_unit_in_word = True
                            break
        
                    # If no unit found in word, treat as regular quantity
                    if not found_unit_in_word:
                        quantity = num_info['value']
                        words_to_remove.append(num_info['word'])
            else:
                # Multiple numbers - handle special cases like "2 5kg tomatoes"
                standalone_numbers = [n for n in numbers_found if n['is_standalone']]
                number_unit_combinations = [n for n in numbers_found if not n['is_standalone']]
                
                if standalone_numbers and number_unit_combinations:
                    # Special case: "2 5kg tomatoes" - first number is quantity, second is number+unit
                    quantity = standalone_numbers[0]['value']
                    words_to_remove.append(standalone_numbers[0]['word'])
                    
                    # Use the number+unit combination for unit (always set, don't check if unit exists)
                    if number_unit_combinations:
                        first_combo = number_unit_combinations[0]
                        # Sort units by length (longest first) to prioritize "kg" over "g"
                        sorted_units = sorted(self.valid_units, key=len, reverse=True)
                        for valid_unit in sorted_units:
                            if first_combo['word'].endswith(valid_unit):
                                unit = valid_unit
                                # Don't remove weight+unit combinations when there are containers
                                # This preserves "10kg bag" in the product name
                                if not any(container in words for container in ['box', 'bag', 'packet', 'punnet', 'bunch', 'head', 'each']):
                                    extra_descriptions.append(first_combo['word'])
                                    words_to_remove.append(first_combo['word'])
                                break
        
                    # Other numbers become descriptions
                    for num_info in numbers_found[1:]:
                        if num_info != standalone_numbers[0] and num_info != number_unit_combinations[0]:
                            extra_descriptions.append(num_info['word'])
                            words_to_remove.append(num_info['word'])
                elif standalone_numbers:
                    # Use first standalone number as quantity
                    quantity = standalone_numbers[0]['value']
                    words_to_remove.append(standalone_numbers[0]['word'])
                    
                    # Other numbers become descriptions
                    for num_info in numbers_found:
                        if num_info != standalone_numbers[0]:
                            extra_descriptions.append(num_info['word'])
                            words_to_remove.append(num_info['word'])
                elif numbers_found:
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
        
        # Step 5: Remove processed words, but preserve weight+container combinations
        if unit_word:
            # Check if this is a weight+container combination (e.g., "5kg box", "10kg bag")
            # Look for container words near the weight unit
            container_words = ['box', 'bag', 'packet', 'punnet', 'bunch', 'head', 'each']
            has_container = any(container in words for container in container_words)
            
            if has_container:
                # For weight+container combinations, keep the weight in the product name
                # e.g., "5kg box tomatoes" -> "5kg box tomatoes" not "box tomatoes"
                pass  # Don't remove the unit_word
            else:
                # For standalone weights, remove them
                words_to_remove.append(unit_word)
        
        remaining_words = [w for w in words if w not in words_to_remove]
        
        if not remaining_words:
            return None
    
        # Step 6: Build product name
        product_name = ' '.join(remaining_words)
        # COMMENTED OUT FOR TESTING: product_name = self._apply_aliases(product_name)
        
        # Clean up product name - remove extra 's' and fix common issues
        product_name = self._clean_product_name(product_name)
        
        # Check for ambiguous packaging specifications
        ambiguous_packaging = self._is_ambiguous_packaging(original_item, unit, packaging_size)
        
        # Always allow parsing, but mark ambiguous packaging for special handling
        if ambiguous_packaging:
            # Add a flag to indicate this needs suggestions due to ambiguous packaging
            extra_descriptions.append("AMBIGUOUS_PACKAGING")
        
        # DEBUG: Log parsing results for specific items
        if any(item in original_item.lower() for item in ['mushroom', 'tomato']):
            print(f"🔍 PARSING DEBUG ({original_item}):")
            print(f"  Quantity: {quantity}")
            print(f"  Unit: {unit}")
            print(f"  Product: '{product_name}'")
            print(f"  Packaging: '{individual_packaging_size}'")
            print(f"  Extra: {extra_descriptions}")
            if 'tomato' in original_item.lower():
                kg_pattern = r'\b\d+(?:\.\d+)?\s*kg\b'
                print(f"  🧠 Unit Detection: has_box={'box' in original_item.lower()}, has_kg_pattern={bool(re.search(kg_pattern, original_item.lower()))}")
        
        return ParsedMessage(
            quantity=quantity,
            unit=unit,
            product_name=product_name,
            extra_descriptions=extra_descriptions,
            original_message=original_item,
            packaging_size=individual_packaging_size
        )
    
    def _apply_aliases(self, product_name: str) -> str:
        """Apply aliases to product name"""
        # Handle special cases first
        if 'sweet potato' in product_name:
            return product_name  # Don't alias sweet potato
        
        # Check for multi-word aliases first
        for alias, replacement in self.aliases.items():
            if ' ' in alias and alias in product_name:
                product_name = product_name.replace(alias, replacement)
        
        # Apply word-level aliases (not substring replacement)
        words = product_name.split()
        result_words = []
        
        for word in words:
            if word in self.aliases:
                result_words.append(self.aliases[word])
            else:
                result_words.append(word)
        
        return ' '.join(result_words)
    
    def _validate_packaging_specification(self, original_item: str, unit: str, packaging_size: str, product_name: str) -> bool:
        """Validate that we're not guessing packaging sizes - always return True to allow suggestions"""
        # Always return True to allow the item to be parsed and get suggestions
        # The ambiguous packaging will be handled by the suggestion system
        return True
    
    def _is_ambiguous_packaging(self, original_item: str, unit: str, packaging_size: str = None) -> bool:
        """Check if this is an ambiguous packaging specification that needs suggestions"""
        original_lower = original_item.lower()
        
        # Check for ambiguous packaging specifications
        # Cases like "3 * box lemons", "2 box tomatoes", "1 bag onions"
        # where we have a container type but no specific size
        
        container_words = ['box', 'bag', 'packet', 'punnet', 'bunch', 'head', 'piece']
        
        # Valid units that don't need packaging size (they are specific enough on their own)
        # Note: 'box', 'bag', 'packet' need specific sizes to avoid ambiguity
        valid_standalone_units = ['head', 'piece', 'each']
        
        # Case 1: No unit specified at all (e.g., "1 cucumber", "2 tomatoes")
        if unit is None or unit == '':
            return True
        
        # Case 2: If we have a unit that's a container type but no packaging size specified
        # BUT exclude valid standalone units like "head", "piece", "each"
        if unit in container_words and unit not in valid_standalone_units and not packaging_size:
            # Check if the original input contains a specific size with the container
            has_specific_size = any([
                re.search(rf'\d+kg\s+{unit}', original_lower),  # e.g., "5kg box"
                re.search(rf'\d+g\s+{unit}', original_lower),   # e.g., "500g box"
                re.search(rf'\d+ml\s+{unit}', original_lower),  # e.g., "500ml box"
                re.search(rf'\d+l\s+{unit}', original_lower),   # e.g., "2l box"
                re.search(rf'{unit}\s+\d+kg', original_lower),  # e.g., "box 5kg"
                re.search(rf'{unit}\s+\d+g', original_lower),   # e.g., "box 500g"
                re.search(rf'{unit}\s+\d+ml', original_lower),  # e.g., "box 500ml"
                re.search(rf'{unit}\s+\d+l', original_lower),   # e.g., "box 2l"
            ])
            
            if not has_specific_size:
                return True
        
        # Case 3: If we have a container unit with a quantity but no packaging size
        # This catches cases like "Pineapple 2 box" where "2" is quantity, not packaging size
        if unit in container_words and unit not in valid_standalone_units and not packaging_size:
            # Check if there's a number before the container word (quantity without packaging size)
            quantity_before_container = re.search(rf'\d+\s+{unit}', original_lower)
            if quantity_before_container:
                return True
        
        return False
    
    def _clean_product_name(self, product_name: str) -> str:
        """Clean up product name by removing extra characters and fixing common issues"""
        # Remove extra spaces and fix common issues
        cleaned_name = re.sub(r'\s+', ' ', product_name).strip()
        
        # Fix specific common issues
        cleaned_name = cleaned_name.replace('tomatoeses', 'tomatoes')
        cleaned_name = cleaned_name.replace('onionss', 'onions')
        cleaned_name = cleaned_name.replace('pepperss', 'peppers')
        cleaned_name = cleaned_name.replace('mushroomss', 'mushrooms')
        cleaned_name = cleaned_name.replace('tomatoe', 'tomatoes')
        cleaned_name = cleaned_name.replace('carrotss', 'carrots')
        cleaned_name = cleaned_name.replace('tomatoess', 'tomatoes')
        
        return cleaned_name
    
    def _get_color_words(self) -> List[str]:
        """Extract color words from product names in the database"""
        if not hasattr(self, '_cached_color_words'):
            # OPTIMIZATION: Use cached product data instead of database queries
            color_words = set()
            
            # Common color patterns in product names
            color_patterns = [
                r'\b(red|green|yellow|white|brown|black|blue|purple|orange|pink|violet|indigo|turquoise|maroon|navy|olive|lime|cyan|magenta)\b',
                r'\b(light|dark|bright|pale|deep|vivid|muted|neon|pastel)\s+(red|green|yellow|white|brown|black|blue|purple|orange|pink|violet|indigo|turquoise|maroon|navy|olive|lime|cyan|magenta)\b'
            ]
            
            for product_data in self.all_products_data:
                product_name = product_data['name'].lower()
                for pattern in color_patterns:
                    matches = re.findall(pattern, product_name)
                    for match in matches:
                        if isinstance(match, tuple):
                            # For compound patterns like "light red"
                            color_words.add(' '.join(match))
                        else:
                            color_words.add(match)
            
            self._cached_color_words = list(color_words)
        
        return self._cached_color_words
    
    def _get_product_type_words(self) -> List[str]:
        """Extract product type words from product names in the database"""
        if not hasattr(self, '_cached_product_type_words'):
            # OPTIMIZATION: Use cached product data instead of database queries
            type_words = set()
            word_counts = {}  # Track word frequency
            
            # Words to exclude (units, containers, measurements, etc.)
            exclude_words = {
                'kg', 'g', 'ml', 'l', 'box', 'bag', 'packet', 'punnet', 'bunch', 'head', 'each', 'piece',
                'pcs', 'tray', 'large', 'small', 'medium', 'big', 'tiny', 'mini', 'jumbo', 'extra',
                'fresh', 'frozen', 'dried', 'canned', 'organic', 'local', 'imported', 'premium',
                'grade', 'quality', 'a', 'an', 'the', 'and', 'or', 'of', 'in', 'on', 'at', 'to', 'for',
                'with', 'by', 'from', 'up', 'down', 'out', 'off', 'over', 'under', 'through'
            }
            
            # First pass: count word frequencies
            for product_data in self.all_products_data:
                product_words = product_data['name'].lower().split()
                for word in product_words:
                    # Clean the word (remove punctuation, numbers)
                    clean_word = re.sub(r'[^\w]', '', word)
                    
                    # Skip if too short, excluded, or contains numbers
                    if (len(clean_word) < 3 or 
                        clean_word in exclude_words or 
                        re.search(r'\d', clean_word) or
                        clean_word in ['', ' ']):
                        continue
                    
                    word_counts[clean_word] = word_counts.get(clean_word, 0) + 1
            
            # Second pass: add words that appear in multiple products
            for word, count in word_counts.items():
                if count > 1:  # Word appears in multiple products
                    type_words.add(word)
            
            self._cached_product_type_words = list(type_words)
        
        return self._cached_product_type_words
    
    def _get_strict_word_matches(self, product_name: str, base_product_name: str, search_terms: List[str]) -> set:
        """
        Implement strict word matching rules:
        - 2-word searches: ONLY products with exactly 2 words (excluding packaging)
        - 1-word searches: ONLY products with exactly 1 word (excluding packaging)
        - If no results, fall back to broader matching but still require search words
        """
        candidate_indices = set()
        
        # Extract search words from the main product name (excluding packaging terms)
        main_search_words = self._extract_search_words(product_name)
        base_search_words = self._extract_search_words(base_product_name)
        
        # PRIMARY SEARCH: Try multi-word matching first (more flexible than exact word count)
        # This allows "3 box avocado hard" to match "Avocado Hard Box" or "Avocado Hard (5kg)"
        if len(main_search_words) >= 2:
            # MULTI-WORD SEARCH: Find products containing ALL search words (flexible word count)
            candidate_indices.update(self._find_multi_word_matches(main_search_words))
        elif len(main_search_words) == 1:
            # SINGLE-WORD SEARCH: Find products containing the word
            candidate_indices.update(self._find_single_word_matches(main_search_words[0]))
        
        # FALLBACK 1: Try exact word count matching if multi-word didn't find results
        # This is more strict but can catch exact matches
        if len(candidate_indices) == 0:
            if len(main_search_words) >= 2:
                candidate_indices.update(self._find_exact_word_count_matches(main_search_words, len(main_search_words)))
            elif len(main_search_words) == 1:
                candidate_indices.update(self._find_exact_word_count_matches(main_search_words, 1))
        
        # FALLBACK 2: Try base product name if main search yields no results
        if len(candidate_indices) == 0 and base_search_words != main_search_words:
            if len(base_search_words) >= 2:
                candidate_indices.update(self._find_multi_word_matches(base_search_words))
            elif len(base_search_words) == 1:
                candidate_indices.update(self._find_single_word_matches(base_search_words[0]))
        
        # LAST RESORT: Original fuzzy matching if we still have no results
        # BUT STILL REQUIRE WORD BOUNDARIES to prevent false matches
        if len(candidate_indices) == 0:
            print(f"[SEARCH] No multi-word matches found for '{product_name}', using fuzzy search with word boundaries")
            import re
            for term in search_terms:
                term_lower = term.lower().strip()
                # Only use single words from search terms, not full phrases
                if ' ' not in term_lower and len(term_lower) > 3:
                    # Direct word match - but verify with word boundaries
                    if term_lower in self.name_index:
                        word_pattern = r'\b' + re.escape(term_lower) + r'\b'
                        for idx in self.name_index[term_lower]:
                            product_data = self.all_products_data[idx]
                            product_name_lower = product_data['name'].lower()
                            # Only add if it's a complete word match
                            if re.search(word_pattern, product_name_lower):
                                candidate_indices.add(idx)
        
        print(f"[SEARCH] Found {len(candidate_indices)} candidates for '{product_name}' ({len(main_search_words)} words)")
        return candidate_indices
    
    def _get_singular(self, word: str) -> str:
        """Convert plural word to singular form"""
        if len(word) <= 3:
            return word
        
        # Common plural patterns
        if word.endswith('ies'):
            return word[:-3] + 'y'  # cherries -> cherry
        elif word.endswith('es') and len(word) > 4:
            # Check if it's a plural (e.g., tomatoes, potatoes)
            if word[-3] in 'aeiou':
                return word[:-2]  # tomatoes -> tomato
            return word[:-1]  # boxes -> box
        elif word.endswith('s') and not word.endswith('ss'):
            return word[:-1]  # lemons -> lemon, apples -> apple
        
        return word
    
    def _get_plural(self, word: str) -> str:
        """Convert singular word to plural form"""
        if len(word) <= 3:
            return word
        
        # Common pluralization rules
        if word.endswith('y') and len(word) > 3:
            return word[:-1] + 'ies'  # cherry -> cherries
        elif word.endswith('s') or word.endswith('x') or word.endswith('z'):
            return word + 'es'  # box -> boxes, fox -> foxes
        elif word.endswith('o'):
            return word + 'es'  # tomato -> tomatoes
        else:
            return word + 's'  # lemon -> lemons, apple -> apples
    
    def _extract_search_words(self, product_name: str) -> List[str]:
        """Extract meaningful search words from product name, excluding packaging info"""
        import re
        
        # Remove packaging info in brackets (e.g., "Cherry Tomatoes (200g)" -> "Cherry Tomatoes")
        clean_name = re.sub(r'\s*\([^)]*\)\s*', ' ', product_name).strip()
        
        # Remove quantity/unit words that aren't part of product names
        # Remove standalone numbers and common quantity/unit words
        quantity_words = {'0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10',
                         '11', '12', '13', '14', '15', '16', '17', '18', '19', '20',
                         'kg', 'g', 'ml', 'l', 'box', 'bag', 'punnet', 'packet', 
                         'bunch', 'head', 'each', 'piece', 'pcs', 'pieces', 'x', '×', '*'}
        
        # Split into words and filter out quantity/unit words
        words = clean_name.lower().split()
        
        # Filter out quantity/unit words and very short words, but KEEP descriptors like "hard", "soft", "ripe", etc.
        exclude_words = {'the', 'and', 'or', 'for', 'with', 'from', 'that', 'this'}
        exclude_words.update(quantity_words)
        
        # Keep meaningful product words (including descriptors like "hard", "soft", "ripe", etc.)
        search_words = [word for word in words if len(word) > 1 and word not in exclude_words]
        
        return search_words
    
    def _find_multi_word_matches(self, search_words: List[str]) -> set:
        """Find products that contain ALL search words as complete words (not substrings)"""
        if not search_words:
            return set()
        
        # Start with products containing the first word (including variants from index)
        result_indices = set(self.name_index.get(search_words[0], []))
        
        # Intersect with products containing each subsequent word (including variants from index)
        for word in search_words[1:]:
            word_indices = set(self.name_index.get(word, []))
            result_indices = result_indices.intersection(word_indices)
            
            # Early exit if no matches remain
            if not result_indices:
                break
        
        # STRICT FILTERING: Require that search words (or their variants) appear as complete words
        # This prevents "tomatoes" from matching "avocados" or "potatoes"
        # But allows "lemon" to match "Lemons" via the index variants we added
        filtered_indices = set()
        import re
        for idx in result_indices:
            product_data = self.all_products_data[idx]
            product_name_lower = product_data['name'].lower()
            product_words = self._extract_search_words(product_data['name'])
            
            # Check if ALL search words (or their variants) appear as complete words in the product name
            all_words_match = True
            for search_word in search_words:
                # Check for original word and its variants
                search_variants = {
                    search_word.lower(),
                    self._get_singular(search_word).lower(),
                    self._get_plural(search_word).lower()
                }
                
                # Check if any variant appears as a complete word
                word_found = False
                for variant in search_variants:
                    word_pattern = r'\b' + re.escape(variant) + r'\b'
                    if re.search(word_pattern, product_name_lower):
                        word_found = True
                        break
                
                if not word_found:
                    all_words_match = False
                    break
            
            if all_words_match:
                filtered_indices.add(idx)
        
        return filtered_indices
    
    def _find_single_word_matches(self, search_word: str) -> set:
        """Find products that contain the search word as a complete word (not substring)"""
        # Get candidates from index (which now includes plural/singular variants)
        candidate_indices = set(self.name_index.get(search_word, []))
        
        # STRICT FILTERING: Require that search word (or its variant) appears as a complete word
        # This prevents "tomato" from matching "potato" or "avocado"
        # But allows "lemon" to match "Lemons" via the index variants we added
        filtered_indices = set()
        import re
        
        # Check for both the original word and its variants
        search_variants = {
            search_word.lower(),
            self._get_singular(search_word).lower(),
            self._get_plural(search_word).lower()
        }
        
        for idx in candidate_indices:
            product_data = self.all_products_data[idx]
            product_name_lower = product_data['name'].lower()
            
            # Check if any variant appears as a complete word (word boundary)
            for variant in search_variants:
                word_pattern = r'\b' + re.escape(variant) + r'\b'
                if re.search(word_pattern, product_name_lower):
                    filtered_indices.add(idx)
                    break
        
        return filtered_indices
    
    def _find_exact_word_count_matches(self, search_words: List[str], target_word_count: int) -> set:
        """
        Find products that:
        1. Contain ALL search words
        2. Have exactly the target number of words (excluding packaging)
        """
        if not search_words:
            return set()
        
        # Start with products containing ALL search words
        if len(search_words) == 1:
            candidate_indices = set(self.name_index.get(search_words[0], []))
        else:
            # Multi-word: intersection of all word matches
            candidate_indices = set(self.name_index.get(search_words[0], []))
            for word in search_words[1:]:
                word_indices = set(self.name_index.get(word, []))
                candidate_indices = candidate_indices.intersection(word_indices)
                if not candidate_indices:
                    break
        
        # Filter by exact word count AND require complete word matches
        filtered_indices = set()
        import re
        
        for idx in candidate_indices:
            product_data = self.all_products_data[idx]
            product_name_lower = product_data['name'].lower()
            product_words = self._extract_search_words(product_data['name'])
            
            # Check word count matches
            if len(product_words) != target_word_count:
                continue
            
            # STRICT: Require that ALL search words appear as complete words (word boundaries)
            all_words_match = True
            for search_word in search_words:
                word_pattern = r'\b' + re.escape(search_word.lower()) + r'\b'
                if not re.search(word_pattern, product_name_lower):
                    all_words_match = False
                    break
            
            if all_words_match:
                filtered_indices.add(idx)
        
        return filtered_indices
    
    def find_matches(self, parsed_message: ParsedMessage, restaurant=None) -> List[SmartMatchResult]:
        """Find matching products using database
        
        Args:
            parsed_message: ParsedMessage instance
            restaurant: Optional RestaurantProfile to filter by package restrictions
        """
        results = self._find_matches_from_database(parsed_message)
        
        # Filter by restaurant package restrictions if restaurant provided
        if restaurant:
            from products.package_restrictions import is_product_allowed_for_restaurant
            results = [
                r for r in results 
                if is_product_allowed_for_restaurant(r.product, restaurant)
            ]
        
        return results
    
    
    def _find_matches_from_database(self, parsed_message: ParsedMessage) -> List[SmartMatchResult]:
        """Find matches using cached data (optimized)"""
        product_name = parsed_message.product_name
        quantity = parsed_message.quantity
        unit = parsed_message.unit
        extra_descriptions = parsed_message.extra_descriptions
        packaging_size = parsed_message.packaging_size
        
        # Store original product name BEFORE aliases (for filtering)
        original_product_name = product_name
        
        # Extract base product name by removing common container/weight words
        base_product_name = self._extract_base_product_name(product_name)
        
        # OPTIMIZATION: Use cached name index for fast lookups
        candidate_indices = set()
        
        # Try multiple search strategies using cached index
        search_terms = [
            product_name,  # Full parsed name
            base_product_name,  # Base product name
        ]
        
        # Add packaging size to search terms if available
        if packaging_size:
            search_terms.append(packaging_size)
        
        # Add individual words from both full and base names, but be more selective
        for term in [product_name, base_product_name]:
            words = term.split()
            for word in words:
                # Only add words that are likely to be product names, not common words
                if len(word) > 3 and word.lower() not in ['the', 'and', 'for', 'with', 'from', 'that', 'this']:
                    search_terms.append(word)
        
        # IMPROVED MULTI-WORD SEARCH: Enforce strict word matching rules
        candidate_indices = self._get_strict_word_matches(product_name, base_product_name, search_terms)
        
        # Get candidate products from cache
        candidates = [self.all_products_data[i] for i in candidate_indices]
        
        # If we have packaging size, prioritize products that contain it with word boundaries
        if packaging_size:
            # Use regex to find exact packaging size matches, not substring matches
            # This prevents "5kg" from matching within "15kg"
            import re
            packaging_pattern = r'\b' + re.escape(packaging_size) + r'\b'
            packaging_candidates = [c for c in candidates if re.search(packaging_pattern, c['name'], re.IGNORECASE)]
            if packaging_candidates:
                # Use packaging-specific candidates as primary, others as secondary
                all_candidates = list(candidates)
                # Put packaging matches first
                candidates = packaging_candidates + [c for c in all_candidates if c not in packaging_candidates]
        
        # Filter by unit if specified, but don't force it if it reduces matches too much
        # If packaging size is present, skip unit filtering to prioritize packaging size matching
        if unit and not packaging_size:
            unit_candidates = [c for c in candidates if c['unit'] == unit]
            # Use unit filtering if we have any candidates, but prefer more candidates
            if unit_candidates:
                if len(unit_candidates) >= 3:
                    candidates = unit_candidates
                else:
                    # If unit filtering gives us too few candidates, use both but prioritize unit matches
                    all_candidates = list(candidates)
                    # Put unit matches first
                    candidates = unit_candidates + [c for c in all_candidates if c not in unit_candidates]
        
        # Filter by extra descriptions (like "200g", "large", etc.)
        # COMMENTED OUT: Removed fallback filtering to focus on strict name matching only
        # if extra_descriptions:
        #     for desc in extra_descriptions:
        #         desc_candidates = [c for c in candidates if desc.lower() in c['name'].lower()]
        #         if desc_candidates:
        #             candidates = desc_candidates
        #             break  # Use first matching description
        
        # STRICT FILTERING: Only include products where the product name STARTS with the search term
        # This ensures "tomato" only matches "Tomato" products, not "Cherry Tomatoes" or "Cocktail Tomatoes"
        # Use ORIGINAL product name (before aliases) for filtering to handle cases like "mixed lettuce"
        original_name_lower = original_product_name.lower().strip()
        parsed_name_lower = product_name.lower().strip()  # After aliases
        base_name_lower = base_product_name.lower().strip()
        original_words = original_name_lower.split()
        parsed_words = parsed_name_lower.split()
        base_words = base_name_lower.split()
        
        # Filter candidates to only those that start with the search term
        filtered_candidates = []
        for product_data in candidates:
            product_name_lower = product_data['name'].lower().strip()
            product_words = product_name_lower.split()
            
            # For single-word searches (e.g., "tomato"), only match if first word starts with search term
            # This excludes "Cherry Tomatoes" and "Cocktail Tomatoes" but includes "Tomato" and "Tomatoes"
            if len(original_words) == 1:
                # Single word search: first word of product name must start with search term
                if not product_words or not product_words[0].startswith(original_name_lower):
                    continue  # Skip products that don't start with the search term
            else:
                # Multi-word search: check if product name starts with ORIGINAL search term (before aliases)
                # This handles cases like "mixed lettuce" matching "Mixed Lettuce" even if alias converts it to "lettuce"
                starts_with_original = product_name_lower.startswith(original_name_lower)
                starts_with_parsed = product_name_lower.startswith(parsed_name_lower)
                starts_with_base = product_name_lower.startswith(base_name_lower)
                
                if not (starts_with_original or starts_with_parsed or starts_with_base):
                    # Check if first words match in order (for exact matches)
                    if len(product_words) >= len(original_words):
                        # Check if first words match in order from original search
                        first_words_match = all(
                            product_words[i].startswith(original_words[i]) if i < len(product_words) else False
                            for i in range(len(original_words))
                        )
                        # Also check parsed words (after alias)
                        first_parsed_words_match = len(parsed_words) > 0 and len(product_words) >= len(parsed_words) and all(
                            product_words[i].startswith(parsed_words[i]) if i < len(product_words) else False
                            for i in range(len(parsed_words))
                        )
                        # Also check base words
                        first_base_words_match = len(base_words) > 0 and len(product_words) >= len(base_words) and all(
                            product_words[i].startswith(base_words[i]) if i < len(product_words) else False
                            for i in range(len(base_words))
                        )
                        
                        if not (first_words_match or first_parsed_words_match or first_base_words_match):
                            continue  # Skip products that don't start with the search term
                    else:
                        continue  # Product has fewer words than search term
            
            filtered_candidates.append(product_data)
        
        # Use filtered candidates instead of all candidates
        candidates = filtered_candidates
        
        # Score and rank candidates
        results = []
        for product_data in candidates:
            # Get Django object for scoring
            django_product = product_data['django_object']
            score = self._calculate_score(django_product, parsed_message)
            if score > 0:
                results.append(SmartMatchResult(
                    product=django_product,
                    quantity=quantity,
                    unit=product_data['unit'],  # Always use the product's unit, not parsed unit
                    confidence_score=score,
                    match_details={
                        'parsed_name': product_name,
                        'base_name': base_product_name,
                        'matched_name': product_data['name'],
                        'unit_match': unit == product_data['unit'] if unit else False,
                        # COMMENTED OUT: Removed substring matching in match_details
                        # 'description_matches': [d for d in extra_descriptions if d in product_data['name'].lower()],
                        # 'name_word_matches': [w for w in base_product_name.split() if w in product_data['name'].lower()]
                        'description_matches': [],
                        'name_word_matches': []
                    }
                ))
        
        # Sort by confidence score, with name matching and packaging size as secondary criteria
        def sort_key(match):
            confidence = match.confidence_score
            
            # Add name match bonus for sorting (prioritize exact matches over partial matches)
            name_match_bonus = 0
            parsed_name = parsed_message.product_name.lower()
            product_name_lower = match.product.name.lower()
            parsed_name_words = set(parsed_name.split())
            product_name_words = set(product_name_lower.split())
            
            # HIGHEST PRIORITY: Check if search term matches the START of product name
            # This ensures "cherry" matches "Cherry Tomatoes" before "Tomatoes (Cherry)"
            if product_name_lower.startswith(parsed_name):
                name_match_bonus = 0.5  # Highest bonus for prefix match
            elif parsed_name.startswith(product_name_lower):
                name_match_bonus = 0.4  # High bonus for reverse prefix match
            # Check if all parsed words are in the product name (exact match priority)
            elif parsed_name_words.issubset(product_name_words):
                # Prioritize products that contain all parsed words
                name_match_bonus = 0.3  # Base bonus for containing all words
                
                # Add bonus for descriptive words (bulk, fresh, etc.) that indicate more specific products
                descriptive_words = {'bulk', 'fresh', 'organic', 'premium', 'large', 'small', 'medium'}
                if any(word in product_name_words for word in descriptive_words):
                    name_match_bonus += 0.2  # Extra bonus for descriptive products
            
            # Add packaging size bonus for sorting (doesn't affect the actual score)
            packaging_bonus = 0
            if parsed_message.packaging_size:
                import re
                packaging_size = parsed_message.packaging_size.lower()
                product_name_lower = match.product.name.lower()
                packaging_pattern = r'\b' + re.escape(packaging_size) + r'\b'
                if re.search(packaging_pattern, product_name_lower):
                    packaging_bonus = 0.1  # Small bonus to break ties
            
            # Add price bonus for sorting (prefer products with prices > 0)
            price_bonus = 0
            if match.product.price and match.product.price > 0:
                price_bonus = 0.05  # Small bonus for products with valid prices
            
            return (confidence, name_match_bonus, packaging_bonus, price_bonus)
        
        results.sort(key=sort_key, reverse=True)
        
        return results
    
    def _extract_base_product_name(self, product_name: str) -> str:
        """Extract base product name by removing container/weight words"""
        # Common container and weight words to remove
        container_words = {
            'bag', 'box', 'packet', 'pack', 'punnet', 'bunch', 'head', 'each', 'piece',
            'kg', 'g', 'ml', 'l', 'pcs', 'tray', 'large', 'small', 'medium'
        }
        
        # Split into words and filter out container/weight words
        words = product_name.split()
        base_words = []
        
        for word in words:
            # Remove numbers, units, and leading/trailing punctuation
            clean_word = re.sub(r'\d+[a-zA-Z]*', '', word).strip()
            # Remove leading/trailing dots, commas, and other punctuation
            clean_word = re.sub(r'^[.,;:\-\s]+|[.,;:\-\s]+$', '', clean_word).strip()
            if clean_word and clean_word.lower() not in container_words:
                base_words.append(clean_word)
        
        return ' '.join(base_words).strip()
    
    def _get_product_types(self, product_name: str) -> List[str]:
        """Extract product types from product name for broader matching"""
        product_types = []
        name_lower = product_name.lower()
        
        # Define product type mappings
        type_mappings = {
            'tomato': ['tomato', 'cherry', 'cocktail'],
            'onion': ['onion', 'spring onion', 'red onion', 'white onion'],
            'pepper': ['pepper', 'chili', 'chilli', 'bell pepper'],
            'mushroom': ['mushroom', 'portabellini', 'brown mushroom', 'button mushroom'],
            'lettuce': ['lettuce', 'mixed lettuce', 'crispy lettuce', 'iceberg'],
            'cucumber': ['cucumber'],
            'carrot': ['carrot'],
            'potato': ['potato', 'sweet potato', 'baby potato'],
            'spinach': ['spinach', 'baby spinach'],
            'broccoli': ['broccoli'],
            'cauliflower': ['cauliflower'],
            'cabbage': ['cabbage', 'red cabbage', 'green cabbage'],
            'avocado': ['avocado', 'avo'],
            'lemon': ['lemon'],
            'lime': ['lime'],
            'orange': ['orange'],
            'apple': ['apple', 'red apple'],
            'grape': ['grape', 'green grape', 'red grape'],
            'strawberry': ['strawberry', 'strawberries'],
            'banana': ['banana'],
            'pineapple': ['pineapple'],
            'herb': ['herb', 'mint', 'parsley', 'rosemary', 'thyme', 'basil', 'dill', 'coriander', 'rocket'],
        }
        
        for product_type, variations in type_mappings.items():
            if any(variation in name_lower for variation in variations):
                product_types.append(product_type)
                # Also add specific variations
                for variation in variations:
                    if variation in name_lower:
                        product_types.append(variation)
        
        return list(set(product_types))  # Remove duplicates
    
    def _get_alias_matches(self, product_name: str, parsed_message: ParsedMessage) -> List[SmartMatchResult]:
        """Get matches based on aliases and common names"""
        alias_matches = []
        product_name_lower = product_name.lower()
        quantity = parsed_message.quantity
        unit = parsed_message.unit
        
        # COMMENTED OUT FOR TESTING: Check if the product name matches any aliases
        # for alias, replacement in self.aliases.items():
        #     if alias in product_name_lower:
        #         # Search for products containing the replacement
        #         replacement_matches = Product.objects.filter(name__icontains=replacement)[:10]
        #         for product in replacement_matches:
        #             score = self._calculate_fuzzy_score(product, parsed_message, 'alias_match')
        #             if score > 0:
        #                 alias_matches.append(SmartMatchResult(
        #                     product=product,
        #                     quantity=quantity,
        #                     unit=product.unit,  # Always use product's unit
        #                     confidence_score=score,
        #                     match_details={
        #                         'strategy': 'alias_match',
        #                         'matched_alias': alias,
        #                         'replacement': replacement,
        #                         'product_name': product.name
        #                     }
        #                 ))
        
        return alias_matches
    
    def _get_spelling_corrections(self, product_name: str, parsed_message: ParsedMessage) -> List[SmartMatchResult]:
        """Get matches based on common spelling corrections"""
        spelling_corrections = []
        product_name_lower = product_name.lower()
        quantity = parsed_message.quantity
        unit = parsed_message.unit
        
        # Common spelling corrections - multi-word first, then single-word
        spelling_fixes = {
           # Multi-word corrections (checked first)
           'rose marry': 'rosemary',
           'gingsorry thyme': 'ginger thyme',
           'patty pen': 'patty pan',
           
           # Single-word corrections
           'cabage': 'cabbage',
           'marry': 'marrow',
           'chilli': 'chili',
           'chillies': 'chilies',
           'tumeric': 'turmeric',
           'brinjals': 'aubergine',
           'brinjal': 'aubergine',
           'mellon': 'melon',
           'mellons': 'melons',
           'cauloflower': 'cauliflower',
           'caulofower': 'cauliflower',
           'pattypan': 'patty pan',
           'naatjies': 'naartjies',
           'naatjie': 'naartjie',
           'gingsorry': 'ginger',
           'avos': 'avocado',
           'avo': 'avocado',
           'avacado': 'avocado',
           'avacados': 'avocados',
           'brocolli': 'broccoli',
           'cucmber': 'cucumber',
           'cucmbers': 'cucumbers',
           'lettuce': 'lettuce',
           'lettuse': 'lettuce',
           'tomatoe': 'tomato',
           'tomatoes': 'tomato',
           'onion': 'onion',
           'onions': 'onion',
           'pepper': 'pepper',
           'peppers': 'pepper',
           'mushroom': 'mushroom',
           'mushrooms': 'mushroom',
       }
        
        # Check for exact phrase matches first (highest priority)
        for misspelling, correction in spelling_fixes.items():
            if ' ' in misspelling and misspelling in product_name_lower:
                # Multi-word correction - exact phrase match
                correction_matches = Product.objects.filter(name__icontains=correction)[:5]
                for product in correction_matches:
                    score = self._calculate_fuzzy_score(product, parsed_message, 'spelling_correction')
                    if score > 0:
                        spelling_corrections.append(SmartMatchResult(
                            product=product,
                            quantity=quantity,
                            unit=product.unit,  # Always use product's unit
                            confidence_score=score,
                            match_details={
                                'strategy': 'spelling_correction',
                                'misspelling': misspelling,
                                'correction': correction,
                                'product_name': product.name
                            }
                        ))
        
        # If we found multi-word matches, return them (don't check single-word matches)
        if spelling_corrections:
            return spelling_corrections
        
        # Then check for single-word corrections (only if no multi-word matches found)
        for misspelling, correction in spelling_fixes.items():
            if ' ' not in misspelling and misspelling in product_name_lower:
                # Single-word correction
                correction_matches = Product.objects.filter(name__icontains=correction)[:5]
                for product in correction_matches:
                    score = self._calculate_fuzzy_score(product, parsed_message, 'spelling_correction')
                    if score > 0:
                        spelling_corrections.append(SmartMatchResult(
                            product=product,
                            quantity=quantity,
                            unit=product.unit,  # Always use product's unit
                            confidence_score=score,
                            match_details={
                                'strategy': 'spelling_correction',
                                'misspelling': misspelling,
                                'correction': correction,
                                'product_name': product.name
                            }
                        ))
        
        return spelling_corrections
    
    def _calculate_score(self, product: Product, parsed_message: ParsedMessage) -> float:
        """Calculate confidence score for a product match"""
        score = 0
        product_name_lower = product.name.lower()
        parsed_name = parsed_message.product_name.lower()
        base_product_name = self._extract_base_product_name(parsed_message.product_name).lower()
        
        # Exact name match (already case-insensitive since both are lowercased)
        if parsed_name == product_name_lower:
            score += 50
        
        # PRIORITY: Check if search term matches the START of product name
        # This ensures "cherry" matches "Cherry Tomatoes" before "Tomatoes (Cherry)"
        elif product_name_lower.startswith(parsed_name):
            # Search term matches the beginning of product name - HIGH PRIORITY
            score += 45  # Very high score for prefix match
        elif parsed_name.startswith(product_name_lower):
            # Product name matches the beginning of search term - also good
            score += 40  # High score for reverse prefix match
        
        # Check for alias matches first (ensure case-insensitive)
        # COMMENTED OUT: Removed hardcoded alias matching to focus on strict name matching
        # elif parsed_name.lower() in self.aliases and self.aliases[parsed_name.lower()] in product_name_lower:
        #     score += 45
        
        # Check for exact word matches using word boundaries (prevents "potatoes" matching "sweet potatoes")
        else:
            parsed_words = parsed_name.split()
            
            # Check if ALL parsed words exist as complete words in product name
            # BUT also ensure we're not matching a subset (e.g., "potatoes" shouldn't match "sweet potatoes")
            parsed_word_set = set(parsed_words)
            product_word_set = set(product_name_lower.split())
            
            # Only match if:
            # 1. All parsed words exist as complete words in product name, AND
            # 2. Either the parsed words are exactly the product words, OR
            # 3. The product words are a superset that makes sense (like "baby potatoes" for "potatoes")
            
            all_words_match = True
            for word in parsed_words:
                # Use word boundaries to ensure exact word match, not substring
                if not re.search(r'\b' + re.escape(word) + r'\b', product_name_lower):
                    all_words_match = False
                    break
            
            if all_words_match:
                # Additional check: if parsed is subset of product, ensure it's a valid relationship
                extra_words = product_word_set - parsed_word_set
                
                # Allow certain modifier words (like "baby", "mini", "organic", etc.)
                allowed_modifiers = {'baby', 'mini', 'organic', 'fresh', 'crispy', 'mixed'}
                
                if not extra_words:
                    # Exact match - highest score
                    score += 50
                elif extra_words.issubset(allowed_modifiers):
                    # Valid modifier relationship (e.g., "baby potatoes" for "potatoes")
                    score += 40
                else:
                    # Invalid relationship (e.g., "sweet potatoes" for "potatoes")
                    score += 5  # Very low score
            
            # Base product name matching (high priority for container/weight products) - STRICT WORD BOUNDARIES
            elif base_product_name:
                # Check if base_product_name appears as complete words (not substring)
                base_words = base_product_name.split()
                base_all_words_match = True
                for word in base_words:
                    if not re.search(r'\b' + re.escape(word.lower()) + r'\b', product_name_lower):
                        base_all_words_match = False
                        break
                if base_all_words_match:
                    score += 35
                else:
                    score += 5  # Low score for no match
            else:
                # No match at all
                score += 5
        
        # Packaging size matching (highest priority when available)
        if parsed_message.packaging_size:
            packaging_size = parsed_message.packaging_size.lower()
            
            # Use regex to find exact packaging size matches, not substring matches
            # This prevents "5kg" from matching within "15kg"
            packaging_pattern = r'\b' + re.escape(packaging_size) + r'\b'
            if re.search(packaging_pattern, product_name_lower):
                score += 50  # Very high bonus for exact packaging size match
            else:
                # Check for similar packaging sizes (e.g., "200g" vs "200g")
                packaging_match = re.search(r'(\d+(?:\.\d+)?)(kg|g|ml|l)', packaging_size)
                if packaging_match:
                    size_num = packaging_match.group(1)
                    size_unit = packaging_match.group(2)
                    # Look for the same size in the product name with word boundaries
                    size_pattern = r'\b' + re.escape(f"{size_num}{size_unit}") + r'\b'
                    if re.search(size_pattern, product_name_lower):
                        score += 45  # High bonus for same size
                    # Penalty logic moved to end of function for consistency
        
        # Color-specific matching bonus/penalty
        # Enhanced color matching logic for better product variations
        color_words = self._get_color_words()
        parsed_colors = [word for word in parsed_name.split() if word in color_words]
        product_colors = [word for word in product_name_lower.split() if word in color_words]
        
        # Check if this is a color-variant product (like onions, apples, peppers)
        color_variant_products = {'onions', 'onion', 'apples', 'apple', 'peppers', 'pepper', 'grapes', 'grape', 'chillies', 'chilli', 'chili'}
        is_color_variant_product = any(variant in parsed_name.lower() for variant in color_variant_products) or \
                                 any(variant in product_name_lower for variant in color_variant_products)
        
        if parsed_colors and product_colors:
            if set(parsed_colors) == set(product_colors):
                score += 25  # Exact color match bonus
            elif any(color in product_colors for color in parsed_colors):
                score += 15  # Partial color match bonus
            else:
                # Different colors - penalty depends on product type
                if is_color_variant_product:
                    score -= 20  # Moderate penalty for color variants (red vs white onions)
                else:
                    score -= 40  # Strong penalty for different colors on non-variants
        elif parsed_colors and not product_colors:
            # Parsed has color but product doesn't - penalty depends on context
            if is_color_variant_product:
                score -= 25  # Moderate penalty for color variants
            else:
                score -= 50  # Strong penalty for missing expected color
        elif not parsed_colors and product_colors:
            # Product has color but parsed doesn't - this is often acceptable for variants
            if is_color_variant_product:
                # For color variants like onions/apples, having a color when none specified is OK
                # "onions" should match "red onions" reasonably well
                score += 5   # Small bonus - color variants are more specific/better
            else:
                score -= 15  # Small penalty for unexpected color on non-variants
        
        # Enhanced product type matching with exact product prioritization
        # COMMENTED OUT: Removed hardcoded product type matching to focus on strict name matching
        # product_type_words = self._get_product_type_words()
        # parsed_types = [word for word in parsed_name.split() if word in product_type_words]
        # product_types = [word for word in product_name_lower.split() if word in product_type_words]
        parsed_types = []
        product_types = []
        
        # Check for product variations (spring onions vs regular onions)
        variation_words = {'spring', 'cocktail', 'cherry', 'baby', 'mini', 'wild', 'crispy'}
        parsed_variations = [word for word in parsed_name.lower().split() if word in variation_words]
        product_variations = [word for word in product_name_lower.split() if word in variation_words]
        
        # Exact product name matching (highest priority)
        # Add words that indicate DIFFERENT products, not just variations
        different_product_words = {'sweet', 'sour', 'bitter', 'hot', 'cold', 'frozen', 'dried', 'pickled'}
        
        parsed_core_words = set(parsed_name.lower().split()) - set(color_words) - set(variation_words) - {'kg', 'g', 'box', 'bag', 'punnet', 'packet', 'bunch', 'head', 'each', 'piece'}
        product_core_words = set(product_name_lower.split()) - set(color_words) - set(variation_words) - {'kg', 'g', 'box', 'bag', 'punnet', 'packet', 'bunch', 'head', 'each', 'piece'}
        
        # Check if there are different-product words that would make this a mismatch
        parsed_different_words = set(parsed_name.lower().split()) & different_product_words
        product_different_words = set(product_name_lower.split()) & different_product_words
        
        if parsed_core_words and product_core_words:
            if parsed_core_words == product_core_words:
                # Check for different-product word conflicts
                if parsed_different_words != product_different_words:
                    # Different product types (e.g., "potatoes" vs "sweet potatoes")
                    score += 5  # Very low score for different product types
            else:
                score += 50  # Huge bonus for exact core product match (onions = onions)
                
                # Additional bonus for exact product type matches with colors
                if parsed_colors and product_colors and set(parsed_colors) == set(product_colors):
                    score += 25  # Extra bonus for exact color + product match
            
            if parsed_core_words.issubset(product_core_words) or product_core_words.issubset(parsed_core_words):
                # Check for different-product word conflicts in subset matching
                if parsed_different_words != product_different_words:
                    # Different product types - don't allow subset matching
                    score += 5  # Very low score
                else:
                    score += 35  # Large bonus for subset match
            elif len(parsed_core_words.intersection(product_core_words)) > 0:
                score += 20  # Medium bonus for partial core match
            else:
                score -= 30  # Penalty for completely different products
                
        # Specific product type prioritization to fix common mismatches
        # COMMENTED OUT: Removed hardcoded specific product matches to focus on strict name matching
        # parsed_lower = parsed_name.lower()
        # product_lower = product_name_lower
        # 
        # # Prioritize exact product matches over similar-sounding ones
        # specific_matches = {
        #     'onions': ['onions', 'onion'],
        #     'apples': ['apples', 'apple'], 
        #     'peppers': ['peppers', 'pepper'],
        #     'grapes': ['grapes', 'grape'],
        #     'chillies': ['chillies', 'chilli', 'chili']
        # }
        # 
        # for product_key, product_terms in specific_matches.items():
        #     if any(term in parsed_lower for term in product_terms):
        #         if any(term in product_lower for term in product_terms):
        #             score += 30  # Strong bonus for matching the right product category
        #         else:
        #             # Check if this is a different product category
        #             other_categories = [cat for cat in specific_matches.keys() if cat != product_key]
        #             if any(any(term in product_lower for term in specific_matches[other_cat]) for other_cat in other_categories):
        #                 score -= 25  # Penalty for wrong product category
        
        # COMMENTED OUT: Product type matching removed
        if False and parsed_types and product_types:
            if set(parsed_types) == set(product_types):
                # Same base product type - now check variations
                if parsed_variations and product_variations:
                    if set(parsed_variations) == set(product_variations):
                        score += 30  # Exact product type + variation match
                    else:
                        score -= 25  # Same product type but wrong variation
                elif parsed_variations and not product_variations:
                    score -= 30  # Expected variation but product doesn't have it
                elif not parsed_variations and product_variations:
                    # No variation specified but product has one
                    # This is often OK for base products (onions -> spring onions is less preferred)
                    if is_color_variant_product:
                        score -= 15  # Moderate penalty - prefer base variants over specialized ones
                    else:
                        score -= 5   # Very small penalty for other products
                else:
                    score += 25  # Perfect match - same type, no variations
            elif any(ptype in product_types for ptype in parsed_types):
                score += 10  # Partial product type match bonus
            else:
                score -= 15  # Penalty for wrong product type
        elif parsed_types and not product_types:
            score -= 20  # Penalty for missing product type
        elif not parsed_types and product_types:
            # Product has type words but parsed doesn't - usually OK
            score -= 5   # Small penalty
        
        # Specific tomato type matching (cherry vs cocktail)
        if 'cherry' in parsed_name and 'cherry' in product_name_lower:
            score += 15  # Bonus for exact cherry tomato match
        elif 'cherry' in parsed_name and 'cocktail' in product_name_lower:
            score -= 10  # Penalty for cherry vs cocktail mismatch
        elif 'cocktail' in parsed_name and 'cocktail' in product_name_lower:
            score += 15  # Bonus for exact cocktail tomato match
        elif 'cocktail' in parsed_name and 'cherry' in product_name_lower:
            score -= 10  # Penalty for cocktail vs cherry mismatch
        
        # Mixed product matching
        if 'mix' in parsed_name and 'mixed' in product_name_lower:
            score += 10  # Bonus for mix vs mixed match
        elif 'mixed' in parsed_name and 'mix' in product_name_lower:
            score += 10  # Bonus for mixed vs mix match
        
        # Partial name match - COMMENTED OUT: Removed substring fallback to focus on strict name matching
        # elif parsed_name in product_name_lower or product_name_lower in parsed_name:
        #     score += 30
        
        # Word-by-word matching with priority for exact product name
        parsed_words = set(parsed_name.split())
        product_words = set(product_name_lower.split())
        
        # Normalize words for better matching (handle singular/plural)
        def normalize_word(word):
            if word.endswith('s') and len(word) > 3:
                return word[:-1]  # Remove 's' for plurals
            return word
        
        normalized_parsed_words = {normalize_word(w) for w in parsed_words}
        normalized_product_words = {normalize_word(w) for w in product_words}
        
        # Find common words using normalized versions
        common_words = normalized_parsed_words.intersection(normalized_product_words)
        
        # Also check original words for exact matches
        original_common_words = parsed_words.intersection(product_words)
        common_words = common_words.union(original_common_words)
        
        if common_words:
            word_match_ratio = len(common_words) / max(len(parsed_words), len(product_words))
            # Only give word matching score if we have a reasonable match ratio
            if word_match_ratio >= 0.5:  # At least 50% of words must match
                score += word_match_ratio * 60  # MASSIVELY INCREASED: Product name match is KING
            else:
                # Very low word match ratio - penalize heavily
                score -= 20
                
            # Special bonus for multi-word products that match in any order (e.g., "lettuce mixed" vs "Mixed Lettuce")
            if len(parsed_words) > 1 and len(product_words) > 1 and len(common_words) == len(parsed_words) == len(product_words):
                score += 80  # MASSIVELY INCREASED: Perfect name match trumps everything
            
            # Extra bonus for reversed word order (e.g., "onion red" -> "Red Onions")
            parsed_words_list = list(parsed_words)
            product_words_list = list(product_words)
            if parsed_words_list == list(reversed(product_words_list)):
                score += 30  # Extra bonus for exact reversed word order
        
        # Unit matching (MINIMAL priority - product name is king)
        if parsed_message.unit:
            if parsed_message.unit == product.unit:
                score += 3  # TINY bonus - product name matters way more
            elif self._compatible_units(parsed_message.unit, product.unit):
                score += 1   # Almost nothing - product name matters way more
        
        # Packaging size matching (high priority for specific variants)
        if parsed_message.packaging_size:
            if parsed_message.packaging_size in product_name_lower:
                score += 30  # High bonus for exact packaging size match
            elif parsed_message.packaging_size.replace('kg', 'g') in product_name_lower:
                score += 25  # Bonus for compatible unit conversion
            elif parsed_message.packaging_size.replace('g', 'kg') in product_name_lower:
                score += 25  # Bonus for compatible unit conversion
        
        # Extra description matching (only if we have a reasonable product name match)
        if score >= 20:  # Only apply extra description bonus if we already have a decent product name match
            for desc in parsed_message.extra_descriptions:
                if desc in product_name_lower:
                    score += 15
        
        # Penalize if no meaningful match
        if score < 10:
            return 0
        
        # Apply packaging size penalties before capping
        if parsed_message.packaging_size:
            packaging_size = parsed_message.packaging_size.lower()
            packaging_pattern = r'\b' + re.escape(packaging_size) + r'\b'
            if not re.search(packaging_pattern, product_name_lower):
                # Check if the product has any packaging size at all
                has_packaging = re.search(r'\b\d+(?:\.\d+)?(kg|g|ml|l)\b', product_name_lower)
                if has_packaging:
                    score -= 25  # Penalty for wrong packaging size (applied before cap)
        else:
                    score -= 10  # Lighter penalty for products without specific packaging
        
        # Unit matching bonus - IMPROVED PRIORITY (MOVED BEFORE RETURN)
        if parsed_message.unit and product.unit:
            parsed_unit = parsed_message.unit.lower()
            product_unit = product.unit.lower()
            
            if parsed_unit == product_unit:
                # Unit match bonus - MINIMAL (product name is king)
                score += 3  # Tiny bonus - product name matters infinitely more
            elif self._compatible_units(parsed_message.unit, product.unit):
                score += 1  # Almost nothing - product name matters infinitely more
            else:
                # TINY penalty for unit mismatch - don't let unit override product name
                score -= 2  # Minimal penalty - product name is what matters
        
        # FINAL CHECK: Strong penalty for different-product words (applied after all bonuses)
        different_product_words = {'sweet', 'sour', 'bitter', 'hot', 'cold', 'frozen', 'dried', 'pickled'}
        parsed_different_words = set(parsed_message.product_name.lower().split()) & different_product_words
        product_different_words = set(product.name.lower().split()) & different_product_words
        
        if parsed_different_words != product_different_words:
            # Strong penalty for different product types (e.g., "potatoes" vs "sweet potatoes")
            score -= 80  # Heavy penalty to override unit bonuses
        
        final_score = min(max(score, 0), 100)  # Restore cap at 100
        
        
        return final_score
    
    
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
    
    def get_suggestions(self, message: str, min_confidence: float = 5.0, max_suggestions: int = 30, restaurant=None) -> SmartMatchSuggestions:
        """Get smart suggestions with multiple options when no good match is found
        
        Args:
            message: Product name or message string
            min_confidence: Minimum confidence score threshold
            max_suggestions: Maximum number of suggestions to return
            restaurant: Optional RestaurantProfile to filter by package restrictions
        """
        parsed_messages = self.parse_message(message)
        
        if not parsed_messages:
            return SmartMatchSuggestions(
                best_match=None,
                suggestions=[],
                parsed_input=ParsedMessage(quantity=0, unit=None, product_name="", extra_descriptions=[], original_message="", packaging_size=None),
                total_candidates=0
            )
        
        parsed = parsed_messages[0]  # Take first parsed result
        all_matches = self.find_matches(parsed, restaurant=restaurant)
        
        # Filter matches above minimum confidence
        valid_matches = [m for m in all_matches if m.confidence_score >= min_confidence]
        
        # Get best match (if confidence is high enough) - stricter threshold
        best_match = None
        if valid_matches and valid_matches[0].confidence_score >= 70:  # Increased from 50
            best_match = valid_matches[0]
        
        # Get top suggestions (including lower confidence ones for suggestions)
        suggestions = valid_matches[:max_suggestions]
        
        # If we don't have enough suggestions, try fuzzy matching
        # COMMENTED OUT: Removed fuzzy matching fallback to focus on strict name matching only
        # if len(suggestions) < max_suggestions:
        #     fuzzy_matches = self._get_fuzzy_suggestions(parsed, max_suggestions - len(suggestions))
        #     
        #     # Add fuzzy matches that aren't already in suggestions
        #     existing_ids = {s.product.id for s in suggestions}
        #     for fuzzy_match in fuzzy_matches:
        #         if fuzzy_match.product.id not in existing_ids:
        #             suggestions.append(fuzzy_match)
        
        return SmartMatchSuggestions(
            best_match=best_match,
            suggestions=suggestions[:max_suggestions],
            parsed_input=parsed,
            total_candidates=len(all_matches)
        )
    
    def _get_fuzzy_suggestions(self, parsed_message: ParsedMessage, max_suggestions: int) -> List[SmartMatchResult]:
        """Get fuzzy suggestions when exact matching fails"""
        return self._get_fuzzy_suggestions_from_database(parsed_message, max_suggestions)
    
    
    def _get_fuzzy_suggestions_from_database(self, parsed_message: ParsedMessage, max_suggestions: int) -> List[SmartMatchResult]:
        """Get comprehensive fuzzy suggestions from Django database"""
        product_name = parsed_message.product_name
        quantity = parsed_message.quantity
        unit = parsed_message.unit
        
        # Try comprehensive matching strategies
        fuzzy_matches = []
        
        # Strategy 1: Match individual words (broader search) - STRICT WORD BOUNDARIES
        import re
        words = product_name.split()
        for word in words:
            if len(word) > 2:  # Skip short words
                # Use regex to match complete words only (word boundaries)
                word_pattern = r'\b' + re.escape(word.lower()) + r'\b'
                # Get all products and filter by regex (more efficient than DB regex)
                all_products = Product.objects.all()[:1000]  # Limit for performance
                word_matches = [p for p in all_products if re.search(word_pattern, p.name.lower(), re.IGNORECASE)]
                for product in word_matches[:20]:  # Limit results
                    score = self._calculate_fuzzy_score(product, parsed_message, 'word_match')
                    if score > 0:
                        fuzzy_matches.append(SmartMatchResult(
                            product=product,
                            quantity=quantity,
                            unit=product.unit,  # Always use product's unit
                            confidence_score=score,
                            match_details={
                                'strategy': 'word_match',
                                'matched_word': word,
                                'product_name': product.name
                            }
                        ))
        
        # Strategy 1.5: Match base product name (remove containers/weights) - STRICT WORD BOUNDARIES
        base_name = self._extract_base_product_name(product_name)
        if base_name and base_name != product_name:
            # Use word boundaries for each word in base_name
            base_words = base_name.split()
            if base_words:
                # Match products that contain ALL base words as complete words
                base_word_patterns = [r'\b' + re.escape(w.lower()) + r'\b' for w in base_words]
                all_products = Product.objects.all()[:1000]  # Limit for performance
                base_matches = []
                for product in all_products:
                    product_name_lower = product.name.lower()
                    all_words_match = all(re.search(pattern, product_name_lower, re.IGNORECASE) for pattern in base_word_patterns)
                    if all_words_match:
                        base_matches.append(product)
                        if len(base_matches) >= 15:
                            break
                
                for product in base_matches:
                    score = self._calculate_fuzzy_score(product, parsed_message, 'base_name_match')
                    if score > 0:
                        fuzzy_matches.append(SmartMatchResult(
                            product=product,
                            quantity=quantity,
                            unit=unit or product.unit,
                            confidence_score=score,
                            match_details={
                                'strategy': 'base_name_match',
                                'matched_base_name': base_name,
                                'product_name': product.name
                            }
                        ))
        
        # Strategy 1.5: Match exact phrase - STRICT WORD BOUNDARIES
        # Match products that contain the phrase as complete words
        phrase_words = product_name.split()
        if phrase_words:
            phrase_patterns = [r'\b' + re.escape(w.lower()) + r'\b' for w in phrase_words]
            all_products = Product.objects.all()[:500]  # Limit for performance
            phrase_matches = []
            for product in all_products:
                product_name_lower = product.name.lower()
                all_words_match = all(re.search(pattern, product_name_lower, re.IGNORECASE) for pattern in phrase_patterns)
                if all_words_match:
                    phrase_matches.append(product)
                    if len(phrase_matches) >= 5:
                        break
            
            for product in phrase_matches:
                score = self._calculate_fuzzy_score(product, parsed_message, 'phrase_match')
                
                if score > 0:
                    fuzzy_matches.append(SmartMatchResult(
                        product=product,
                        quantity=quantity,
                        unit=unit or product.unit,
                        confidence_score=score,
                        match_details={
                            'strategy': 'phrase_match',
                            'matched_phrase': product_name,
                            'product_name': product.name
                        }
                    ))
        
        # Strategy 2: Match with word order variations (e.g., "onion red" -> "Red Onions") - STRICT WORD BOUNDARIES
        if len(words) >= 2:
            # Try reversed word order - require ALL words as complete words
            reversed_words = list(reversed(words))
            reversed_patterns = [r'\b' + re.escape(w.lower()) + r'\b' for w in reversed_words]
            all_products = Product.objects.all()[:500]  # Limit for performance
            reversed_matches = []
            for product in all_products:
                product_name_lower = product.name.lower()
                all_words_match = all(re.search(pattern, product_name_lower, re.IGNORECASE) for pattern in reversed_patterns)
                if all_words_match:
                    reversed_matches.append(product)
                    if len(reversed_matches) >= 5:
                        break
            
            for product in reversed_matches:
                score = self._calculate_fuzzy_score(product, parsed_message, 'reversed_word_match')
                if score > 0:
                    fuzzy_matches.append(SmartMatchResult(
                        product=product,
                        quantity=quantity,
                        unit=unit or product.unit,
                        confidence_score=score,
                        match_details={
                            'strategy': 'reversed_word_match',
                            'reversed_name': ' '.join(reversed_words),
                            'product_name': product.name
                        }
                    ))
            
            # Try partial word order matches - require ALL words as complete words
            for i in range(len(words)):
                partial_words = words[i:]
                if len(partial_words) > 0 and len(' '.join(partial_words)) > 3:
                    partial_patterns = [r'\b' + re.escape(w.lower()) + r'\b' for w in partial_words]
                    all_products = Product.objects.all()[:300]  # Limit for performance
                    partial_matches = []
                    for product in all_products:
                        product_name_lower = product.name.lower()
                        all_words_match = all(re.search(pattern, product_name_lower, re.IGNORECASE) for pattern in partial_patterns)
                        if all_words_match:
                            partial_matches.append(product)
                            if len(partial_matches) >= 3:
                                break
                    
                    for product in partial_matches:
                        score = self._calculate_fuzzy_score(product, parsed_message, 'partial_word_match')
                        if score > 0:
                            fuzzy_matches.append(SmartMatchResult(
                                product=product,
                                quantity=quantity,
                                unit=unit or product.unit,
                                confidence_score=score,
                                match_details={
                                    'strategy': 'partial_word_match',
                                    'partial_name': ' '.join(partial_words),
                                    'product_name': product.name
                                }
                            ))
        
        # Strategy 3: Match by unit if specified
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
        
        # Strategy 4: Match by extra descriptions
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
        
        # Strategy 5: Similar sounding products (basic phonetic matching)
        if len(product_name) > 3:
            similar_matches = self._get_phonetic_matches(product_name, parsed_message)
            fuzzy_matches.extend(similar_matches)
        
        # Strategy 6: Match by product type/category (broader matching)
        # COMMENTED OUT: Removed hardcoded product type mappings to focus on strict name matching
        # product_types = self._get_product_types(product_name)
        # for product_type in product_types:
        #     type_matches = Product.objects.filter(name__icontains=product_type)[:10]
        #     for product in type_matches:
        #         score = self._calculate_fuzzy_score(product, parsed_message, 'type_match')
        #         if score > 0:
        #             fuzzy_matches.append(SmartMatchResult(
        #                 product=product,
        #                 quantity=quantity,
        #                 unit=unit or product.unit,
        #                 confidence_score=score,
        #                 match_details={
        #                     'strategy': 'type_match',
        #                     'matched_type': product_type,
        #                     'product_name': product.name
        #                 }
        #             ))
        
        # Strategy 7: Match by aliases and common names
        # COMMENTED OUT: Removed hardcoded alias mappings to focus on strict name matching
        # alias_matches = self._get_alias_matches(product_name, parsed_message)
        # fuzzy_matches.extend(alias_matches)
        
        # Strategy 8: Common spelling corrections
        # COMMENTED OUT: Removed hardcoded spelling corrections to focus on strict name matching
        # spelling_corrections = self._get_spelling_corrections(product_name, parsed_message)
        # fuzzy_matches.extend(spelling_corrections)
        
        # Strategy 8: Match by partial word combinations
        if len(words) > 1:
            for i in range(len(words)):
                for j in range(i + 1, len(words) + 1):
                    partial_phrase = ' '.join(words[i:j])
                    if len(partial_phrase) > 3:
                        partial_matches = Product.objects.filter(name__icontains=partial_phrase)[:5]
                        for product in partial_matches:
                            score = self._calculate_fuzzy_score(product, parsed_message, 'partial_phrase_match')
                            if score > 0:
                                fuzzy_matches.append(SmartMatchResult(
                                    product=product,
                                    quantity=quantity,
                                    unit=unit or product.unit,
                                    confidence_score=score,
                                    match_details={
                                        'strategy': 'partial_phrase_match',
                                        'matched_phrase': partial_phrase,
                                        'product_name': product.name
                                    }
                                ))
        
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
        elif strategy == 'base_name_match':
            score = 40  # Higher score for base name matches
        elif strategy == 'phrase_match':
            score = 40  # Higher score for exact phrase matches
        elif strategy == 'reversed_word_match':
            score = 35  # Higher score for reversed word matches
        elif strategy == 'partial_word_match':
            score = 30  # Good score for partial matches
        elif strategy == 'partial_phrase_match':
            score = 25  # Good score for partial phrase matches
        elif strategy == 'unit_match':
            score = 20
        elif strategy == 'description_match':
            score = 30
        elif strategy == 'type_match':
            score = 35  # Good score for product type matches
        elif strategy == 'alias_match':
            score = 45  # High score for alias matches
        elif strategy == 'spelling_correction':
            score = 50  # Very high score for spelling corrections
        elif strategy == 'phonetic_match':
            score = 15
        
        # Boost score for additional matches
        if parsed_name in product_name_lower or product_name_lower in parsed_name:
            score += 15
        
        # Product type preference - NEW
        # Prefer exact product types over variations
        if self._is_exact_product_type_match(parsed_name, product_name_lower):
            score += 20
        elif self._is_product_variation(parsed_name, product_name_lower):
            score -= 5  # Slight penalty for variations
        
        # Boost score for multiple word matches
        parsed_words = set(parsed_name.split())
        product_words = set(product_name_lower.split())
        common_words = parsed_words.intersection(product_words)
        if len(common_words) > 1:
            score += len(common_words) * 5  # Bonus for multiple word matches
        
        
        # Package size matching bonus - NEW
        parsed_name_lower = parsed_message.product_name.lower()
        product_name_lower = product.name.lower()
        
        # Extract package sizes from both names
        import re
        parsed_sizes = re.findall(r'(\d+(?:\.\d+)?)\s*(kg|g|ml|l)', parsed_name_lower)
        product_sizes = re.findall(r'(\d+(?:\.\d+)?)\s*(kg|g|ml|l)', product_name_lower)
        
        if parsed_sizes and product_sizes:
            # Convert to comparable format (grams)
            parsed_weight = self._normalize_weight_to_grams(parsed_sizes[0])
            product_weight = self._normalize_weight_to_grams(product_sizes[0])
            
            if parsed_weight == product_weight:
                score += 20  # Exact package size match
            elif abs(parsed_weight - product_weight) / max(parsed_weight, product_weight) < 0.2:
                score += 10  # Close package size match (within 20%)
            else:
                # Penalty for significantly wrong package size
                score -= 10
        
        # Description matching bonus
        for desc in parsed_message.extra_descriptions:
            if desc in product_name_lower:
                score += 10
        
        # Penalize very long product names (less likely to be what user wants)
        if len(product.name) > 50:
            score -= 5
        
        # ENHANCED CONFIDENCE SCORING - Normalize to 0-100 scale
        # Base scores are now more meaningful
        if score >= 80:
            confidence_level = "Excellent"  # 80-100: Very high confidence
        elif score >= 60:
            confidence_level = "Good"       # 60-79: Good confidence  
        elif score >= 40:
            confidence_level = "Fair"       # 40-59: Fair confidence
        elif score >= 20:
            confidence_level = "Poor"       # 20-39: Poor confidence
        else:
            confidence_level = "Very Poor"  # 0-19: Very poor confidence
        
        # Cap score at 100 for better interpretation
        normalized_score = min(100, max(0, score))
        
        return normalized_score
    
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
    
    
    
    def _calculate_string_similarity(self, str1: str, str2: str) -> float:
        """Calculate enhanced string similarity with word-based matching"""
        str1_lower = str1.lower().strip()
        str2_lower = str2.lower().strip()
        
        # Exact match
        if str1_lower == str2_lower:
            return 1.0
        
        # Check if one contains the other
        if str1_lower in str2_lower or str2_lower in str1_lower:
            return 0.8
        
        # Word-based matching
        words1 = set(str1_lower.split())
        words2 = set(str2_lower.split())
        
        if not words1 or not words2:
            return 0.0
        
        # Calculate word overlap
        common_words = words1.intersection(words2)
        if common_words:
            # All words match
            if len(common_words) == len(words1) and len(common_words) == len(words2):
                return 0.9
            # Most words match
            elif len(common_words) >= min(len(words1), len(words2)) * 0.7:
                return 0.7
            # Some words match
            else:
                return 0.5
        
        # Character-based Jaccard similarity as fallback
        set1 = set(str1_lower)
        set2 = set(str2_lower)
        
        intersection = set1.intersection(set2)
        union = set1.union(set2)
        
        if not union:
            return 0.0
        
        return len(intersection) / len(union)
    
    def _fuzzy_match(self, str1: str, str2: str) -> bool:
        """Check if two strings are fuzzy matches"""
        return self._calculate_string_similarity(str1, str2) > 0.4
    
    def _normalize_weight_to_grams(self, weight_tuple) -> float:
        """Convert weight to grams for comparison"""
        amount, unit = weight_tuple
        amount = float(amount)
        unit = unit.lower()
        
        if unit == 'kg':
            return amount * 1000
        elif unit == 'g':
            return amount
        elif unit == 'ml':
            return amount  # Treat ml as grams for comparison
        elif unit == 'l':
            return amount * 1000  # Treat liters as kg equivalent
        else:
            return amount
    
    def _is_exact_product_type_match(self, parsed_name: str, product_name: str) -> bool:
        """Check if this is an exact product type match (e.g., 'onions' matches 'red onions' better than 'spring onions')"""
        parsed_words = set(parsed_name.lower().split())
        product_words = set(product_name.lower().split())
        
        # Remove color words and size words for core product matching
        color_words = {'red', 'green', 'white', 'yellow', 'purple', 'orange', 'black'}
        size_words = {'baby', 'mini', 'large', 'small', 'medium', 'big'}
        
        parsed_core = parsed_words - color_words - size_words
        product_core = product_words - color_words - size_words
        
        # Exact core match (e.g., 'onions' core matches 'red onions' core)
        return len(parsed_core) > 0 and parsed_core.issubset(product_core)
    
    def _is_product_variation(self, parsed_name: str, product_name: str) -> bool:
        """Check if this is a product variation (e.g., 'onions' matching 'spring onions')"""
        parsed_words = set(parsed_name.lower().split())
        product_words = set(product_name.lower().split())
        
        # Check for variation keywords
        variation_words = {'spring', 'cocktail', 'cherry', 'deveined', 'mixed', 'crispy'}
        
        # If product has variation words but parsed doesn't, it's a variation
        product_variations = product_words.intersection(variation_words)
        parsed_variations = parsed_words.intersection(variation_words)
        
        return len(product_variations) > 0 and len(parsed_variations) == 0

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
