"""
Integration tests for WhatsApp API endpoints
Tests the complete WhatsApp message processing workflow through API endpoints
"""

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
import json

from whatsapp.models import WhatsAppMessage, StockUpdate, MessageProcessingLog
from orders.models import Order, OrderItem
from products.models import Product, Department
from accounts.models import RestaurantProfile, User
from inventory.models import FinishedInventory

User = get_user_model()


class WhatsAppAPIEndpointsTest(TestCase):
    """Test WhatsApp API endpoints integration"""
    
    def setUp(self):
        self.client = APIClient()
        
        # Create test user for authentication
        self.admin_user = User.objects.create_user(
            email='admin@fambrifarms.com',
            password='testpass123',
            user_type='admin',
            is_staff=True
        )
        
        # Create test customer
        self.customer = User.objects.create_user(
            email='sylvia@customer.com',
            password='testpass123',
            first_name='Sylvia',
            last_name='Customer',
            user_type='restaurant'
        )
        
        RestaurantProfile.objects.create(
            user=self.customer,
            business_name='Sylvia Restaurant',
            address='123 Restaurant St',
            city='Food City',
            postal_code='12345'
        )
        
        # Create test products
        self.department = Department.objects.create(name='Vegetables')
        
        self.lettuce = Product.objects.create(
            name='Lettuce',
            department=self.department,
            price=Decimal('25.00'),
            unit='kg'
        )
        
        self.tomatoes = Product.objects.create(
            name='Tomatoes',
            department=self.department,
            price=Decimal('30.00'),
            unit='kg'
        )
        
        # Create inventory
        FinishedInventory.objects.get_or_create(
            product=self.lettuce,
            defaults={
                'available_quantity': Decimal('100.00'),
                'reserved_quantity': Decimal('0.00')
            }
        )
        
        FinishedInventory.objects.get_or_create(
            product=self.tomatoes,
            defaults={
                'available_quantity': Decimal('80.00'),
                'reserved_quantity': Decimal('0.00')
            }
        )
        
        # API URLs
        self.health_check_url = reverse('whatsapp-health')
        self.receive_messages_url = reverse('receive-messages')
        self.get_messages_url = reverse('get-messages')
        self.process_messages_url = reverse('process-messages')
        self.get_companies_url = reverse('get-companies')
        
        # Authenticate client
        self.client.force_authenticate(user=self.admin_user)
    
    def test_health_check_endpoint(self):
        """Test WhatsApp health check endpoint"""
        response = self.client.get(self.health_check_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'healthy')
        self.assertEqual(response.data['service'], 'django-whatsapp-integration')
        self.assertIn('timestamp', response.data)
        self.assertEqual(response.data['version'], '1.0.0')
    
    def test_health_check_unauthenticated(self):
        """Test health check without authentication"""
        self.client.force_authenticate(user=None)
        response = self.client.get(self.health_check_url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_receive_messages_endpoint(self):
        """Test receiving WhatsApp messages through API"""
        message_data = {
            'messages': [
                {
                    'id': 'msg_001',
                    'chat_name': 'ORDERS Restaurants',
                    'sender': '+27 73 621 2471',
                    'sender_name': 'Sylvia',
                    'content': '30kg lettuce\n20kg tomatoes',
                    'timestamp': timezone.now().isoformat(),
                    'media_type': '',
                    'media_url': ''
                },
                {
                    'id': 'msg_002',
                    'chat_name': 'ORDERS Restaurants',
                    'sender': '+27 61 674 9368',
                    'sender_name': 'SHALLOME',
                    'content': 'STOCK AS AT 25/09/2025\n1. Lettuce - 100kg\n2. Tomatoes - 80kg',
                    'timestamp': timezone.now().isoformat(),
                    'media_type': '',
                    'media_url': ''
                }
            ]
        }
        
        # Remove authentication requirement for this endpoint
        self.client.force_authenticate(user=None)
        response = self.client.post(
            self.receive_messages_url, 
            message_data, 
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('received', response.data)
        self.assertIn('processed', response.data)
        self.assertEqual(response.data['received'], 2)
        
        # Verify messages were created
        messages = WhatsAppMessage.objects.filter(
            message_id__in=['msg_001', 'msg_002']
        )
        self.assertEqual(messages.count(), 2)
        
        # Check message classification
        order_message = messages.get(message_id='msg_001')
        stock_message = messages.get(message_id='msg_002')
        
        self.assertEqual(order_message.message_type, 'order')
        self.assertEqual(stock_message.message_type, 'stock')
    
    def test_receive_messages_invalid_data(self):
        """Test receiving messages with invalid data"""
        invalid_data = {
            'messages': [
                {
                    'id': 'invalid_msg',
                    # Missing required fields
                }
            ]
        }
        
        self.client.force_authenticate(user=None)
        response = self.client.post(
            self.receive_messages_url,
            invalid_data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_get_messages_endpoint(self):
        """Test retrieving WhatsApp messages"""
        # Create test messages
        WhatsAppMessage.objects.create(
            message_id='test_msg_1',
            chat_name='ORDERS Restaurants',
            sender_name='Sylvia',
            sender_phone='+27 73 621 2471',
            content='30kg lettuce',
            timestamp=timezone.now(),
            message_type='order'
        )
        
        WhatsAppMessage.objects.create(
            message_id='test_msg_2',
            chat_name='ORDERS Restaurants',
            sender_name='SHALLOME',
            sender_phone='+27 61 674 9368',
            content='STOCK AS AT 25/09/2025\n1. Lettuce - 100kg',
            timestamp=timezone.now(),
            message_type='stock'
        )
        
        response = self.client.get(self.get_messages_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('messages', response.data)
        self.assertEqual(len(response.data['messages']), 2)
        
        # Check message data structure
        message = response.data['messages'][0]
        self.assertIn('message_id', message)
        self.assertIn('sender_name', message)
        self.assertIn('content', message)
        self.assertIn('message_type', message)
    
    def test_get_messages_with_filters(self):
        """Test retrieving messages with filters"""
        # Create messages of different types
        WhatsAppMessage.objects.create(
            message_id='order_msg',
            chat_name='ORDERS Restaurants',
            sender_name='Sylvia',
            content='30kg lettuce',
            timestamp=timezone.now(),
            message_type='order'
        )
        
        WhatsAppMessage.objects.create(
            message_id='stock_msg',
            chat_name='ORDERS Restaurants',
            sender_name='SHALLOME',
            content='STOCK AS AT 25/09/2025',
            timestamp=timezone.now(),
            message_type='stock'
        )
        
        # Filter by message type
        response = self.client.get(self.get_messages_url, {'message_type': 'order'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['messages']), 1)
        self.assertEqual(response.data['messages'][0]['message_type'], 'order')
    
    def test_process_messages_to_orders_endpoint(self):
        """Test processing messages to orders through API"""
        # Create test order message
        message = WhatsAppMessage.objects.create(
            message_id='process_msg_1',
            chat_name='ORDERS Restaurants',
            sender_name='Sylvia',
            sender_phone='+27 73 621 2471',
            content='30kg lettuce\n20kg tomatoes',
            timestamp=timezone.now(),
            message_type='order',
            manual_company='Sylvia Restaurant'
        )
        
        process_data = {
            'message_ids': ['process_msg_1']
        }
        
        self.client.force_authenticate(user=None)  # Remove auth for this endpoint
        response = self.client.post(
            self.process_messages_url,
            process_data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('orders_created', response.data)
        self.assertIn('errors', response.data)
        self.assertEqual(len(response.data['orders_created']), 1)
        
        # Verify order was created
        order = Order.objects.filter(restaurant=self.customer).first()
        self.assertIsNotNone(order)
        self.assertEqual(order.status, 'parsed')
        self.assertTrue(order.parsed_by_ai)
        
        # Verify order items
        items = order.items.all()
        self.assertEqual(items.count(), 2)
        
        # Verify message was marked as processed
        message.refresh_from_db()
        self.assertTrue(message.processed)
        self.assertEqual(message.order, order)
    
    def test_process_messages_already_processed(self):
        """Test processing already processed messages"""
        # Create processed message
        message = WhatsAppMessage.objects.create(
            message_id='processed_msg',
            chat_name='ORDERS Restaurants',
            sender_name='Sylvia',
            content='30kg lettuce',
            timestamp=timezone.now(),
            message_type='order',
            processed=True  # Already processed
        )
        
        process_data = {
            'message_ids': ['processed_msg']
        }
        
        self.client.force_authenticate(user=None)
        response = self.client.post(
            self.process_messages_url,
            process_data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['orders_created']), 0)
        self.assertEqual(len(response.data['warnings']), 1)
        self.assertIn('already processed', response.data['warnings'][0]['warning'])
    
    def test_get_companies_endpoint(self):
        """Test retrieving companies list"""
        response = self.client.get(self.get_companies_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('companies', response.data)
        
        # Should include the test restaurant profile
        companies = response.data['companies']
        company_names = [company['name'] for company in companies]
        self.assertIn('Sylvia Restaurant', company_names)
    
    def test_edit_message_endpoint(self):
        """Test editing message content"""
        message = WhatsAppMessage.objects.create(
            message_id='edit_msg_1',
            chat_name='ORDERS Restaurants',
            sender_name='Sylvia',
            content='Original content',
            timestamp=timezone.now(),
            message_type='order'
        )
        
        edit_data = {
            'message_id': 'edit_msg_1',
            'new_content': 'Edited content with 30kg lettuce'
        }
        
        edit_url = reverse('edit-message')
        self.client.force_authenticate(user=None)
        response = self.client.post(edit_url, edit_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
        
        # Verify message was updated
        message.refresh_from_db()
        self.assertEqual(message.content, 'Edited content with 30kg lettuce')
        self.assertTrue(message.edited)
        self.assertEqual(message.original_content, 'Original content')
    
    def test_update_message_company_endpoint(self):
        """Test updating message company assignment"""
        message = WhatsAppMessage.objects.create(
            message_id='company_msg_1',
            chat_name='ORDERS Restaurants',
            sender_name='Unknown',
            content='30kg lettuce',
            timestamp=timezone.now(),
            message_type='order'
        )
        
        update_data = {
            'message_id': 'company_msg_1',
            'company_name': 'Sylvia Restaurant'
        }
        
        update_url = reverse('update-message-company')
        self.client.force_authenticate(user=None)
        response = self.client.post(update_url, update_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify company was assigned
        message.refresh_from_db()
        self.assertEqual(message.manual_company, 'Sylvia Restaurant')
    
    def test_update_message_type_endpoint(self):
        """Test updating message type"""
        message = WhatsAppMessage.objects.create(
            message_id='type_msg_1',
            chat_name='ORDERS Restaurants',
            sender_name='Sylvia',
            content='Some ambiguous content',
            timestamp=timezone.now(),
            message_type='other'
        )
        
        update_data = {
            'message_id': 'type_msg_1',
            'message_type': 'order'
        }
        
        update_url = reverse('update-message-type')
        self.client.force_authenticate(user=None)
        response = self.client.post(update_url, update_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify message type was updated
        message.refresh_from_db()
        self.assertEqual(message.message_type, 'order')
    
    def test_delete_message_endpoint(self):
        """Test deleting a message"""
        message = WhatsAppMessage.objects.create(
            message_id='delete_msg_1',
            chat_name='ORDERS Restaurants',
            sender_name='Sylvia',
            content='Message to delete',
            timestamp=timezone.now(),
            message_type='other'
        )
        
        delete_url = reverse('delete-message', kwargs={'message_id': message.id})
        self.client.force_authenticate(user=None)
        response = self.client.delete(delete_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify message was soft deleted
        message.refresh_from_db()
        self.assertTrue(message.is_deleted)
    
    def test_bulk_delete_messages_endpoint(self):
        """Test bulk deleting messages"""
        # Create multiple messages
        msg1 = WhatsAppMessage.objects.create(
            message_id='bulk_msg_1',
            chat_name='ORDERS Restaurants',
            sender_name='Sylvia',
            content='Message 1',
            timestamp=timezone.now(),
            message_type='other'
        )
        
        msg2 = WhatsAppMessage.objects.create(
            message_id='bulk_msg_2',
            chat_name='ORDERS Restaurants',
            sender_name='Sylvia',
            content='Message 2',
            timestamp=timezone.now(),
            message_type='other'
        )
        
        bulk_delete_data = {
            'message_ids': [msg1.id, msg2.id]
        }
        
        bulk_delete_url = reverse('bulk-delete-messages')
        self.client.force_authenticate(user=None)
        response = self.client.post(bulk_delete_url, bulk_delete_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['deleted_count'], 2)
        
        # Verify messages were soft deleted
        msg1.refresh_from_db()
        msg2.refresh_from_db()
        self.assertTrue(msg1.is_deleted)
        self.assertTrue(msg2.is_deleted)
    
    def test_validate_order_stock_endpoint(self):
        """Test validating order against stock"""
        # Create test order
        from datetime import date, timedelta
        today = date.today()
        days_ahead = 0 - today.weekday()  # Monday
        if days_ahead <= 0:
            days_ahead += 7
        order_date = today + timedelta(days_ahead)
        
        order = Order.objects.create(
            restaurant=self.customer,
            order_date=order_date,
            status='received'
        )
        
        OrderItem.objects.create(
            order=order,
            product=self.lettuce,
            quantity=Decimal('50.00'),  # Less than available (100kg)
            price=Decimal('25.00'),
            unit='kg'
        )
        
        validate_url = reverse('validate-order-stock', kwargs={'order_id': order.id})
        self.client.force_authenticate(user=None)
        response = self.client.post(validate_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('can_fulfill', response.data)
        self.assertIn('items', response.data)
        
        # Should be able to fulfill (50kg needed, 100kg available)
        self.assertTrue(response.data['can_fulfill'])
        
        # Check item validation details
        items = response.data['items']
        self.assertEqual(len(items), 1)
        
        item_result = items[0]
        self.assertTrue(item_result['sufficient_stock'])
        self.assertEqual(item_result['available_quantity'], 100.0)
        self.assertEqual(item_result['ordered_quantity'], 50.0)
