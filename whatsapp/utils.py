"""
WhatsApp Message Parsing Utilities
Implements free/low-cost parsing with manual patterns and Claude API fallback
"""
import re
import json
import logging
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
from django.conf import settings

logger = logging.getLogger(__name__)


class MessageParser:
    """Manual pattern-based message parser for common WhatsApp orders"""
    
    def __init__(self):
        # Common order patterns with realistic restaurant quantities
        self.patterns = {
            # Quantity + product patterns (e.g., "2 x onions", "3x tomatoes")
            r'(\d+)\s*x?\s*onions?': {'product': 'Red Onions', 'unit': 'kg', 'default_qty': 5},
            r'(\d+)\s*x?\s*tomatoes?': {'product': 'Tomatoes', 'unit': 'kg', 'default_qty': 3},
            r'(\d+)\s*x?\s*potatoes?': {'product': 'Potatoes', 'unit': 'kg', 'default_qty': 10},
            r'(\d+)\s*x?\s*carrots?': {'product': 'Carrots', 'unit': 'kg', 'default_qty': 2},
            r'(\d+)\s*x?\s*cabbage': {'product': 'Cabbage', 'unit': 'kg', 'default_qty': 3},
            r'(\d+)\s*x?\s*lettuce': {'product': 'Lettuce', 'unit': 'head', 'default_qty': 2},
            r'(\d+)\s*x?\s*spinach': {'product': 'Spinach', 'unit': 'kg', 'default_qty': 1},
            
            # Weight-specific patterns (e.g., "5kg potatoes", "2kg onions")
            r'(\d+(?:\.\d+)?)\s*kg\s*(\w+)': {'extract_product': True, 'unit': 'kg'},
            r'(\d+(?:\.\d+)?)\s*g\s*(\w+)': {'extract_product': True, 'unit': 'g'},
            
            # Bunch/piece patterns (e.g., "3 bunches carrots", "5 pieces lettuce")
            r'(\d+)\s*bunch(?:es)?\s*(?:of\s*)?(\w+)': {'extract_product': True, 'unit': 'bunch'},
            r'(\d+)\s*pieces?\s*(?:of\s*)?(\w+)': {'extract_product': True, 'unit': 'piece'},
            r'(\d+)\s*heads?\s*(?:of\s*)?(\w+)': {'extract_product': True, 'unit': 'head'},
        }
        
        # Product name aliases for fuzzy matching
        self.product_aliases = {
            'onions': 'Red Onions',
            'onion': 'Red Onions', 
            'red onions': 'Red Onions',
            'white onions': 'White Onions',
            'tomatoes': 'Tomatoes',
            'tomato': 'Tomatoes',
            'cherry tomatoes': 'Cherry Tomatoes',
            'potatoes': 'Potatoes',
            'potato': 'Potatoes',
            'carrots': 'Carrots',
            'carrot': 'Carrots',
            'cabbage': 'Cabbage',
            'lettuce': 'Lettuce',
            'spinach': 'Spinach',
            'broccoli': 'Broccoli',
            'cauliflower': 'Cauliflower',
            'peppers': 'Bell Peppers',
            'pepper': 'Bell Peppers',
            'bell peppers': 'Bell Peppers',
        }
        
        # Typical restaurant order quantities (for "x" patterns)
        self.typical_quantities = {
            'Red Onions': 5,      # "1 x onions" = 5kg
            'Tomatoes': 3,        # "1 x tomatoes" = 3kg  
            'Potatoes': 10,       # "1 x potatoes" = 10kg
            'Carrots': 2,         # "1 x carrots" = 2kg
            'Cabbage': 3,         # "1 x cabbage" = 3kg
            'Lettuce': 2,         # "1 x lettuce" = 2 heads
            'Spinach': 1,         # "1 x spinach" = 1kg
        }
    
    def parse_message(self, message_text: str) -> Dict:
        """Parse WhatsApp message into structured order items"""
        message_text = message_text.lower().strip()
        
        parsed_items = []
        confidence_scores = []
        matched_text = set()  # Track what we've already matched
        
        # Try each pattern
        for pattern, config in self.patterns.items():
            matches = re.finditer(pattern, message_text, re.IGNORECASE)
            
            for match in matches:
                # Skip if we've already matched this text
                if match.group(0) in matched_text:
                    continue
                    
                item = self._process_match(match, config)
                if item:
                    parsed_items.append(item)
                    confidence_scores.append(item.get('confidence', 0.5))
                    matched_text.add(match.group(0))
        
        # If no patterns matched, try fuzzy matching
        if not parsed_items:
            fuzzy_items = self._fuzzy_parse(message_text)
            parsed_items.extend(fuzzy_items)
            confidence_scores.extend([0.3] * len(fuzzy_items))
        
        # Calculate overall confidence
        overall_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
        
        return {
            'items': parsed_items,
            'confidence': round(overall_confidence, 2),
            'original_message': message_text,
            'parsing_method': 'manual_patterns',
            'needs_review': overall_confidence < 0.7 or len(parsed_items) == 0,
            'matched_patterns': len(parsed_items),
            'total_items': len(parsed_items)
        }
    
    def _process_match(self, match, config) -> Optional[Dict]:
        """Process a regex match into an order item"""
        groups = match.groups()
        
        try:
            if config.get('extract_product'):
                # Pattern like "5 kg potatoes" or "3 bunches carrots"
                quantity = Decimal(str(groups[0]))
                product_text = groups[1].lower().strip()
                product_name = self.product_aliases.get(product_text, product_text.title())
                
                return {
                    'product_name': product_name,
                    'quantity': float(quantity),
                    'unit': config['unit'],
                    'confidence': 0.8,
                    'original_text': match.group(0),
                    'parsing_notes': f'Extracted from pattern: {match.group(0)}'
                }
            else:
                # Pattern like "2 x onions" - use typical quantities
                multiplier = int(groups[0]) if groups else 1
                product_name = config['product']
                typical_qty = self.typical_quantities.get(product_name, config.get('default_qty', 1))
                final_quantity = multiplier * typical_qty
                
                return {
                    'product_name': product_name,
                    'quantity': float(final_quantity),
                    'unit': config['unit'],
                    'confidence': 0.9,
                    'original_text': match.group(0),
                    'parsing_notes': f'Interpreted "{match.group(0)}" as {final_quantity}{config["unit"]} (typical restaurant portion)'
                }
                
        except (ValueError, IndexError) as e:
            logger.warning(f"Error processing match {match.group(0)}: {e}")
            return None
    
    def _fuzzy_parse(self, message_text: str) -> List[Dict]:
        """Fallback fuzzy parsing for unmatched text"""
        items = []
        
        # Look for product names without quantities
        for alias, product_name in self.product_aliases.items():
            if alias in message_text and len(alias) > 3:  # Avoid short false matches
                typical_qty = self.typical_quantities.get(product_name, 1)
                
                items.append({
                    'product_name': product_name,
                    'quantity': float(typical_qty),
                    'unit': 'kg',  # Default unit
                    'confidence': 0.3,
                    'original_text': alias,
                    'parsing_notes': f'Fuzzy match: found "{alias}" in message, using typical quantity',
                    'needs_manual_review': True
                })
        
        return items


