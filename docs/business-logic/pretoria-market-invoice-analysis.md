# Pretoria Market Invoice Structure Analysis

## Overview
This document analyzes the structure of Pretoria Market invoices to prepare for automated invoice import functionality.

## Expected Invoice Structure

### Header Information
- **Invoice Number**: Unique identifier (e.g., PM-2024-001234)
- **Invoice Date**: Date of invoice generation
- **Due Date**: Payment due date
- **Supplier Information**: 
  - Pretoria Market details
  - Contact information
  - Tax registration numbers

### Customer Information
- **Customer Name**: Fambri Farms
- **Delivery Address**: Farm location
- **Billing Address**: If different from delivery
- **Customer Account Number**: Reference number

### Line Items Structure
Each line item typically contains:
- **Product Code/SKU**: Supplier's product identifier
- **Product Description**: Name and details
- **Quantity**: Amount delivered
- **Unit**: Unit of measure (kg, bunch, box, etc.)
- **Unit Price**: Price per unit
- **Line Total**: Quantity × Unit Price
- **Quality Grade**: A, B, C, R (if specified)
- **Batch/Lot Number**: Traceability information

### Totals Section
- **Subtotal**: Sum of all line items
- **Tax Amount**: VAT or other taxes
- **Delivery Charges**: Transportation costs
- **Total Amount**: Final amount due

## Common Variations

### Format Types
1. **PDF Invoices**: Most common format
2. **Excel Spreadsheets**: Sometimes provided
3. **Paper Invoices**: Require manual entry
4. **Electronic Data**: XML or CSV (rare)

### Unit Variations
- **Weight Units**: kg, g, tons
- **Count Units**: pieces, bunches, heads
- **Package Units**: boxes, crates, bags
- **Volume Units**: liters (for liquids)

### Price Structures
- **Per Unit Pricing**: Standard approach
- **Bulk Pricing**: Discounts for large quantities
- **Grade-Based Pricing**: Different prices by quality
- **Seasonal Pricing**: Market-based fluctuations

## Data Extraction Strategy

### Automated Processing
1. **PDF Text Extraction**: Use OCR for scanned documents
2. **Pattern Recognition**: Identify invoice sections
3. **Data Validation**: Cross-check against expected formats
4. **Error Handling**: Flag unusual patterns for review

### Manual Verification Points
- **New Products**: Items not in system
- **Price Variances**: Significant price changes
- **Quality Issues**: Grade downgrades
- **Quantity Discrepancies**: Delivery vs invoice differences

## Integration with Existing System

### Product Matching
1. **SKU Mapping**: Map supplier codes to internal products
2. **Name Matching**: Fuzzy matching for product names
3. **Category Assignment**: Auto-assign to departments
4. **New Product Creation**: Add missing items

### Price Validation
1. **Historical Comparison**: Check against PriceHistory
2. **Variance Analysis**: Use BusinessSettings thresholds
3. **Approval Workflow**: Flag high variances
4. **Market Price Checks**: External price validation

### Inventory Updates
1. **Stock Movements**: Create receipt records
2. **Batch Tracking**: Link to RawMaterialBatch
3. **Quality Recording**: Update quality grades
4. **Expiry Tracking**: Set expiry dates

## Implementation Plan

### Phase 1: Manual Import Template
- Create standardized Excel template
- Map fields to system requirements
- Implement basic validation
- Test with sample invoices

### Phase 2: Semi-Automated Processing
- PDF text extraction
- Pattern recognition for common formats
- Automated field mapping
- Manual review and approval

### Phase 3: Full Automation
- Machine learning for format recognition
- Automated product matching
- Exception-based review only
- Integration with email processing

## Data Validation Rules

### Required Fields
- Invoice number (unique)
- Invoice date (valid date)
- Product identification (SKU or name)
- Quantity (positive number)
- Unit price (positive amount)

### Optional Fields
- Batch/lot numbers
- Expiry dates
- Quality grades
- Delivery charges

### Business Rule Validation
- Price variance within acceptable limits
- Products exist in system or can be created
- Units are compatible with product definitions
- Quantities are reasonable for product type

## Error Handling

### Common Issues
1. **Missing Products**: Items not in system
   - Solution: Create new products with approval
   
2. **Unit Mismatches**: Supplier vs internal units
   - Solution: Use unit conversion system
   
3. **Price Variances**: Significant price changes
   - Solution: Flag for manager approval
   
4. **Quality Downgrades**: Lower than expected grades
   - Solution: Alert quality control team

### Exception Reporting
- Daily exception summary
- Price variance alerts
- New product notifications
- Quality issue reports

## Testing Strategy

### Test Data Requirements
- Sample invoices from different periods
- Various product types and categories
- Different invoice formats
- Edge cases and exceptions

### Validation Tests
- Price variance detection
- Unit conversion accuracy
- Product matching reliability
- Data integrity checks

## Performance Considerations

### Processing Speed
- Batch processing for multiple invoices
- Parallel processing where possible
- Caching for frequently accessed data
- Database optimization for large datasets

### Storage Requirements
- Archive original invoice files
- Maintain audit trails
- Backup processed data
- Compress historical records

## Security and Compliance

### Data Protection
- Secure file upload and storage
- Access control for sensitive data
- Audit logging for all changes
- Encryption for stored documents

### Financial Compliance
- Maintain invoice audit trails
- Support tax reporting requirements
- Enable financial reconciliation
- Provide detailed transaction history

## Future Enhancements

### Advanced Features
1. **Email Integration**: Process invoices from email
2. **Mobile Capture**: Photo-based invoice processing
3. **Supplier Portal**: Direct electronic invoicing
4. **Analytics Dashboard**: Invoice processing metrics
5. **Predictive Pricing**: Market trend analysis

### Integration Opportunities
- Accounting system integration
- Bank reconciliation automation
- Supplier performance tracking
- Procurement optimization

---

This analysis provides the foundation for implementing robust invoice import functionality that integrates seamlessly with the existing inventory management system while maintaining data integrity and business rule compliance.
