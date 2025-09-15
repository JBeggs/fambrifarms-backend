# Intelligent Pricing System

## Overview

The Intelligent Pricing System is a comprehensive AI-powered solution that manages market volatility, customer pricing, and business intelligence for restaurant supply operations. It transforms raw market data into intelligent pricing decisions through automated analysis and customer-specific pricing strategies.

## System Architecture

### Core Components

1. **Stock Analysis Engine** - Analyzes customer orders against available inventory
2. **Market Intelligence** - Processes invoice data to track price volatility
3. **Dynamic Pricing Rules** - Customer segment-based pricing strategies
4. **Automated Price Lists** - Generated customer pricing from market data
5. **Business Intelligence** - Comprehensive reporting and analytics

## Phase 1: Stock Analysis Engine

### Models

#### StockAnalysis
```python
class StockAnalysis(models.Model):
    analysis_date = models.DateTimeField(auto_now_add=True)
    order_period_start = models.DateField()  # Monday
    order_period_end = models.DateField()    # Thursday
    total_orders_value = models.DecimalField(max_digits=12, decimal_places=2)
    total_stock_value = models.DecimalField(max_digits=12, decimal_places=2)
    fulfillment_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
```

#### StockAnalysisItem
```python
class StockAnalysisItem(models.Model):
    analysis = models.ForeignKey(StockAnalysis, on_delete=models.CASCADE)
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE)
    total_ordered_quantity = models.DecimalField(max_digits=10, decimal_places=2)
    available_stock_quantity = models.DecimalField(max_digits=10, decimal_places=2)
    shortfall_quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    needs_procurement = models.BooleanField(default=False)
    suggested_order_quantity = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    suggested_supplier = models.ForeignKey('suppliers.Supplier', on_delete=models.SET_NULL, null=True)
```

### API Endpoints

- `GET /api/inventory/stock-analysis/` - List all stock analyses
- `POST /api/inventory/stock-analysis/analyze_current_period/` - Run analysis for current period
- `GET /api/inventory/stock-analysis/{id}/` - Get specific analysis details

### Business Logic

1. **Order Period Analysis**: Analyzes Monday-Thursday customer orders
2. **Stock Comparison**: Compares ordered quantities against available inventory
3. **Shortfall Calculation**: Identifies products needing procurement
4. **Supplier Suggestions**: Recommends optimal suppliers based on historical data

## Phase 2: Market Intelligence System

### Models

#### MarketPrice
```python
class MarketPrice(models.Model):
    supplier_name = models.CharField(max_length=200)
    invoice_date = models.DateField()
    invoice_reference = models.CharField(max_length=100, blank=True)
    product_name = models.CharField(max_length=200)
    matched_product = models.ForeignKey('products.Product', on_delete=models.SET_NULL, null=True)
    unit_price_excl_vat = models.DecimalField(max_digits=10, decimal_places=2)
    vat_amount = models.DecimalField(max_digits=8, decimal_places=2)
    unit_price_incl_vat = models.DecimalField(max_digits=10, decimal_places=2)
    quantity_unit = models.CharField(max_length=50, default="each")
    vat_percentage = models.DecimalField(max_digits=5, decimal_places=2)
```

#### ProcurementRecommendation
```python
class ProcurementRecommendation(models.Model):
    stock_analysis = models.ForeignKey(StockAnalysis, on_delete=models.CASCADE)
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE)
    supplier = models.ForeignKey('suppliers.Supplier', on_delete=models.CASCADE)
    recommended_quantity = models.DecimalField(max_digits=10, decimal_places=2)
    estimated_unit_cost = models.DecimalField(max_digits=10, decimal_places=2)
    estimated_total_cost = models.DecimalField(max_digits=12, decimal_places=2)
    urgency_level = models.CharField(max_length=20, choices=URGENCY_CHOICES)
    recommended_order_date = models.DateField()
```

#### PriceAlert
```python
class PriceAlert(models.Model):
    product_name = models.CharField(max_length=200)
    previous_price = models.DecimalField(max_digits=10, decimal_places=2)
    current_price = models.DecimalField(max_digits=10, decimal_places=2)
    price_change_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    acknowledged = models.BooleanField(default=False)
```

