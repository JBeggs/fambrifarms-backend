# Free AI Message Parsing - Development Strategy

## 🎯 **Cost-Free AI Parsing During Development**

**Problem**: OpenAI API costs $0.0006-$0.015 per message  
**Solution**: Use Claude API (free tier) + manual patterns during development  
**Production**: Start simple, add complexity only when needed  

---

## 💰 **Cost Comparison**

### **OpenAI Costs (Expensive)**
```
GPT-3.5-turbo: $0.0015/1K input + $0.002/1K output tokens
GPT-4: $0.03/1K input + $0.06/1K output tokens

Daily cost for 50 messages:
- GPT-3.5: ~$0.03/day = $10.95/year
- GPT-4: ~$0.75/day = $273.75/year
```

### **Claude API (Free Tier)**
```
Claude 3 Haiku: Free tier available
Claude 3 Sonnet: Limited free usage
Claude 3 Opus: Pay-per-use

Development cost: $0 (using free tier)
```

### **Manual Patterns (Free)**
```python
# Simple regex patterns for common orders
PATTERNS = {
    r'(\d+)\s*x?\s*onions?': 'Red Onions',
    r'(\d+)\s*x?\s*tomatoes?': 'Tomatoes', 
    r'(\d+)\s*kg\s*potatoes?': 'Potatoes',
}
Cost: $0 forever
```

---

## 🛠️ **Development Implementation**

### **Phase 1: Manual Pattern Matching (Week 1)**
```python
# orders/utils/message_parser.py
import re
from typing import Dict, List, Optional
from .models import Product

class MessageParser:
    def __init__(self):
        self.patterns = {
            # Quantity + product patterns
            r'(\d+)\s*x?\s*onions?': {'product': 'Red Onions', 'unit': 'kg', 'default_qty': 5},
            r'(\d+)\s*x?\s*tomatoes?': {'product': 'Tomatoes', 'unit': 'kg', 'default_qty': 3},
            r'(\d+)\s*x?\s*potatoes?': {'product': 'Potatoes', 'unit': 'kg', 'default_qty': 10},
            r'(\d+)\s*x?\s*carrots?': {'product': 'Carrots', 'unit': 'kg', 'default_qty': 2},
            
            # Weight-specific patterns
            r'(\d+)\s*kg\s*(\w+)': {'extract_product': True, 'unit': 'kg'},
            r'(\d+)\s*g\s*(\w+)': {'extract_product': True, 'unit': 'g'},
            
            # Bunch/piece patterns
            r'(\d+)\s*bunch(?:es)?\s*(\w+)': {'extract_product': True, 'unit': 'bunch'},
            r'(\d+)\s*pieces?\s*(\w+)': {'extract_product': True, 'unit': 'piece'},
        }
        
        self.product_aliases = {
            'onions': 'Red Onions',
            'onion': 'Red Onions', 
            'red onions': 'Red Onions',
            'tomatoes': 'Tomatoes',
            'tomato': 'Tomatoes',
            'potatoes': 'Potatoes',
            'potato': 'Potatoes',
            'carrots': 'Carrots',
            'carrot': 'Carrots',
        }
    
    def parse_message(self, message_text: str) -> Dict:
        """Parse WhatsApp message into structured order items"""
        message_text = message_text.lower().strip()
        
        parsed_items = []
        confidence_scores = []
        
        for pattern, config in self.patterns.items():
            matches = re.finditer(pattern, message_text, re.IGNORECASE)
            
            for match in matches:
                item = self._process_match(match, config)
                if item:
                    parsed_items.append(item)
                    confidence_scores.append(item.get('confidence', 0.5))
        
        # If no patterns matched, try fuzzy matching
        if not parsed_items:
            fuzzy_items = self._fuzzy_parse(message_text)
            parsed_items.extend(fuzzy_items)
            confidence_scores.extend([0.3] * len(fuzzy_items))
        
        overall_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
        
        return {
            'items': parsed_items,
            'confidence': overall_confidence,
            'original_message': message_text,
            'parsing_method': 'manual_patterns',
            'needs_review': overall_confidence < 0.7
        }
    
    def _process_match(self, match, config) -> Optional[Dict]:
        """Process a regex match into an order item"""
        groups = match.groups()
        
        if config.get('extract_product'):
            # Pattern like "5 kg potatoes"
            quantity = int(groups[0])
            product_text = groups[1].lower()
            product_name = self.product_aliases.get(product_text, product_text.title())
            
            return {
                'product_name': product_name,
                'quantity': quantity,
                'unit': config['unit'],
                'confidence': 0.8,
                'original_text': match.group(0)
            }
        else:
            # Pattern like "2 x onions"
            quantity = int(groups[0]) if groups else config.get('default_qty', 1)
            
            return {
                'product_name': config['product'],
                'quantity': quantity,
                'unit': config['unit'],
                'confidence': 0.9,
                'original_text': match.group(0)
            }
    
    def _fuzzy_parse(self, message_text: str) -> List[Dict]:
        """Fallback fuzzy parsing for unmatched text"""
        items = []
        
        # Look for product names without quantities
        for alias, product_name in self.product_aliases.items():
            if alias in message_text:
                items.append({
                    'product_name': product_name,
                    'quantity': 1,  # Default quantity
                    'unit': 'kg',   # Default unit
                    'confidence': 0.3,
                    'original_text': alias,
                    'needs_manual_review': True
                })
        
        return items

# Usage example
parser = MessageParser()
result = parser.parse_message("Hi, can I get 2 x onions and 5kg tomatoes please")
print(result)
```