class ClaudeParser:
    """Claude API integration for complex message parsing"""
    
    def __init__(self):
        self.api_key = getattr(settings, 'CLAUDE_API_KEY', None)
        self.available_products = self._get_available_products()
    
    def parse_with_claude(self, message_text: str) -> Dict:
        """Use Claude API to parse complex messages (fallback)"""
        
        if not self.api_key:
            logger.info("Claude API key not configured, using manual parsing only")
            manual_parser = MessageParser()
            return manual_parser.parse_message(message_text)
        
        try:
            import anthropic
            
            client = anthropic.Anthropic(api_key=self.api_key)
            
            prompt = self._build_claude_prompt(message_text)
            
            response = client.messages.create(
                model="claude-3-haiku-20240307",  # Cheapest model
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
            )
            
            result = json.loads(response.content[0].text)
            result['parsing_method'] = 'claude_api'
            result['needs_review'] = result.get('overall_confidence', 0) < 0.8
            
            return result
            
        except Exception as e:
            logger.error(f"Claude API error: {e}")
            # Fallback to manual parsing
            manual_parser = MessageParser()
            result = manual_parser.parse_message(message_text)
            result['claude_error'] = str(e)
            result['parsing_method'] = 'manual_fallback'
            return result
    
    def _build_claude_prompt(self, message_text: str) -> str:
        """Build Claude API prompt with context"""
        return f"""
Parse this restaurant WhatsApp order message into specific products:
"{message_text}"

Available products: {', '.join(self.available_products)}

Parsing rules:
- "1 x onions" typically means 5kg Red Onions (standard restaurant order)
- "2 x tomatoes" typically means 6kg Tomatoes (2 × 3kg)
- "potatoes" without quantity usually means 10kg
- Convert vague quantities to realistic restaurant portions
- If quantity is unclear, use typical restaurant order sizes
- Mark low confidence items for manual review

Return ONLY valid JSON in this exact format:
{{
    "items": [
        {{"product_name": "Red Onions", "quantity": 5.0, "unit": "kg", "confidence": 0.9, "parsing_notes": "Interpreted '1 x onions' as 5kg"}},
        {{"product_name": "Tomatoes", "quantity": 6.0, "unit": "kg", "confidence": 0.8, "parsing_notes": "2 x typical 3kg portions"}}
    ],
    "confidence": 0.85,
    "total_items": 2,
    "parsing_method": "claude_api"
}}
"""
    
    def _get_available_products(self) -> List[str]:
        """Get list of available products from database"""
        try:
            from products.models import Product
            return list(Product.objects.filter(is_active=True).values_list('name', flat=True))
        except Exception:
            # Fallback list if database not available
            return ['Red Onions', 'Tomatoes', 'Potatoes', 'Carrots', 'Cabbage', 'Lettuce', 'Spinach']