### API Endpoints

- `GET /api/inventory/market-prices/` - List market prices with filtering
- `POST /api/inventory/market-prices/bulk_import/` - Import market data from invoices
- `GET /api/inventory/market-prices/price_trends/` - Get price trend analysis
- `GET /api/inventory/procurement-recommendations/` - List procurement recommendations
- `POST /api/inventory/procurement-recommendations/generate_from_analysis/` - Generate from stock analysis
- `GET /api/inventory/price-alerts/` - List price alerts
- `POST /api/inventory/price-alerts/acknowledge_all/` - Acknowledge all alerts

### Business Logic

1. **Market Data Processing**: Extracts pricing data from invoice images
2. **Price Trend Analysis**: Identifies rising, falling, stable, and volatile trends
3. **Volatility Detection**: Calculates price volatility levels (stable to extremely volatile)
4. **Procurement Intelligence**: Generates smart procurement recommendations
5. **Alert Management**: Monitors significant price changes and notifies users

## Phase 3: Dynamic Price Management System

### Models

#### PricingRule
```python
class PricingRule(models.Model):
    name = models.CharField(max_length=100)
    customer_segment = models.CharField(max_length=50, choices=SEGMENT_CHOICES)
    base_markup_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    volatility_adjustment = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    minimum_margin_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    category_adjustments = models.JSONField(default=dict)
    trend_multiplier = models.DecimalField(max_digits=4, decimal_places=2, default=1.00)
    seasonal_adjustment = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    effective_from = models.DateField()
    effective_until = models.DateField(null=True, blank=True)
```

#### CustomerPriceList
```python
class CustomerPriceList(models.Model):
    customer = models.ForeignKey('accounts.User', on_delete=models.CASCADE)
    pricing_rule = models.ForeignKey(PricingRule, on_delete=models.CASCADE)
    list_name = models.CharField(max_length=200)
    effective_from = models.DateField()
    effective_until = models.DateField()
    based_on_market_data = models.DateField()
    market_data_source = models.CharField(max_length=100, default="Tshwane Market")
    total_products = models.IntegerField(default=0)
    average_markup_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    total_list_value = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
```

#### CustomerPriceListItem
```python
class CustomerPriceListItem(models.Model):
    price_list = models.ForeignKey(CustomerPriceList, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE)
    market_price_excl_vat = models.DecimalField(max_digits=10, decimal_places=2)
    market_price_incl_vat = models.DecimalField(max_digits=10, decimal_places=2)
    markup_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    customer_price_excl_vat = models.DecimalField(max_digits=10, decimal_places=2)
    customer_price_incl_vat = models.DecimalField(max_digits=10, decimal_places=2)
    previous_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    price_change_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    is_volatile = models.BooleanField(default=False)
    is_premium = models.BooleanField(default=False)
```

#### WeeklyPriceReport
```python
class WeeklyPriceReport(models.Model):
    report_week_start = models.DateField()
    report_week_end = models.DateField()
    report_name = models.CharField(max_length=200)
    total_market_prices_analyzed = models.IntegerField(default=0)
    average_market_volatility = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    most_volatile_product = models.CharField(max_length=200, blank=True)
    most_volatile_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    total_price_lists_generated = models.IntegerField(default=0)
    total_customers_affected = models.IntegerField(default=0)
    average_price_increase = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    key_insights = models.JSONField(default=list)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='generating')
```

### API Endpoints

#### Pricing Rules
- `GET /api/inventory/pricing-rules/` - List pricing rules
- `POST /api/inventory/pricing-rules/` - Create pricing rule
- `GET /api/inventory/pricing-rules/{id}/` - Get pricing rule details
- `PUT /api/inventory/pricing-rules/{id}/` - Update pricing rule
- `POST /api/inventory/pricing-rules/{id}/test_markup/` - Test markup calculation

