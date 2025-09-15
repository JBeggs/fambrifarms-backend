from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from datetime import datetime, timezone as dt_tz, timedelta
from .models import WhatsAppMessage
from .services import classify_message_type, has_order_items


class ReceiveMessagesTests(TestCase):
    def setUp(self):
        self.receive_url = reverse('receive-messages')
        self.list_url = reverse('get-messages')

    def test_receive_uses_incoming_timestamp_and_persists(self):
        payload = {
            "messages": [
                {
                    "id": "MSG_1",
                    "chat": "ORDERS Restaurants",
                    "sender": "Karl",
                    "content": "Test order",
                    "cleanedContent": "Test order",
                    # WhatsApp-derived ISO timestamp (UTC)
                    "timestamp": "2025-09-10T19:55:00+00:00",
                    "items": [],
                    "instructions": "",
                    "message_type": "order",
                    "media_type": "",
                    "media_url": "",
                    "media_info": "",
                }
            ]
        }

        resp = self.client.post(self.receive_url, data=payload, content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(WhatsAppMessage.objects.count(), 1)

        msg = WhatsAppMessage.objects.first()
        self.assertEqual(msg.message_id, "MSG_1")
        self.assertEqual(msg.content, "Test order")
        # Confirm exact timestamp match
        expected_dt = datetime.fromisoformat("2025-09-10T19:55:00+00:00")
        self.assertEqual(msg.timestamp, expected_dt)

        # List endpoint should return it
        list_resp = self.client.get(self.list_url)
        self.assertEqual(list_resp.status_code, 200)
        self.assertEqual(list_resp.data['returned_count'], 1)

    def test_soft_delete_excludes_from_listing_and_receive_does_not_undelete(self):
        # Create a message
        WhatsAppMessage.objects.create(
            message_id="MSG_DEL",
            chat_name="ORDERS Restaurants",
            sender_name="Karl",
            content="Delete me",
            cleaned_content="Delete me",
            timestamp=datetime.now(dt_tz.utc),
            message_type='other',
            is_deleted=True,
        )

        # Listing should exclude it
        list_resp = self.client.get(self.list_url)
        self.assertEqual(list_resp.status_code, 200)
        self.assertEqual(list_resp.data['returned_count'], 0)

        # Try to re-send the same ID; receive should not resurrect deleted record
        payload = {
            "messages": [
                {
                    "id": "MSG_DEL",
                    "chat": "ORDERS Restaurants",
                    "sender": "Karl",
                    "content": "Delete me",
                    "cleanedContent": "Delete me",
                    "timestamp": datetime.now(dt_tz.utc).isoformat(),
                    "items": [],
                    "instructions": "",
                    "message_type": "other",
                    "media_type": "",
                    "media_url": "",
                    "media_info": "",
                }
            ]
        }
        resp = self.client.post(self.receive_url, data=payload, content_type='application/json')
        self.assertEqual(resp.status_code, 200)

        # Still exactly one (deleted) record, not resurrected
        self.assertEqual(WhatsAppMessage.objects.filter(message_id="MSG_DEL").count(), 1)
        self.assertTrue(WhatsAppMessage.objects.get(message_id="MSG_DEL").is_deleted)

        # Listing remains empty
        list_resp = self.client.get(self.list_url)
        self.assertEqual(list_resp.data['returned_count'], 0)

    def test_classify_and_has_order_items(self):
        msg_data_stock = {
            'id': 'X1', 'sender': '+27 61 674 9368', 'content': 'STOCK AS AT 10 SEPT 2025'}
        self.assertEqual(classify_message_type(msg_data_stock), 'stock')

        msg_data_demarc = {'id': 'X2', 'sender': 'Karl', 'content': 'THURSDAY ORDERS STARTS HERE'}
        self.assertEqual(classify_message_type(msg_data_demarc), 'demarcation')

        self.assertTrue(has_order_items('2x lettuce'))
        self.assertTrue(has_order_items('3 boxes tomatoes'))
        self.assertFalse(has_order_items('Hello team, thanks'))


    def test_receive_image_message_persists_media_fields(self):
        image_url = 'https://media.example.com/photo.jpg'
        payload = {
            "messages": [
                {
                    "id": "IMG_1",
                    "chat": "ORDERS Restaurants",
                    "sender": "Karl",
                    "content": "",
                    "cleanedContent": "",
                    "timestamp": "2025-09-10T19:55:00+00:00",
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

        resp = self.client.post(self.receive_url, data=payload, content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(WhatsAppMessage.objects.count(), 1)

        msg = WhatsAppMessage.objects.first()
        self.assertEqual(msg.media_type, 'image')
        self.assertEqual(msg.media_url, image_url)

        # Ensure list endpoint returns media fields
        list_resp = self.client.get(self.list_url)
        self.assertEqual(list_resp.status_code, 200)
        self.assertEqual(list_resp.data['returned_count'], 1)
        first = list_resp.data['messages'][0]
        self.assertEqual(first['media_type'], 'image')
        self.assertEqual(first['media_url'], image_url)


class CompanyAssignmentTests(TestCase):
    """Test company assignment scenarios to ensure assignments are preserved"""
    
    def setUp(self):
        self.receive_url = reverse('receive-messages')
        self.list_url = reverse('get-messages')
        self.edit_url = reverse('edit-message')
        self.base_time = datetime.now(dt_tz.utc)
    
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
        
        resp = self.client.post(self.receive_url, data=payload, content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        return WhatsAppMessage.objects.get(message_id=message_id)
    
    def _get_message_from_api(self, db_id):
        """Helper to get message data from the API"""
        list_resp = self.client.get(self.list_url)
        self.assertEqual(list_resp.status_code, 200)
        
        for msg in list_resp.data['messages']:
            if msg['id'] == db_id:
                return msg
        return None
    
    def test_order_message_with_company_name_sets_manual_company(self):
        """Test that order messages containing company names automatically set manual_company"""
        # Create order message with company name inside
        msg = self._create_message(
            "TEST_COMPANY_IN_ORDER",
            "Casa Bella\n\n5kg potatoes\n3kg onions\n2kg carrots"
        )
        
        # Check that both company_name and manual_company are set
        api_msg = self._get_message_from_api(msg.id)
        self.assertIsNotNone(api_msg)
        self.assertEqual(api_msg['company_name'], 'Casa Bella')
        self.assertEqual(api_msg['manual_company'], 'Casa Bella')
    
    def test_context_based_company_assignment_sets_manual_company(self):
        """Test that context-based company assignments set manual_company"""
        # Create company name message
        company_msg = self._create_message(
            "TEST_CONTEXT_COMPANY",
            "Venue",
            timestamp_offset_seconds=0,
            message_type="other"
        )
        
        # Create order message that should get company from context
        order_msg = self._create_message(
            "TEST_CONTEXT_ORDER",
            "4kg apples\n2kg bananas\n1kg oranges",
            timestamp_offset_seconds=30
        )
        
        # Check that order message got company from context AND set manual_company
        api_msg = self._get_message_from_api(order_msg.id)
        self.assertIsNotNone(api_msg)
        self.assertEqual(api_msg['company_name'], 'Venue')
        self.assertEqual(api_msg['manual_company'], 'Venue')
    
    def test_edit_message_preserves_company_when_company_name_removed(self):
        """Test the MAIN BUG FIX: editing message to remove company name preserves assignment"""
        # Create order message with company name
        msg = self._create_message(
            "TEST_EDIT_PRESERVE",
            "Wimpy\n\n2x burgers\n1x fries\n1x shake"
        )
        
        # Verify initial state
        api_msg = self._get_message_from_api(msg.id)
        self.assertEqual(api_msg['company_name'], 'Wimpy')
        self.assertEqual(api_msg['manual_company'], 'Wimpy')
        
        # Edit message to remove company name
        edit_payload = {
            'message_id': msg.message_id,  # Use WhatsApp message ID
            'edited_content': '2x burgers\n1x fries\n1x shake'  # Company name removed
        }
        
        edit_resp = self.client.post(self.edit_url, data=edit_payload, content_type='application/json')
        self.assertEqual(edit_resp.status_code, 200)
        
        # Check that company assignment is preserved
        api_msg_after = self._get_message_from_api(msg.id)
        self.assertIsNotNone(api_msg_after)
        self.assertEqual(api_msg_after['company_name'], 'Wimpy')  # Should be preserved
        self.assertEqual(api_msg_after['manual_company'], 'Wimpy')  # Should be preserved
        self.assertNotIn('Wimpy', api_msg_after['content'])  # Company name should be removed from content
    
    def test_delete_company_message_preserves_manual_assignments(self):
        """Test that deleting company name messages preserves manual assignments"""
        # Create company name message
        company_msg = self._create_message(
            "TEST_DELETE_COMPANY",
            "Marco",
            timestamp_offset_seconds=0,
            message_type="other"
        )
        
        # Create order message that gets company from context
        order_msg = self._create_message(
            "TEST_DELETE_ORDER",
            "6x small veg boxes\n4x fruit boxes",
            timestamp_offset_seconds=20
        )
        
        # Verify order got company assignment
        api_msg = self._get_message_from_api(order_msg.id)
        self.assertEqual(api_msg['company_name'], 'Marco')
        self.assertEqual(api_msg['manual_company'], 'Marco')
        
        # Delete the company name message
        delete_url = reverse('delete-message', kwargs={'message_id': company_msg.id})
        delete_resp = self.client.delete(delete_url)
        self.assertEqual(delete_resp.status_code, 200)
        
        # Check that order message still has company assignment
        api_msg_after = self._get_message_from_api(order_msg.id)
        self.assertIsNotNone(api_msg_after)
        self.assertEqual(api_msg_after['company_name'], 'Marco')  # Should be preserved
        self.assertEqual(api_msg_after['manual_company'], 'Marco')  # Should be preserved
    
    def test_manual_company_selection_via_api_persists(self):
        """Test that manual company selection via API persists through edits"""
        # Create order message without company
        msg = self._create_message(
            "TEST_MANUAL_SELECTION",
            "3kg tomatoes\n2kg cucumbers"
        )
        
        # Manually assign company via API
        update_url = reverse('update-message-company')
        update_payload = {
            'message_id': msg.id,  # Use database ID for this endpoint
            'company_name': 'Maltos'
        }
        
        update_resp = self.client.post(update_url, data=update_payload, content_type='application/json')
        self.assertEqual(update_resp.status_code, 200)
        
        # Verify manual assignment
        api_msg = self._get_message_from_api(msg.id)
        self.assertEqual(api_msg['company_name'], 'Maltos')
        self.assertEqual(api_msg['manual_company'], 'Maltos')
        
        # Edit the message content
        edit_payload = {
            'message_id': msg.message_id,  # Use WhatsApp message ID
            'edited_content': '3kg tomatoes\n2kg cucumbers\n1kg peppers'  # Add item
        }
        
        edit_resp = self.client.post(self.edit_url, data=edit_payload, content_type='application/json')
        self.assertEqual(edit_resp.status_code, 200)
        
        # Check that manual assignment persists
        api_msg_after = self._get_message_from_api(msg.id)
        self.assertEqual(api_msg_after['company_name'], 'Maltos')  # Should persist
        self.assertEqual(api_msg_after['manual_company'], 'Maltos')  # Should persist
    
    def test_multiple_company_aliases_resolved_correctly(self):
        """Test that company aliases are resolved and manual_company is set"""
        test_cases = [
            ("mugg bean", "Mugg and Bean"),
            ("casa bella", "Casa Bella"),
            ("t junction", "T-junction"),
            ("debonairs", "Debonairs"),
        ]
        
        for i, (input_name, expected_canonical) in enumerate(test_cases):
            with self.subTest(input_name=input_name):
                msg = self._create_message(
                    f"TEST_ALIAS_{i}",
                    f"{input_name}\n\n2kg test item",
                    timestamp_offset_seconds=i * 60  # Space out timestamps
                )
                
                api_msg = self._get_message_from_api(msg.id)
                self.assertEqual(api_msg['company_name'], expected_canonical)
                self.assertEqual(api_msg['manual_company'], expected_canonical)
    
    def test_order_without_company_gets_empty_assignment(self):
        """Test that orders without company context get empty assignments"""
        msg = self._create_message(
            "TEST_NO_COMPANY",
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

