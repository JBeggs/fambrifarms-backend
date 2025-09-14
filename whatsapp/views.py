from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils import timezone
from datetime import datetime, timedelta
import traceback

from .models import WhatsAppMessage, StockUpdate, OrderDayDemarcation, MessageProcessingLog
from .serializers import (
    WhatsAppMessageSerializer, StockUpdateSerializer, MessageBatchSerializer,
    ProcessMessagesSerializer, EditMessageSerializer, OrderCreationResultSerializer,
    StockValidationSerializer
)
from .services import (
    classify_message_type, create_order_from_message, process_stock_updates,
    validate_order_against_stock, log_processing_action, has_order_items
)
from accounts.models import RestaurantProfile

@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """Health check endpoint for the WhatsApp integration service"""
    return Response({
        'status': 'healthy',
        'service': 'django-whatsapp-integration',
        'timestamp': timezone.now().isoformat(),
        'version': '1.0.0'
    })

@api_view(['GET'])
@permission_classes([AllowAny])
def get_companies(request):
    """Get list of valid companies from RestaurantProfile"""
    try:
        # Get all restaurant profiles, ordered by business name
        profiles = RestaurantProfile.objects.select_related('user').order_by('business_name')
        
        companies = []
        for profile in profiles:
            company_data = {
                'id': profile.id,
                'name': profile.business_name,
                'branch_name': profile.branch_name,
                'display_name': str(profile),  # Uses __str__ method
                'email': profile.user.email,
                'phone': profile.user.phone,
                'address': profile.address,
                'city': profile.city,
                'payment_terms': profile.payment_terms,
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
@permission_classes([AllowAny])
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
                
                # Classification diagnostics (pre-save)
                content = msg_data.get('content', '')
                content_upper = content.upper()
                msg_id = msg_data.get('id', '')
                sender = msg_data.get('sender', '')
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
                
                # CRITICAL FIX: Trigger company extraction immediately after creation/update
                # This ensures context-based assignments set manual_company right away
                if message.message_type == 'order':
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
                errors.append({
                    'message_id': msg_data.get('id', 'unknown'),
                    'error': str(e),
                    'traceback': traceback.format_exc()
                })
    
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

@api_view(['GET'])
@permission_classes([AllowAny])
def get_messages(request):
    """Get WhatsApp messages for the Flutter app"""
    
    # Filter parameters
    message_type = request.GET.get('type')
    processed = request.GET.get('processed')
    order_day = request.GET.get('order_day')
    limit = int(request.GET.get('limit', 100))
    
    queryset = WhatsAppMessage.objects.filter(is_deleted=False)
    
    if message_type:
        queryset = queryset.filter(message_type=message_type)
    
    if processed is not None:
        queryset = queryset.filter(processed=processed.lower() == 'true')
    
    if order_day:
        queryset = queryset.filter(order_day=order_day)
    
    # Get recent messages
    messages = queryset.order_by('-timestamp')[:limit]
    
    serializer = WhatsAppMessageSerializer(messages, many=True)
    return Response({
        'messages': serializer.data,
        'total_count': queryset.count(),
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
    
    try:
        message = WhatsAppMessage.objects.get(message_id=message_id)
        
        # Store original content if not already edited
        if not message.edited:
            message.original_content = message.content
        
        # Clean the edited content by removing company names to avoid confusion
        from .message_parser import django_message_parser
        cleaned_content = django_message_parser.clean_message_content(edited_content)
        
        message.content = cleaned_content
        message.edited = True
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
            {'error': 'Message not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {'error': str(e)}, 
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
            {'error': f'Message with ID {message_id} not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {'error': str(e)}, 
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
    
    with transaction.atomic():
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
                
                # Create order from message
                order = create_order_from_message(message)
                
                if order:
                    orders_created.append(order)
                    message.processed = True
                    message.order = order
                    message.save()
                    
                    log_processing_action(message, 'order_created', {
                        'order_number': order.order_number,
                        'items_count': order.items.count()
                    })
                else:
                    errors.append({
                        'message_id': message.message_id,
                        'error': 'Failed to create order - no valid items found'
                    })
                    
            except Exception as e:
                errors.append({
                    'message_id': message.message_id,
                    'error': str(e),
                    'traceback': traceback.format_exc()
                })
                
                log_processing_action(message, 'error', {
                    'error': str(e),
                    'action': 'order_creation'
                })
    
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

@api_view(['GET'])
@permission_classes([AllowAny])
def get_stock_updates(request):
    """Get stock updates from SHALLOME"""
    
    order_day = request.GET.get('order_day')
    processed = request.GET.get('processed')
    limit = int(request.GET.get('limit', 10))
    
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
    limit = int(request.GET.get('limit', 50))
    
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
            log_processing_action(message, 'manual_company_preserved_after_deletion', {
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
                    log_processing_action(message, 'context_company_changed_after_deletion', {
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

