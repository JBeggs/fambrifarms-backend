from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.conf import settings
from django.core.management import call_command
from datetime import datetime, timezone as dt_tz, timedelta
from .models import WhatsAppMessage
from .services import classify_message_type, has_order_items
from .smart_product_matcher import SmartProductMatcher
from accounts.models import User, RestaurantProfile
from products.models import Product, Department
from decimal import Decimal


class ReceiveMessagesTests(TestCase):
    def setUp(self):
        # Set up authentication
        self.api_key = getattr(settings, 'WHATSAPP_API_KEY', 'fambri-whatsapp-secure-key-2025')
        self.auth_headers = {'HTTP_X_API_KEY': self.api_key}
        
        # Set up URLs
        self.receive_url = reverse('receive-messages')
        self.list_url = reverse('get-messages')
        
        # Seed test data
        call_command('import_customers', verbosity=0)
        
        # Get real company names from database
        self.companies = list(RestaurantProfile.objects.values_list('business_name', flat=True))
        self.test_company = self.companies[0] if self.companies else 'Test Company'

    def test_receive_uses_incoming_timestamp_and_persists(self):
        # Generate dynamic test data
        test_timestamp = timezone.now().isoformat()
        test_message_id = f"MSG_{timezone.now().timestamp()}"
        
        payload = {
            "messages": [
                {
                    "id": test_message_id,
                    "chat": "ORDERS Restaurants",
                    "sender": "Test Manager",
                    "content": "Test order content",
                    "cleanedContent": "Test order content",
                    "timestamp": test_timestamp,
                    "items": [],
                    "instructions": "",
                    "message_type": "order",
                    "media_type": "",
                    "media_url": "",
                    "media_info": "",
                }
            ]
        }

        resp = self.client.post(self.receive_url, data=payload, content_type='application/json', **self.auth_headers)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(WhatsAppMessage.objects.count(), 1)

        msg = WhatsAppMessage.objects.first()
        self.assertEqual(msg.message_id, test_message_id)
        self.assertEqual(msg.content, "Test order content")
        # Confirm exact timestamp match
        expected_dt = datetime.fromisoformat(test_timestamp)
        self.assertEqual(msg.timestamp, expected_dt)

        # List endpoint should return it
        list_resp = self.client.get(f"{self.list_url}?limit=100", **self.auth_headers)
        self.assertEqual(list_resp.status_code, 200)
        self.assertEqual(list_resp.data['returned_count'], 1)

    def test_soft_delete_excludes_from_listing_and_receive_does_not_undelete(self):
        # Generate dynamic test data
        test_message_id = f"MSG_DEL_{timezone.now().timestamp()}"
        test_timestamp = datetime.now(dt_tz.utc)
        
        # Create a message
        WhatsAppMessage.objects.create(
            message_id=test_message_id,
            chat_name="ORDERS Restaurants",
            sender_name="Test Manager",
            content="Test delete message",
            cleaned_content="Test delete message",
            timestamp=test_timestamp,
            message_type='other',
            is_deleted=True,
        )

        # Listing should exclude it
        list_resp = self.client.get(f"{self.list_url}?limit=100", **self.auth_headers)
        self.assertEqual(list_resp.status_code, 200)
        self.assertEqual(list_resp.data['returned_count'], 0)

        # Try to re-send the same ID; receive should not resurrect deleted record
        payload = {
            "messages": [
                {
                    "id": test_message_id,
                    "chat": "ORDERS Restaurants",
                    "sender": "Test Manager",
                    "content": "Test delete message",
                    "cleanedContent": "Test delete message",
                    "timestamp": test_timestamp.isoformat(),
                    "items": [],
                    "instructions": "",
                    "message_type": "other",
                    "media_type": "",
                    "media_url": "",
                    "media_info": "",
                }
            ]
        }
        resp = self.client.post(self.receive_url, data=payload, content_type='application/json', **self.auth_headers)
        self.assertEqual(resp.status_code, 200)

        # Still exactly one (deleted) record, not resurrected
        self.assertEqual(WhatsAppMessage.objects.filter(message_id=test_message_id).count(), 1)
        self.assertTrue(WhatsAppMessage.objects.get(message_id=test_message_id).is_deleted)

        # Listing remains empty
        list_resp = self.client.get(f"{self.list_url}?limit=100", **self.auth_headers)
        self.assertEqual(list_resp.data['returned_count'], 0)

    def test_classify_and_has_order_items(self):
        # Generate dynamic test data
        current_date = timezone.now().strftime('%d %b %Y').upper()
        test_phone = '+27 11 555 0001'
        
        msg_data_stock = {
            'id': f'STOCK_{timezone.now().timestamp()}', 
            'sender': test_phone, 
            'content': f'STOCK AS AT {current_date}'
        }
        self.assertEqual(classify_message_type(msg_data_stock), 'stock')

        msg_data_demarc = {
            'id': f'DEMARC_{timezone.now().timestamp()}', 
            'sender': 'Test Manager', 
            'content': 'THURSDAY ORDERS STARTS HERE'
        }
        self.assertEqual(classify_message_type(msg_data_demarc), 'demarcation')

        # Test order item detection with dynamic content
        self.assertTrue(has_order_items('2x lettuce'))
        self.assertTrue(has_order_items('3 boxes tomatoes'))
        self.assertFalse(has_order_items('Hello team, thanks for the update'))


    def test_receive_image_message_persists_media_fields(self):
        # Generate dynamic test data
        test_message_id = f"IMG_{timezone.now().timestamp()}"
        test_timestamp = timezone.now().isoformat()
        image_url = 'https://media.example.com/test_photo.jpg'
        
        payload = {
            "messages": [
                {
                    "id": test_message_id,
                    "chat": "ORDERS Restaurants",
                    "sender": "Test Manager",
                    "content": "",
                    "cleanedContent": "",
                    "timestamp": test_timestamp,
                    "items": [],
                    "instructions": "",
                    # classification is computed server-side; media_type is for UI/media
                    "message_type": "other",
                    "media_type": "image",
                    "media_url": image_url,
                    "media_info": ""
                }
            ]
        }

        resp = self.client.post(self.receive_url, data=payload, content_type='application/json', **self.auth_headers)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(WhatsAppMessage.objects.count(), 1)

        msg = WhatsAppMessage.objects.first()
        self.assertEqual(msg.media_type, 'image')
        self.assertEqual(msg.media_url, image_url)

        # Ensure list endpoint returns media fields
        list_resp = self.client.get(f"{self.list_url}?limit=100", **self.auth_headers)
        self.assertEqual(list_resp.status_code, 200)
        self.assertEqual(list_resp.data['returned_count'], 1)
        first = list_resp.data['messages'][0]
        self.assertEqual(first['media_type'], 'image')
        self.assertEqual(first['media_url'], image_url)


