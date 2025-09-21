"""
Order Item Parser - Preserved from original WhatsApp processing system
Handles sophisticated order item extraction with quantity patterns
"""

import re
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass


@dataclass
class OrderItem:
    """Structured representation of an order item"""
    text: str
    quantity: Optional[str] = None
    unit: Optional[str] = None
    product: Optional[str] = None
    confidence: float = 0.0


class OrderItemParser:
    """
    Extract and parse order items from WhatsApp messages
    Preserves all original business logic and quantity patterns
    """
    
    def __init__(self):
        self.quantity_patterns = self._load_quantity_patterns()
        self.product_keywords = self._load_product_keywords()
        
    def _load_quantity_patterns(self) -> List[str]:
        """
        PRESERVED: Quantity detection patterns from original system
        These patterns were refined through real WhatsApp message analysis
        """
        return [
            r'\d+\s*x\s*\d*\s*kg',  # 2x5kg, 10x kg
            r'\d+\s*kg',            # 10kg, 5 kg
            r'\d+\s*box',           # 3box, 5 box
            r'\d+\s*boxes',         # 3boxes
            r'x\d+',                # x3, x12
            r'\d+x',                # 3x, 12x
            r'\d+\*',               # 3*, 5*
            r'\d+\s*pcs',           # 5pcs, 10 pcs
            r'\d+\s*pieces',        # 5pieces
            r'\d+\s*pkts',          # 6pkts
            r'\d+\s*packets',       # 6packets
            r'\d+\s*heads',         # 5heads
            r'\d+\s*bunches',       # 10bunches
            r'\d+\s*bags',          # 5bags
            r'\d+\s*tubs',          # 3tubs
            r'\d+\s*trays',         # 2trays
        ]
    
    def _load_product_keywords(self) -> List[str]:
        """
        ENHANCED: Product keywords based on real inventory data
        Helps identify order items vs other message content
        """
        return [
            # Vegetables (from real SHALLOME stock reports)
            'carrot', 'carrots', 'lettuce', 'onion', 'onions', 'potato', 'potatoes',
            'tomato', 'tomatoes', 'cabbage', 'spinach', 'beetroot', 'cucumber',
            'pepper', 'peppers', 'broccoli', 'cauliflower', 'celery', 'leek',
            'parsley', 'coriander', 'mint', 'basil', 'thyme', 'rosemary',
            
            # Fruits
            'apple', 'apples', 'banana', 'bananas', 'orange', 'oranges',
            'lemon', 'lemons', 'lime', 'limes', 'avocado', 'avocados',
            
            # Common units/containers
            'bag', 'bags', 'box', 'boxes', 'tub', 'tubs', 'tray', 'trays',
            'head', 'heads', 'bunch', 'bunches', 'packet', 'packets',
            'piece', 'pieces', 'kg', 'gram', 'grams'
        ]
    
    def extract_order_items(self, text: str) -> List[OrderItem]:
        """
        PRESERVED: Extract order items from message text
        Enhanced with structured output and confidence scoring
        """
        if not text:
            return []
        
        items = []
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        for line in lines:
            # Skip lines that are clearly not order items
            if self._is_greeting_or_instruction(line):
                continue
            
            # Check if line contains quantity indicators
            if self._has_quantity_indicators(line):
                item = self._parse_order_line(line)
                if item:
                    items.append(item)
            # Check if line contains product keywords (even without explicit quantities)
            elif self._contains_product_keywords(line):
                item = self._parse_product_line(line)
                if item:
                    items.append(item)
        
        return items
    
    def extract_items_text(self, text: str) -> str:
        """
        PRESERVED: Extract order items as text (backward compatibility)
        Returns concatenated item text for existing integrations
        """
        items = self.extract_order_items(text)
        if not items:
            return ""
        
        item_texts = [item.text for item in items]
        return '\n'.join(item_texts)
    
    def _has_quantity_indicators(self, text: str) -> bool:
        """
        PRESERVED: Check if text contains quantity indicators
        Original logic from message_parser.py
        """
        if not text:
            return False
            
        text_upper = text.upper()
        for pattern in self.quantity_patterns:
            if re.search(pattern, text_upper, re.IGNORECASE):
                return True
        
        return False
    
    def _contains_product_keywords(self, text: str) -> bool:
        """Check if text contains product-related keywords"""
        text_lower = text.lower()
        
        for keyword in self.product_keywords:
            if keyword in text_lower:
                return True
        
        return False
    
    def _parse_order_line(self, line: str) -> Optional[OrderItem]:
        """
        Parse a line that contains quantity indicators
        Extract quantity, unit, and product information
        """
        line_clean = line.strip()
        
        # Extract quantity and unit using patterns
        quantity_info = self._extract_quantity_info(line_clean)
        
        # Extract product name (remaining text after removing quantity)
        product_text = self._extract_product_text(line_clean, quantity_info)
        
        # Calculate confidence based on various factors
        confidence = self._calculate_item_confidence(line_clean, quantity_info, product_text)
        
        return OrderItem(
            text=line_clean,
            quantity=quantity_info.get('quantity'),
            unit=quantity_info.get('unit'),
            product=product_text,
            confidence=confidence
        )
    
    def _parse_product_line(self, line: str) -> Optional[OrderItem]:
        """
        Parse a line that contains product keywords but no explicit quantity
        These might be items with implied quantities
        """
        line_clean = line.strip()
        
        # Check if it's a reasonable product line
        if len(line_clean) < 2 or len(line_clean) > 100:
            return None
        
        # Calculate confidence (lower for items without explicit quantities)
        confidence = self._calculate_product_confidence(line_clean)
        
        if confidence > 0.3:  # Minimum confidence threshold
            return OrderItem(
                text=line_clean,
                product=line_clean,
                confidence=confidence
            )
        
        return None
    
    def _extract_quantity_info(self, text: str) -> Dict[str, Optional[str]]:
        """Extract quantity and unit information from text"""
        text_upper = text.upper()
        
        for pattern in self.quantity_patterns:
            match = re.search(pattern, text_upper, re.IGNORECASE)
            if match:
                quantity_text = match.group(0)
                
                # Parse the quantity text to extract number and unit
                numbers = re.findall(r'\d+', quantity_text)
                
                # Determine unit
                unit = None
                if 'KG' in quantity_text:
                    unit = 'kg'
                elif 'BOX' in quantity_text:
                    unit = 'boxes'
                elif 'HEAD' in quantity_text:
                    unit = 'heads'
                elif 'BUNCH' in quantity_text:
                    unit = 'bunches'
                elif 'PCS' in quantity_text or 'PIECE' in quantity_text:
                    unit = 'pieces'
                elif 'PKT' in quantity_text or 'PACKET' in quantity_text:
                    unit = 'packets'
                elif 'BAG' in quantity_text:
                    unit = 'bags'
                elif 'TUB' in quantity_text:
                    unit = 'tubs'
                elif 'TRAY' in quantity_text:
                    unit = 'trays'
                
                # Determine quantity
                quantity = numbers[0] if numbers else None
                
                return {
                    'quantity': quantity,
                    'unit': unit,
                    'raw_text': quantity_text
                }
        
        return {'quantity': None, 'unit': None, 'raw_text': None}
    
    def _extract_product_text(self, line: str, quantity_info: Dict) -> Optional[str]:
        """Extract product name by removing quantity information"""
        if quantity_info.get('raw_text'):
            # Remove the quantity text to get product name
            product_text = line.replace(quantity_info['raw_text'], '').strip()
            
            # Clean up common separators
            product_text = re.sub(r'^[-\s]+|[-\s]+$', '', product_text)
            
            if product_text:
                return product_text
        
        # If no quantity found, the whole line might be the product
        return line.strip()
    
    def _calculate_item_confidence(self, line: str, quantity_info: Dict, product_text: Optional[str]) -> float:
        """Calculate confidence score for order item recognition"""
        confidence = 0.0
        
        # Base confidence for having quantity indicators
        if quantity_info.get('quantity'):
            confidence += 0.4
        
        if quantity_info.get('unit'):
            confidence += 0.2
        
        # Boost confidence for known product keywords
        if product_text:
            product_lower = product_text.lower()
            for keyword in self.product_keywords:
                if keyword in product_lower:
                    confidence += 0.3
                    break
        
        # Reduce confidence for instruction-like content
        if self._is_greeting_or_instruction(line):
            confidence *= 0.1
        
        # Boost confidence for reasonable line length
        if 5 <= len(line) <= 50:
            confidence += 0.1
        
        return min(confidence, 1.0)  # Cap at 1.0
    
    def _calculate_product_confidence(self, line: str) -> float:
        """Calculate confidence for product lines without explicit quantities"""
        confidence = 0.0
        
        line_lower = line.lower()
        
        # Check for product keywords
        keyword_matches = sum(1 for keyword in self.product_keywords if keyword in line_lower)
        confidence += min(keyword_matches * 0.2, 0.6)
        
        # Reduce confidence for instruction-like content
        if self._is_greeting_or_instruction(line):
            confidence *= 0.1
        
        # Reasonable length
        if 3 <= len(line) <= 30:
            confidence += 0.1
        
        return confidence
    
    def _is_greeting_or_instruction(self, text: str) -> bool:
        """
        PRESERVED: Check if text is greeting or instruction
        Original logic from message_parser.py
        """
        if not text:
            return False
            
        text_upper = text.upper()
        
        # PRESERVED: Greeting and instruction keywords
        greeting_keywords = [
            'GOOD MORNING', 'GOOD AFTERNOON', 'GOOD EVENING', 'HELLO', 'HI',
            'THANKS', 'THANK YOU', 'PLEASE', 'KINDLY', 'REGARDS', 'CHEERS',
            'NOTE', 'REMEMBER', 'SEPARATE INVOICE', 'SEPERATE INVOICE',
            'THAT\'S ALL', 'THATS ALL', 'TNX', 'CHEERS'
        ]
        
        for keyword in greeting_keywords:
            if keyword in text_upper:
                return True
                
        return False
    
    def extract_instructions(self, text: str) -> str:
        """
        PRESERVED: Extract instructions from message text
        Separates delivery notes and special requests from order items
        """
        if not text:
            return ""
        
        instruction_lines = []
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        for line in lines:
            # Include lines that are clearly instructions
            if self._is_greeting_or_instruction(line):
                instruction_lines.append(line)
            # Include lines that don't look like order items but contain useful info
            elif not self._has_quantity_indicators(line) and not self._contains_product_keywords(line):
                # Check if it's a meaningful instruction (not just random text)
                if self._is_meaningful_instruction(line):
                    instruction_lines.append(line)
        
        return '\n'.join(instruction_lines)
    
    def _is_meaningful_instruction(self, line: str) -> bool:
        """Check if a line contains meaningful instruction content"""
        line_clean = line.strip()
        
        # Skip very short or very long lines
        if len(line_clean) < 3 or len(line_clean) > 200:
            return False
        
        # Look for instruction indicators
        instruction_indicators = [
            'deliver', 'delivery', 'invoice', 'separate', 'note', 'remember',
            'urgent', 'asap', 'today', 'tomorrow', 'monday', 'tuesday', 'wednesday',
            'thursday', 'friday', 'saturday', 'sunday', 'morning', 'afternoon',
            'evening', 'pm', 'am'
        ]
        
        line_lower = line_clean.lower()
        for indicator in instruction_indicators:
            if indicator in line_lower:
                return True
        
        return False
    
    def get_parsing_stats(self) -> Dict[str, int]:
        """Get statistics about order item parsing"""
        return {
            'quantity_patterns': len(self.quantity_patterns),
            'product_keywords': len(self.product_keywords),
            'supported_units': len(set(pattern for pattern in self.quantity_patterns if 'kg' in pattern or 'box' in pattern))
        }


# Singleton instance for efficient reuse
_order_item_parser_instance = None

def get_order_item_parser() -> OrderItemParser:
    """Get singleton OrderItemParser instance"""
    global _order_item_parser_instance
    if _order_item_parser_instance is None:
        _order_item_parser_instance = OrderItemParser()
    return _order_item_parser_instance

