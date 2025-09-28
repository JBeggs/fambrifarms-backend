# Unit Tests Errors

## Summary
- **First Error**: URL reverse lookup failure
- **Issue**: `NoReverseMatch: Reverse for 'customer-list' not found`

## Root Cause
The unit tests are trying to reverse URL names that don't exist in the URL configuration. This suggests that the API endpoints are not properly registered with the Django URL router.

## Specific Error

### 1. URL Reverse Lookup Failure
**Error**: `NoReverseMatch: Reverse for 'customer-list' not found`

**Location**: `tests/unit/test_api_endpoints.py`, line 294 in `setUp` method

**Code**:
```python
self.customers_url = reverse('customer-list')
```

**Affected Test Class**: `CustomerAPITest`

## Analysis
The test is expecting a URL pattern named 'customer-list' but it doesn't exist. This typically happens when:

1. **Missing URL Registration**: The CustomerViewSet is not registered in the URLs
2. **Incorrect URL Name**: The URL is registered with a different name
3. **Missing Router Registration**: DRF ViewSets need to be registered with a router

## Required Investigation
Need to check:
1. `accounts/urls.py` - Customer API URL configuration
2. `familyfarms_api/urls.py` - Main URL configuration
3. `accounts/views.py` - CustomerViewSet definition

## Likely Fix
The CustomerViewSet needs to be properly registered in the URL configuration:

```python
# In accounts/urls.py
from rest_framework.routers import DefaultRouter
from .views import CustomerViewSet

router = DefaultRouter()
router.register(r'customers', CustomerViewSet, basename='customer')
urlpatterns = router.urls
```

Or if using explicit URL patterns:
```python
# In accounts/urls.py
from django.urls import path
from .views import CustomerViewSet

urlpatterns = [
    path('customers/', CustomerViewSet.as_view({'get': 'list', 'post': 'create'}), name='customer-list'),
    # ... other patterns
]
```

## Priority
**HIGH** - This is blocking all API endpoint tests from running.

## Next Steps
1. Investigate URL configuration
2. Fix missing URL registrations
3. Re-run tests to identify next set of issues