### **Phase 2: Claude API Integration (Week 2)**
```python
# orders/utils/claude_parser.py
import anthropic
from django.conf import settings
from typing import Dict
import json

class ClaudeParser:
    def __init__(self):
        self.client = anthropic.Anthropic(
            api_key=settings.CLAUDE_API_KEY  # Free tier key
        )
        
        self.available_products = self._get_available_products()
    
    def parse_with_claude(self, message_text: str) -> Dict:
        """Use Claude API to parse complex messages"""
        
        prompt = f"""
        Parse this restaurant order message into specific products:
        "{message_text}"
        
        Available products: {', '.join(self.available_products)}
        
        Rules:
        - "1 x onions" usually means 5kg Red Onions (typical restaurant order)
        - "tomatoes" usually means 3kg unless specified
        - Convert vague quantities to realistic restaurant portions
        - If unsure, mark for manual review
        
        Return JSON format:
        {{
            "items": [
                {{"product_name": "Red Onions", "quantity": 5, "unit": "kg", "confidence": 0.9}},
                {{"product_name": "Tomatoes", "quantity": 3, "unit": "kg", "confidence": 0.8}}
            ],
            "overall_confidence": 0.85,
            "notes": "Interpreted '1 x onions' as 5kg based on typical restaurant order size"
        }}
        """
        
        try:
            response = self.client.messages.create(
                model="claude-3-haiku-20240307",  # Cheapest model
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
            )
            
            result = json.loads(response.content[0].text)
            result['parsing_method'] = 'claude_api'
            return result
            
        except Exception as e:
            # Fallback to manual parsing if Claude fails
            manual_parser = MessageParser()
            result = manual_parser.parse_message(message_text)
            result['claude_error'] = str(e)
            return result
    
    def _get_available_products(self) -> List[str]:
        """Get list of available products from database"""
        from orders.models import Product
        return list(Product.objects.filter(is_active=True).values_list('name', flat=True))

# Usage with fallback
def parse_message_smart(message_text: str) -> Dict:
    """Smart parsing with multiple fallbacks"""
    
    # Try Claude first (if API key available)
    if hasattr(settings, 'CLAUDE_API_KEY') and settings.CLAUDE_API_KEY:
        claude_parser = ClaudeParser()
        result = claude_parser.parse_with_claude(message_text)
        
        # If confidence is high, use Claude result
        if result.get('overall_confidence', 0) > 0.7:
            return result
    
    # Fallback to manual patterns
    manual_parser = MessageParser()
    return manual_parser.parse_message(message_text)
```

