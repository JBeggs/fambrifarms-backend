from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.response import Response
from familyfarms_api.authentication import FlexibleAuthentication
from django.shortcuts import get_object_or_404
from django.db import transaction, models
from django.utils import timezone
from django.conf import settings
from django.http import JsonResponse
from datetime import datetime, timedelta
import traceback
import logging
import hashlib
from bs4 import BeautifulSoup
import re
from .utils import safe_html_content

logger = logging.getLogger(__name__)


def clean_timestamp_from_text(text):
    """
    Comprehensive timestamp cleaning function
    Removes timestamps from the end of text in various formats
    """
    if not text:
        return text
    
    # Pattern 1: "Thanks12:46" -> "Thanks" (no space before timestamp)
    text = re.sub(r'([a-zA-Z])\d{1,2}:\d{2}$', r'\1', text).strip()
    
    # Pattern 2: "Pecanwood 09:40" -> "Pecanwood" (space before timestamp)
    text = re.sub(r'\s+\d{1,2}:\d{2}$', '', text).strip()
    
    # Pattern 3: Standalone timestamps at end "09:40"
    text = re.sub(r'^\d{1,2}:\d{2}$|(?<=\s)\d{1,2}:\d{2}$', '', text).strip()
    
    # Pattern 4: Any remaining timestamp patterns at end
    text = re.sub(r'\d{1,2}:\d{2}$', '', text).strip()
    
    # Pattern 5: Handle multiline - remove timestamp from end of each line
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        line = line.strip()
        if line:
            # Apply same patterns to each line
            line = re.sub(r'([a-zA-Z])\d{1,2}:\d{2}$', r'\1', line).strip()
            line = re.sub(r'\s+\d{1,2}:\d{2}$', '', line).strip()
            line = re.sub(r'\d{1,2}:\d{2}$', '', line).strip()
            
            # Only keep non-empty lines that aren't just timestamps
            if line and not re.match(r'^\d{1,2}:\d{2}$', line):
                cleaned_lines.append(line)
    
    return '\n'.join(cleaned_lines)


def clean_numbering_from_text(text):
    """
    Remove numbering from stock messages and order lists.
    Handles various numbering formats commonly found in stock messages.
    """
    if not text:
        return text
    
    lines = text.split('\n')
    cleaned_lines = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Pattern 1: "1.Product name" -> "Product name"  
        line = re.sub(r'^\d+\.\s*', '', line)
        
        # Pattern 2: "1) Product name" -> "Product name"
        line = re.sub(r'^\d+\)\s*', '', line)
        
        # Pattern 3: "1 Product name" -> "Product name" (only at start, be careful not to remove quantities)
        # Only remove if it looks like a list number (single digit at start)
        if re.match(r'^\d\s+[A-Za-z]', line):
            line = re.sub(r'^\d\s+', '', line)
        
        # Pattern 4: "(1) Product name" -> "Product name"
        line = re.sub(r'^\(\d+\)\s*', '', line)
        
        # Pattern 5: "# Product name" -> "Product name" (hash numbering)
        line = re.sub(r'^#\s*', '', line)
        
        # Pattern 6: "- Product name" -> "Product name" (dash numbering)  
        line = re.sub(r'^-\s+', '', line)
        
        # Pattern 7: "• Product name" -> "Product name" (bullet points)
        line = re.sub(r'^•\s*', '', line)
        
        # Pattern 8: "* Product name" -> "Product name" (asterisk bullets)
        line = re.sub(r'^\*\s*', '', line)
        
        # Only keep non-empty lines
        line = line.strip()
        if line:
            cleaned_lines.append(line)
    
    return '\n'.join(cleaned_lines)


from .models import WhatsAppMessage, StockUpdate, OrderDayDemarcation, MessageProcessingLog
from .serializers import (
    WhatsAppMessageSerializer, StockUpdateSerializer, MessageBatchSerializer,
    ProcessMessagesSerializer, EditMessageSerializer, UpdateMessageTypeSerializer, 
    OrderCreationResultSerializer, StockValidationSerializer
)
from .services import (
    classify_message_type, create_order_from_message, process_stock_updates,
    validate_order_against_stock, log_processing_action, has_order_items, parse_stock_message
)
from accounts.models import RestaurantProfile

@api_view(['GET'])
@authentication_classes([FlexibleAuthentication])
@permission_classes([IsAuthenticated])
def health_check(request):
    """Health check endpoint for the WhatsApp integration service"""
    return Response({
        'status': 'healthy',
        'service': 'django-whatsapp-integration',
        'timestamp': timezone.now().isoformat(),
        'version': '1.0.0'
    })

@api_view(['GET'])
@authentication_classes([FlexibleAuthentication])
@permission_classes([IsAuthenticated])
def get_companies(request):
    """Get list of valid companies from RestaurantProfile, PrivateCustomerProfile and WhatsApp messages"""
    try:
        companies = []
        
        # First, get companies from RestaurantProfile (seeded data)
        profiles = RestaurantProfile.objects.select_related('user').order_by('business_name')
        for profile in profiles:
            company_data = {
                'id': f'restaurant_{profile.id}',
                'name': profile.business_name,
                'branch_name': profile.branch_name,
                'display_name': str(profile),  # Uses __str__ method
                'email': profile.user.email,
                'phone': profile.user.phone,
                'address': profile.address,
                'city': profile.city,
                'payment_terms': profile.payment_terms,
                'customer_type': 'restaurant',
            }
            companies.append(company_data)
        
        # Add private customers
        from accounts.models import PrivateCustomerProfile, User
        
        # Get private customers with profiles
        private_profiles = PrivateCustomerProfile.objects.select_related('user').order_by('user__first_name')
        for profile in private_profiles:
            display_name = f"{profile.user.first_name} {profile.user.last_name}".strip()
            if not display_name:
                display_name = profile.user.email.split('@')[0]  # Use email username as fallback
            
            company_data = {
                'id': f'private_{profile.id}',
                'name': display_name,
                'branch_name': '',
                'display_name': display_name,
                'email': profile.user.email,
                'phone': profile.whatsapp_number or profile.user.phone,
                'address': profile.delivery_address,
                'city': '',
                'payment_terms': 'Net 30',  # Default for private customers
                'customer_type': 'private',
            }
            companies.append(company_data)
        
        # Also add private users without profiles (like Sylvia)
        private_users_without_profiles = User.objects.filter(
            user_type='private'
        ).exclude(
            id__in=private_profiles.values_list('user_id', flat=True)
        ).order_by('first_name')
        
        for user in private_users_without_profiles:
            display_name = f"{user.first_name} {user.last_name}".strip()
            if not display_name:
                display_name = user.email.split('@')[0]  # Use email username as fallback
            
            company_data = {
                'id': f'private_user_{user.id}',
                'name': display_name,
                'branch_name': '',
                'display_name': display_name,
                'email': user.email,
                'phone': user.phone,
                'address': '',
                'city': '',
                'payment_terms': 'Net 30',  # Default for private customers
                'customer_type': 'private',
            }
            companies.append(company_data)
        
        # If no restaurant profiles exist, fall back to WhatsApp extraction system
        if not companies:
            from .processors.company_extractor import get_company_extractor
            
            company_extractor = get_company_extractor()
            company_aliases = company_extractor.company_aliases
            
            # Get unique companies from WhatsApp messages
            unique_companies = set()
            
            # Add companies from CompanyExtractor aliases (canonical names)
            for canonical_name in company_aliases.values():
                unique_companies.add(canonical_name)
            
            # Also get companies that have been extracted from actual messages
            actual_companies = WhatsAppMessage.objects.filter(
                manual_company__isnull=False,
                is_deleted=False
            ).exclude(manual_company='').values_list('manual_company', flat=True).distinct()
            
            for company in actual_companies:
                unique_companies.add(company)
            
            # Convert to list and sort
            companies_list = sorted(list(unique_companies))
            
            # Format for Flutter dropdown
            for i, company_name in enumerate(companies_list):
                company_data = {
                    'id': i + 1,  # Simple ID for dropdown
                    'name': company_name,
                    'branch_name': '',
                    'display_name': company_name,
                    'email': '',
                    'phone': '',
                    'address': '',
                    'city': '',
                    'payment_terms': 'Net 30',  # Default
                }
                companies.append(company_data)
        
        return Response({
            'status': 'success',
            'count': len(companies),
            'companies': companies
        })
        
    except Exception as e:
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@authentication_classes([FlexibleAuthentication])
@permission_classes([IsAuthenticated])
def receive_messages(request):
    """
    Receive scraped messages from the Python WhatsApp scraper
    
    Expected format:
    {
        "messages": [
            {
                "id": "message_id",
                "chat": "ORDERS Restaurants",
                "sender": "Sender Name",
                "content": "Message content",
                "timestamp": "2025-01-01T12:00:00Z",
                "cleanedContent": "Cleaned content",
                "items": ["item1", "item2"],
                "instructions": "Additional instructions"
            }
        ]
    }
    """
    serializer = MessageBatchSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    messages_data = serializer.validated_data['messages']
    print(f"[DJANGO][RECEIVE] batch_count={len(messages_data)}")
    created_messages = []
    updated_messages = []
    errors = []
    
    with transaction.atomic():
        for msg_data in messages_data:
            try:
                # Parse timestamp
                timestamp = datetime.fromisoformat(msg_data['timestamp'].replace('Z', '+00:00'))
                
                # Classification diagnostics (pre-save) - require explicit values
                content = msg_data.get('content')
                if content is None:
                    return JsonResponse({
                        'error': 'Message content is required',
                        'processed': 0
                    }, status=400)
                
                content_upper = content.upper()
                msg_id = msg_data.get('id')
                if msg_id is None:
                    return JsonResponse({
                        'error': 'Message ID is required',
                        'processed': 0
                    }, status=400)
                
                sender = msg_data.get('sender')
                if sender is None:
                    return JsonResponse({
                        'error': 'Message sender is required',
                        'processed': 0
                    }, status=400)
                flags = {
                    'stock_header': ('STOKE AS AT' in content_upper or 'STOCK AS AT' in content_upper),
                    'demarcation': any(k in content_upper for k in [
                        'ORDERS STARTS HERE', '👇👇👇', 'THURSDAY ORDERS STARTS HERE', 'TUESDAY ORDERS STARTS HERE', 'MONDAY ORDERS STARTS HERE']
                    ),
                    'has_order_items': has_order_items(content),
                    'instructionish': any(w in content_upper for w in ['PLEASE', 'THANKS', 'HELLO', 'HI', 'GOOD MORNING'])
                }
                print(f"[DJANGO][CLASSIFY][IN] id={msg_id} sender='{sender}' len={len(content)} flags={flags}")

                # Check for existing message by multiple criteria to prevent duplicates
                existing_message = None
                
                # First try by message_id
                try:
                    existing_message = WhatsAppMessage.objects.get(message_id=msg_data['id'])
                    # Respect soft-delete: if deleted, skip updates/creation
                    if existing_message.is_deleted:
                        continue
                except WhatsAppMessage.DoesNotExist:
                    # If not found by ID, check by content + sender + timestamp (within 1 minute window)
                    time_window_start = timestamp - timedelta(minutes=1)
                    time_window_end = timestamp + timedelta(minutes=1)
                    
                    existing_message = WhatsAppMessage.objects.filter(
                        sender_name=msg_data['sender'],
                        content=msg_data['content'],
                        timestamp__gte=time_window_start,
                        timestamp__lte=time_window_end,
                        is_deleted=False
                    ).first()
                
                if existing_message:
                    # Update existing message if any relevant field changed
                    incoming_media_info = msg_data.get('media_info', msg_data.get('mediaInfo', ''))
                    incoming_message_type = msg_data.get('message_type', existing_message.message_type)
                    django_message_type = classify_message_type(msg_data)

                    updated = False
                    needs_update = (
                        existing_message.content != msg_data['content'] or
                        existing_message.cleaned_content != msg_data.get('cleanedContent', '') or
                        existing_message.media_url != msg_data.get('media_url', '') or
                        existing_message.media_type != msg_data.get('media_type', '') or
                        existing_message.media_info != incoming_media_info or
                        existing_message.message_type != django_message_type
                    )

                    if needs_update:
                        # Don't overwrite content if message has been manually edited
                        if not existing_message.edited:
                            existing_message.content = msg_data['content']
                            existing_message.cleaned_content = msg_data.get('cleanedContent', '')
                            print(f"[DJANGO][RECEIVE][CONTENT_UPDATE] id={existing_message.message_id} - Updated content (not edited)")
                        else:
                            print(f"[DJANGO][RECEIVE][CONTENT_PROTECTED] id={existing_message.message_id} - Preserving edited content")
                        
                        existing_message.media_url = msg_data.get('media_url', '')
                        existing_message.media_type = msg_data.get('media_type', '')
                        existing_message.media_info = incoming_media_info
                        # Always use Django decision
                        existing_message.message_type = django_message_type
                        existing_message.is_forwarded = msg_data.get('is_forwarded', False)
                        existing_message.forwarded_info = msg_data.get('forwarded_info', '')
                        existing_message.is_reply = msg_data.get('is_reply', False)
                        existing_message.reply_content = msg_data.get('reply_content', '')
                        existing_message.save()
                        updated = True
                        print(f"[DJANGO][RECEIVE][UPDATED] id={existing_message.message_id} type={existing_message.message_type} incoming={incoming_message_type}")
                    
                    message = existing_message
                    created = False
                    if updated:
                        updated_messages.append(message)
                else:
                    # Create new message
                    django_message_type = classify_message_type(msg_data)
                    message = WhatsAppMessage.objects.create(
                        message_id=msg_data['id'],
                        chat_name=msg_data['chat'],
                        sender_name=msg_data['sender'],
                        content=msg_data['content'],
                        cleaned_content=msg_data.get('cleanedContent', ''),
                        timestamp=timestamp,
                        # Always use Django decision
                        message_type=django_message_type,
                        parsed_items=msg_data.get('items', []),
                        instructions=msg_data.get('instructions', ''),
                        confidence_score=0.8,  # Default confidence
                        # Media fields
                        media_url=msg_data.get('media_url', ''),
                        media_type=msg_data.get('media_type', ''),
                        media_info=msg_data.get('media_info', msg_data.get('mediaInfo', '')),
                        # Context fields
                        is_forwarded=msg_data.get('is_forwarded', False),
                        forwarded_info=msg_data.get('forwarded_info', ''),
                        is_reply=msg_data.get('is_reply', False),
                        reply_content=msg_data.get('reply_content', ''),
                    )
                    created = True
                    print(f"[DJANGO][RECEIVE][CREATED] id={message.message_id} decided_type={message.message_type} incoming={msg_data.get('message_type', '')}")
                
                # Debug: Always log what happened
                action = "CREATED" if created else "UPDATED" if updated else "SKIPPED"
                print(f"[DJANGO][RECEIVE][{action}] id={message.message_id} type={message.message_type}")
                
                # CRITICAL FIX: Trigger company extraction for ALL order messages
                # This ensures context-based assignments work for both new and existing messages
                if message.message_type == 'order' and not message.manual_company:
                    company = message.extract_company_name()  # This will auto-set manual_company if found from context
                    if company:
                        print(f"[DJANGO][RECEIVE][COMPANY] id={message.message_id} company='{company}' manual='{message.manual_company}'")
                
                if created:
                    created_messages.append(message)
                    log_processing_action(message, 'classified', {
                        'type': message.message_type,
                        'confidence': message.confidence_score
                    })
                
            except Exception as e:
                error_info = {
                    'message_id': msg_data.get('id', 'unknown'),
                    'error': str(e),
                    'traceback': traceback.format_exc()
                }
                errors.append(error_info)
                # CRITICAL: Log the actual error that's preventing message processing
                print(f"[DJANGO][RECEIVE][ERROR] id={msg_data.get('id', 'unknown')} error={str(e)}")
                print(f"[DJANGO][RECEIVE][TRACEBACK] {traceback.format_exc()}")
    
    # Process stock updates and order day demarcations
    try:
        stock_updates_created = process_stock_updates(created_messages)
        process_order_demarcations(created_messages)
    except Exception as e:
        errors.append({
            'type': 'stock_processing',
            'error': str(e),
            'traceback': traceback.format_exc()
        })
        stock_updates_created = 0
    
    return Response({
        'status': 'success',
        'messages_received': len(messages_data),
        'new_messages': len(created_messages),
        'updated_messages': len(updated_messages),
        'stock_updates_created': stock_updates_created,
        'errors': errors
    })


