# Integration Tests Errors

## Summary
- **First Error**: Missing test data - Karl (Farm Manager) user doesn't exist
- **Issue**: Integration tests expect seeded data that hasn't been created

## Root Cause
The integration tests are expecting pre-seeded data (users, companies, products, etc.) but the test database is empty. Integration tests typically require either:
1. Test fixtures to be loaded
2. Management commands to be run during test setup
3. setUp methods to create the required data

## Specific Error

### 1. Missing User Data
**Error**: `AssertionError: unexpectedly None : Karl (Farm Manager) should exist`

**Location**: `tests/integration/test_fambri_digital_transformation.py`, line 51

**Code**:
```python
karl = User.objects.filter(first_name='Karl', user_type='farm_manager').first()
self.assertIsNotNone(karl, "Karl (Farm Manager) should exist")
```

**Test Class**: `FambriFarmsDigitalTransformationTest`

## Analysis
The test `test_01_user_system_integrity` is looking for specific users that should exist in the system:
- Karl (Farm Manager)
- Likely other users with specific roles

This suggests the integration tests expect the database to be populated with realistic test data, possibly through management commands like:
- `seed_fambri_users`
- `import_customers`
- `seed_fambri_suppliers`
- etc.

## Required Investigation
Need to check:
1. `tests/integration/test_fambri_digital_transformation.py` - What data is expected
2. Management commands in various apps - What seeding commands exist
3. Test setup methods - How data should be populated

## Likely Fixes

### Option 1: Add setUp Method to Load Data
```python
def setUp(self):
    # Run management commands to seed test data
    call_command('seed_fambri_users')
    call_command('import_customers')
    call_command('seed_fambri_suppliers')
    # etc.
```

### Option 2: Create Test Fixtures
```python
def setUp(self):
    # Create required test users
    self.karl = User.objects.create(
        first_name='Karl',
        user_type='farm_manager',
        # ... other required fields
    )
```

### Option 3: Use Django Fixtures
Create fixture files and load them in the test class:
```python
class FambriFarmsDigitalTransformationTest(TestCase):
    fixtures = ['users.json', 'companies.json', 'products.json']
```

## Priority
**HIGH** - Integration tests are critical for validating the complete system workflow.

## Next Steps
1. Analyze what data the integration tests expect
2. Identify available management commands for seeding
3. Implement proper test data setup
4. Re-run tests to identify next set of issues