### **Phase 3: Manager Review Interface (Week 3)**
```python
# orders/views.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .utils.message_parser import parse_message_smart

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def parse_whatsapp_message(request):
    """Parse WhatsApp message and return for manager review"""
    
    message_text = request.data.get('message_text')
    sender_name = request.data.get('sender_name')
    
    # Parse message
    parsing_result = parse_message_smart(message_text)
    
    # Save for review
    whatsapp_message = WhatsAppMessage.objects.create(
        sender_name=sender_name,
        message_text=message_text,
        parsed_items=parsing_result['items'],
        parsing_confidence=parsing_result.get('overall_confidence', 0),
        processed=False
    )
    
    return Response({
        'message_id': whatsapp_message.id,
        'parsing_result': parsing_result,
        'needs_review': parsing_result.get('needs_review', True),
        'suggested_items': parsing_result['items']
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def confirm_parsing(request, message_id):
    """Manager confirms/corrects parsing result"""
    
    message = WhatsAppMessage.objects.get(id=message_id)
    confirmed_items = request.data.get('items')
    
    # Create order from confirmed items
    order = Order.objects.create(
        restaurant=message.sender_name,  # Will link to proper user later
        whatsapp_message_id=message.message_id,
        original_message=message.message_text,
        parsed_by_ai=True,
        status='confirmed'
    )
    
    # Create order items
    for item_data in confirmed_items:
        OrderItem.objects.create(
            order=order,
            product_name=item_data['product_name'],
            quantity=item_data['quantity'],
            unit=item_data['unit'],
            original_text=item_data.get('original_text', ''),
            confidence_score=item_data.get('confidence', 0),
            manually_corrected=item_data.get('manually_corrected', False)
        )
    
    message.processed = True
    message.order = order
    message.save()
    
    return Response({'order_id': order.id, 'status': 'confirmed'})
```

---

## 📊 **Cost Savings Analysis**

### **Development Phase (6 months)**
```
OpenAI Cost: 50 messages/day × $0.015 × 180 days = $135
Claude Free Tier: $0
Manual Patterns: $0

Savings: $135 during development
```

### **Production Phase (1 year)**
```
Option 1 - OpenAI: 100 messages/day × $0.015 × 365 = $547.50/year
Option 2 - Claude: ~$200/year (estimated)
Option 3 - Manual + Review: $0 + manager time

Recommendation: Start with manual patterns, add AI for complex cases only
```

---

## 🎯 **Implementation Strategy**

### **Week 1: Manual Patterns**
- Build regex-based parser for common patterns
- Create manager review interface
- Test with real WhatsApp messages
- **Cost: $0**

### **Week 2: Claude Integration**
- Add Claude API as fallback for complex messages
- Implement confidence scoring
- Create hybrid parsing system
- **Cost: Free tier usage**

### **Week 3: Production Ready**
- Optimize parsing accuracy
- Add more product patterns
- Create manager correction tools
- **Cost: Minimal**

### **Future: Scale as Needed**
- Monitor parsing accuracy
- Add AI only where manual patterns fail
- Keep costs under control
- **Cost: Pay only for what you need**

---

## 🛠️ **Development Script Example**

```python
# scripts/test_message_parsing.py
from orders.utils.message_parser import MessageParser

def test_parsing():
    parser = MessageParser()
    
    test_messages = [
        "Hi, can I get 2 x onions and 3 x tomatoes?",
        "Need 5kg potatoes and 2 bunches carrots",
        "1 x onions, some tomatoes, and carrots please",
        "Can I order vegetables for tomorrow?",
    ]
    
    for message in test_messages:
        result = parser.parse_message(message)
        print(f"Message: {message}")
        print(f"Parsed: {result}")
        print(f"Confidence: {result['confidence']}")
        print("---")

if __name__ == "__main__":
    test_parsing()
```

**Bottom Line**: Start with free manual patterns, add Claude API for complex cases, keep OpenAI as last resort. This approach gives you 90% of the functionality at 0% of the cost during development!
