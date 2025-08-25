from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@api_view(['GET'])
@permission_classes([AllowAny])
def api_overview(request):
    """
    Comprehensive API overview for Fambri Farms backend system
    """
    
    api_endpoints = {
        "base_url": request.build_absolute_uri('/')[:-1],
        "version": "1.0",
        "description": "Fambri Farms - Farm to Restaurant Supply Chain API",
        
        "authentication": {
            "login": "/api/auth/login/",
            "register": "/api/auth/register/",
            "token_refresh": "/api/auth/token/refresh/",
            "user_profile": "/api/auth/profile/"
        },
        
        "products": {
            "list_products": "/api/products/",
            "product_detail": "/api/products/{id}/",
            "departments": "/api/products/departments/",
            "department_detail": "/api/products/departments/{id}/",
        },
        
        "orders": {
            "list_orders": "/api/orders/",
            "order_detail": "/api/orders/{id}/",
            "update_status": "/api/orders/{id}/status/ [PATCH]",
            "order_days": "Mondays and Thursdays only"
        },
        
        "suppliers": {
            "list_suppliers": "/api/suppliers/suppliers/",
            "supplier_detail": "/api/suppliers/suppliers/{id}/",
            "supplier_products": "/api/suppliers/suppliers/{id}/products/",
            "available_products": "/api/suppliers/suppliers/{id}/available_products/",
            "performance_summary": "/api/suppliers/suppliers/performance_summary/",
            
            "supplier_products": "/api/suppliers/supplier-products/",
            "supplier_product_detail": "/api/suppliers/supplier-products/{id}/",
            "low_stock": "/api/suppliers/supplier-products/low_stock/",
            "price_comparison": "/api/suppliers/supplier-products/price_comparison/?product_id={id}",
            "update_stock": "/api/suppliers/supplier-products/{id}/update_stock/ [POST]",
            
            "summary": "/api/suppliers/summary/",
            "best_prices": "/api/suppliers/best-prices/"
        },
        
        "inventory": {
            "dashboard": "/api/inventory/dashboard/",
            "stock_levels": "/api/inventory/stock-levels/",
            
            "units_of_measure": "/api/inventory/units/",
            "unit_detail": "/api/inventory/units/{id}/",
            
            "raw_materials": "/api/inventory/raw-materials/",
            "raw_material_detail": "/api/inventory/raw-materials/{id}/",
            "raw_material_batches": "/api/inventory/raw-materials/{id}/batches/",
            "low_stock_raw": "/api/inventory/raw-materials/low_stock/",
            
            "raw_material_batches": "/api/inventory/raw-material-batches/",
            "batch_detail": "/api/inventory/raw-material-batches/{id}/",
            "expiring_batches": "/api/inventory/raw-material-batches/expiring_soon/",
            
            "production_recipes": "/api/inventory/recipes/",
            "recipe_detail": "/api/inventory/recipes/{id}/",
            "add_ingredient": "/api/inventory/recipes/{id}/add_ingredient/ [POST]",
            "remove_ingredient": "/api/inventory/recipes/{id}/remove_ingredient/ [DELETE]",
            
            "finished_inventory": "/api/inventory/finished-inventory/",
            "inventory_detail": "/api/inventory/finished-inventory/{id}/",
            "low_stock_finished": "/api/inventory/finished-inventory/low_stock/",
            "inventory_summary": "/api/inventory/finished-inventory/summary/",
            
            "production_batches": "/api/inventory/production-batches/",
            "production_batch_detail": "/api/inventory/production-batches/{id}/",
            "start_production": "/api/inventory/production-batches/{id}/start_production/ [POST]",
            "complete_production": "/api/inventory/production-batches/{id}/complete_production/ [POST]",
            
            "stock_movements": "/api/inventory/stock-movements/",
            "movement_detail": "/api/inventory/stock-movements/{id}/",
            
            "alerts": "/api/inventory/alerts/",
            "alert_detail": "/api/inventory/alerts/{id}/",
            "acknowledge_alert": "/api/inventory/alerts/{id}/acknowledge/ [POST]",
            "acknowledge_multiple": "/api/inventory/alerts/acknowledge_multiple/ [POST]",
            
            "actions": {
                "reserve_stock": "/api/inventory/actions/reserve-stock/ [POST]",
                "stock_adjustment": "/api/inventory/actions/stock-adjustment/ [POST]"
            }
        },
        
        "invoices": {
            "list_invoices": "/api/invoices/",
            "invoice_detail": "/api/invoices/{id}/",
            "payment_terms": "Net 30 days",
            "vat_rate": "15%"
        },
        
        "wishlist": {
            "user_wishlist": "/api/wishlist/",
            "add_to_wishlist": "/api/wishlist/add/ [POST]",
            "remove_from_wishlist": "/api/wishlist/remove/{id}/ [DELETE]",
            "convert_to_order": "/api/wishlist/convert-to-order/ [POST]"
        },
        
        "cms": {
            "company_info": "/api/products/company-info/",
            "page_content": "/api/products/page-content/{page}/",
            "business_hours": "/api/products/business-hours/",
            "team_members": "/api/products/team-members/",
            "faqs": "/api/products/faqs/",
            "testimonials": "/api/products/testimonials/"
        },
        
        "business_rules": {
            "order_days": "Orders can only be placed on Mondays and Thursdays",
            "business_hours": {
                "monday_friday": "7:00 AM - 5:00 PM",
                "saturday": "8:00 AM - 2:00 PM", 
                "sunday": "Closed"
            },
            "payment_terms": "Net 30 days",
            "vat_rate": "15%",
            "location": "Hartbeespoort, South Africa",
            "timezone": "Africa/Johannesburg"
        },
        
        "features": {
            "dual_supply_chain": "Supports both direct product suppliers and raw material processing",
            "batch_tracking": "Complete traceability from supplier to customer",
            "production_management": "Recipe-based production with yield tracking",
            "automated_stock_management": "Orders automatically update inventory levels",
            "quality_control": "Supplier ratings and batch quality tracking", 
            "cost_management": "Automatic costing with FIFO/weighted average",
            "alert_system": "Automated notifications for stock levels, expiry, production needs",
            "comprehensive_reporting": "Stock levels, movements, supplier performance"
        },
        
        "filtering_parameters": {
            "common": "?is_active=true&search=keyword",
            "pagination": "?page=1&page_size=20",
            "date_ranges": "?date_from=2024-01-01&date_to=2024-12-31",
            "stock_filters": "?low_stock=true&has_stock=true",
            "price_filters": "?min_price=10&max_price=100"
        },
        
        "response_formats": {
            "list_views": "Paginated with simplified data",
            "detail_views": "Complete object data with relationships",
            "summary_views": "Aggregated statistics and analytics",
            "action_responses": "Success/error with updated object data"
        }
    }
    
    return Response(api_endpoints)
