"""
WhatsApp Message Parser - Extract companies and order items from messages
Handles the complex parsing logic that was previously in JavaScript
"""

import re
import json
import os
from typing import List, Dict, Any, Optional, Tuple


class MessageParser:
    def __init__(self):
        self.company_aliases = self._load_company_aliases()
        self.quantity_patterns = self._load_quantity_patterns()
        
    def _load_company_aliases(self) -> Dict[str, str]:
        """Load company aliases mapping from config file"""
        try:
            # Try to load from place-order-final config first
            config_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'place-order-final', 'python', 'config', 'company_aliases.json')
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    return config.get('company_aliases', {})
        except Exception as e:
            print(f"⚠️ Failed to load company aliases config: {e}")
        
        # Fallback to default aliases
        return {
            "mugg and bean": "Mugg and Bean",
            "mugg bean": "Mugg and Bean", 
            "mugg": "Mugg and Bean",
            "venue": "Venue",
            "debonairs": "Debonairs",
            "t-junction": "T-junction",
            "t junction": "T-junction",
            "wimpy": "Wimpy",
            "wimpy mooinooi": "Wimpy",
            "shebeen": "Shebeen",
            "casa bella": "Casa Bella",
            "casabella": "Casa Bella",
            "luma": "Luma",
            "marco": "Marco",
            "maltos": "Maltos"
        }
    
    def _load_quantity_patterns(self) -> List[str]:
        """Load quantity detection patterns from config file"""
        try:
            config_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'place-order-final', 'python', 'config', 'company_aliases.json')
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    return config.get('quantity_patterns', [])
        except Exception as e:
            print(f"⚠️ Failed to load quantity patterns config: {e}")
        
        # Fallback to default patterns
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
        ]
    
    def to_canonical_company(self, text: str) -> Optional[str]:
        """Convert text to canonical company name"""
        if not text:
            return None
            
        text_lower = text.lower().strip()
        
        # Direct match
        if text_lower in self.company_aliases:
            return self.company_aliases[text_lower]
            
        # Partial match
        for alias, canonical in self.company_aliases.items():
            if alias in text_lower or text_lower in alias:
                return canonical
                
        return None
    
    def has_quantity_indicators(self, text: str) -> bool:
        """Check if text contains quantity indicators"""
        if not text:
            return False
            
        text_upper = text.upper()
        for pattern in self.quantity_patterns:
            if re.search(pattern, text_upper, re.IGNORECASE):
                return True
                
        return False
    
    def is_likely_order_item(self, text: str) -> bool:
        """Check if text looks like an order item"""
        if not text or len(text.strip()) < 3:
            return False
            
        text = text.strip()
        
        # Has quantity indicators
        if self.has_quantity_indicators(text):
            return True
            
        # Contains food/product keywords
        food_keywords = [
            'tomato', 'potato', 'onion', 'lettuce', 'spinach', 'carrot',
            'mushroom', 'pepper', 'cucumber', 'broccoli', 'cauliflower',
            'cabbage', 'rocket', 'lemon', 'orange', 'banana', 'apple',
            'avocado', 'corn', 'butternut', 'marrow', 'chilli', 'basil',
            'parsley', 'coriander', 'rosemary', 'strawberry', 'lime',
            'naartjie', 'ginger', 'garlic', 'herbs', 'greens'
        ]
        
        text_lower = text.lower()
        for keyword in food_keywords:
            if keyword in text_lower:
                return True
                
        return False
    
    def extract_order_items(self, text: str) -> List[str]:
        """Extract order items from multi-line text"""
        if not text:
            return []
            
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        items = []
        
        for line in lines:
            # Skip greetings and instructions
            if self._is_greeting_or_instruction(line):
                continue
                
            # Skip company names
            if self.to_canonical_company(line):
                continue
                
            # Check if it's likely an order item
            if self.is_likely_order_item(line):
                items.append(line)
                
        return items
    
    def extract_instructions(self, text: str) -> List[str]:
        """Extract instructions/greetings from text"""
        if not text:
            return []
            
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        instructions = []
        
        for line in lines:
            if self._is_greeting_or_instruction(line) and not self.is_likely_order_item(line):
                instructions.append(line)
                
        return instructions
    
    def clean_message_content(self, text: str) -> str:
        """Remove company names from message content to avoid confusion with manual selection"""
        if not text:
            return text
            
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line_stripped = line.strip()
            if not line_stripped:
                continue
                
            # Skip lines that are just company names
            if self.to_canonical_company(line_stripped):
                continue
                
            cleaned_lines.append(line)
            
        return '\n'.join(cleaned_lines)
    
    def _is_greeting_or_instruction(self, text: str) -> bool:
        """Check if text is a greeting or instruction"""
        if not text:
            return False
            
        text_upper = text.upper()
        
        greeting_keywords = [
            'GOOD MORNING', 'MORNING', 'HELLO', 'HI', 'HALLO',
            'THANKS', 'THANK YOU', 'PLEASE', 'PLZ', 'PLIZ',
            'NOTE', 'REMEMBER', 'SEPARATE INVOICE', 'SEPERATE INVOICE',
            'THAT\'S ALL', 'THATS ALL', 'TNX', 'CHEERS'
        ]
        
        # Use word boundary matching to avoid false positives like "CHILI" containing "HI"
        import re
        for keyword in greeting_keywords:
            # Create word boundary pattern for the keyword
            pattern = r'\b' + re.escape(keyword) + r'\b'
            if re.search(pattern, text_upper):
                return True
                
        return False


# Global parser instance for Django
django_message_parser = MessageParser()
