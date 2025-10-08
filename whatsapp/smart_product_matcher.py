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
        """Load and analyze all products from database"""
        # Use database directly
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
        
        # Step 2: Find unit/container words - look for number+unit combinations first
        unit = None
        unit_word = None
        unit_index = -1
        
        # First check for number+unit combinations (like "5kg", "200g")
        # Sort units by length (longest first) to prioritize "kg" over "g"
        sorted_units = sorted(self.valid_units, key=len, reverse=True)
        for i, word in enumerate(words):
            for valid_unit in sorted_units:
                # Check if word ends with unit AND starts with a number
                if word.endswith(valid_unit) and len(word) > len(valid_unit):
                    # Verify it actually starts with a number
                    number_match = re.search(r'^(\d+(?:\.\d+)?)', word)
                    if number_match:
                        # This word contains a number + unit
                        unit = valid_unit
                        unit_word = word
                        unit_index = i
                        break
            if unit:
                break
        
        # If no number+unit found, look for standalone units
        if not unit:
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
            
        # Step 4: Determine quantity and extra descriptions
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
        product_name = self._apply_aliases(product_name)
        
        # Clean up product name - remove extra 's' and fix common issues
        product_name = self._clean_product_name(product_name)
        
        # Check for ambiguous packaging specifications
        ambiguous_packaging = self._is_ambiguous_packaging(original_item, unit, packaging_size)
        
        # Always allow parsing, but mark ambiguous packaging for special handling
        if ambiguous_packaging:
            # Add a flag to indicate this needs suggestions due to ambiguous packaging
            extra_descriptions.append("AMBIGUOUS_PACKAGING")
        
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
            # Get all product names and extract potential color words
            all_products = Product.objects.all()
            color_words = set()
            
            # Common color patterns in product names
            color_patterns = [
                r'\b(red|green|yellow|white|brown|black|blue|purple|orange|pink|violet|indigo|turquoise|maroon|navy|olive|lime|cyan|magenta)\b',
                r'\b(light|dark|bright|pale|deep|vivid|muted|neon|pastel)\s+(red|green|yellow|white|brown|black|blue|purple|orange|pink|violet|indigo|turquoise|maroon|navy|olive|lime|cyan|magenta)\b'
            ]
            
            for product in all_products:
                product_name = product.name.lower()
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
            # Get all product names and extract potential product type words
            all_products = Product.objects.all()
            type_words = set()
            
            # Words to exclude (units, containers, measurements, etc.)
            exclude_words = {
                'kg', 'g', 'ml', 'l', 'box', 'bag', 'packet', 'punnet', 'bunch', 'head', 'each', 'piece',
                'pcs', 'tray', 'large', 'small', 'medium', 'big', 'tiny', 'mini', 'jumbo', 'extra',
                'fresh', 'frozen', 'dried', 'canned', 'organic', 'local', 'imported', 'premium',
                'grade', 'quality', 'a', 'an', 'the', 'and', 'or', 'of', 'in', 'on', 'at', 'to', 'for',
                'with', 'by', 'from', 'up', 'down', 'out', 'off', 'over', 'under', 'through'
            }
            
            for product in all_products:
                product_words = product.name.lower().split()
                for word in product_words:
                    # Clean the word (remove punctuation, numbers)
                    clean_word = re.sub(r'[^\w]', '', word)
                    
                    # Skip if too short, excluded, or contains numbers
                    if (len(clean_word) < 3 or 
                        clean_word in exclude_words or 
                        re.search(r'\d', clean_word) or
                        clean_word in ['', ' ']):
                        continue
                    
                    # Check if this word appears in multiple products (likely a product type)
                    if Product.objects.filter(name__icontains=clean_word).count() > 1:
                        type_words.add(clean_word)
            
            self._cached_product_type_words = list(type_words)
        
        return self._cached_product_type_words
    
    def find_matches(self, parsed_message: ParsedMessage) -> List[SmartMatchResult]:
        """Find matching products using database"""
        return self._find_matches_from_database(parsed_message)
    
    
    def _find_matches_from_database(self, parsed_message: ParsedMessage) -> List[SmartMatchResult]:
        """Find matches from Django database (fallback)"""
        product_name = parsed_message.product_name
        quantity = parsed_message.quantity
        unit = parsed_message.unit
        extra_descriptions = parsed_message.extra_descriptions
        packaging_size = parsed_message.packaging_size
        
        # Extract base product name by removing common container/weight words
        base_product_name = self._extract_base_product_name(product_name)
        
        # Build Q query for product name matching
        name_queries = Q()
        
        # Try multiple search strategies
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
        
        # Create queries for all search terms
        for term in search_terms:
            name_queries |= Q(name__icontains=term)
        
        # Get initial candidates
        candidates = Product.objects.filter(name_queries)
        
        # If we have packaging size, prioritize products that contain it with word boundaries
        if packaging_size:
            # Use regex to find exact packaging size matches, not substring matches
            # This prevents "5kg" from matching within "15kg"
            import re
            packaging_pattern = r'\b' + re.escape(packaging_size) + r'\b'
            packaging_candidates = [c for c in candidates if re.search(packaging_pattern, c.name, re.IGNORECASE)]
            if packaging_candidates:
                # Use packaging-specific candidates as primary, others as secondary
                all_candidates = list(candidates)
                # Put packaging matches first
                candidates = packaging_candidates + [c for c in all_candidates if c not in packaging_candidates]
        
        # Filter by unit if specified, but don't force it if it reduces matches too much
        # If packaging size is present, skip unit filtering to prioritize packaging size matching
        if unit and not packaging_size:
            unit_candidates = candidates.filter(unit=unit)
            # Use unit filtering if we have any candidates, but prefer more candidates
            if unit_candidates.exists():
                if len(unit_candidates) >= 3:
                    candidates = unit_candidates
        else:
                    # If unit filtering gives us too few candidates, use both but prioritize unit matches
                    all_candidates = list(candidates)
                    unit_candidates_list = list(unit_candidates)
                    # Put unit matches first
                    candidates = unit_candidates_list + [c for c in all_candidates if c not in unit_candidates_list]
        
        # Filter by extra descriptions (like "200g", "large", etc.)
        if extra_descriptions and not isinstance(candidates, list):
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
                        'base_name': base_product_name,
                        'matched_name': product.name,
                        'unit_match': unit == product.unit if unit else False,
                        'description_matches': [d for d in extra_descriptions if d in product.name.lower()],
                        'name_word_matches': [w for w in base_product_name.split() if w in product.name.lower()]
                    }
                ))
        
        # Sort by confidence score
        results.sort(key=lambda x: x.confidence_score, reverse=True)
        
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
        
        # Check if the product name matches any aliases
        for alias, replacement in self.aliases.items():
            if alias in product_name_lower:
                # Search for products containing the replacement
                replacement_matches = Product.objects.filter(name__icontains=replacement)[:10]
                for product in replacement_matches:
                    score = self._calculate_fuzzy_score(product, parsed_message, 'alias_match')
                    if score > 0:
                        alias_matches.append(SmartMatchResult(
                            product=product,
                            quantity=quantity,
                            unit=unit or product.unit,
                            confidence_score=score,
                            match_details={
                                'strategy': 'alias_match',
                                'matched_alias': alias,
                                'replacement': replacement,
                                'product_name': product.name
                            }
                        ))
        
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
                            unit=unit or product.unit,
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
                            unit=unit or product.unit,
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
        
        # Exact name match
        if parsed_name == product_name_lower:
            score += 50
        
        # Check for alias matches first
        elif parsed_name in self.aliases and self.aliases[parsed_name] in product_name_lower:
            score += 45
        
        # Check for exact phrase match in product name (highest priority)
        elif parsed_name in product_name_lower:
            score += 45
        
        # Check for exact word matches in product name (ALL words must match)
        elif all(word in product_name_lower for word in parsed_name.split()):
            # Count how many words match exactly
            matched_words = sum(1 for word in parsed_name.split() if word in product_name_lower)
            total_words = len(parsed_name.split())
            if matched_words == total_words:
                score += 50  # High score for exact word match
                else:
                score += 30  # Lower score for partial word match
        
        # Base product name matching (high priority for container/weight products)
        elif base_product_name and base_product_name in product_name_lower:
            score += 35
        
        # Check for base product word matches (ALL words must match)
        elif base_product_name and all(word in product_name_lower for word in base_product_name.split()):
            score += 30
        
        # Penalty for partial matches that don't include all words
        else:
            # Check if we have some words matching but not all
        parsed_words = set(parsed_name.split())
        product_words = set(product_name_lower.split())
        common_words = parsed_words.intersection(product_words)
        
            if common_words and len(common_words) < len(parsed_words):
                # Some words match but not all - this is likely a wrong match
                score -= 50  # Heavy penalty for partial word matches
            elif not common_words:
                # No words match at all
                score -= 100  # Very heavy penalty for no word matches
        
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
            else:
                        score -= 30  # Penalty for different packaging size
        
        # Color-specific matching bonus/penalty
        color_words = self._get_color_words()
        parsed_colors = [word for word in parsed_name.split() if word in color_words]
        product_colors = [word for word in product_name_lower.split() if word in color_words]
        
        if parsed_colors and product_colors:
            if set(parsed_colors) == set(product_colors):
                score += 25  # Exact color match bonus
            elif any(color in product_colors for color in parsed_colors):
                score += 15  # Partial color match bonus
                else:
                # Different colors - strong penalty
                score -= 40  # Strong penalty for different colors
        elif parsed_colors and not product_colors:
            # Penalty for color mismatch - if parsed has color but product doesn't
            score -= 50  # Very strong penalty for missing expected color
        elif not parsed_colors and product_colors:
            # Penalty for extra color - if product has color but parsed doesn't
            score -= 30  # Strong penalty for unexpected color
        
        # Product type matching bonus/penalty
        product_type_words = self._get_product_type_words()
        parsed_types = [word for word in parsed_name.split() if word in product_type_words]
        product_types = [word for word in product_name_lower.split() if word in product_type_words]
        
        if parsed_types and product_types:
            if set(parsed_types) == set(product_types):
                score += 20  # Exact product type match bonus
            elif any(ptype in product_types for ptype in parsed_types):
                score += 10  # Partial product type match bonus
                else:
                score -= 15  # Penalty for wrong product type
        
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
        
        # Partial name match
        elif parsed_name in product_name_lower or product_name_lower in parsed_name:
            score += 30
        
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
                score += word_match_ratio * 40  # Increased from 25 for better name matching
            else:
                # Very low word match ratio - penalize heavily
                score -= 20
                
            # Special bonus for multi-word products that match in any order (e.g., "lettuce mixed" vs "Mixed Lettuce")
            if len(parsed_words) > 1 and len(product_words) > 1 and len(common_words) == len(parsed_words) == len(product_words):
                score += 50  # High bonus for multi-word products matching in any order
            
            # Extra bonus for reversed word order (e.g., "onion red" -> "Red Onions")
            parsed_words_list = list(parsed_words)
            product_words_list = list(product_words)
            if parsed_words_list == list(reversed(product_words_list)):
                score += 30  # Extra bonus for exact reversed word order
        
        # Unit matching (reduced priority)
        if parsed_message.unit:
            if parsed_message.unit == product.unit:
                score += 10  # Reduced from 20
            elif self._compatible_units(parsed_message.unit, product.unit):
                score += 5   # Reduced from 10
        
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
    
    def get_suggestions(self, message: str, min_confidence: float = 5.0, max_suggestions: int = 20) -> SmartMatchSuggestions:
        """Get smart suggestions with multiple options when no good match is found"""
        parsed_messages = self.parse_message(message)
        
        if not parsed_messages:
            return SmartMatchSuggestions(
                best_match=None,
                suggestions=[],
                parsed_input=ParsedMessage(quantity=0, unit=None, product_name="", extra_descriptions=[], original_message="", packaging_size=None),
                total_candidates=0
            )
        
        parsed = parsed_messages[0]  # Take first parsed result
        all_matches = self.find_matches(parsed)
        
        # Filter matches above minimum confidence
        valid_matches = [m for m in all_matches if m.confidence_score >= min_confidence]
        
        # Get best match (if confidence is high enough) - stricter threshold
        best_match = None
        if valid_matches and valid_matches[0].confidence_score >= 70:  # Increased from 50
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
            return self._get_fuzzy_suggestions_from_database(parsed_message, max_suggestions)
    
    
    def _get_fuzzy_suggestions_from_database(self, parsed_message: ParsedMessage, max_suggestions: int) -> List[SmartMatchResult]:
        """Get comprehensive fuzzy suggestions from Django database"""
        product_name = parsed_message.product_name
        quantity = parsed_message.quantity
        unit = parsed_message.unit
        
        # Try comprehensive matching strategies
        fuzzy_matches = []
        
        # Strategy 1: Match individual words (broader search)
        words = product_name.split()
        for word in words:
            if len(word) > 2:  # Skip short words
                word_matches = Product.objects.filter(name__icontains=word)[:20]  # Increased from 10
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
        
        # Strategy 1.5: Match base product name (remove containers/weights)
        base_name = self._extract_base_product_name(product_name)
        if base_name and base_name != product_name:
            base_matches = Product.objects.filter(name__icontains=base_name)[:15]
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
        
        # Strategy 1.5: Match exact phrase
        phrase_matches = Product.objects.filter(name__icontains=product_name)[:5]
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
        
        # Strategy 2: Match with word order variations (e.g., "onion red" -> "Red Onions")
        if len(words) >= 2:
            # Try reversed word order
            reversed_name = ' '.join(reversed(words))
            reversed_matches = Product.objects.filter(name__icontains=reversed_name)[:5]
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
                            'reversed_name': reversed_name,
                            'product_name': product.name
                        }
                    ))
            
            # Try partial word order matches
            for i in range(len(words)):
                partial_name = ' '.join(words[i:])
                if len(partial_name) > 3:
                    partial_matches = Product.objects.filter(name__icontains=partial_name)[:3]
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
                                    'partial_name': partial_name,
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
        product_types = self._get_product_types(product_name)
        for product_type in product_types:
            type_matches = Product.objects.filter(name__icontains=product_type)[:10]
            for product in type_matches:
                score = self._calculate_fuzzy_score(product, parsed_message, 'type_match')
                if score > 0:
                    fuzzy_matches.append(SmartMatchResult(
                        product=product,
                        quantity=quantity,
                        unit=unit or product.unit,
                        confidence_score=score,
                        match_details={
                            'strategy': 'type_match',
                            'matched_type': product_type,
                            'product_name': product.name
                        }
                    ))
        
        # Strategy 7: Match by aliases and common names
        alias_matches = self._get_alias_matches(product_name, parsed_message)
        fuzzy_matches.extend(alias_matches)
        
        # Strategy 8: Common spelling corrections
        spelling_corrections = self._get_spelling_corrections(product_name, parsed_message)
        fuzzy_matches.extend(spelling_corrections)
        
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
        
        # Boost score for multiple word matches
        parsed_words = set(parsed_name.split())
        product_words = set(product_name_lower.split())
        common_words = parsed_words.intersection(product_words)
        if len(common_words) > 1:
            score += len(common_words) * 5  # Bonus for multiple word matches
        
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
