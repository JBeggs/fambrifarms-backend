# WhatsApp App Test Errors

## Summary
- **Total Tests**: 12
- **Failures**: 14 (some tests run multiple times with different parameters)
- **Main Issue**: Authentication failures (401 Unauthorized)

## Root Cause
All failing tests are related to API authentication. The tests are making HTTP requests to WhatsApp API endpoints but are not providing proper authentication credentials.

## Specific Errors

### 1. Authentication Issue (401 Unauthorized)
**Error Pattern**: `AssertionError: 401 != 200`

**Affected Tests**:
- `test_company_extraction_from_context_time_window`
- `test_context_based_company_assignment_sets_manual_company`
- `test_delete_company_message_preserves_manual_assignments`
- `test_edit_message_preserves_company_when_company_name_removed`
- `test_manual_company_selection_via_api_persists`
- `test_multiple_company_aliases_resolved_correctly` (multiple variants)
- `test_order_message_with_company_name_sets_manual_company`
- `test_order_without_company_gets_empty_assignment`
- `test_receive_image_message_persists_media_fields`
- `test_receive_uses_incoming_timestamp_and_persists`
- `test_soft_delete_excludes_from_listing_and_receive_does_not_undelete`

**API Endpoints Failing**:
- `/api/whatsapp/receive-messages/`
- `/api/whatsapp/messages/`

## Analysis
The tests are using Django's test client to make HTTP requests but are not setting up proper authentication. The WhatsApp API endpoints require either:
1. JWT authentication
2. API key authentication (WhatsAppAPIKeyAuthentication)

## Required Fixes

### Option 1: Add API Key Authentication to Tests
```python
# In test setup
def setUp(self):
    # Set up API key authentication
    self.api_key = settings.WHATSAPP_API_KEY
    self.auth_headers = {'HTTP_X_API_KEY': self.api_key}

# In test methods
resp = self.client.post('/api/whatsapp/receive-messages/', data, **self.auth_headers)
```

### Option 2: Use JWT Authentication
```python
# In test setup
def setUp(self):
    # Create test user and get JWT token
    self.user = User.objects.create_user(username='testuser', password='testpass')
    refresh = RefreshToken.for_user(self.user)
    self.access_token = str(refresh.access_token)
    self.auth_headers = {'HTTP_AUTHORIZATION': f'Bearer {self.access_token}'}
```

### Option 3: Override Authentication for Tests
```python
# In test setup
def setUp(self):
    # Override authentication classes for testing
    from whatsapp.views import ReceiveMessagesView
    ReceiveMessagesView.authentication_classes = []
    ReceiveMessagesView.permission_classes = []
```

## Recommendation
Use **Option 1** (API Key Authentication) as it matches the production authentication method for WhatsApp webhooks and is simpler to implement in tests.

## Files to Modify
- `whatsapp/tests.py` - Add proper authentication setup
- Potentially `whatsapp/views.py` - Ensure test-friendly authentication configuration

## Priority
**HIGH** - These are integration tests that validate critical WhatsApp functionality including company assignment and message processing.