class CompanyAssignmentTests(TestCase):
    """Test company assignment scenarios to ensure assignments are preserved"""
    
    def setUp(self):
        # Set up authentication
        self.api_key = getattr(settings, 'WHATSAPP_API_KEY', 'fambri-whatsapp-secure-key-2025')
        self.auth_headers = {'HTTP_X_API_KEY': self.api_key}
        
        # Set up URLs
        self.receive_url = reverse('receive-messages')
        self.list_url = reverse('get-messages')
        self.edit_url = reverse('edit-message')
        self.base_time = datetime.now(dt_tz.utc)
        
        # Seed test data
        call_command('import_customers', verbosity=0)
        
        # Get real company names from database
        self.companies = list(RestaurantProfile.objects.values_list('business_name', flat=True))
        self.test_companies = {
            'casa_bella': next((name for name in self.companies if 'Casa Bella' in name), 'Casa Bella'),
            'venue': next((name for name in self.companies if 'Venue' in name), 'Venue'),
            'wimpy': next((name for name in self.companies if 'Wimpy' in name), 'Wimpy'),
            'mugg_bean': next((name for name in self.companies if 'Mugg' in name), 'Mugg and Bean'),
            'debonairs': next((name for name in self.companies if 'Debonair' in name), 'Debonair Pizza'),
            't_junction': next((name for name in self.companies if 'T-junction' in name), 'T-junction'),
            'maltos': next((name for name in self.companies if 'Maltos' in name), 'Maltos'),
        }
    
    def _create_message(self, message_id, content, timestamp_offset_seconds=0, message_type="order"):
        """Helper to create a message via the receive endpoint"""
        timestamp = self.base_time + timedelta(seconds=timestamp_offset_seconds)
        payload = {
            "messages": [{
                "id": message_id,
                "chat": "ORDERS Restaurants",
                "sender": "Test Customer",
                "content": content,
                "cleanedContent": content,
                "timestamp": timestamp.isoformat(),
                "items": [],
                "instructions": "",
                "message_type": message_type,
                "media_type": "",
                "media_url": "",
                "media_info": "",
            }]
        }
        
        resp = self.client.post(self.receive_url, data=payload, content_type='application/json', **self.auth_headers)
        self.assertEqual(resp.status_code, 200)
        return WhatsAppMessage.objects.get(message_id=message_id)
    
    def _get_message_from_api(self, db_id):
        """Helper to get message data from the API"""
        list_resp = self.client.get(f"{self.list_url}?limit=100", **self.auth_headers)
        self.assertEqual(list_resp.status_code, 200)
        
        for msg in list_resp.data['messages']:
            if msg['id'] == db_id:
                return msg
        return None
    
    def test_order_message_with_company_name_sets_manual_company(self):
        """Test that order messages containing company names automatically set manual_company"""
        # Use real company name from database
        company_name = self.test_companies['casa_bella']
        test_message_id = f"TEST_COMPANY_IN_ORDER_{timezone.now().timestamp()}"
        
        # Create order message with company name inside
        msg = self._create_message(
            test_message_id,
            f"{company_name}\n\n5kg potatoes\n3kg onions\n2kg carrots"
        )
        
        # Check that both company_name and manual_company are set
        api_msg = self._get_message_from_api(msg.id)
        self.assertIsNotNone(api_msg)
        self.assertEqual(api_msg['company_name'], company_name)
        self.assertEqual(api_msg['manual_company'], company_name)
    
    def test_context_based_company_assignment_sets_manual_company(self):
        """Test that context-based company assignments set manual_company"""
        # Use real company name from database
        company_name = self.test_companies['venue']
        timestamp_base = timezone.now().timestamp()
        
        # Create company name message
        company_msg = self._create_message(
            f"TEST_CONTEXT_COMPANY_{timestamp_base}",
            company_name,
            timestamp_offset_seconds=0,
            message_type="other"
        )
        
        # Create order message that should get company from context
        order_msg = self._create_message(
            f"TEST_CONTEXT_ORDER_{timestamp_base}",
            "4kg apples\n2kg bananas\n1kg oranges",
            timestamp_offset_seconds=30
        )
        
        # Check that order message got company from context AND set manual_company
        api_msg = self._get_message_from_api(order_msg.id)
        self.assertIsNotNone(api_msg)
        self.assertEqual(api_msg['company_name'], company_name)
        self.assertEqual(api_msg['manual_company'], company_name)
    
    def test_edit_message_preserves_company_when_company_name_removed(self):
        """Test the MAIN BUG FIX: editing message to remove company name preserves assignment"""
        # Use real company name from database
        company_name = self.test_companies['wimpy']
        test_message_id = f"TEST_EDIT_PRESERVE_{timezone.now().timestamp()}"
        
        # Create order message with company name
        msg = self._create_message(
            test_message_id,
            f"{company_name}\n\n2x burgers\n1x fries\n1x shake"
        )
        
        # Verify initial state
        api_msg = self._get_message_from_api(msg.id)
        self.assertEqual(api_msg['company_name'], company_name)
        self.assertEqual(api_msg['manual_company'], company_name)
        
        # Edit message to remove company name
        edit_payload = {
            'message_id': msg.message_id,  # Use WhatsApp message ID
            'edited_content': '2x burgers\n1x fries\n1x shake'  # Company name removed
        }
        
        edit_resp = self.client.post(self.edit_url, data=edit_payload, content_type='application/json', **self.auth_headers)
        self.assertEqual(edit_resp.status_code, 200)
        
        # Check that company assignment is preserved
        api_msg_after = self._get_message_from_api(msg.id)
        self.assertIsNotNone(api_msg_after)
        self.assertEqual(api_msg_after['company_name'], company_name)  # Should be preserved
        self.assertEqual(api_msg_after['manual_company'], company_name)  # Should be preserved
        self.assertNotIn(company_name, api_msg_after['content'])  # Company name should be removed from content
    
    def test_delete_company_message_preserves_manual_assignments(self):
        """Test that deleting company name messages preserves manual assignments"""
        # Use real company name from database
        company_name = self.test_companies['venue']
        timestamp_base = timezone.now().timestamp()
        
        # Create company name message
        company_msg = self._create_message(
            f"TEST_DELETE_COMPANY_{timestamp_base}",
            company_name,
            timestamp_offset_seconds=0,
            message_type="other"
        )
        
        # Create order message that gets company from context
        order_msg = self._create_message(
            f"TEST_DELETE_ORDER_{timestamp_base}",
            "6x small veg boxes\n4x fruit boxes",
            timestamp_offset_seconds=20
        )
        
        # Verify order got company assignment
        api_msg = self._get_message_from_api(order_msg.id)
        self.assertEqual(api_msg['company_name'], company_name)
        self.assertEqual(api_msg['manual_company'], company_name)
        
        # Delete the company name message
        delete_url = reverse('delete-message', kwargs={'message_id': company_msg.id})
        delete_resp = self.client.delete(delete_url, **self.auth_headers)
        self.assertEqual(delete_resp.status_code, 200)
        
        # Check that order message still has company assignment
        api_msg_after = self._get_message_from_api(order_msg.id)
        self.assertIsNotNone(api_msg_after)
        self.assertEqual(api_msg_after['company_name'], company_name)  # Should be preserved
        self.assertEqual(api_msg_after['manual_company'], company_name)  # Should be preserved
    
    def test_manual_company_selection_via_api_persists(self):
        """Test that manual company selection via API persists through edits"""
        # Use real company name from database
        company_name = self.test_companies['maltos']
        test_message_id = f"TEST_MANUAL_SELECTION_{timezone.now().timestamp()}"
        
        # Create order message without company
        msg = self._create_message(
            test_message_id,
            "3kg tomatoes\n2kg cucumbers"
        )
        
        # Manually assign company via API
        update_url = reverse('update-message-company')
        update_payload = {
            'message_id': msg.id,  # Use database ID for this endpoint
            'company_name': company_name
        }
        
        update_resp = self.client.post(update_url, data=update_payload, content_type='application/json', **self.auth_headers)
        self.assertEqual(update_resp.status_code, 200)
        
        # Verify manual assignment
        api_msg = self._get_message_from_api(msg.id)
        self.assertEqual(api_msg['company_name'], company_name)
        self.assertEqual(api_msg['manual_company'], company_name)
        
        # Edit the message content
        edit_payload = {
            'message_id': msg.message_id,  # Use WhatsApp message ID
            'edited_content': '3kg tomatoes\n2kg cucumbers\n1kg peppers'  # Add item
        }
        
        edit_resp = self.client.post(self.edit_url, data=edit_payload, content_type='application/json', **self.auth_headers)
        self.assertEqual(edit_resp.status_code, 200)
        
        # Check that manual assignment persists
        api_msg_after = self._get_message_from_api(msg.id)
        self.assertEqual(api_msg_after['company_name'], company_name)  # Should persist
        self.assertEqual(api_msg_after['manual_company'], company_name)  # Should persist
    
    def test_multiple_company_aliases_resolved_correctly(self):
        """Test that company aliases are resolved and manual_company is set"""
        # Use real company names from database
        timestamp_base = timezone.now().timestamp()
        test_cases = [
            ("mugg bean", self.test_companies['mugg_bean']),
            ("casa bella", self.test_companies['casa_bella']),
            ("t junction", self.test_companies['t_junction']),
            ("debonairs", self.test_companies['debonairs']),
        ]
        
        for i, (input_name, expected_canonical) in enumerate(test_cases):
            with self.subTest(input_name=input_name):
                msg = self._create_message(
                    f"TEST_ALIAS_{timestamp_base}_{i}",
                    f"{input_name}\n\n2kg test item",
                    timestamp_offset_seconds=i * 60  # Space out timestamps
                )
                
                api_msg = self._get_message_from_api(msg.id)
                self.assertEqual(api_msg['company_name'], expected_canonical)
                self.assertEqual(api_msg['manual_company'], expected_canonical)
    
    def test_order_without_company_gets_empty_assignment(self):
        """Test that orders without company context get empty assignments"""
        test_message_id = f"TEST_NO_COMPANY_{timezone.now().timestamp()}"
        msg = self._create_message(
            test_message_id,
            "5kg random vegetables\n3kg mystery items"
        )
        
        api_msg = self._get_message_from_api(msg.id)
        self.assertEqual(api_msg['company_name'], '')
        self.assertIn(api_msg['manual_company'], [None, '', 'None'])  # Could be any of these
    
    def test_company_extraction_from_context_time_window(self):
        """Test that context-based extraction works within time windows"""
        # Create company message
        company_msg = self._create_message(
            "TEST_TIME_WINDOW_COMPANY",
            "Shebeen",
            timestamp_offset_seconds=0,
            message_type="other"
        )
        
        # Create order message within 30-second immediate window
        immediate_order = self._create_message(
            "TEST_TIME_WINDOW_IMMEDIATE",
            "2kg chicken\n1kg beef",
            timestamp_offset_seconds=25  # Within 30-second window
        )
        
        # Create order message within 5-minute extended window
        extended_order = self._create_message(
            "TEST_TIME_WINDOW_EXTENDED",
            "3kg pork\n2kg lamb",
            timestamp_offset_seconds=240  # 4 minutes - within 5-minute window
        )
        
        # Create order message outside time window
        outside_order = self._create_message(
            "TEST_TIME_WINDOW_OUTSIDE",
            "1kg fish\n2kg prawns",
            timestamp_offset_seconds=400  # 6.67 minutes - outside window
        )
        
        # Check immediate window assignment
        immediate_api = self._get_message_from_api(immediate_order.id)
        self.assertEqual(immediate_api['company_name'], 'Shebeen')
        self.assertEqual(immediate_api['manual_company'], 'Shebeen')
        
        # Check extended window assignment
        extended_api = self._get_message_from_api(extended_order.id)
        self.assertEqual(extended_api['company_name'], 'Shebeen')
        self.assertEqual(extended_api['manual_company'], 'Shebeen')
        
        # Check outside window (should not get company)
        outside_api = self._get_message_from_api(outside_order.id)
        self.assertEqual(outside_api['company_name'], '')
        self.assertIn(outside_api['manual_company'], [None, '', 'None'])


