"""
Background Message Processor - Orchestrates preserved business logic
Runs sophisticated message analysis without blocking real-time HTML processing
"""

import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from django.utils import timezone
from django.db import transaction

from ..models import WhatsAppMessage, MessageProcessingLog
from .company_extractor import get_company_extractor
from .order_item_parser import get_order_item_parser
from .message_classifier import get_message_classifier, MessageType

logger = logging.getLogger(__name__)


class BackgroundMessageProcessor:
    """
    Main background processor that applies preserved business logic
    Handles intelligent message analysis, company extraction, and order creation
    """
    
    def __init__(self):
        self.company_extractor = get_company_extractor()
        self.item_parser = get_order_item_parser()
        self.classifier = get_message_classifier()
        
    def process_unprocessed_messages(self, batch_size: int = 50) -> Dict[str, int]:
        """
        Process messages that haven't been analyzed by background processor
        Returns statistics about processing results
        """
        logger.info(f"[BackgroundProcessor] Starting batch processing (batch_size={batch_size})")
        
        # Get unprocessed messages
        unprocessed_messages = WhatsAppMessage.objects.filter(
            processed=False,
            # Focus on messages that could benefit from intelligent processing
            message_type__in=['order', 'instruction', 'other']
        ).order_by('timestamp')[:batch_size]
        
        if not unprocessed_messages.exists():
            logger.info("[BackgroundProcessor] No unprocessed messages found")
            return {'processed': 0, 'enhanced': 0, 'orders_created': 0}
        
        logger.info(f"[BackgroundProcessor] Processing {len(unprocessed_messages)} messages")
        
        stats = {
            'processed': 0,
            'enhanced': 0,
            'companies_extracted': 0,
            'items_parsed': 0,
            'reclassified': 0,
            'orders_created': 0,
            'errors': 0
        }
        
        with transaction.atomic():
            for message in unprocessed_messages:
                try:
                    enhanced = self._process_single_message(message)
                    stats['processed'] += 1
                    if enhanced:
                        stats['enhanced'] += 1
                        
                except Exception as e:
                    logger.error(f"[BackgroundProcessor] Error processing message {message.id}: {e}")
                    stats['errors'] += 1
        
        # Try to create orders from processed messages
        try:
            orders_created = self._create_intelligent_orders()
            stats['orders_created'] = orders_created
        except Exception as e:
            logger.error(f"[BackgroundProcessor] Error creating orders: {e}")
        
        logger.info(f"[BackgroundProcessor] Batch complete: {stats}")
        return stats
    
    def _process_single_message(self, message: WhatsAppMessage) -> bool:
        """
        Process a single message with preserved business logic
        Returns True if message was enhanced
        """
        enhanced = False
        original_data = {
            'message_type': message.message_type,
            'manual_company': message.manual_company,
            'parsed_items': message.parsed_items,
            'instructions': message.instructions
        }
        
        # 1. Enhanced Classification
        if message.content:
            new_type, confidence = self.classifier.classify_message(
                message.content, 
                message.media_type or 'text',
                message.sender_name
            )
            
            # Update classification if we have higher confidence
            if confidence > 0.7 and new_type.value != message.message_type:
                logger.info(f"[BackgroundProcessor] Reclassifying message {message.id}: "
                          f"{message.message_type} → {new_type.value} (confidence: {confidence:.2f})")
                message.message_type = new_type.value
                message.confidence_score = confidence
                enhanced = True
        
        # 2. Company Extraction (if not manually set)
        if not message.manual_company and message.content:
            extracted_company = self.company_extractor.extract_company(message.content)
            if extracted_company:
                logger.info(f"[BackgroundProcessor] Extracted company for message {message.id}: '{extracted_company}'")
                message.manual_company = extracted_company
                enhanced = True
        
        # 3. Order Item Parsing (for order messages)
        if message.message_type == 'order' and message.content:
            # Parse items using preserved logic
            parsed_items = self.item_parser.extract_items_text(message.content)
            if parsed_items and parsed_items != message.parsed_items:
                logger.info(f"[BackgroundProcessor] Enhanced item parsing for message {message.id}")
                message.parsed_items = parsed_items.split('\n') if parsed_items else []
                enhanced = True
            
            # Extract instructions
            instructions = self.item_parser.extract_instructions(message.content)
            if instructions and instructions != message.instructions:
                logger.info(f"[BackgroundProcessor] Extracted instructions for message {message.id}")
                message.instructions = instructions
                enhanced = True
        
        # 4. Mark as processed
        message.processed = True
        message.save()
        
        # 5. Log processing results
        if enhanced:
            self._log_processing_enhancement(message, original_data)
        
        return enhanced
    
    def _create_intelligent_orders(self) -> int:
        """
        PRESERVED: Create orders using complex message sequencing logic
        Implements the sophisticated pattern matching from original system
        """
        # Get recent processed messages that could form orders
        recent_messages = WhatsAppMessage.objects.filter(
            processed=True,
            timestamp__gte=timezone.now() - timedelta(days=2),  # Last 2 days
            message_type__in=['order', 'instruction']
        ).order_by('timestamp')
        
        if not recent_messages.exists():
            return 0
        
        # Convert to format expected by preserved logic
        message_data = []
        for msg in recent_messages:
            message_data.append({
                'id': msg.message_id or str(msg.id),
                'content': msg.content,
                'timestamp': msg.timestamp.isoformat(),
                'sender': msg.sender_name,
                'company': msg.manual_company
            })
        
        # Apply preserved order creation logic
        orders_created = self._parse_messages_to_orders(message_data)
        
        logger.info(f"[BackgroundProcessor] Created {len(orders_created)} intelligent orders")
        return len(orders_created)
    
    def _parse_messages_to_orders(self, messages: List[Dict]) -> List[Dict]:
        """
        PRESERVED: Complex message parsing logic from original system
        Handles items-before-company patterns and intelligent order grouping
        """
        if not messages:
            return []
        
        orders = []
        current_buffer = []  # Buffer for items waiting for company assignment
        
        for i, message in enumerate(messages):
            content = message.get('content', '').strip()
            if not content:
                continue
            
            # Split message into lines
            lines = [line.strip() for line in content.split('\n') if line.strip()]
            if not lines:
                continue
            
            # Check if this is a company-only message
            if len(lines) == 1:
                company = self.company_extractor.extract_company(lines[0])
                if company:
                    # This is a company name - flush buffer to this company
                    if current_buffer:
                        order = self._create_order_from_buffer(company, current_buffer, message)
                        if order:
                            orders.append(order)
                        current_buffer = []
                    continue
            
            # Check for items-before-company pattern
            has_items = any(self.item_parser._has_quantity_indicators(line) for line in lines)
            
            if has_items and i + 1 < len(messages):
                next_message = messages[i + 1]
                next_content = next_message.get('content', '').strip()
                next_lines = [line.strip() for line in next_content.split('\n') if line.strip()]
                
                if len(next_lines) == 1:
                    next_company = self.company_extractor.extract_company(next_lines[0])
                    if next_company:
                        # Pattern: current message has items, next message is company
                        items = self.item_parser.extract_items_text(content)
                        instructions = self.item_parser.extract_instructions(content)
                        
                        if items:
                            order = {
                                'company_name': next_company,
                                'items_text': items,
                                'instructions': instructions,
                                'timestamp': message.get('timestamp', ''),
                                'message_ids': [message.get('id', ''), next_message.get('id', '')]
                            }
                            orders.append(order)
                        continue
            
            # Check for mixed content (items + company in same message)
            company_in_message = None
            for line in lines:
                company = self.company_extractor.extract_company(line)
                if company:
                    company_in_message = company
                    break
            
            if company_in_message and has_items:
                # Mixed content - extract items and assign to company
                items = self.item_parser.extract_items_text(content)
                instructions = self.item_parser.extract_instructions(content)
                
                if items:
                    order = {
                        'company_name': company_in_message,
                        'items_text': items,
                        'instructions': instructions,
                        'timestamp': message.get('timestamp', ''),
                        'message_ids': [message.get('id', '')]
                    }
                    orders.append(order)
                continue
            
            # If message has items but no company, add to buffer
            if has_items:
                current_buffer.append({
                    'content': content,
                    'message': message,
                    'items': self.item_parser.extract_items_text(content),
                    'instructions': self.item_parser.extract_instructions(content)
                })
        
        # Process any remaining buffer items
        if current_buffer:
            # Try to assign to most recent company or create unassigned order
            recent_company = self._find_recent_company(messages)
            if recent_company:
                order = self._create_order_from_buffer(recent_company, current_buffer, None)
                if order:
                    orders.append(order)
        
        return orders
    
    def _create_order_from_buffer(self, company: str, buffer: List[Dict], company_message: Optional[Dict]) -> Optional[Dict]:
        """Create order from buffered items"""
        if not buffer:
            return None
        
        # Combine all items and instructions from buffer
        all_items = []
        all_instructions = []
        message_ids = []
        
        for item in buffer:
            if item.get('items'):
                all_items.append(item['items'])
            if item.get('instructions'):
                all_instructions.append(item['instructions'])
            if item.get('message', {}).get('id'):
                message_ids.append(item['message']['id'])
        
        if company_message and company_message.get('id'):
            message_ids.append(company_message['id'])
        
        if all_items:
            return {
                'company_name': company,
                'items_text': '\n'.join(all_items),
                'instructions': '\n'.join(all_instructions),
                'timestamp': buffer[0].get('message', {}).get('timestamp', ''),
                'message_ids': message_ids
            }
        
        return None
    
    def _find_recent_company(self, messages: List[Dict]) -> Optional[str]:
        """Find the most recent company mentioned in messages"""
        for message in reversed(messages):
            content = message.get('content', '')
            company = self.company_extractor.extract_company(content)
            if company:
                return company
        return None
    
    def _log_processing_enhancement(self, message: WhatsAppMessage, original_data: Dict):
        """Log what enhancements were made to the message"""
        changes = []
        
        if message.message_type != original_data['message_type']:
            changes.append(f"type: {original_data['message_type']} → {message.message_type}")
        
        if message.manual_company != original_data['manual_company']:
            changes.append(f"company: {original_data['manual_company']} → {message.manual_company}")
        
        if message.parsed_items != original_data['parsed_items']:
            changes.append(f"items: enhanced parsing")
        
        if message.instructions != original_data['instructions']:
            changes.append(f"instructions: extracted")
        
        if changes:
            MessageProcessingLog.objects.create(
                message=message,
                processing_type='background_enhancement',
                details=f"Enhanced: {', '.join(changes)}",
                success=True
            )
    
    def process_specific_messages(self, message_ids: List[int]) -> Dict[str, int]:
        """Process specific messages by ID (for manual processing)"""
        messages = WhatsAppMessage.objects.filter(id__in=message_ids)
        
        stats = {'processed': 0, 'enhanced': 0, 'errors': 0}
        
        for message in messages:
            try:
                enhanced = self._process_single_message(message)
                stats['processed'] += 1
                if enhanced:
                    stats['enhanced'] += 1
            except Exception as e:
                logger.error(f"[BackgroundProcessor] Error processing message {message.id}: {e}")
                stats['errors'] += 1
        
        return stats
    
    def get_processing_stats(self) -> Dict[str, any]:
        """Get statistics about background processing"""
        total_messages = WhatsAppMessage.objects.count()
        processed_messages = WhatsAppMessage.objects.filter(processed=True).count()
        
        # Company extraction stats
        messages_with_companies = WhatsAppMessage.objects.filter(
            manual_company__isnull=False
        ).exclude(manual_company='').count()
        
        # Classification stats
        classification_counts = {}
        for msg_type in ['order', 'stock', 'instruction', 'demarcation', 'other']:
            count = WhatsAppMessage.objects.filter(message_type=msg_type).count()
            classification_counts[msg_type] = count
        
        return {
            'total_messages': total_messages,
            'processed_messages': processed_messages,
            'processing_rate': (processed_messages / total_messages * 100) if total_messages > 0 else 0,
            'messages_with_companies': messages_with_companies,
            'classification_counts': classification_counts,
            'company_extraction_rate': (messages_with_companies / total_messages * 100) if total_messages > 0 else 0
        }


# Singleton instance for efficient reuse
_background_processor_instance = None

def get_background_processor() -> BackgroundMessageProcessor:
    """Get singleton BackgroundMessageProcessor instance"""
    global _background_processor_instance
    if _background_processor_instance is None:
        _background_processor_instance = BackgroundMessageProcessor()
    return _background_processor_instance