@api_view(['POST'])
@permission_classes([AllowAny])  # Allow Python crawler without authentication
def receive_html_messages(request):
    """
    Receive raw HTML messages from simplified Python WhatsApp crawler
    
    Expected format:
    {
        "messages": [
            {
                "id": "message_id",
                "chat": "ORDERS Restaurants", 
                "html": "<div>Raw HTML content</div>",
                "timestamp": "2025-01-01T12:00:00Z",
                "message_data": {
                    "was_expanded": true,
                    "expansion_failed": false,
                    "original_preview": "truncated text..."
                }
            }
        ]
    }
    """
    try:
        data = request.data
        html_messages = data.get('messages', [])
        
        if not html_messages:
            return Response({
                'status': 'error',
                'message': 'No messages provided'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        processed_messages = []
        expansion_stats = {
            'total': len(html_messages),
            'expanded': 0,
            'expansion_failed': 0,
            'no_expansion_needed': 0,
            'parsing_errors': 0
        }
        
        print(f"[DJANGO][HTML] Processing {len(html_messages)} HTML messages")
        
        for html_msg in html_messages:
            try:
                message_id = html_msg.get('id')
                chat_name = html_msg.get('chat', 'ORDERS Restaurants')
                raw_html = html_msg.get('html', '')
                timestamp_str = html_msg.get('timestamp')
                message_data = html_msg.get('message_data', {})
                
                if not message_id or not raw_html:
                    print(f"[DJANGO][HTML][SKIP] Missing ID or HTML: id={message_id}")
                    continue
                
                # Parse timestamp
                try:
                    if timestamp_str:
                        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                    else:
                        timestamp = timezone.now()
                except Exception as e:
                    print(f"[DJANGO][HTML][TIMESTAMP] Error parsing timestamp: {e}")
                    timestamp = timezone.now()
                
                # Parse HTML content using BeautifulSoup
                parsed_content = parse_html_message(raw_html)
                
                # Track expansion statistics
                if message_data.get('was_expanded'):
                    expansion_stats['expanded'] += 1
                elif message_data.get('expansion_failed'):
                    expansion_stats['expansion_failed'] += 1
                else:
                    expansion_stats['no_expansion_needed'] += 1
                
                # Use enhanced classification if available, otherwise fallback to basic
                if parsed_content.get('classified_type'):
                    message_type = parsed_content['classified_type']
                else:
                    message_type = classify_message_type({
                        'content': parsed_content['content'],
                        'media_type': 'image' if parsed_content['image_urls'] else ('voice' if parsed_content['has_voice'] else 'text')
                    })
                
                # Check if message already exists (by ID or content hash for deduplication)
                content_hash = hashlib.md5(parsed_content['content'].encode('utf-8')).hexdigest()
                
                existing_message = WhatsAppMessage.objects.filter(
                    models.Q(message_id=message_id) | 
                    models.Q(content_hash=content_hash)
                ).first()
                
                if existing_message:
                    # Update existing message with new HTML data
                    # CRITICAL FIX: Don't overwrite content if message has been manually edited
                    if not existing_message.edited:
                        existing_message.content = parsed_content['content']
                        print(f"[DJANGO][HTML][CONTENT_UPDATE] id={message_id} - Updated content (not edited)")
                    else:
                        print(f"[DJANGO][HTML][CONTENT_PROTECTED] id={message_id} - Preserving edited content")
                    
                    existing_message.content_hash = content_hash
                    existing_message.message_type = message_type
                    existing_message.media_url = ', '.join(parsed_content['image_urls']) if parsed_content['image_urls'] else ''
                    existing_message.media_type = 'image' if parsed_content['image_urls'] else ('voice' if parsed_content['has_voice'] else '')
                    existing_message.raw_html = safe_html_content(raw_html)
                    existing_message.was_expanded = message_data.get('was_expanded', False)
                    existing_message.expansion_failed = message_data.get('expansion_failed', False)
                    existing_message.original_preview = message_data.get('original_preview', '')
                    existing_message.save()
                    
                    message = existing_message
                    print(f"[DJANGO][HTML][UPDATED] id={message_id} type={message_type} hash={content_hash[:8]}")
                else:
                    # Create new message with enhanced data
                    message = WhatsAppMessage.objects.create(
                        message_id=message_id,
                        chat_name=chat_name,
                        sender_name="Group Member",  # Will be extracted later if needed
                        content=parsed_content['content'],
                        cleaned_content=parsed_content['content'],
                        content_hash=content_hash,
                        timestamp=timestamp,
                        message_type=message_type,
                        media_url=', '.join(parsed_content['image_urls']) if parsed_content['image_urls'] else '',
                        media_type='image' if parsed_content['image_urls'] else ('voice' if parsed_content['has_voice'] else ''),
                        media_info='',
                        raw_html=safe_html_content(raw_html),
                        was_expanded=message_data.get('was_expanded', False),
                        expansion_failed=message_data.get('expansion_failed', False),
                        original_preview=message_data.get('original_preview', ''),
                        # ENHANCED: Use preserved business logic results
                        confidence_score=parsed_content.get('classification_confidence', 0.9),
                        manual_company=parsed_content.get('extracted_company', ''),
                    )
                    print(f"[DJANGO][HTML][CREATED] id={message_id} type={message_type} hash={content_hash[:8]}")
                
                # Flag messages that failed expansion for manual review
                if message_data.get('expansion_failed'):
                    message.needs_manual_review = True
                    message.review_reason = 'Truncated message expansion failed'
                    message.save()
                
                # Extract company for order messages
                if message.message_type == 'order' and not message.manual_company:
                    company = message.extract_company_name()
                    if company:
                        print(f"[DJANGO][HTML][COMPANY] id={message_id} company='{company}'")
                
                processed_messages.append(message)
                
            except Exception as e:
                expansion_stats['parsing_errors'] += 1
                print(f"[DJANGO][HTML][ERROR] Failed to process message {html_msg.get('id', 'unknown')}: {e}")
                continue
        
        print(f"[DJANGO][HTML] Processed {len(processed_messages)} messages successfully")
        print(f"[DJANGO][HTML] Expansion stats: {expansion_stats}")
        
        return Response({
            'status': 'success',
            'processed_count': len(processed_messages),
            'expansion_stats': expansion_stats,
            'message_ids': [msg.message_id for msg in processed_messages]
        })
        
    except Exception as e:
        print(f"[DJANGO][HTML][CRITICAL] Error processing HTML messages: {e}")
        import traceback
        print(f"[DJANGO][HTML][TRACEBACK] {traceback.format_exc()}")
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def parse_html_message(html):
    """
    Enhanced HTML parsing with preserved business logic
    Combines fast HTML extraction with intelligent content analysis
    """
    try:
        soup = BeautifulSoup(html, 'html.parser')
        
        # FIXED: Extract text content avoiding duplicate copyable-text elements
        # Use the same logic as the fixed frontend crawler
        content_lines = []
        
        # First try to find primary copyable-text containers (avoid nested duplicates)
        primary_copyable = soup.select('._ahy1.copyable-text, ._ahy2.copyable-text')
        
        if primary_copyable:
            # Use only the first primary container to avoid duplicates
            elem = primary_copyable[0]
            
            # FIXED: Get text directly from primary element to avoid nested duplication
            # The nested selectable-text spans often contain duplicate content
            text = elem.get_text().strip()
            # Remove timestamps from end of text (comprehensive patterns)
            text = clean_timestamp_from_text(text)
            if text and not re.match(r'^\d{1,2}:\d{2}$', text):
                content_lines.append(text)
        else:
            # Fallback: use any .copyable-text element (but only the first one)
            copyable_elements = soup.select('.copyable-text')
            if copyable_elements:
                elem = copyable_elements[0]  # Only use the first one to avoid duplicates
                text = elem.get_text().strip()
                # Remove timestamps from end of text (comprehensive patterns)
                text = clean_timestamp_from_text(text)
                if text and not re.match(r'^\d{1,2}:\d{2}$', text):
                    content_lines.append(text)
        
        content = '\n'.join(content_lines) if content_lines else ''
        
        # Extract image URLs
        image_elements = soup.select('[aria-label="Open picture"] img[src], img[src^="http"]')
        image_urls = []
        for img in image_elements:
            src = img.get('src', '')
            if src and src.startswith('http'):
                image_urls.append(src)
        
        # Check for voice messages
        voice_elements = soup.select('button[aria-label*="voice" i], [aria-label*="Voice message" i]')
        has_voice = len(voice_elements) > 0
        
        # ENHANCED: Apply preserved business logic for immediate insights
        enhanced_data = {}
        if content:
            try:
                # Import preserved processors
                from .processors.company_extractor import get_company_extractor
                from .processors.order_item_parser import get_order_item_parser
                from .processors.message_classifier import get_message_classifier
                
                # Quick classification (lightweight)
                classifier = get_message_classifier()
                message_type, confidence = classifier.classify_message(content)
                enhanced_data['classified_type'] = message_type.value
                enhanced_data['classification_confidence'] = confidence
                
                # Quick company extraction (if high confidence classification)
                if confidence > 0.7:
                    company_extractor = get_company_extractor()
                    extracted_company = company_extractor.extract_company(content)
                    if extracted_company:
                        enhanced_data['extracted_company'] = extracted_company
                
                # Quick item detection (for order messages)
                if message_type.value == 'order':
                    item_parser = get_order_item_parser()
                    has_items = any(item_parser._has_quantity_indicators(line) for line in content_lines)
                    enhanced_data['has_order_items'] = has_items
                
            except Exception as e:
                print(f"[DJANGO][HTML][ENHANCE] Error in enhanced processing: {e}")
                # Continue with basic parsing if enhancement fails
        
        return {
            'content': content,
            'image_urls': image_urls,
            'has_voice': has_voice,
            'parsed_elements': len(content_lines),
            # ENHANCED: Include preserved business logic results
            **enhanced_data
        }
        
    except Exception as e:
        print(f"[DJANGO][HTML][PARSE] Error parsing HTML: {e}")
        return {
            'content': '',
            'image_urls': [],
            'has_voice': False,
            'parsing_error': str(e)
        }


@api_view(['GET'])
@authentication_classes([FlexibleAuthentication])
@permission_classes([IsAuthenticated])
def get_messages(request):
    """Get WhatsApp messages for the Flutter app with pagination"""
    
    # Filter parameters
    message_type = request.GET.get('type')
    processed = request.GET.get('processed')
    order_day = request.GET.get('order_day')
    
    # Pagination parameters
    page_param = request.GET.get('page', '1')
    page_size_param = request.GET.get('page_size', '20')
    
    # Legacy limit parameter for backward compatibility
    limit_param = request.GET.get('limit')
    
    try:
        page = int(page_param)
        page_size = int(page_size_param)
        
        if page < 1:
            return Response({
                'error': 'page must be 1 or greater'
            }, status=400)
            
        if page_size < 1 or page_size > 100:
            return Response({
                'error': 'page_size must be between 1 and 100'
            }, status=400)
            
    except ValueError:
        return Response({
            'error': 'page and page_size must be valid integers'
        }, status=400)
    
    # Handle legacy limit parameter
    if limit_param:
        try:
            limit = int(limit_param)
            if limit <= 0 or limit > 1000:
                return Response({
                    'error': 'limit must be between 1 and 1000'
                }, status=400)
            # Use limit as page_size and set page to 1
            page_size = limit
            page = 1
        except ValueError:
            return Response({
                'error': 'limit must be a valid integer'
            }, status=400)
    
    queryset = WhatsAppMessage.objects.filter(is_deleted=False)
    
    if message_type:
        queryset = queryset.filter(message_type=message_type)
    
    if processed is not None:
        queryset = queryset.filter(processed=processed.lower() == 'true')
    
    if order_day:
        queryset = queryset.filter(order_day=order_day)
    
    # Calculate pagination
    total_count = queryset.count()
    total_pages = (total_count + page_size - 1) // page_size  # Ceiling division
    
    # Calculate offset
    offset = (page - 1) * page_size
    
    # Get messages for current page - order by timestamp ascending (oldest first) to match frontend expectation
    messages = queryset.order_by('timestamp')[offset:offset + page_size]
    
    serializer = WhatsAppMessageSerializer(messages, many=True)
    
    return Response({
        'messages': serializer.data,
        'pagination': {
            'current_page': page,
            'page_size': page_size,
            'total_pages': total_pages,
            'total_count': total_count,
            'has_next': page < total_pages,
            'has_previous': page > 1,
            'next_page': page + 1 if page < total_pages else None,
            'previous_page': page - 1 if page > 1 else None
        },
        'returned_count': len(serializer.data)
    })

@api_view(['POST'])
@permission_classes([AllowAny])
def edit_message(request):
    """Edit a WhatsApp message content"""
    
    serializer = EditMessageSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    message_id = serializer.validated_data['message_id']
    edited_content = serializer.validated_data['edited_content']
    processed = serializer.validated_data.get('processed')
    
    try:
        message = WhatsAppMessage.objects.get(message_id=message_id)
        
        # Store original content if not already edited
        if not message.edited:
            message.original_content = message.content
        
        # CRITICAL FIX: Do NOT clean company names from edited content
        # Karl should be able to keep company names in messages if needed
        # The manual_company field preserves the assignment regardless of content
        message.content = edited_content
        message.edited = True
        print(f"[DJANGO][EDIT] id={message.message_id} - Message marked as edited")
        
        # Update processed status if provided
        if processed is not None:
            message.processed = processed
            
            # STOCK UPDATE FIX: If this is a stock message being marked as unprocessed,
            # also mark the associated StockUpdate as unprocessed so it can be reapplied to inventory
            if message.message_type == 'stock' and processed == False:
                try:
                    from .models import StockUpdate
                    stock_update = StockUpdate.objects.get(message=message)
                    stock_update.processed = False
                    stock_update.save()
                    print(f"[STOCK FIX] Marked StockUpdate {stock_update.id} as unprocessed for message {message.message_id}")
                except StockUpdate.DoesNotExist:
                    print(f"[STOCK FIX] No StockUpdate found for message {message.message_id}")
                except Exception as e:
                    print(f"[STOCK FIX] Error updating StockUpdate: {e}")
        
        # CRITICAL: Preserve manual_company assignment - it should NEVER be cleared by editing
        # Only Karl can change the customer assignment through the dropdown, not by editing content
        # This ensures customer assignments are stable and don't get lost accidentally
        
        message.save()
        
        # Log the edit
        log_processing_action(message, 'edited', {
            'original_length': len(message.original_content or ''),
            'new_length': len(edited_content)
        })
        
        serializer = WhatsAppMessageSerializer(message)
        return Response({
            'status': 'success',
            'message': serializer.data
        })
        
    except WhatsAppMessage.DoesNotExist:
        return Response(
            {
                'error': 'Message not found',
                'message': 'The requested WhatsApp message could not be found. It may have been deleted or the ID is incorrect.'
            }, 
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Failed to update message: {str(e)}")
        return Response(
            {
                'error': 'Unable to update message',
                'message': 'An unexpected error occurred while updating the message. Please try again.',
                'details': str(e) if settings.DEBUG else None
            }, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([AllowAny])
def update_message_company(request):
    """Update manual company selection for a message"""
    
    message_id = request.data.get('message_id')
    company_name = request.data.get('company_name')
    
    if not message_id:
        return Response({'error': 'message_id is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        message = WhatsAppMessage.objects.get(id=message_id)  # Using database ID
        message.manual_company = company_name
        message.save()
        
        # Log the company update
        log_processing_action(message, 'company_updated', {
            'company_name': company_name
        })
        
        serializer = WhatsAppMessageSerializer(message)
        return Response({
            'status': 'success',
            'message': 'Company updated successfully',
            'data': serializer.data
        })
        
    except WhatsAppMessage.DoesNotExist:
        return Response(
            {
                'error': 'Message not found',
                'message': f'WhatsApp message with ID {message_id} could not be found. Please verify the message ID is correct.'
            }, 
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Failed to update message company: {str(e)}")
        return Response(
            {
                'error': 'Unable to update company assignment',
                'message': 'An error occurred while updating the company assignment. Please try again.',
                'details': str(e) if settings.DEBUG else None
            }, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([AllowAny])
def update_message_type(request):
    """Update message type (order, stock, instruction, etc.)"""
    
    serializer = UpdateMessageTypeSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    message_id = serializer.validated_data['message_id']
    new_message_type = serializer.validated_data['message_type']
    
    try:
        message = WhatsAppMessage.objects.get(id=message_id)
        old_message_type = message.message_type
        
        # Update message type
        message.message_type = new_message_type
        
        # CRITICAL: Always preserve customer assignments regardless of message type
        # Customer assignments should NEVER be cleared automatically
        # Users can manually clear them if needed through the UI
        
        # Reset processed status when changing type so it can be reprocessed
        message.processed = False
        
        message.save()
        
        # Log the type change
        log_processing_action(message, 'type_updated', {
            'old_type': old_message_type,
            'new_type': new_message_type
        })
        
        serializer = WhatsAppMessageSerializer(message)
        return Response({
            'status': 'success',
            'message': f'Message type updated from {old_message_type} to {new_message_type}',
            'data': serializer.data
        })
        
    except WhatsAppMessage.DoesNotExist:
        return Response(
            {
                'error': 'Message not found',
                'message': f'WhatsApp message with ID {message_id} could not be found.'
            }, 
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Failed to update message type: {str(e)}")
        return Response(
            {
                'error': 'Unable to update message type',
                'message': 'An error occurred while updating the message type. Please try again.',
                'details': str(e) if settings.DEBUG else None
            }, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([AllowAny])
def process_messages_to_orders(request):
    """Convert selected WhatsApp messages to Django orders"""
    
    serializer = ProcessMessagesSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    message_ids = serializer.validated_data['message_ids']
    
    orders_created = []
    errors = []
    warnings = []
    
    # Store error messages for logging OUTSIDE transaction
    error_logs = []
    
    # Get messages first - handle both database IDs and WhatsApp message IDs
    # Check if message_ids are integers (database IDs) or strings (WhatsApp message IDs)
    try:
        # Try to convert first ID to int to determine the type
        int(message_ids[0])
        # If successful, these are database IDs
        messages = WhatsAppMessage.objects.filter(
            id__in=message_ids,
            message_type='order'
        )
    except (ValueError, TypeError, IndexError):
        # If conversion fails, these are WhatsApp message IDs
        messages = WhatsAppMessage.objects.filter(
            message_id__in=message_ids,
            message_type='order'
        )
    
    for message in messages:
        try:
            # Skip if already processed
            if message.processed:
                warnings.append({
                    'message_id': message.message_id,
                    'warning': 'Message already processed',
                    'existing_order': message.order.order_number if message.order else None
                })
                continue
            
            # Create order from message (this handles message.processed, message.order, and message.save())
            order_result = create_order_from_message(message)
            
            if isinstance(order_result, dict) and order_result.get('status') == 'failed':
                # Order creation failed but we have suggestions
                errors.append({
                    'message_id': message.message_id,
                    'error': order_result.get('message', 'Failed to create order - no valid items found'),
                    'items': order_result.get('items', []),  # Include successfully processed items
                    'failed_products': order_result.get('failed_products', []),
                    'parsing_failures': order_result.get('parsing_failures', []),
                    'unparseable_lines': order_result.get('unparseable_lines', [])
                })
                # Store message for detailed error analysis
                error_logs.append({
                    'message': message,
                    'error': order_result.get('message', 'Failed to create order - no valid items found'),
                    'failed_products': order_result.get('failed_products', []),
                    'action': 'order_creation_failed_with_suggestions'
                })
            elif order_result:
                # Order created successfully
                orders_created.append(order_result)
                # Note: message.processed, message.order, and message.save() are already handled in create_order_from_message()
            else:
                # Order creation failed with no suggestions
                errors.append({
                    'message_id': message.message_id,
                    'error': 'Failed to create order - no valid items found'
                })
                # Store message for detailed error analysis
                error_logs.append({
                    'message': message,
                    'error': 'Failed to create order - no valid items found',
                    'action': 'order_creation_failed'
                })
                
        except Exception as e:
            errors.append({
                'message_id': message.message_id,
                'error': str(e),
                'traceback': traceback.format_exc()
            })
            # Store for logging
            error_logs.append({
                'message': message,
                'error': str(e)
            })
    
    # Log errors and get detailed error info OUTSIDE transaction to avoid conflicts
    for error_log in error_logs:
        try:
            log_processing_action(error_log['message'], 'error', {
                'error': error_log['error'],
                'action': error_log.get('action', 'order_creation')
            })
            
            # Get detailed error information for failed orders
            if error_log.get('action') == 'order_creation_failed':
                try:
                    from .services import parse_order_items
                    
                    # Just parse the items to see what failed - don't create order items
                    parsed_items = parse_order_items(error_log['message'].content)
                    
                    failed_products = []
                    for item in parsed_items:
                        # Get suggestions for this failed product
                        from .services import get_or_create_product_enhanced
                        product_name = item.get('product_name', 'Unknown')
                        
                        # Try to get suggestions
                        suggestions_list = []
                        try:
                            # Use the smart matcher to get suggestions
                            from .smart_product_matcher import SmartProductMatcher
                            matcher = SmartProductMatcher()
                            suggestions = matcher.get_suggestions(product_name, min_confidence=10.0, max_suggestions=30)
                            
                            for suggestion in suggestions.suggestions:
                                suggestions_list.append({
                                    'name': suggestion.product.name,
                                    'confidence': suggestion.confidence_score,
                                    'unit': suggestion.product.unit,
                                    'price': float(suggestion.product.price),
                                    'id': suggestion.product.id
                                })
                        except Exception as e:
                            print(f"Error getting suggestions for {product_name}: {e}")
                        
                        failed_products.append({
                            'original_name': product_name,
                            'quantity': item.get('quantity', 1),
                            'unit': item.get('unit', 'piece'),
                            'failure_reason': 'Product not found in database',
                            'suggestions': suggestions_list
                        })
                    
                    # Update the error in the errors list with simple failed products info
                    for error in errors:
                        if error.get('message_id') == error_log['message'].message_id:
                            error.update({
                                'failed_products': failed_products,
                                'items_attempted': len(parsed_items),
                                'items_created': 0,
                                'message': 'Products not found. Please select from available products.'
                            })
                            break
                except Exception as detail_e:
                    print(f"Failed to get detailed error info: {detail_e}")
                    
        except Exception as log_e:
            print(f"Failed to log error: {log_e}")
    
    # Check if we have failed products with suggestions (new format) BEFORE creating serializer
    has_detailed_errors = any(
        'failed_products' in error or 
        'parsing_failures' in error or 
        'unparseable_lines' in error 
        for error in errors
    )
    
    if has_detailed_errors and len(orders_created) == 0:
        # Return new format for failed products with suggestions
        failed_products = []
        parsing_failures = []
        unparseable_lines = []
        successful_items = []
        
        for error in errors:
            if 'failed_products' in error:
                failed_products.extend(error['failed_products'])
            if 'parsing_failures' in error:
                parsing_failures.extend(error['parsing_failures'])
            if 'unparseable_lines' in error:
                unparseable_lines.extend(error['unparseable_lines'])
            if 'items' in error:  # Include successfully processed items
                successful_items.extend(error['items'])
        
        return Response({
            'status': 'failed',
            'message': f'Order creation failed - {len(failed_products)} items need attention. Use suggestions to fix and retry.',
            'items': successful_items,  # Include successfully processed items
            'failed_products': failed_products,
            'parsing_failures': parsing_failures,
            'unparseable_lines': unparseable_lines
        })
    
    # Use old format for other cases
    result_serializer = OrderCreationResultSerializer(data={
        'status': 'completed',
        'orders_created': len(orders_created),
        'order_numbers': [order.order_number for order in orders_created],
        'errors': errors,
        'warnings': warnings
    })
    
    if result_serializer.is_valid():
        return Response(result_serializer.data)
    else:
        return Response({
            'status': 'completed',
            'orders_created': len(orders_created),
            'order_numbers': [order.order_number for order in orders_created],
            'errors': errors,
            'warnings': warnings
        })

@api_view(['POST'])
@permission_classes([AllowAny])
def process_stock_messages(request):
    """Process selected stock messages to update inventory levels"""
    
    serializer = ProcessMessagesSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    message_ids = serializer.validated_data['message_ids']
    
    stock_updates_created = 0
    errors = []
    warnings = []
    error_logs = []
    
    with transaction.atomic():
        messages = WhatsAppMessage.objects.filter(
            message_id__in=message_ids,
            message_type='stock'
        )
        
        for message in messages:
            try:
                # Skip if already processed
                if message.processed:
                    warnings.append({
                        'message_id': message.message_id,
                        'warning': 'Stock message already processed'
                    })
                    continue
                
                # Process stock update
                if message.is_stock_controller():
                    stock_data = parse_stock_message(message)
                    if stock_data:
                        stock_update, created = StockUpdate.objects.get_or_create(
                            message=message,
                            defaults={
                                'stock_date': stock_data['date'],
                                'order_day': stock_data['order_day'],
                                'items': stock_data['items']
                            }
                        )
                        
                        if created:
                            stock_updates_created += 1
                            message.processed = True
                            message.save()
                            
                            log_processing_action(message, 'stock_updated', {
                                'items_count': len(stock_data['items']),
                                'order_day': stock_data['order_day']
                            })
                        else:
                            warnings.append({
                                'message_id': message.message_id,
                                'warning': 'Stock update already exists for this message'
                            })
                    else:
                        errors.append({
                            'message_id': message.message_id,
                            'error': 'Failed to parse stock data from message'
                        })
                else:
                    errors.append({
                        'message_id': message.message_id,
                        'error': 'Message is not from stock controller (SHALLOME)'
                    })
                    
            except Exception as e:
                errors.append({
                    'message_id': message.message_id,
                    'error': str(e),
                    'traceback': traceback.format_exc()
                })
                
                # Store for logging OUTSIDE transaction
                error_logs.append({
                    'message': message,
                    'error': str(e),
                    'action': 'stock_processing'
                })
    
    # Log errors OUTSIDE transaction to avoid conflicts
    for error_log in error_logs:
        try:
            log_processing_action(error_log['message'], 'error', {
                'error': error_log['error'],
                'action': error_log['action']
            })
        except Exception as log_e:
            print(f"Failed to log error: {log_e}")
    
    return Response({
        'status': 'completed',
        'stock_updates_created': stock_updates_created,
        'errors': errors,
        'warnings': warnings
    })

@api_view(['GET'])
@permission_classes([AllowAny])
def get_stock_updates(request):
    """Get stock updates from SHALLOME"""
    
    order_day = request.GET.get('order_day')
    processed = request.GET.get('processed')
    limit_param = request.GET.get('limit')
    if limit_param is None:
        return Response({
            'error': 'limit parameter is required'
        }, status=400)
    
    try:
        limit = int(limit_param)
        if limit <= 0 or limit > 100:
            return Response({
                'error': 'limit must be between 1 and 100'
            }, status=400)
    except ValueError:
        return Response({
            'error': 'limit must be a valid integer'
        }, status=400)
    
    queryset = StockUpdate.objects.all()
    
    if order_day:
        queryset = queryset.filter(order_day=order_day)
    
    if processed is not None:
        queryset = queryset.filter(processed=processed.lower() == 'true')
    
    stock_updates = queryset.order_by('-stock_date')[:limit]
    
    serializer = StockUpdateSerializer(stock_updates, many=True)
    return Response({
        'stock_updates': serializer.data,
        'total_count': queryset.count()
    })

@api_view(['GET'])
@permission_classes([AllowAny])
def validate_order_stock(request, order_id):
    """Validate an order against available stock"""
    
    try:
        from orders.models import Order
        order = get_object_or_404(Order, id=order_id)
        
        validation_result = validate_order_against_stock(order)
        
        serializer = StockValidationSerializer(data=validation_result)
        if serializer.is_valid():
            return Response(serializer.data)
        else:
            return Response(validation_result)
            
    except Exception as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([AllowAny])
def get_processing_logs(request):
    """Get message processing logs"""
    
    message_id = request.GET.get('message_id')
    action = request.GET.get('action')
    limit_param = request.GET.get('limit')
    if limit_param is None:
        return Response({
            'error': 'limit parameter is required'
        }, status=400)
    
    try:
        limit = int(limit_param)
        if limit <= 0 or limit > 200:
            return Response({
                'error': 'limit must be between 1 and 200'
            }, status=400)
    except ValueError:
        return Response({
            'error': 'limit must be a valid integer'
        }, status=400)
    
    queryset = MessageProcessingLog.objects.all()
    
    if message_id:
        queryset = queryset.filter(message__message_id=message_id)
    
    if action:
        queryset = queryset.filter(action=action)
    
    logs = queryset.order_by('-timestamp')[:limit]
    
    from .serializers import MessageProcessingLogSerializer
    serializer = MessageProcessingLogSerializer(logs, many=True)
    
    return Response({
        'logs': serializer.data,
        'total_count': queryset.count()
    })

def process_order_demarcations(messages):
    """Process order day demarcation messages"""
    
    for message in messages:
        if message.is_order_day_demarcation():
            try:
                # Extract order day from content
                content_upper = message.content.upper()
                if 'THURSDAY' in content_upper:
                    order_day = 'Thursday'
                elif 'TUESDAY' in content_upper:
                    order_day = 'Tuesday'  # Note: User mentioned Tuesday in some contexts
                else:
                    order_day = 'Monday'  # Default
                
                # Create or update demarcation
                demarcation, created = OrderDayDemarcation.objects.get_or_create(
                    order_day=order_day,
                    demarcation_date=message.timestamp.date(),
                    defaults={'message': message, 'active': True}
                )
                
                # Update order_day context for subsequent messages
                message.order_day = order_day
                message.save()
                
                if created:
                    log_processing_action(message, 'classified', {
                        'type': 'demarcation',
                        'order_day': order_day
                    })
                    
            except Exception as e:
                log_processing_action(message, 'error', {
                    'error': str(e),
                    'action': 'demarcation_processing'
                })

def _reevaluate_company_assignments_after_deletion(deleted_message, deleted_company):
    """Re-evaluate company assignments for messages that might have been affected by deletion"""
    from datetime import timedelta
    
    print(f"[DJANGO][DELETE][REEVALUATE] Starting re-evaluation for deleted company '{deleted_company}'")
    
    # Find messages in the same chat within a time window that might have been affected
    time_window_start = deleted_message.timestamp - timedelta(minutes=10)
    time_window_end = deleted_message.timestamp + timedelta(minutes=10)
    
    affected_messages = WhatsAppMessage.objects.filter(
        chat_name=deleted_message.chat_name,
        timestamp__gte=time_window_start,
        timestamp__lte=time_window_end,
        is_deleted=False,
        message_type='order'  # Only check order messages
    ).exclude(id=deleted_message.id)
    
    for message in affected_messages:
        # Check if this message might have been affected by the deletion
        from .message_parser import django_message_parser
        own_company = django_message_parser.to_canonical_company(message.content)
        
        # Case 1: Message has manual assignment to the deleted company
        # DON'T clear manual assignments - user explicitly chose this company
        # Manual assignments should persist even if the company name message is deleted
        if message.manual_company == deleted_company:
            # Log that we found a manual assignment but are preserving it
            log_processing_action(message, 'manual_company_preserved', {
                'deleted_company': deleted_company,
                'deleted_message_id': deleted_message.id,
                'preserved_manual_company': message.manual_company
            })
            
        # Case 2: Message doesn't have its own company and might be using context
        elif not own_company and not message.manual_company:
            # This message relies on context - check if it would have used the deleted company
            current_company = message.extract_company_name()
            
            if current_company == deleted_company:
                # This message was getting company from the deleted context
                # Force re-evaluation by temporarily clearing and recalculating
                # (Note: since manual_company is already None, extract_company_name will re-evaluate)
                new_company = message.extract_company_name()
                
                # Log the change if company actually changed
                if new_company != deleted_company:
                    log_processing_action(message, 'context_company_changed', {
                        'deleted_company': deleted_company,
                        'deleted_message_id': deleted_message.id,
                        'new_company': new_company
                    })

@api_view(['DELETE'])
@permission_classes([AllowAny])
def delete_message(request, message_id):
    """Delete a single WhatsApp message and re-evaluate related company assignments"""
    try:
        message = WhatsAppMessage.objects.get(id=message_id)
        message_content = message.content[:50]  # For logging
        
        # Check if this message contains a company name
        from .message_parser import django_message_parser
        deleted_company = django_message_parser.to_canonical_company(message.content)
        
        print(f"[DJANGO][DELETE] Deleting message ID {message_id}, content: '{message.content[:30]}', detected_company: '{deleted_company}'")
        
        message.is_deleted = True
        message.save()
        
        # If we deleted a company name message, re-evaluate related messages
        if deleted_company:
            print(f"[DJANGO][DELETE] Company '{deleted_company}' detected, starting re-evaluation...")
            _reevaluate_company_assignments_after_deletion(message, deleted_company)
        else:
            print(f"[DJANGO][DELETE] No company detected in deleted message, skipping re-evaluation")
        
        return Response({
            'status': 'success',
            'message': f'Message deleted: {message_content}...'
        })
    except WhatsAppMessage.DoesNotExist:
        return Response({
            'status': 'error',
            'message': 'Message not found'
        }, status=404)
    except Exception as e:
        return Response({
            'status': 'error',
            'message': f'Failed to delete message: {str(e)}'
        }, status=500)

@api_view(['POST'])
@permission_classes([AllowAny])
def bulk_delete_messages(request):
    """Delete multiple WhatsApp messages and re-evaluate related company assignments"""
    try:
        message_ids = request.data.get('message_ids', [])
        
        if not message_ids:
            return Response({
                'status': 'error',
                'message': 'No message IDs provided'
            }, status=400)
        
        # Get messages before deletion to check for company names
        messages_to_delete = WhatsAppMessage.objects.filter(id__in=message_ids)
        deleted_companies = []
        
        from .message_parser import django_message_parser
        for message in messages_to_delete:
            company = django_message_parser.to_canonical_company(message.content)
            if company:
                deleted_companies.append((message, company))
        
        # Perform the deletion
        deleted_count = messages_to_delete.update(is_deleted=True)
        
        # Re-evaluate affected messages
        for message, company in deleted_companies:
            _reevaluate_company_assignments_after_deletion(message, company)
        
        return Response({
            'status': 'success',
            'message': f'Deleted {deleted_count} messages',
            'deleted_count': deleted_count
        })
    except Exception as e:
        return Response({
            'status': 'error',
            'message': f'Failed to delete messages: {str(e)}'
        }, status=500)

@api_view(['POST'])
@permission_classes([AllowAny])
def refresh_company_extraction(request):
    """Refresh company name extraction for messages using context-aware logic"""
    try:
        # Get all order messages without company names
        messages_to_update = WhatsAppMessage.objects.filter(
            message_type='order',
            company_name='',
            is_deleted=False
        ).order_by('timestamp')
        
        updated_count = 0
        for message in messages_to_update:
            # Re-extract company name with new context-aware logic
            new_company = message.extract_company_name()
            if new_company and new_company != message.company_name:
                message.company_name = new_company
                message.save(update_fields=['company_name'])
                updated_count += 1
                print(f"Updated message {message.id}: '{message.content[:50]}...' -> Company: '{new_company}'")
        
        return Response({
            'status': 'success',
            'message': f'Updated company names for {updated_count} messages',
            'updated_count': updated_count
        })
    except Exception as e:
        return Response({
            'status': 'error',
            'message': f'Failed to refresh company extraction: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def apply_stock_updates_to_inventory(request):
    """Apply processed StockUpdate data to FinishedInventory"""
    
    try:
        from .services import apply_stock_updates_to_inventory as apply_updates
        from .models import StockUpdate
        
        # Allow explicit control of reset behavior via request data
        reset_before_processing = request.data.get('reset_before_processing', True)
        
        result = apply_updates(reset_before_processing=reset_before_processing)
        
        # Update related messages with processing results
        try:
            # If no items were processed (because all stock updates are already processed),
            # we need to temporarily mark some stock updates as unprocessed to get real results
            if result.get('total_items_processed', 0) == 0:
                # Find the most recent stock updates and temporarily mark them as unprocessed
                recent_stock_updates = StockUpdate.objects.filter(processed=True).order_by('-id')[:3]
                
                if recent_stock_updates.exists():
                    # Temporarily mark as unprocessed
                    for update in recent_stock_updates:
                        update.processed = False
                        update.save()
                    
                    # Re-run the inventory application to get real results
                    result = apply_updates(reset_before_processing=reset_before_processing)
                    
                    # Mark them back as processed
                    for update in recent_stock_updates:
                        update.processed = True
                        update.save()
            
            # Find messages that need inventory info updates
            from django.db.models import Q
            
            all_messages_to_update = WhatsAppMessage.objects.filter(
                processing_notes__icontains='Stock processed:'
            ).filter(
                Q(processing_notes__icontains='Inventory: 0/0 applied (0%)') |
                ~Q(processing_notes__icontains='Inventory:')
            )
            
            for message in all_messages_to_update:
                success_rate = result.get('success_rate', 0)
                successful_items = result.get('successful_items', 0)
                total_items = result.get('total_items_processed', 0)
                
                if success_rate >= 90:
                    status_icon = "✅"
                elif success_rate >= 70:
                    status_icon = "⚠️"
                else:
                    status_icon = "❌"
                
                # Replace the old inventory info or add new inventory info
                if 'Inventory: 0/0 applied (0%)' in message.processing_notes:
                    # Replace the placeholder inventory info
                    message.processing_notes = message.processing_notes.replace(
                        'Inventory: 0/0 applied (0%)',
                        f'Inventory: {successful_items}/{total_items} applied ({success_rate}%)'
                    )
                    # Also update the status icon
                    message.processing_notes = message.processing_notes.replace(
                        '❌ Inventory:',
                        f'{status_icon} Inventory:'
                    )
                elif 'Inventory:' not in message.processing_notes:
                    # Add inventory info for the first time
                    message.processing_notes += f" | {status_icon} Inventory: {successful_items}/{total_items} applied ({success_rate}%)"
                
                # Add detailed failure information
                if result.get('failed_items'):
                    failure_details = []
                    for failed_item in result['failed_items']:
                        failure_details.append(f"'{failed_item['original_name']}': {failed_item['failure_reason']}")
                    
                    if failure_details:
                        # Remove old failed items info if it exists
                        if 'Failed items:' in message.processing_notes:
                            parts = message.processing_notes.split('Failed items:')
                            if len(parts) > 1:
                                # Keep everything before "Failed items:" and add new failure info
                                before_failures = parts[0].rstrip(' |')
                                message.processing_notes = f"{before_failures} | Failed items: {'; '.join(failure_details)}"
                        else:
                            message.processing_notes += f" | Failed items: {'; '.join(failure_details)}"
                
                # Add processing warnings summary
                if result.get('processing_warnings'):
                    warning_count = len(result['processing_warnings'])
                    if 'warnings' not in message.processing_notes:
                        message.processing_notes += f" | ⚠️ {warning_count} warnings"
                
                message.save()
        except Exception as msg_error:
            # Don't fail the main operation if message updates fail
            print(f"Warning: Failed to update message processing notes: {msg_error}")
        
        return Response({
            'status': 'success',
            'data': result
        })
        
    except Exception as e:
        # Try to update any related messages with error status
        try:
            from .models import StockUpdate
            unprocessed_updates = StockUpdate.objects.filter(processed=False)
            for stock_update in unprocessed_updates:
                if hasattr(stock_update, 'message') and stock_update.message:
                    message = stock_update.message
                    if not message.processing_notes:
                        message.processing_notes = ""
                    message.processing_notes += f" | ❌ Inventory application failed: {str(e)}"
                    message.save()
        except:
            pass  # Don't fail if we can't update messages
            
        return Response({
            'status': 'error',
            'message': f'Failed to apply stock updates: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_stock_take_data(request):
    """Get stock take data, optionally filtered to only show items with stock"""
    
    try:
        from .services import get_stock_take_data as get_data
        
        only_with_stock = request.GET.get('only_with_stock', 'true').lower() == 'true'
        
        result = get_data(only_with_stock=only_with_stock)
        
        return Response({
            'status': 'success',
            'data': result
        })
        
    except Exception as e:
        return Response({
            'status': 'error',
            'message': f'Failed to get stock take data: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def process_stock_and_apply_to_inventory(request):
    """Process selected stock messages and apply to inventory in one step"""
    
    serializer = ProcessMessagesSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    message_ids = serializer.validated_data['message_ids']
    reset_before_processing = request.data.get('reset_before_processing', True)
    
    try:
        from .services import apply_stock_updates_to_inventory as apply_updates
        from django.db import transaction
        
        with transaction.atomic():
            # First process the stock messages
            stock_updates_created = 0
            processing_errors = []
            processing_warnings = []
            
            messages = WhatsAppMessage.objects.filter(
                message_id__in=message_ids,
                message_type='stock'
            )
            
            for message in messages:
                try:
                    if not message.processed and message.is_stock_controller():
                        stock_data = parse_stock_message(message)
                        if stock_data:
                            stock_update, created = StockUpdate.objects.get_or_create(
                                message=message,
                                defaults={
                                    'stock_date': stock_data['date'],
                                    'order_day': stock_data['order_day'],
                                    'items': stock_data['items']
                                }
                            )
                            
                            if created:
                                stock_updates_created += 1
                            else:
                                # If StockUpdate already exists, update it and mark as unprocessed for reprocessing
                                stock_update.stock_date = stock_data['date']
                                stock_update.order_day = stock_data['order_day']
                                stock_update.items = stock_data['items']
                                stock_update.processed = False  # Mark as unprocessed so it can be applied to inventory
                                stock_update.save()
                                
                            # Update message with detailed processing status
                            message.processed = True
                            total_lines = stock_data.get('total_lines_processed', 0)
                            success_count = len(stock_data['items'])
                            failure_count = len(stock_data.get('parsing_failures', []))
                            success_rate = stock_data.get('parsing_success_rate', 0)
                            
                            message.processing_notes = f"✅ Stock processed: {success_count}/{total_lines} items parsed ({success_rate}%)"
                            
                            # Add parsing failure details
                            if stock_data.get('parsing_failures'):
                                message.processing_notes += f" | ⚠️ {failure_count} parsing failures"
                                
                                # Add detailed failure information - show ALL failures
                                failure_details = []
                                for failure in stock_data['parsing_failures']:  # Show ALL failures
                                    failure_details.append(f"'{failure['original_line']}': {failure['failure_reason']}")
                                
                                if failure_details:
                                    message.processing_notes += f" | Failed lines: {'; '.join(failure_details)}"
                                
                                # Add to processing warnings for API response
                                processing_warnings.extend([f"Message {message.message_id}: {failure['failure_reason']}" for failure in stock_data['parsing_failures']])
                            
                            message.save()
                        else:
                            # Failed to parse stock message
                            message.processing_notes = "❌ Failed to parse stock message"
                            message.save()
                            processing_errors.append(f"Message {message.message_id}: Failed to parse stock data")
                    elif message.processed:
                        processing_warnings.append(f"Message {message.message_id}: Already processed")
                    elif not message.is_stock_controller():
                        processing_warnings.append(f"Message {message.message_id}: Not from stock controller")
                        
                except Exception as e:
                    # Update message with error
                    message.processing_notes = f"❌ Processing error: {str(e)}"
                    message.save()
                    processing_errors.append(f"Message {message.message_id}: {str(e)}")
            
            # Then apply stock updates to inventory
            inventory_result = apply_updates(reset_before_processing=reset_before_processing)
            
            # Update messages with inventory application results
            if inventory_result.get('failed_items'):
                for failed_item in inventory_result['failed_items']:
                    processing_errors.append(f"Inventory update failed: {failed_item['original_name']} - {failed_item['failure_reason']}")
            
            if inventory_result.get('processing_warnings'):
                processing_warnings.extend(inventory_result['processing_warnings'])
            
            # Update all processed messages with detailed final results
            for message in messages.filter(processed=True):
                success_rate = inventory_result.get('success_rate', 0)
                successful_items = inventory_result.get('successful_items', 0)
                total_items = inventory_result.get('total_items_processed', 0)
                failed_count = len(inventory_result.get('failed_items', []))
                
                if success_rate >= 90:
                    status_icon = "✅"
                elif success_rate >= 70:
                    status_icon = "⚠️"
                else:
                    status_icon = "❌"
                    
                message.processing_notes += f" | {status_icon} Inventory: {successful_items}/{total_items} applied ({success_rate}%)"
                
                # Add detailed failure information for inventory application - show ALL failures
                if inventory_result.get('failed_items'):
                    failure_details = []
                    for failed_item in inventory_result['failed_items']:  # Show ALL failures
                        failure_details.append(f"'{failed_item['original_name']}': {failed_item['failure_reason']}")
                    
                    if failure_details:
                        message.processing_notes += f" | Failed items: {'; '.join(failure_details)}"
                
                # Add processing warnings summary
                if inventory_result.get('processing_warnings'):
                    warning_count = len(inventory_result['processing_warnings'])
                    message.processing_notes += f" | ⚠️ {warning_count} warnings"
                
                message.save()
            
            return Response({
                'status': 'success',
                'stock_updates_created': stock_updates_created,
                'inventory_updates': inventory_result,
                'errors': processing_errors,
                'warnings': processing_warnings,
                'message': f'Processed {stock_updates_created} stock messages and applied to inventory. Success rate: {inventory_result.get("success_rate", 0)}%'
            })
            
    except Exception as e:
        # Update all messages with global error
        try:
            messages = WhatsAppMessage.objects.filter(message_id__in=message_ids)
            for message in messages:
                message.processing_notes = f"❌ Global error: {str(e)}"
                message.save()
        except:
            pass  # Don't fail if we can't update messages
            
        return Response({
            'status': 'error',
            'message': f'Failed to process stock and apply to inventory: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def update_message_corrections(request):
    """Update message with user corrections for failed products"""
    from .serializers import MessageCorrectionSerializer
    
    serializer = MessageCorrectionSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    message_id = serializer.validated_data['message_id']
    corrections = serializer.validated_data['corrections']
    
    try:
        message = WhatsAppMessage.objects.get(message_id=message_id)
        
        # Store corrections in the message's processing_notes
        import json
        try:
            # Try to parse as JSON first
            current_notes = json.loads(message.processing_notes) if message.processing_notes else {}
        except (json.JSONDecodeError, TypeError):
            # If not JSON, create a new structure with the old notes as a comment
            current_notes = {
                'original_notes': message.processing_notes or '',
                'notes_type': 'legacy_string'
            }
        
        current_notes['user_corrections'] = corrections
        current_notes['corrections_applied'] = True
        current_notes['corrections_timestamp'] = timezone.now().isoformat()
        
        message.processing_notes = json.dumps(current_notes, indent=2)
        message.save()
        
        # Log the corrections
        log_processing_action(message, 'corrections_applied', {
            'corrections_count': len(corrections),
            'corrections': corrections
        })
        
        return Response({
            'status': 'success',
            'message': 'Corrections saved successfully',
            'corrections_applied': len(corrections)
        })
        
    except WhatsAppMessage.DoesNotExist:
        return Response({
            'error': 'Message not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Failed to save message corrections: {str(e)}")
        return Response({
            'error': 'Failed to save corrections',
            'details': str(e) if settings.DEBUG else None
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def reprocess_message_with_corrections(request):
    """Reprocess a message using saved corrections"""
    from .serializers import MessageReprocessSerializer
    
    serializer = MessageReprocessSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    message_id = serializer.validated_data['message_id']
    
    try:
        message = WhatsAppMessage.objects.get(message_id=message_id)
        
        # Check if corrections exist
        import json
        current_notes = json.loads(message.processing_notes) if message.processing_notes else {}
        corrections = current_notes.get('user_corrections', {})
        
        if not corrections:
            return Response({
                'error': 'No corrections found for this message'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Reset processing status
        message.processed = False
        message.processing_notes = json.dumps({
            **current_notes,
            'reprocessing_with_corrections': True,
            'reprocess_timestamp': timezone.now().isoformat()
        })
        message.save()
        
        # Log the reprocessing
        log_processing_action(message, 'reprocess_initiated', {
            'corrections_count': len(corrections),
            'reason': 'user_corrections_applied'
        })
        
        # Actually reprocess the message with corrections
        from .services import reprocess_message_with_corrections
        
        result = reprocess_message_with_corrections(message_id, corrections)
        
        if isinstance(result, dict) and 'error' in result:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        elif isinstance(result, dict) and result.get('status') == 'failed':
            # Still has failures, return suggestions
            return Response({
                'status': 'failed',
                'message': result['message'],
                'failed_products': result['failed_products'],
                'parsing_failures': result['parsing_failures'],
                'unparseable_lines': result['unparseable_lines']
            })
        else:
            # Success - order created
            if hasattr(result, 'order_number'):
                # result is an Order object
                return Response({
                    'status': 'success',
                    'message': 'Order created successfully with corrections',
                    'order_number': result.order_number,
                    'order_id': result.id,
                    'items_count': result.items.count()
                })
            else:
                # result is a dict with success info
                return Response({
                    'status': 'success',
                    'message': 'Order created successfully with corrections',
                    'order_number': result.get('order_number', 'Unknown'),
                    'order_id': result.get('order_id', 'Unknown'),
                    'items_count': result.get('items_count', 0)
                })
        
    except WhatsAppMessage.DoesNotExist:
        return Response({
            'error': 'Message not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Failed to reprocess message: {str(e)}")
        return Response({
            'error': 'Failed to reprocess message',
            'details': str(e) if settings.DEBUG else None
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([AllowAny])
def process_message_with_suggestions(request):
    """
    Process a WhatsApp message and return suggestions for all items - requires user confirmation
    """
    message_id = request.data.get('message_id')
    
    if not message_id:
        return Response({
            'error': 'message_id is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        message = WhatsAppMessage.objects.get(message_id=message_id)
        
        # Use the new always-suggestions function
        from .services import create_order_from_message_with_suggestions
        result = create_order_from_message_with_suggestions(message)
        
        if result['status'] == 'confirmation_required':
            return Response({
                'status': 'success',
                'message': result['message'],
                'customer': result['customer'],
                'items': result['items'],
                'total_items': result['total_items']
            })
        else:
            return Response({
                'status': 'error',
                'message': result['message'],
                'items': result.get('items', [])
            }, status=status.HTTP_400_BAD_REQUEST)
        
    except WhatsAppMessage.DoesNotExist:
        return Response({
            'error': 'Message not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Failed to process message with suggestions: {str(e)}")
        return Response({
            'error': 'Failed to process message',
            'details': str(e) if settings.DEBUG else None
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([AllowAny])
def create_order_from_suggestions(request):
    """
    Create an order from confirmed suggestions
    """
    try:
        message_id = request.data.get('message_id')
        customer_data = request.data.get('customer')
        items_data = request.data.get('items', [])
        
        if not message_id or not customer_data or not items_data:
            return Response({
                'status': 'error',
                'message': 'message_id, customer, and items are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get the message
        try:
            message = WhatsAppMessage.objects.get(message_id=message_id)
        except WhatsAppMessage.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Message not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Get or create customer
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        customer, created = User.objects.get_or_create(
            email=customer_data.get('email', f"{customer_data.get('name', 'Unknown')}@example.com"),
            defaults={
                'first_name': customer_data.get('name', 'Unknown'),
                'is_active': True,
            }
        )
        
        # Create the order
        from orders.models import Order
        from products.models import Product
        
        from datetime import date
        from decimal import Decimal
        
        # Generate unique order number (max 20 chars)
        import random
        from django.utils import timezone
        
        date_str = timezone.now().strftime('%Y%m%d')  # 8 chars
        random_suffix = random.randint(1000, 9999)   # 4 chars
        order_number = f"WA{date_str}{random_suffix}"  # WA20241008123 = 14 chars ✅
        
        # Ensure order number is unique
        while Order.objects.filter(order_number=order_number).exists():
            random_suffix = random.randint(1000, 9999)
            order_number = f"WA{date_str}{random_suffix}"
        
        # Create order with required fields
        order = Order.objects.create(
            restaurant=customer,
            order_number=order_number,
            status='received',
            order_date=date.today(),
            delivery_date=date.today(),  # Will be calculated properly in production
            whatsapp_message_id=message_id,
            original_message=message.content,
            parsed_by_ai=True,
            subtotal=Decimal('0.00'),
            total_amount=Decimal('0.00'),
        )
        
        # Create order items
        total_amount = Decimal('0.00')
        created_items = []
        
        for item_data in items_data:
            try:
                product = Product.objects.get(id=item_data['product_id'])
                quantity = Decimal(str(item_data.get('quantity', 1.0)))
                unit = item_data.get('unit', product.unit)
                
                # CRITICAL: Calculate customer-specific price on backend (don't trust frontend)
                from .services import get_customer_specific_price
                price = get_customer_specific_price(product, customer)
                print(f"[ORDER_CREATION] {product.name}: Base={product.price}, Customer Price={price}, Segment={customer.get_full_name()}")
                
                total_price = quantity * price
                stock_action = item_data.get('stock_action', 'reserve')  # Default to reserve
                
                # Handle stock actions
                stock_result = None
                if stock_action == 'reserve':
                    # Reserve stock for this item
                    from .services import reserve_stock_for_customer
                    stock_result = reserve_stock_for_customer(
                        product=product,
                        quantity=quantity,
                        customer=customer,
                        fulfillment_method='user_confirmed'
                    )
                    
                    if not stock_result.get('success', False):
                        logger.warning(f"Failed to reserve stock for {product.name}: {stock_result.get('message', 'Unknown error')}")
                
                elif stock_action == 'convert_to_kg':
                    # Convert bag/box items to kg equivalent
                    from .services import convert_to_bulk_kg_for_order
                    conversion_result = convert_to_bulk_kg_for_order(
                        product=product,
                        quantity=quantity,
                        customer=customer
                    )
                    
                    if conversion_result.get('success', False):
                        # Use the kg product instead
                        product = conversion_result['kg_product']
                        quantity = conversion_result['kg_quantity']
                        unit = 'kg'
                        # Recalculate customer price for the kg product
                        price = get_customer_specific_price(product, customer)
                        total_price = quantity * price
                        logger.info(f"Converted to bulk kg: {conversion_result['message']}")
                        print(f"[KG_CONVERSION] {product.name}: Customer Price={price}")
                    else:
                        logger.warning(f"Failed to convert to kg: {conversion_result.get('message', 'Unknown error')}")
                
                # stock_action == 'no_reserve' requires no special handling - just create the order item
                
                from orders.models import OrderItem
                order_item = OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=quantity,
                    unit=unit,
                    price=price,
                    total_price=total_price,
                    original_text=item_data.get('original_text', ''),
                    confidence_score=100.0,  # User confirmed selection
                )
                
                created_items.append({
                    'id': order_item.id,
                    'product_name': product.name,
                    'quantity': float(quantity),
                    'unit': unit,
                    'price': float(price),
                    'total_price': float(total_price),
                    'stock_action': stock_action,
                    'stock_result': stock_result
                })
                
                total_amount += total_price
                
            except Product.DoesNotExist:
                logger.warning(f"Product with ID {item_data['product_id']} not found")
                continue
            except Exception as e:
                logger.error(f"Error creating order item: {str(e)}")
                continue
        
        # Update order total
        order.total_amount = total_amount
        order.subtotal = total_amount
        order.save()
        
        # Update message content with confirmed items
        confirmed_items_text = []
        for item in created_items:
            confirmed_items_text.append(f"{item['quantity']} {item['unit']} {item['product_name']}")
        
        # Update message content to show confirmed items
        original_content = message.content
        updated_content = f"CONFIRMED ORDER:\n" + "\n".join(confirmed_items_text) + f"\n\nOriginal message:\n{original_content}"
        
        # Mark message as processed
        message.processed = True
        message.processing_notes = f"✅ Order #{order.order_number} created successfully with {len(created_items)} items for {customer.first_name or customer.email}"
        message.content = updated_content
        message.save()
        
        return Response({
            'status': 'success',
            'message': f'Order created successfully with {len(created_items)} items',
            'order_id': order.id,
            'total_amount': total_amount,
            'items': created_items,
        })
        
    except Exception as e:
        logger.error(f"Failed to create order from suggestions: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return Response({
            'status': 'error',
            'message': 'Failed to create order',
            'details': str(e) if settings.DEBUG else 'Internal server error'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([AllowAny])
def process_stock_message_with_suggestions(request):
    """
    Process a stock message and return suggestions for all items - requires user confirmation
    """
    message_id = request.data.get('message_id')
    
    if not message_id:
        return Response({
            'error': 'message_id is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        message = WhatsAppMessage.objects.get(message_id=message_id)
        
        # Use the new stock suggestions function
        from .services import create_stock_update_from_message_with_suggestions
        result = create_stock_update_from_message_with_suggestions(message)
        
        if result['status'] == 'confirmation_required':
            return Response({
                'status': 'success',
                'message': result['message'],
                'customer': result['customer'],
                'items': result['items'],
                'total_items': result['total_items'],
                'stock_date': result['stock_date'],
                'order_day': result['order_day']
            })
        else:
            return Response({
                'status': 'error',
                'message': result['message'],
                'items': result.get('items', [])
            }, status=status.HTTP_400_BAD_REQUEST)
        
    except WhatsAppMessage.DoesNotExist:
        return Response({
            'error': 'Message not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Failed to process stock message with suggestions: {str(e)}")
        return Response({
            'error': 'Failed to process stock message',
            'details': str(e) if settings.DEBUG else None
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([AllowAny])
def get_stock_update_history(request):
    """
    Get stock update history with WhatsApp message references
    """
    try:
        from .models import StockUpdate
        from inventory.models import StockMovement
        from products.models import Product
        
        # Get recent stock updates with their WhatsApp messages
        stock_updates = StockUpdate.objects.select_related('message').order_by('-created_at')[:10]
        
        history_data = []
        for stock_update in stock_updates:
            message = stock_update.message
            
            # Get stock movements created from this update
            movement_reference = f"SHALLOME-{stock_update.stock_date.strftime('%Y%m%d')}"
            movements = StockMovement.objects.filter(
                reference_number=movement_reference
            ).select_related('product')
            
            # Build product updates list
            product_updates = []
            for movement in movements:
                product_updates.append({
                    'product_id': movement.product.id,
                    'product_name': movement.product.name,
                    'quantity_change': float(movement.quantity),
                    'unit': movement.product.unit,
                    'notes': movement.notes
                })
            
            history_data.append({
                'stock_update_id': stock_update.id,
                'message_id': message.message_id,
                'sender_name': message.sender_name,
                'timestamp': message.timestamp.isoformat(),
                'stock_date': stock_update.stock_date.isoformat(),
                'order_day': stock_update.order_day,
                'processed': stock_update.processed,
                'items_count': len(stock_update.items),
                'product_updates': product_updates,
                'movement_reference': movement_reference
            })
        
        return Response({
            'status': 'success',
            'history': history_data
        })
        
    except Exception as e:
        logger.error(f"Failed to get stock update history: {str(e)}")
        return Response({
            'error': 'Failed to get stock update history',
            'details': str(e) if settings.DEBUG else None
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def compare_stock_with_previous(request):
    """
    Compare current stock levels with the previous stock take to identify discrepancies
    """
    try:
        from .models import StockUpdate
        from inventory.models import FinishedInventory, StockMovement
        from products.models import Product
        from django.db.models import Q
        import logging
        
        logger = logging.getLogger(__name__)
        
        # Get the two most recent processed stock updates
        recent_stock_updates = StockUpdate.objects.filter(processed=True).order_by('-created_at')[:2]
        
        if len(recent_stock_updates) < 2:
            return Response({
                'status': 'error',
                'message': 'Need at least 2 stock takes to compare',
                'comparison_data': []
            })
        
        current_stock_update = recent_stock_updates[0]
        previous_stock_update = recent_stock_updates[1]
        
        # Build comparison data
        comparison_data = []
        all_products = set()
        
        # Get all products from both stock takes
        all_products.update(current_stock_update.items.keys())
        all_products.update(previous_stock_update.items.keys())
        
        for product_name in all_products:
            # Get current stock take data
            current_data = current_stock_update.items.get(product_name, {})
            current_quantity = current_data.get('quantity', 0)
            current_unit = current_data.get('unit', '')
            
            # Get previous stock take data
            previous_data = previous_stock_update.items.get(product_name, {})
            previous_quantity = previous_data.get('quantity', 0)
            previous_unit = previous_data.get('unit', '')
            
            # Calculate difference
            difference = current_quantity - previous_quantity
            
            # Get current inventory level
            try:
                product = Product.objects.filter(name__iexact=product_name).first()
                if product:
                    inventory = FinishedInventory.objects.filter(product=product).first()
                    current_inventory = float(inventory.available_quantity) if inventory else 0.0
                    product_id = product.id
                else:
                    current_inventory = 0.0
                    product_id = None
            except:
                current_inventory = 0.0
                product_id = None
            
            # Determine status
            if difference == 0:
                status = 'unchanged'
                severity = 'normal'
            elif abs(difference) <= 1:
                status = 'minor_change'
                severity = 'low'
            elif abs(difference) <= 5:
                status = 'moderate_change'
                severity = 'medium'
            else:
                status = 'major_change'
                severity = 'high'
            
            # Check if current inventory matches expected
            inventory_matches = abs(current_inventory - current_quantity) <= 0.1
            
            comparison_data.append({
                'product_name': product_name,
                'product_id': product_id,
                'previous_quantity': previous_quantity,
                'current_quantity': current_quantity,
                'difference': difference,
                'unit': current_unit or previous_unit,
                'current_inventory': current_inventory,
                'inventory_matches': inventory_matches,
                'status': status,
                'severity': severity
            })
        
        # Sort by severity and difference
        severity_order = {'high': 0, 'medium': 1, 'low': 2, 'normal': 3}
        comparison_data.sort(key=lambda x: (severity_order[x['severity']], abs(x['difference'])), reverse=True)
        
        # Calculate summary statistics
        total_products = len(comparison_data)
        unchanged = len([x for x in comparison_data if x['status'] == 'unchanged'])
        minor_changes = len([x for x in comparison_data if x['status'] == 'minor_change'])
        moderate_changes = len([x for x in comparison_data if x['status'] == 'moderate_change'])
        major_changes = len([x for x in comparison_data if x['status'] == 'major_change'])
        inventory_mismatches = len([x for x in comparison_data if not x['inventory_matches']])
        
        return Response({
            'status': 'success',
            'current_stock_date': current_stock_update.stock_date.isoformat(),
            'previous_stock_date': previous_stock_update.stock_date.isoformat(),
            'current_order_day': current_stock_update.order_day,
            'previous_order_day': previous_stock_update.order_day,
            'summary': {
                'total_products': total_products,
                'unchanged': unchanged,
                'minor_changes': minor_changes,
                'moderate_changes': moderate_changes,
                'major_changes': major_changes,
                'inventory_mismatches': inventory_mismatches
            },
            'comparison_data': comparison_data
        })
        
    except Exception as e:
        logger.error(f"Failed to compare stock with previous: {str(e)}")
        return Response({
            'error': 'Failed to compare stock with previous',
            'details': str(e) if settings.DEBUG else None
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def create_stock_update_from_suggestions(request):
    """
    Create a stock update from confirmed suggestions and apply to inventory
    """
    message_id = request.data.get('message_id')
    confirmed_items = request.data.get('confirmed_items', [])
    stock_date = request.data.get('stock_date')
    order_day = request.data.get('order_day')
    reset_before_processing = request.data.get('reset_before_processing', True)
    
    if not message_id:
        return Response({
            'error': 'message_id is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    if not confirmed_items:
        return Response({
            'error': 'confirmed_items is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        from .services import create_stock_update_from_confirmed_suggestions
        result = create_stock_update_from_confirmed_suggestions(
            message_id=message_id,
            confirmed_items=confirmed_items,
            stock_date=stock_date,
            order_day=order_day,
            reset_before_processing=reset_before_processing
        )
        
        if result['status'] == 'success':
            return Response({
                'status': 'success',
                'message': result['message'],
                'stock_update_id': result['stock_update_id'],
                'items_processed': result['items_processed'],
                'inventory_result': result['inventory_result']
            })
        else:
            return Response({
                'status': 'error',
                'message': result['message']
            }, status=status.HTTP_400_BAD_REQUEST)
        
    except Exception as e:
        logger.error(f"Failed to create stock update from suggestions: {str(e)}")
        return Response({
            'error': 'Failed to create stock update',
            'details': str(e) if settings.DEBUG else None
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@authentication_classes([FlexibleAuthentication])
@permission_classes([IsAuthenticated])
def analyze_items(request):
    """
    Analyze message content and provide suggestions for improving each item line.
    """
    try:
        content = request.data.get('content', '').strip()
        if not content:
            return Response({'error': 'No content provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        improvements = []
        
        for i, line in enumerate(lines):
            # Skip comment lines (lines starting with #)
            if line.startswith('#'):
                improvements.append({
                    'line_index': i,
                    'original_text': line,
                    'suggestions': [],  # No suggestions for comments
                    'is_comment': True
                })
                continue
                
            line_improvements = analyze_single_item(line)
            improvements.append({
                'line_index': i,
                'original_text': line,
                'suggestions': line_improvements,
                'is_comment': False
            })
        
        return Response({
            'improvements': improvements
        })
        
    except Exception as e:
        logger.error(f"Error analyzing items: {str(e)}")
        return Response({
            'error': 'Failed to analyze items',
            'details': str(e) if settings.DEBUG else None
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def analyze_single_item(line):
    """
    Analyze a single item line and provide parser-friendly improvement suggestions.
    All suggestions are validated against the actual parser before being recommended.
    """
    suggestions = []
    
    # Skip non-product lines
    if not line or len(line.strip()) < 3:
        return suggestions
    
    # Check for common greeting patterns
    greeting_patterns = [
        r'\b(hi|hello|hey|good morning|good afternoon|good evening)\b',
        r'\b(please|thank you|thanks)\b',
        r'\b(order|ordering|need|want)\b'
    ]
    
    is_greeting = any(re.search(pattern, line.lower()) for pattern in greeting_patterns)
    if is_greeting:
        return suggestions  # Skip greeting lines
    
    # Skip lines that appear to be already processed through suggestions
    # Use dynamic pattern detection instead of hardcoded product names
    
    # Pattern 1: Any text with parentheses containing size and optional container
    # Examples: "Potatoes (10kg bag)", "Strawberries (500g)", "Red Onions (3kg)"
    if re.search(r'\([0-9]+(?:\.[0-9]+)?\s*(?:kg|g|ml|l)\s*(?:bag|box|punnet|packet|bunch|head)?\)', line, re.IGNORECASE):
        return suggestions  # Skip - has parentheses with size/container pattern
    
    # Pattern 2: Capitalized product names with size in parentheses
    # Examples: "Sweet Potatoes (5kg)", "Cherry Tomatoes (200g)"
    if re.search(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s*\([0-9]+(?:\.[0-9]+)?\s*(?:kg|g|ml|l)\)', line):
        return suggestions  # Skip - capitalized product with size in parentheses
    
    # Pattern 3: Quantity-first format with proper capitalization
    # Examples: "500.0 g Strawberries", "2.5 kg Sweet Potatoes"
    if re.search(r'^\s*[0-9]+(?:\.[0-9]+)?\s+(?:g|kg|ml|l)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s*$', line):
        return suggestions  # Skip - quantity-first with proper capitalization
    
    # Pattern 5: Product name followed by weight (processed format)
    # Examples: "Butternut 3.0kg", "Carrots 5.5kg", "Tomatoes 2.0kg"
    if re.search(r'^\s*[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+[0-9]+(?:\.[0-9]+)?\s*(?:kg|g|ml|l)\s*$', line):
        return suggestions  # Skip - product with weight (processed format)
    
    # Pattern 4: Check if this looks like a database product name by checking format
    # Examples: "Red Onions", "White Onions", "Green Apples" (proper case, multiple words)
    # Dynamic check: if it has proper capitalization and matches database naming patterns
    if re.search(r'^\s*[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\s*(?:\([^)]*\))?\s*$', line):
        # Additional check: see if this matches any existing product name pattern
        from products.models import Product
        try:
            # Check if there's a product with similar name structure
            line_clean = re.sub(r'\s*\([^)]*\)', '', line).strip()  # Remove parentheses content
            if Product.objects.filter(name__icontains=line_clean.split()[0]).exists():
                return suggestions  # Skip - likely a database product name
        except:
            pass  # If database check fails, continue with analysis
    
    # Test if current line parses correctly
    from whatsapp.services import parse_single_item
    current_parse_result = parse_single_item(line)
    
    # Generate potential improvements
    potential_suggestions = generate_parser_friendly_suggestions(line, current_parse_result)
    
    # Validate each suggestion against the parser
    for suggestion in potential_suggestions:
        improved_text = suggestion.get('improved_text', '')
        suggestion_type = suggestion.get('type', '')
        
        if improved_text and improved_text != line:
            # Test the improved text against the parser
            test_result = parse_single_item(improved_text)
            
            # Always allow formatting suggestions if they parse correctly
            if suggestion_type == 'formatting' and test_result:
                suggestions.append(suggestion)
            elif test_result and is_better_parse_result(current_parse_result, test_result, line, improved_text):
                # Only add non-formatting suggestions that parse correctly and are better
                suggestions.append(suggestion)
    
    return suggestions


def generate_parser_friendly_suggestions(line, current_parse_result):
    """
    Generate potential improvements using parser-friendly formats.
    Includes 10 perfect examples that work 100% of the time.
    """
    suggestions = []
    line_lower = line.lower()
    
    # ADD PERFECT EXAMPLES that work 100% - these are the gold standard formats
    perfect_examples = [
        "5 Potatoes 2kg bag",           # quantity + product + weight + container
        "3 Tomatoes 500g punnet",       # quantity + product + weight + container  
        "1 Spinach 200g packet",        # quantity + product + weight + container
        "2 Carrots 1kg bag",            # quantity + product + weight + container
        "4 Mushrooms 200g punnet",      # quantity + product + weight + container
        "1 Broccoli 500g head",         # quantity + product + weight + unit
        "6 Lemons 2kg box",             # quantity + product + weight + container
        "1 Lettuce 300g head",          # quantity + product + weight + unit
        "3 Onions 5kg bag",             # quantity + product + weight + container  
        "2 Strawberries 250g punnet"    # quantity + product + weight + container
    ]
    
    # If line is very unclear, suggest one of the perfect examples
    if (len(line.strip()) < 5 or 
        not re.search(r'\d', line) or 
        not current_parse_result):
        suggestions.append({
            'suggestion': '💡 Use these perfect formats that work 100%: quantity + product + weight + container',
            'improved_text': '\n'.join([f"✅ {ex}" for ex in perfect_examples]),
            'type': 'perfect_examples',
            'examples': perfect_examples
        })
    
    # 1. MISSING QUANTITY - Use parser-friendly format: "quantity product"
    if not re.search(r'^\s*\d+', line):  # No number at start
        suggestions.append({
            'suggestion': 'Missing quantity - defaulting to 1 item',
            'improved_text': f'1 {line}',
            'type': 'missing_quantity'
        })
    
    # 2. WEIGHT WITHOUT CONTAINER - Use format: "quantity product weight"
    weight_match = re.search(r'(\d+(?:\.\d+)?)\s*(kg|g)\b', line, re.IGNORECASE)
    if weight_match and not re.search(r'\b(box|bag|packet|punnet|bunch|head)\b', line_lower):
        weight_num, weight_unit = weight_match.groups()
        # Ensure no space between weight and unit
        weight = f'{weight_num}{weight_unit}'
        product_name = re.sub(r'\d+(?:\.\d+)?\s*(kg|g)\b', '', line, flags=re.IGNORECASE).strip()
        
        # Try different container formats that parse well
        container_options = ['box', 'bag', 'packet', 'punnet']
        for container in container_options:
            if should_use_container(product_name, container):
                improved_text = f'{product_name} {weight} {container}'
                suggestions.append({
                    'suggestion': f'Weight without container - consider specifying {container}',
                    'improved_text': improved_text,
                    'type': 'missing_container'
                })
                break
    
    # 3. CONTAINER WITHOUT WEIGHT - Use format: "quantity product weight container"
    container_match = re.search(r'\b(box|bag|packet|punnet|bunch|head)\b', line_lower)
    if container_match and not re.search(r'\d+(?:\.\d+)?(kg|g|ml|l)\b', line):
        container = container_match.group(1)
        suggested_weight = get_standard_weight_for_container(line, container)
        if suggested_weight and container not in ['bunch', 'head']:  # Skip bunches and heads
            # Remove existing container and add weight + container
            product_base = re.sub(r'\b(box|bag|packet|punnet|bunch|head)\b', '', line, flags=re.IGNORECASE).strip()
            # Clean up any extra spaces and fix weight formatting
            product_base = re.sub(r'\s+', ' ', product_base).strip()
            # Fix any spaced weights in the product base
            product_base = re.sub(r'(\d+)\s+(kg|g|ml|l)\b', r'\1\2', product_base, flags=re.IGNORECASE)
            improved_text = f'{product_base} {suggested_weight} {container}'
            suggestions.append({
                'suggestion': f'Container without weight - consider specifying {suggested_weight}',
                'improved_text': improved_text,
                'type': 'missing_weight'
            })
    
    # 4. REORDER FOR BETTER PARSING - Use format: "quantity product weight[container]"
    if re.search(r'\d+\s*(box|bag|packet|punnet)\s*\d+(kg|g)', line, re.IGNORECASE):
        # Pattern like "1 box 3kg green pepper" -> "1 green pepper 3kg box"
        match = re.search(r'(\d+)\s*(box|bag|packet|punnet)\s*(\d+(?:\.\d+)?)\s*(kg|g)\s*(.+)', line, re.IGNORECASE)
        if match:
            quantity, container, weight_num, weight_unit, product = match.groups()
            # Ensure no space between weight and unit
            improved_text = f'{quantity} {product.strip()} {weight_num}{weight_unit} {container}'
            suggestions.append({
                'suggestion': 'Reorder for better parsing - put product name first',
                'improved_text': improved_text,
                'type': 'reorder_parsing'
            })
    
    # 5. FORMATTING FIXES - Always suggest removing spaces from weight units
    formatting_issues = []
    cleaned_line = line
    
    # Multiple spaces
    if '  ' in line:
        formatting_issues.append('multiple spaces')
        cleaned_line = re.sub(r'\s+', ' ', cleaned_line)
    
    # Stray characters
    if re.search(r'\s+[xX*]\s*$', line) or re.search(r'^\s*[xX*]\s+', line):
        formatting_issues.append('stray characters (x, *)')
        cleaned_line = re.sub(r'\s+[xX*]\s*$', '', cleaned_line)
        cleaned_line = re.sub(r'^\s*[xX*]\s+', '', cleaned_line)
        cleaned_line = cleaned_line.replace('*', ' ')
    
    # Fix spaces in weight units (e.g., "100 g" -> "100g", "5 kg" -> "5kg")
    # This is ALWAYS a formatting issue that should be fixed
    if re.search(r'\d+\s+(kg|g|ml|l)\b', line, re.IGNORECASE):
        formatting_issues.append('spaces in weight units (should be 100g not 100 g)')
        cleaned_line = re.sub(r'(\d+)\s+(kg|g|ml|l)\b', r'\1\2', cleaned_line, flags=re.IGNORECASE)
    
    # Missing spaces around numbers (but not for weight units)
    if re.search(r'[a-zA-Z]\d|\d[a-zA-Z]', line) and not re.search(r'\d+(kg|g|ml|l)', line, re.IGNORECASE):
        formatting_issues.append('missing spaces around numbers')
        cleaned_line = re.sub(r'([a-zA-Z])(\d)', r'\1 \2', cleaned_line)
        cleaned_line = re.sub(r'(\d)([a-zA-Z])', r'\1 \2', cleaned_line)
        # Re-fix weight units that might have been affected
        cleaned_line = re.sub(r'(\d+)\s+(kg|g|ml|l)\b', r'\1\2', cleaned_line, flags=re.IGNORECASE)
    
    if formatting_issues:
        cleaned_line = re.sub(r'\s+', ' ', cleaned_line).strip()
        suggestions.append({
            'suggestion': f'Formatting issues: {", ".join(formatting_issues)}',
            'improved_text': cleaned_line,
            'type': 'formatting'
        })
    
    return suggestions


def is_better_parse_result(current_result, new_result, original_line, improved_line):
    """
    Determine if the new parse result is better than the current one.
    """
    # If current doesn't parse but new does, new is better
    if not current_result and new_result:
        return True
    
    # If current parses but new doesn't, new is worse
    if current_result and not new_result:
        return False
    
    # If neither parse, no improvement
    if not current_result and not new_result:
        return False
    
    # Both parse - check quality
    current_product = current_result.get('product_name', '').lower()
    new_product = new_result.get('product_name', '').lower()
    
    # Avoid truncated product names like "1 Bo", "200 G"
    if (len(new_product) < 3 or 
        new_product in ['1 bo', '2 bo', '3 bo'] or
        re.match(r'^\d+\s*[a-z]$', new_product)):
        return False
    
    # Check for obvious parsing failures in current result
    current_is_bad = (
        len(current_product) < 3 or
        current_product in ['1 bo', '2 bo', '3 bo'] or
        re.match(r'^\d+\s*[a-z]$', current_product) or  # Like "200 g"
        current_product.startswith('1 bo') or
        current_product.startswith('2 bo') or
        current_product.startswith('3 bo')
    )
    
    # If current result is already good, be very conservative
    if not current_is_bad:
        # Check if the current result already looks like a proper product name
        # If it contains actual product words and reasonable structure, don't suggest changes
        original_words = set(original_line.lower().split())
        product_words = set(current_product.split())
        
        # If current product name contains most of the meaningful words from original, it's probably good
        meaningful_words = [w for w in original_words if len(w) > 2 and w not in ['box', 'bag', 'packet', 'punnet', 'kg', 'g']]
        current_meaningful_overlap = len([w for w in meaningful_words if any(pw in w or w in pw for pw in product_words)])
        
        # If current result captures most meaningful words, don't suggest changes
        if meaningful_words and current_meaningful_overlap >= len(meaningful_words) * 0.7:
            return False
        
        # Check if product name makes more sense
        current_word_overlap = len([word for word in current_product.split() if word in original_words])
        new_word_overlap = len([word for word in new_product.split() if word in original_words])
        
        # Only suggest if significantly better
        if new_word_overlap > current_word_overlap + 1:
            return True
        
        # Prefer results with proper package sizes
        current_has_package = bool(current_result.get('package_size'))
        new_has_package = bool(new_result.get('package_size'))
        
        if new_has_package and not current_has_package and new_word_overlap >= current_word_overlap:
            return True
    
    # If current is bad and new is good, suggest the improvement
    if current_is_bad and len(new_product) > 3:
        return True
    
    return False


def should_use_container(product_name, container):
    """
    Determine if a container type is appropriate for a product.
    """
    product_lower = product_name.lower()
    
    container_mappings = {
        'punnet': ['strawberries', 'cherry tomatoes', 'mushrooms', 'berries'],
        'packet': ['herbs', 'mint', 'parsley', 'coriander', 'spinach', 'dill'],
        'box': ['tomatoes', 'potatoes', 'onions', 'carrots', 'peppers', 'cucumber', 'lettuce', 'avocados', 'lemons'],
        'bag': ['potatoes', 'onions', 'carrots']
    }
    
    suitable_products = container_mappings.get(container, [])
    return any(product in product_lower for product in suitable_products)


def get_standard_weight_for_container(line, container):
    """
    Get standard weight for a container type based on the product.
    Returns weight without spaces (e.g., '5kg' not '5 kg').
    """
    line_lower = line.lower()
    
    weight_mappings = {
        'punnet': '200g',
        'packet': '100g',
        'box': '5kg',
        'bag': '10kg',
        'bunch': None,  # Bunches don't need weights
        'head': None    # Heads don't need weights
    }
    
    # Special cases based on product
    if 'strawberries' in line_lower or 'mushrooms' in line_lower:
        return '200g'
    elif 'herbs' in line_lower or 'mint' in line_lower or 'parsley' in line_lower or 'dill' in line_lower:
        return '100g'
    elif 'potatoes' in line_lower or 'onions' in line_lower:
        return '10kg'
    elif 'tomatoes' in line_lower or 'peppers' in line_lower or 'carrots' in line_lower or 'butternut' in line_lower or 'pineapple' in line_lower:
        return '5kg'
    elif 'cucumber' in line_lower:
        return '5kg'  # Updated from your list
    elif 'spinach' in line_lower:
        return '5kg'  # For packet spinach
    
    return weight_mappings.get(container)


def suggest_weight_for_container_product(line):
    """
    Suggest appropriate weight for products with containers but no weight specified.
    """
    line_lower = line.lower()
    
    # Common weight suggestions based on product and container type
    weight_suggestions = {
        # Punnet products
        ('strawberries', 'punnet'): '200g',
        ('cherry tomatoes', 'punnet'): '200g',
        ('mushrooms', 'punnet'): '200g',
        ('berries', 'punnet'): '200g',
        
        # Box products
        ('tomatoes', 'box'): '5kg',
        ('potatoes', 'box'): '10kg',
        ('onions', 'box'): '10kg',
        ('carrots', 'box'): '10kg',
        ('peppers', 'box'): '5kg',
        ('cucumber', 'box'): '5kg',
        ('lettuce', 'box'): '2kg',
        
        # Bag products
        ('potatoes', 'bag'): '10kg',
        ('onions', 'bag'): '10kg',
        ('carrots', 'bag'): '5kg',
        
        # Packet products
        ('herbs', 'packet'): '100g',
        ('spinach', 'packet'): '200g',
        ('mint', 'packet'): '100g',
        ('parsley', 'packet'): '100g',
    }
    
    # Try to match product and container
    for (product, container), weight in weight_suggestions.items():
        if product in line_lower and container in line_lower:
            return weight
    
    # Default suggestions based on container type
    if 'punnet' in line_lower:
        return '200g'
    elif 'box' in line_lower:
        return '5kg'
    elif 'bag' in line_lower:
        return '5kg'
    elif 'packet' in line_lower:
        return '100g'
    
    return None


def suggest_container_for_product(line):
    """
    Suggest appropriate container for products with weight but no container.
    """
    line_lower = line.lower()
    
    # Container suggestions based on product type and weight
    if any(product in line_lower for product in ['strawberries', 'cherry tomatoes', 'mushrooms', 'berries']):
        return 'punnet'
    elif any(product in line_lower for product in ['herbs', 'mint', 'parsley', 'coriander', 'spinach']):
        return 'packet'
    elif any(product in line_lower for product in ['tomatoes', 'potatoes', 'onions', 'carrots', 'peppers']):
        # Check weight to determine container
        if re.search(r'[1-9]\d*kg', line_lower):  # Multi-kg suggests box
            return 'box'
        else:
            return 'bag'
    
    # Default based on weight
    if re.search(r'[5-9]\d*kg|[1-9]\d+kg', line_lower):  # 5kg+ suggests box
        return 'box'
    elif re.search(r'\d+g', line_lower):  # Grams suggest packet or punnet
        return 'packet'
    
    return 'box'  # Default


def suggest_specific_packaging(line):
    """
    Suggest specific packaging to replace ambiguous terms.
    """
    line_lower = line.lower()
    
    # Replace ambiguous terms with specific suggestions
    replacements = {
        r'\bsmall\s+box\b': '2kg box',
        r'\blarge\s+box\b': '10kg box',
        r'\bbig\s+box\b': '15kg box',
        r'\bsmall\s+bag\b': '2kg bag',
        r'\blarge\s+bag\b': '10kg bag',
        r'\bsmall\s+packet\b': '100g packet',
        r'\blarge\s+packet\b': '500g packet',
        r'\bsmall\s+punnet\b': '200g punnet',
        r'\blarge\s+punnet\b': '500g punnet',
    }
    
    improved_text = line
    for pattern, replacement in replacements.items():
        improved_text = re.sub(pattern, replacement, improved_text, flags=re.IGNORECASE)
    
    # If no specific replacement, add default weights
    if improved_text == line:
        if 'box' in line_lower and not re.search(r'\d+kg', line_lower):
            improved_text = re.sub(r'\bbox\b', '5kg box', line, flags=re.IGNORECASE)
        elif 'bag' in line_lower and not re.search(r'\d+kg', line_lower):
            improved_text = re.sub(r'\bbag\b', '5kg bag', line, flags=re.IGNORECASE)
        elif 'packet' in line_lower and not re.search(r'\d+g', line_lower):
            improved_text = re.sub(r'\bpacket\b', '200g packet', line, flags=re.IGNORECASE)
        elif 'punnet' in line_lower and not re.search(r'\d+g', line_lower):
            improved_text = re.sub(r'\bpunnet\b', '200g punnet', line, flags=re.IGNORECASE)
    
    return improved_text if improved_text != line else None


def get_product_specific_suggestions(line):
    """
    Get product-specific packaging and quantity suggestions.
    """
    suggestions = []
    line_lower = line.lower()
    
    # Specific product recommendations
    product_recommendations = {
        'strawberries': {
            'container': 'punnet',
            'weight': '200g',
            'example': 'Strawberries 5 punnet 200g'
        },
        'cherry tomatoes': {
            'container': 'punnet',
            'weight': '200g',
            'example': 'Cherry tomatoes 10 punnet 200g'
        },
        'mushrooms': {
            'container': 'punnet',
            'weight': '200g',
            'example': 'Mushrooms 3 punnet 200g'
        },
        'herbs': {
            'container': 'packet',
            'weight': '100g',
            'example': 'Fresh herbs 2 packet 100g'
        },
        'spinach': {
            'container': 'bunch',
            'weight': None,
            'example': 'Spinach 5 bunch'
        }
    }
    
    for product, recommendation in product_recommendations.items():
        if product in line_lower:
            # Check if the line is missing the recommended packaging
            has_recommended_container = recommendation['container'] in line_lower
            has_recommended_weight = recommendation['weight'] and recommendation['weight'] in line_lower
            
            if not has_recommended_container or (recommendation['weight'] and not has_recommended_weight):
                suggestions.append({
                    'suggestion': f'Consider standard {product} packaging',
                    'improved_text': recommendation['example'],
                    'type': 'product_specific'
                })
                break
    
    return suggestions


def suggest_unit_for_product(line):
    """
    Suggest appropriate unit based on product type.
    """
    line_lower = line.lower()
    
    # Weight-based products (usually sold by kg)
    weight_products = [
        'tomato', 'potato', 'onion', 'carrot', 'cabbage', 'lettuce',
        'spinach', 'broccoli', 'cauliflower', 'pepper', 'cucumber'
    ]
    
    # Count-based products (usually sold by piece/each)
    count_products = [
        'pineapple', 'melon', 'watermelon', 'avocado', 'mango'
    ]
    
    # Bunch-based products
    bunch_products = [
        'spinach', 'parsley', 'coriander', 'mint', 'basil'
    ]
    
    # Check product type and suggest unit
    for product in weight_products:
        if product in line_lower:
            return 'kg'
    
    for product in count_products:
        if product in line_lower:
            return 'each'
    
    for product in bunch_products:
        if product in line_lower:
            return 'bunch'
    
    # Default suggestion
    return 'kg'


def clean_line_formatting(line):
    """
    Clean up common formatting issues in a line.
    """
    # Remove stray x/X/* at end or beginning
    cleaned = re.sub(r'\s+[xX*]\s*$', '', line)
    cleaned = re.sub(r'^\s*[xX*]\s+', '', cleaned)
    
    # Replace asterisks with spaces
    cleaned = cleaned.replace('*', ' ')
    
    # Add spaces around numbers where missing
    cleaned = re.sub(r'([a-zA-Z])(\d)', r'\1 \2', cleaned)
    cleaned = re.sub(r'(\d)([a-zA-Z])', r'\1 \2', cleaned)
    
    # Normalize multiple spaces
    cleaned = re.sub(r'\s+', ' ', cleaned)
    
    return cleaned.strip()


@api_view(['POST'])
@authentication_classes([FlexibleAuthentication])
@permission_classes([IsAuthenticated])
def apply_quick_fix(request):
    """
    Apply quick fixes to message content including Remove Numbering.
    """
    try:
        content = request.data.get('content', '').strip()
        fix_type = request.data.get('fix_type', '').strip()
        
        if not content:
            return Response({'error': 'No content provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        if not fix_type:
            return Response({'error': 'No fix type specified'}, status=status.HTTP_400_BAD_REQUEST)
        
        fixed_content = content
        
        if fix_type == 'remove_numbering':
            fixed_content = clean_numbering_from_text(content)
        elif fix_type == 'remove_timestamps':
            fixed_content = clean_timestamp_from_text(content)
        elif fix_type == 'clean_spacing':
            # Clean spacing: remove extra spaces, normalize whitespace
            fixed_content = re.sub(r'\s+', ' ', content.strip())
            # Clean line by line
            lines = fixed_content.split('\n')
            cleaned_lines = [clean_line_formatting(line) for line in lines if line.strip()]
            fixed_content = '\n'.join(cleaned_lines)
        elif fix_type == 'remove_greetings':
            # Remove greeting lines
            lines = content.split('\n')
            cleaned_lines = []
            for line in lines:
                line = line.strip()
                if line and not _is_greeting_line(line):
                    cleaned_lines.append(line)
            fixed_content = '\n'.join(cleaned_lines)
        elif fix_type == 'remove_emojis':
            # Remove emojis and special characters
            fixed_content = re.sub(r'[^\w\s\d\.\(\)\-\+\×\*\/\,\:\;]', '', content)
            fixed_content = re.sub(r'\s+', ' ', fixed_content).strip()
        elif fix_type == 'items_only':
            # Keep only lines that look like items (have numbers/quantities)
            lines = content.split('\n')
            item_lines = []
            for line in lines:
                line = line.strip()
                if line and _looks_like_item_line(line):
                    item_lines.append(line)
            fixed_content = '\n'.join(item_lines)
        else:
            return Response({'error': f'Unknown fix type: {fix_type}'}, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({
            'fixed_content': fixed_content,
            'original_content': content,
            'fix_applied': fix_type
        })
        
    except Exception as e:
        logger.error(f"Error applying quick fix: {str(e)}")
        return Response({
            'error': 'Failed to apply quick fix',
            'details': str(e) if settings.DEBUG else None
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def _is_greeting_line(line):
    """Check if a line is a greeting or polite expression"""
    line_upper = line.upper()
    greeting_patterns = [
        r'\b(GOOD MORNING|MORNING|HELLO|HI|HALLO|GREETINGS)\b',
        r'\b(THANKS?|THANK YOU|PLEASE|PLZ|PLIZ)\b', 
        r'\b(THAT\'?S ALL|THATS ALL|TNX|CHEERS)\b',
        r'\b(HERE IS MY ORDER|MY ORDER|ORDER FOR)\b',
        r'\b(MAY I PLEASE|CAN I|COULD I)\b'
    ]
    
    for pattern in greeting_patterns:
        if re.search(pattern, line_upper):
            return True
    return False


def _looks_like_item_line(line):
    """Check if a line looks like a product item (has quantities/numbers)"""
    # Must have at least a number and some text
    if not re.search(r'\d', line):
        return False
    
    # Skip if it's just a greeting with numbers
    if _is_greeting_line(line):
        return False
    
    # Must have some alphabetic characters (product name)
    if not re.search(r'[a-zA-Z]', line):
        return False
    
    return True