class SmartProductMatcherTestCase(TestCase):
    """Test cases for the Smart Product Matcher"""

    def setUp(self):
        """Set up test data"""
        # Create test department
        self.department = Department.objects.create(
            name='Test Department',
            description='Test department for smart matcher tests'
        )

        # Create test products
        self.products = [
            Product.objects.create(
                name='Carrots',
                unit='kg',
                price=Decimal('25.00'),
                department=self.department
            ),
            Product.objects.create(
                name='Rosemary (200g packet)',
                unit='packet',
                price=Decimal('25.00'),
                department=self.department
            ),
            Product.objects.create(
                name='Cucumber',
                unit='each',
                price=Decimal('8.00'),
                department=self.department
            ),
        ]

        self.matcher = SmartProductMatcher()

    def test_perfect_packet_match(self):
        """Test perfect packet matching with weight specification"""
        message = "packet rosemary 200g"
        suggestions = self.matcher.get_suggestions(message)
        
        self.assertIsNotNone(suggestions.best_match)
        self.assertEqual(suggestions.best_match.product.name, 'Rosemary (200g packet)')
        self.assertGreaterEqual(suggestions.best_match.confidence_score, 50)

    def test_each_unit_matching(self):
        """Test matching with 'each' unit"""
        message = "cucumber 5 each"
        suggestions = self.matcher.get_suggestions(message)
        
        self.assertIsNotNone(suggestions.best_match)
        self.assertEqual(suggestions.best_match.product.name, 'Cucumber')
        self.assertEqual(suggestions.best_match.unit, 'each')

    def test_suggestions_for_ambiguous_input(self):
        """Test suggestions for ambiguous input"""
        message = "carrot"  # Should match 'Carrots'
        suggestions = self.matcher.get_suggestions(message, min_confidence=10.0)
        
        # Should find carrot-related products
        self.assertGreater(len(suggestions.suggestions), 0)

    def test_confidence_scoring(self):
        """Test that confidence scores are reasonable"""
        message = "carrots"
        suggestions = self.matcher.get_suggestions(message)
        
        if suggestions.best_match:
            self.assertGreaterEqual(suggestions.best_match.confidence_score, 50)
        
        for suggestion in suggestions.suggestions:
            self.assertGreater(suggestion.confidence_score, 0)