def parse_whatsapp_message(message_text: str, use_claude: bool = False) -> Dict:
    """
    Smart parsing with multiple fallbacks
    
    Args:
        message_text: The WhatsApp message to parse
        use_claude: Whether to try Claude API first (default: False for cost control)
    
    Returns:
        Dict with parsed items, confidence scores, and metadata
    """
    
    # Try Claude first if requested and available
    if use_claude and hasattr(settings, 'CLAUDE_API_KEY') and settings.CLAUDE_API_KEY:
        claude_parser = ClaudeParser()
        result = claude_parser.parse_with_claude(message_text)
        
        # If confidence is high enough, use Claude result
        if result.get('confidence', 0) > 0.7:
            return result
        
        logger.info(f"Claude confidence too low ({result.get('confidence')}), falling back to manual parsing")
    
    # Use manual patterns (primary method)
    manual_parser = MessageParser()
    result = manual_parser.parse_message(message_text)
    
    # Add suggestion to try Claude if manual parsing failed
    if result.get('confidence', 0) < 0.5 and result.get('total_items', 0) == 0:
        result['suggestion'] = 'Consider using Claude API for this complex message'
        result['claude_available'] = hasattr(settings, 'CLAUDE_API_KEY') and bool(settings.CLAUDE_API_KEY)
    
    return result


# Test function for development
def test_message_parsing():
    """Test the parsing functionality with sample messages"""
    
    test_messages = [
        "Hi, can I get 2 x onions and 3 x tomatoes?",
        "Need 5kg potatoes and 2 bunches carrots please",
        "1 x onions, some tomatoes, and 2kg carrots",
        "Can I order 3 heads lettuce and spinach?",
        "2x cabbage, 10kg potatoes, 1 x onions",
        "vegetables for tomorrow - onions, tomatoes, carrots",
    ]
    
    parser = MessageParser()
    
    print("=== WhatsApp Message Parsing Test ===\n")
    
    for i, message in enumerate(test_messages, 1):
        print(f"Test {i}: {message}")
        result = parser.parse_message(message)
        
        print(f"  Confidence: {result['confidence']}")
        print(f"  Items found: {result['total_items']}")
        print(f"  Needs review: {result['needs_review']}")
        
        for item in result['items']:
            print(f"    - {item['product_name']}: {item['quantity']}{item['unit']} (confidence: {item['confidence']})")
            if 'parsing_notes' in item:
                print(f"      Notes: {item['parsing_notes']}")
        
        print()


if __name__ == "__main__":
    test_message_parsing()
