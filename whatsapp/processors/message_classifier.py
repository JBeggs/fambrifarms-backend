"""
Message Classifier - Preserved from original WhatsApp processing system
Handles intelligent message classification with business-specific rules
"""

import re
from typing import Dict, List, Tuple, Optional
from enum import Enum


class MessageType(Enum):
    """Message type classifications"""
    ORDER = 'order'
    STOCK = 'stock'
    INSTRUCTION = 'instruction'
    DEMARCATION = 'demarcation'
    IMAGE = 'image'
    VOICE = 'voice'
    VIDEO = 'video'
    DOCUMENT = 'document'
    STICKER = 'sticker'
    OTHER = 'other'


class MessageClassifier:
    """
    Classify WhatsApp messages by type and content
    Preserves all original business logic and classification rules
    """
    
    def __init__(self):
        self.classification_rules = self._load_classification_rules()
        
    def _load_classification_rules(self) -> Dict[str, Dict]:
        """
        PRESERVED: Classification rules from original system
        Enhanced with confidence scoring and business context
        """
        return {
            'demarcation': {
                'keywords': [
                    'ORDERS STARTS HERE', 'ORDERS START HERE', 'THURSDAY ORDERS', 
                    'TUESDAY ORDERS', 'MONDAY ORDERS', 'ORDERS FOR THURSDAY',
                    'ORDERS FOR TUESDAY', 'ORDERS FOR MONDAY', '👇👇👇'
                ],
                'patterns': [
                    r'ORDERS?\s+STARTS?\s+HERE',
                    r'(MONDAY|TUESDAY|WEDNESDAY|THURSDAY|FRIDAY)\s+ORDERS?',
                    r'ORDERS?\s+FOR\s+(MONDAY|TUESDAY|WEDNESDAY|THURSDAY|FRIDAY)'
                ],
                'priority': 10,  # Highest priority
                'confidence_boost': 0.9
            },
            
            'stock': {
                'keywords': [
                    'STOCK', 'AVAILABLE', 'INVENTORY', 'SUPPLY', 'STOKE',  # PRESERVED: Including misspelling
                    'IN STOCK', 'OUT OF STOCK', 'STOCK UPDATE', 'STOCK REPORT',
                    'AVAILABLE TODAY', 'FRESH STOCK', 'NEW STOCK'
                ],
                'patterns': [
                    r'STOCK\s+(UPDATE|REPORT|AVAILABLE)',
                    r'(IN|OUT\s+OF)\s+STOCK',
                    r'AVAILABLE\s+(TODAY|NOW|THIS\s+WEEK)'
                ],
                'priority': 8,
                'confidence_boost': 0.8,
                'sender_indicators': ['SHALLOME', 'HAZVINEI']  # PRESERVED: Stock controller names
            },
            
            'order': {
                'keywords': [
                    'ORDER', 'NEED', 'WANT', 'REQUIRE', 'REQUEST',
                    'KG', 'BOXES', 'HEADS', 'BUNCHES', 'PIECES'
                ],
                'patterns': [
                    r'\d+\s*KG', r'\d+\s*X', r'X\d+', r'\d+\s*BOX', r'\d+\s*BOXES',
                    r'\d+\s*HEAD', r'\d+\s*HEADS', r'\d+\s*BUNCH', r'\d+\s*BUNCHES',
                    r'\d+\s*PCS', r'\d+\s*PIECES', r'\d+\s*PKT', r'\d+\s*PACKETS'
                ],
                'priority': 7,
                'confidence_boost': 0.7,
                'product_indicators': [
                    'CARROT', 'LETTUCE', 'ONION', 'POTATO', 'TOMATO', 'CABBAGE',
                    'SPINACH', 'BEETROOT', 'CUCUMBER', 'PEPPER', 'BROCCOLI'
                ]
            },
            
            'instruction': {
                'keywords': [
                    'GOOD MORNING', 'GOOD AFTERNOON', 'GOOD EVENING', 'HELLO', 'HI',
                    'THANKS', 'THANK YOU', 'PLEASE', 'KINDLY', 'NOTE', 'REMEMBER',
                    'SEPARATE INVOICE', 'SEPERATE INVOICE', 'DELIVERY', 'URGENT'
                ],
                'patterns': [
                    r'GOOD\s+(MORNING|AFTERNOON|EVENING)',
                    r'THANK\s+YOU', r'SEPERATE?\s+INVOICE',
                    r'DELIVER(Y)?\s+(TODAY|TOMORROW|ASAP)'
                ],
                'priority': 5,
                'confidence_boost': 0.6
            }
        }
    
    def classify_message(self, content: str, media_type: str = "text", sender_name: str = "") -> Tuple[MessageType, float]:
        """
        PRESERVED: Classify message with confidence scoring
        Enhanced with media type handling and sender context
        """
        if not content and not media_type:
            return MessageType.OTHER, 0.0
        
        # Handle media types first (highest confidence)
        if media_type and media_type != "text":
            media_classification = self._classify_media_type(media_type)
            if media_classification:
                return media_classification, 0.95
        
        # Handle text content classification
        if content:
            return self._classify_text_content(content, sender_name)
        
        return MessageType.OTHER, 0.0
    
    def _classify_media_type(self, media_type: str) -> Optional[MessageType]:
        """Classify based on media type"""
        media_mapping = {
            'image': MessageType.IMAGE,
            'voice': MessageType.VOICE,
            'video': MessageType.VIDEO,
            'document': MessageType.DOCUMENT,
            'sticker': MessageType.STICKER
        }
        return media_mapping.get(media_type.lower())
    
    def _classify_text_content(self, content: str, sender_name: str = "") -> Tuple[MessageType, float]:
        """
        PRESERVED: Text content classification with enhanced confidence
        """
        content_upper = content.upper()
        best_classification = MessageType.OTHER
        best_confidence = 0.0
        
        # Check each classification rule in priority order
        for msg_type, rules in sorted(
            self.classification_rules.items(), 
            key=lambda x: x[1]['priority'], 
            reverse=True
        ):
            confidence = self._calculate_classification_confidence(
                content_upper, rules, sender_name
            )
            
            if confidence > best_confidence:
                best_confidence = confidence
                best_classification = MessageType(msg_type)
        
        # Apply minimum confidence threshold
        if best_confidence < 0.3:
            return MessageType.OTHER, best_confidence
        
        return best_classification, best_confidence
    
    def _calculate_classification_confidence(self, content_upper: str, rules: Dict, sender_name: str = "") -> float:
        """Calculate confidence score for a specific classification"""
        confidence = 0.0
        
        # Check keywords
        keyword_matches = 0
        for keyword in rules.get('keywords', []):
            if keyword in content_upper:
                keyword_matches += 1
        
        if keyword_matches > 0:
            confidence += min(keyword_matches * 0.2, 0.6)  # Max 0.6 from keywords
        
        # Check patterns
        pattern_matches = 0
        for pattern in rules.get('patterns', []):
            if re.search(pattern, content_upper):
                pattern_matches += 1
        
        if pattern_matches > 0:
            confidence += min(pattern_matches * 0.3, 0.7)  # Max 0.7 from patterns
        
        # Check sender indicators (for stock messages)
        sender_indicators = rules.get('sender_indicators', [])
        if sender_indicators and sender_name:
            sender_upper = sender_name.upper()
            for indicator in sender_indicators:
                if indicator in sender_upper:
                    confidence += 0.4
                    break
        
        # Check product indicators (for order messages)
        product_indicators = rules.get('product_indicators', [])
        if product_indicators:
            product_matches = sum(1 for indicator in product_indicators if indicator in content_upper)
            if product_matches > 0:
                confidence += min(product_matches * 0.1, 0.3)
        
        # Apply confidence boost
        confidence_boost = rules.get('confidence_boost', 0.0)
        if confidence > 0:
            confidence = min(confidence + confidence_boost * 0.1, 1.0)
        
        return confidence
    
    def classify_message_simple(self, content: str, media_type: str = "text") -> str:
        """
        PRESERVED: Simple classification for backward compatibility
        Returns string type as expected by existing code
        """
        message_type, _ = self.classify_message(content, media_type)
        return message_type.value
    
    def is_order_day_demarcation(self, content: str) -> bool:
        """
        PRESERVED: Check if message marks start of order day
        Original logic from WhatsAppMessage model
        """
        if not content:
            return False
            
        content_upper = content.upper()
        demarcation_indicators = [
            'ORDERS STARTS HERE', 'ORDERS START HERE', '👇👇👇',
            'THURSDAY ORDERS STARTS HERE', 'TUESDAY ORDERS STARTS HERE',
            'MONDAY ORDERS STARTS HERE'
        ]
        
        for indicator in demarcation_indicators:
            if indicator in content_upper:
                return True
        
        return False
    
    def is_stock_message(self, content: str, sender_name: str = "") -> bool:
        """Check if message is a stock update"""
        message_type, confidence = self.classify_message(content, sender_name=sender_name)
        return message_type == MessageType.STOCK and confidence > 0.5
    
    def is_order_message(self, content: str) -> bool:
        """Check if message contains order information"""
        message_type, confidence = self.classify_message(content)
        return message_type == MessageType.ORDER and confidence > 0.5
    
    def extract_classification_features(self, content: str) -> Dict[str, any]:
        """
        Extract features used in classification for analysis/debugging
        Useful for understanding why messages were classified certain ways
        """
        if not content:
            return {}
        
        content_upper = content.upper()
        features = {
            'content_length': len(content),
            'line_count': len(content.split('\n')),
            'word_count': len(content.split()),
            'has_numbers': bool(re.search(r'\d', content)),
            'has_quantities': bool(re.search(r'\d+\s*(KG|BOX|HEAD|BUNCH|PCS)', content_upper)),
            'classification_matches': {}
        }
        
        # Check matches for each classification type
        for msg_type, rules in self.classification_rules.items():
            matches = {
                'keywords': [kw for kw in rules.get('keywords', []) if kw in content_upper],
                'patterns': [p for p in rules.get('patterns', []) if re.search(p, content_upper)]
            }
            features['classification_matches'][msg_type] = matches
        
        return features
    
    def get_classification_stats(self) -> Dict[str, int]:
        """Get statistics about classification rules"""
        stats = {}
        for msg_type, rules in self.classification_rules.items():
            stats[msg_type] = {
                'keywords': len(rules.get('keywords', [])),
                'patterns': len(rules.get('patterns', [])),
                'priority': rules.get('priority', 0)
            }
        return stats


# Singleton instance for efficient reuse
_message_classifier_instance = None

def get_message_classifier() -> MessageClassifier:
    """Get singleton MessageClassifier instance"""
    global _message_classifier_instance
    if _message_classifier_instance is None:
        _message_classifier_instance = MessageClassifier()
    return _message_classifier_instance