#### Customer Price Lists
- `GET /api/inventory/customer-price-lists/` - List customer price lists
- `POST /api/inventory/customer-price-lists/generate_from_market_data/` - Generate from market data
- `GET /api/inventory/customer-price-lists/{id}/` - Get price list details
- `POST /api/inventory/customer-price-lists/{id}/activate/` - Activate price list
- `POST /api/inventory/customer-price-lists/{id}/send_to_customer/` - Send to customer

#### Weekly Reports
- `GET /api/inventory/weekly-reports/` - List weekly reports
- `POST /api/inventory/weekly-reports/generate_current_week/` - Generate current week report
- `GET /api/inventory/weekly-reports/{id}/` - Get report details

#### Enhanced Market Intelligence
- `GET /api/inventory/enhanced-market-prices/` - Enhanced market price data
- `GET /api/inventory/enhanced-market-prices/volatility_dashboard/` - Volatility dashboard data

### Business Logic

1. **Customer Segmentation**: Premium, Standard, Budget, Wholesale, Retail segments
2. **Dynamic Markup Calculation**: Base markup + volatility adjustment + category adjustments
3. **Price List Generation**: Automated generation from market data using pricing rules
4. **Volatility Management**: Handles extreme price swings (up to 275% tested)
5. **Business Intelligence**: Comprehensive weekly reports with insights and recommendations

## Pricing Calculation Logic

### Standard Pricing Formula
```python
def calculate_customer_price(market_price, pricing_rule, product, volatility_level):
    base_markup = pricing_rule.base_markup_percentage
    volatility_adjustment = pricing_rule.volatility_adjustment if volatility_level == 'volatile' else 0
    category_adjustment = pricing_rule.category_adjustments.get(product.category, 0)
    trend_multiplier = pricing_rule.trend_multiplier
    
    total_markup = (base_markup + volatility_adjustment + category_adjustment) * trend_multiplier
    customer_price = market_price * (1 + total_markup / 100)
    
    # Ensure minimum margin
    minimum_price = market_price * (1 + pricing_rule.minimum_margin_percentage / 100)
    return max(customer_price, minimum_price)
```

### Volatility Levels
- **Stable**: 0-5% price change
- **Volatile**: 5-15% price change
- **Highly Volatile**: 15-30% price change
- **Extremely Volatile**: 30%+ price change

### Customer Segments
- **Premium Restaurants**: Higher markup, premium service
- **Standard Restaurants**: Standard markup, regular service
- **Budget Cafes**: Lower markup, volume-based pricing
- **Wholesale Buyers**: Minimal markup, bulk pricing
- **Retail Customers**: Highest markup, small quantities

## Integration Points

### WhatsApp Integration
- Stock analysis triggered by order processing
- Price alerts sent via WhatsApp notifications
- Customer price lists distributed through WhatsApp

### Order Management
- Stock analysis compares orders against inventory
- Procurement recommendations feed into purchase orders
- Dynamic pricing applied to new orders

### Supplier Management
- Market price data linked to supplier performance
- Procurement recommendations consider supplier reliability
- Price trend analysis informs supplier negotiations

## Performance Metrics

### System Capabilities
- **Market Volatility Handling**: Tested up to 275% price swings
- **Customer Segments**: 5 distinct pricing strategies
- **Automated Processing**: End-to-end automation from market data to customer pricing
- **Real-time Analysis**: Live price volatility monitoring
- **Scalable Architecture**: Handles multiple suppliers and thousands of products

### Business Impact
- **Cost Management**: Volatility-responsive pricing protects margins
- **Customer Segmentation**: Optimized pricing for different customer types
- **Operational Efficiency**: Automated price list generation and distribution
- **Business Intelligence**: Data-driven insights for strategic decisions
- **Profit Optimization**: Intelligent markup strategies maximize profitability

## Future Enhancements

1. **Machine Learning Integration**: Predictive pricing based on historical patterns
2. **Seasonal Adjustments**: Automatic seasonal pricing modifications
3. **Competitor Analysis**: Market positioning based on competitor pricing
4. **Customer Behavior Analytics**: Pricing optimization based on purchase patterns
5. **Supply Chain Integration**: Real-time supplier pricing updates
