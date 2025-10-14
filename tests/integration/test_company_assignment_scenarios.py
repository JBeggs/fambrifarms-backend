#!/usr/bin/env python3
"""
Integration tests for company assignment scenarios.
These tests verify the complete flow from message creation to company assignment preservation.
"""

import os
import sys
import django
import json
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from datetime import datetime, timezone as dt_tz, timedelta

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from whatsapp.models import WhatsAppMessage


class CompanyAssignmentIntegrationTests(TransactionTestCase):
    """Integration tests for the complete company assignment flow"""
    
    def setUp(self):
        """Set up test fixtures"""
        from django.contrib.auth import get_user_model
        from rest_framework.test import APIClient
        
        # Create test user for authentication
        User = get_user_model()
        self.test_user = User.objects.create_user(
            email='test@fambrifarms.co.za',
            first_name='Test',
            last_name='User',
            user_type='admin'
        )
        
        # Use API client and authenticate
        self.client = APIClient()
        self.client.force_authenticate(user=self.test_user)
        
        self.receive_url = reverse('receive-messages')
        self.list_url = reverse('get-messages')
        self.edit_url = reverse('edit-message')
        self.delete_url_template = 'whatsapp:delete-message'
        self.update_company_url = reverse('update-message-company')
        self.base_time = datetime.now(dt_tz.utc)
    
    def _create_message_via_api(self, message_id, content, timestamp_offset_seconds=0, message_type="order"):
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
        
        import json
        response = self.client.post(self.receive_url, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 200, f"Failed to create message: {response.content}")
        return WhatsAppMessage.objects.get(message_id=message_id)
    
    def _get_message_from_api(self, db_id):
        """Helper to get message data from the API"""
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200)
        
        for msg in response.data['messages']:
            if msg['id'] == db_id:
                return msg
        return None
    
    def test_scenario_1_order_with_embedded_company_name(self):
        """
        SCENARIO 1: Order message contains company name
        - Create order with company name inside content
        - Verify both company_name and manual_company are set
        - Edit to remove company name
        - Verify company assignment is preserved
        """
        print("\n=== SCENARIO 1: Order with embedded company name ===")
        
        # Step 1: Create order message with company name
        msg = self._create_message_via_api(
            "SCENARIO_1_ORDER",
            "Casa Bella\n\n5kg potatoes\n3kg onions\n2kg carrots"
        )
        
        # Step 2: Verify initial company assignment
        api_msg = self._get_message_from_api(msg.id)
        self.assertIsNotNone(api_msg, "Message should be retrievable from API")
        self.assertEqual(api_msg['company_name'], 'Casa Bella', "Company should be extracted from content")
        self.assertEqual(api_msg['manual_company'], 'Casa Bella', "Manual company should be set automatically")
        print(f"✅ Initial state: Company='{api_msg['company_name']}', Manual='{api_msg['manual_company']}'")
        
        # Step 3: Edit message to remove company name
        edit_payload = {
            'message_id': msg.message_id,  # Use WhatsApp message ID
            'edited_content': '5kg potatoes\n3kg onions\n2kg carrots'  # Company name removed
        }
        
        edit_response = self.client.post(self.edit_url, data=json.dumps(edit_payload), content_type='application/json')
        self.assertEqual(edit_response.status_code, 200, f"Edit should succeed: {edit_response.content}")
        print("✅ Message edited to remove company name")
        
        # Step 4: Verify company assignment is preserved
        api_msg_after = self._get_message_from_api(msg.id)
        self.assertIsNotNone(api_msg_after, "Message should still be retrievable after edit")
        self.assertEqual(api_msg_after['company_name'], 'Casa Bella', "Company should be preserved after edit")
        self.assertEqual(api_msg_after['manual_company'], 'Casa Bella', "Manual company should be preserved")
        self.assertNotIn('Casa Bella', api_msg_after['content'], "Company name should be removed from content")
        print(f"✅ After edit: Company='{api_msg_after['company_name']}', Manual='{api_msg_after['manual_company']}'")
        print("✅ SCENARIO 1 PASSED: Company assignment preserved after editing")
    
    def test_scenario_2_context_based_assignment(self):
        """
        SCENARIO 2: Context-based company assignment
        - Create standalone company message
        - Create order message that gets company from context
        - Verify manual_company is set for context-based assignment
        - Delete company message
        - Verify order message preserves company assignment
        """
        print("\n=== SCENARIO 2: Context-based assignment ===")
        
        # Step 1: Create company name message
        company_msg = self._create_message_via_api(
            "SCENARIO_2_COMPANY",
            "Venue",
            timestamp_offset_seconds=0,
            message_type="other"
        )
        print("✅ Created standalone company message: 'Venue'")
        
        # Step 2: Create order message that should get company from context
        order_msg = self._create_message_via_api(
            "SCENARIO_2_ORDER",
            "4kg apples\n2kg bananas\n1kg oranges",
            timestamp_offset_seconds=30
        )
        
        # Step 3: Verify context-based assignment
        api_msg = self._get_message_from_api(order_msg.id)
        self.assertIsNotNone(api_msg, "Order message should be retrievable")
        self.assertEqual(api_msg['company_name'], 'Venue', "Order should get company from context")
        self.assertEqual(api_msg['manual_company'], 'Venue', "Manual company should be set for context assignment")
        print(f"✅ Context assignment: Company='{api_msg['company_name']}', Manual='{api_msg['manual_company']}'")
        
        # Step 4: Delete the company name message
        delete_url = reverse('delete-message', kwargs={'message_id': company_msg.id})
        delete_response = self.client.delete(delete_url)
        self.assertEqual(delete_response.status_code, 200, f"Delete should succeed: {delete_response.content}")
        print("✅ Deleted company name message")
        
        # Step 5: Verify order message still has company assignment
        api_msg_after = self._get_message_from_api(order_msg.id)
        self.assertIsNotNone(api_msg_after, "Order message should still exist after company deletion")
        self.assertEqual(api_msg_after['company_name'], 'Venue', "Company should be preserved after context deletion")
        self.assertEqual(api_msg_after['manual_company'], 'Venue', "Manual company should preserve assignment")
        print(f"✅ After deletion: Company='{api_msg_after['company_name']}', Manual='{api_msg_after['manual_company']}'")
        print("✅ SCENARIO 2 PASSED: Context-based assignment preserved after company message deletion")
    
    def test_scenario_3_manual_company_selection(self):
        """
        SCENARIO 3: Manual company selection via API
        - Create order message without company
        - Manually assign company via API
        - Edit message content
        - Verify manual assignment persists
        """
        print("\n=== SCENARIO 3: Manual company selection ===")
        
        # Step 1: Create order message without company
        msg = self._create_message_via_api(
            "SCENARIO_3_ORDER",
            "3kg tomatoes\n2kg cucumbers"
        )
        
        # Step 2: Verify no initial company assignment
        api_msg = self._get_message_from_api(msg.id)
        self.assertEqual(api_msg['company_name'], '', "Should have no company initially")
        print("✅ Created order without company assignment")
        
        # Step 3: Manually assign company via API
        update_payload = {
            'message_id': msg.id,  # Use database ID for this endpoint
            'company_name': 'Maltos'
        }
        
        update_response = self.client.post(self.update_company_url, data=json.dumps(update_payload), content_type='application/json')
        self.assertEqual(update_response.status_code, 200, f"Manual assignment should succeed: {update_response.content}")
        print("✅ Manually assigned company: 'Maltos'")
        
        # Step 4: Verify manual assignment
        api_msg_manual = self._get_message_from_api(msg.id)
        self.assertEqual(api_msg_manual['company_name'], 'Maltos', "Manual assignment should set company")
        self.assertEqual(api_msg_manual['manual_company'], 'Maltos', "Manual company should be set")
        print(f"✅ Manual assignment: Company='{api_msg_manual['company_name']}', Manual='{api_msg_manual['manual_company']}'")
        
        # Step 5: Edit the message content
        edit_payload = {
            'message_id': msg.message_id,  # Use WhatsApp message ID
            'edited_content': '3kg tomatoes\n2kg cucumbers\n1kg peppers'  # Add item
        }
        
        edit_response = self.client.post(self.edit_url, data=json.dumps(edit_payload), content_type='application/json')
        self.assertEqual(edit_response.status_code, 200, f"Edit should succeed: {edit_response.content}")
        print("✅ Edited message content")
        
        # Step 6: Verify manual assignment persists
        api_msg_after = self._get_message_from_api(msg.id)
        self.assertEqual(api_msg_after['company_name'], 'Maltos', "Manual assignment should persist after edit")
        self.assertEqual(api_msg_after['manual_company'], 'Maltos', "Manual company should persist")
        print(f"✅ After edit: Company='{api_msg_after['company_name']}', Manual='{api_msg_after['manual_company']}'")
        print("✅ SCENARIO 3 PASSED: Manual company selection persists through edits")
    
    def test_scenario_4_company_aliases(self):
        """
        SCENARIO 4: Company aliases resolution
        - Test various company aliases are resolved correctly
        - Verify manual_company is set for all aliases
        """
        print("\n=== SCENARIO 4: Company aliases resolution ===")
        
        test_cases = [
            ("mugg bean", "Mugg and Bean"),
            ("casa bella", "Casa Bella"),
            ("t junction", "T-junction"),
            ("debonairs", "Debonairs Pizza"),
        ]
        
        for i, (alias, expected_canonical) in enumerate(test_cases):
            with self.subTest(alias=alias):
                msg = self._create_message_via_api(
                    f"SCENARIO_4_ALIAS_{i}",
                    f"{alias}\n\n2kg test item",
                    timestamp_offset_seconds=i * 60  # Space out timestamps
                )
                
                api_msg = self._get_message_from_api(msg.id)
                self.assertEqual(api_msg['company_name'], expected_canonical, 
                    f"Alias '{alias}' should resolve to '{expected_canonical}'")
                self.assertEqual(api_msg['manual_company'], expected_canonical,
                    f"Manual company should be set for alias '{alias}'")
                print(f"✅ Alias '{alias}' → '{expected_canonical}' (Manual: '{api_msg['manual_company']}')")
        
        print("✅ SCENARIO 4 PASSED: All company aliases resolved correctly")
    
    def test_scenario_5_time_window_context_extraction(self):
        """
        SCENARIO 5: Time window for context extraction
        - Test immediate window (30 seconds)
        - Test extended window (5 minutes)
        - Test outside window (should not get company)
        """
        print("\n=== SCENARIO 5: Time window context extraction ===")
        
        # Step 1: Create company message
        company_msg = self._create_message_via_api(
            "SCENARIO_5_COMPANY",
            "Shebeen",
            timestamp_offset_seconds=0,
            message_type="other"
        )
        print("✅ Created company message: 'Shebeen'")
        
        # Step 2: Create order within immediate window (30 seconds)
        immediate_order = self._create_message_via_api(
            "SCENARIO_5_IMMEDIATE",
            "2kg chicken\n1kg beef",
            timestamp_offset_seconds=25  # Within 30-second window
        )
        
        api_immediate = self._get_message_from_api(immediate_order.id)
        self.assertEqual(api_immediate['company_name'], 'Shebeen', "Should get company from immediate window")
        self.assertEqual(api_immediate['manual_company'], 'Shebeen', "Manual company should be set")
        print(f"✅ Immediate window (25s): Company='{api_immediate['company_name']}'")
        
        # Step 3: Create order within extended window (5 minutes)
        extended_order = self._create_message_via_api(
            "SCENARIO_5_EXTENDED",
            "3kg pork\n2kg lamb",
            timestamp_offset_seconds=240  # 4 minutes - within 5-minute window
        )
        
        api_extended = self._get_message_from_api(extended_order.id)
        self.assertEqual(api_extended['company_name'], 'Shebeen', "Should get company from extended window")
        self.assertEqual(api_extended['manual_company'], 'Shebeen', "Manual company should be set")
        print(f"✅ Extended window (4m): Company='{api_extended['company_name']}'")
        
        # Step 4: Create order outside window
        outside_order = self._create_message_via_api(
            "SCENARIO_5_OUTSIDE",
            "1kg fish\n2kg prawns",
            timestamp_offset_seconds=400  # 6.67 minutes - outside window
        )
        
        api_outside = self._get_message_from_api(outside_order.id)
        self.assertEqual(api_outside['company_name'], '', "Should not get company from outside window")
        self.assertIn(api_outside['manual_company'], [None, '', 'None'], "Manual company should be empty")
        print(f"✅ Outside window (6.67m): Company='{api_outside['company_name']}' (correctly empty)")
        print("✅ SCENARIO 5 PASSED: Time window context extraction working correctly")


def run_integration_tests():
    """Run the integration tests"""
    import unittest
    
    print("🧪 Running Company Assignment Integration Tests")
    print("=" * 60)
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(CompanyAssignmentIntegrationTests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print("🎉 ALL INTEGRATION TESTS PASSED!")
        print("✅ Company assignment scenarios are working correctly")
    else:
        print("❌ SOME TESTS FAILED!")
        print(f"Failures: {len(result.failures)}")
        print(f"Errors: {len(result.errors)}")
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_integration_tests()
    sys.exit(0 if success else 1)
