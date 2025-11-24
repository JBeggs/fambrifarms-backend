"""
Intelligent Procurement Services for Fambri Farms
Handles market purchase predictions, buffer calculations, and recipe breakdowns
"""

from django.db.models import Sum, Q, F
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Tuple
import logging

from .models import Product, ProcurementBuffer, MarketProcurementRecommendation, MarketProcurementItem, Recipe
from orders.models import Order, OrderItem
from inventory.models import FinishedInventory, MarketPrice
from suppliers.models import Supplier

logger = logging.getLogger(__name__)

class ProcurementIntelligenceService:
    """
    Core service for intelligent market procurement recommendations
    """
    
    def __init__(self):
        self.tshwane_market = None
        try:
            # Ensure supplier exists or create it
            self.tshwane_market, created = Supplier.objects.get_or_create(
                name='Tshwane Fresh Produce Market',
                defaults={
                    'contact_person': 'Market Manager',
                    'phone': '+27 12 358 8000',
                    'email': 'info@tshwanemarket.co.za',
                    'address': 'Tshwane Fresh Produce Market, Pretoria',
                    'supplier_type': 'market',
                    'is_active': True
                }
            )
            if created:
                logger.info("Created Tshwane Fresh Produce Market supplier")
            else:
                logger.info("Using existing Tshwane Fresh Produce Market supplier")
        except Exception as e:
            logger.error(f"Error setting up Tshwane Market supplier: {e}")
            # Continue without supplier - system will still work but without supplier-specific features
    
    def generate_market_recommendation(self, for_date: datetime.date = None, use_historical_dates: bool = True) -> MarketProcurementRecommendation:
        """
        Generate intelligent market procurement recommendation based on:
        1. Current stock levels
        2. Pending orders (next 3-5 days)
        3. Historical patterns
        4. Recipe requirements
        5. Wastage/spoilage buffers
        
        Args:
            for_date: Target date for recommendation (defaults to today or latest order date)
            use_historical_dates: If True, use latest order date for historical analysis
        """
        if not for_date:
            if use_historical_dates:
                # Use LATEST order date from recent orders for historical analysis
                # This prevents getting stuck on old dates
                from orders.models import Order
                recent_orders = Order.objects.filter(
                    status__in=['confirmed', 'processing', 'received']
                ).order_by('-order_date')[:10]  # Changed to -order_date for LATEST first
                
                if recent_orders.exists():
                    for_date = recent_orders.first().order_date
                    logger.info(f"Using latest historical date from recent order: {for_date}")
                else:
                    for_date = timezone.now().date()
                    logger.info(f"No orders found, using current date: {for_date}")
            else:
                for_date = timezone.now().date()
        
        logger.info(f"Generating market recommendation for {for_date}")
        
        # Create recommendation record
        recommendation = MarketProcurementRecommendation.objects.create(
            for_date=for_date,
            status='pending'
        )
        
        # Analyze requirements
        analysis_data = {
            'analysis_date': for_date.isoformat(),
            'upcoming_orders': [],
            'stock_analysis': {},
            'recipe_breakdowns': {},
            'buffer_calculations': {}
        }
        
        # 1. Get upcoming orders (next 5 days)
        upcoming_orders = self._get_upcoming_orders(for_date)
        analysis_data['upcoming_orders'] = [
            {
                'order_id': order.id,
                'customer': order.restaurant.get_full_name() if order.restaurant else 'Unknown Customer',
                'delivery_date': order.delivery_date.isoformat(),
                'total_value': float(order.total_amount)
            }
            for order in upcoming_orders
        ]
        
        # 2. Calculate product requirements
        product_requirements = self._calculate_product_requirements(upcoming_orders)
        
        # 3. Analyze current stock
        stock_analysis = self._analyze_current_stock(product_requirements)
        analysis_data['stock_analysis'] = stock_analysis
        
        # 4. Generate procurement items
        total_cost = Decimal('0.00')
        for product_id, requirement_data in product_requirements.items():
            try:
                product = Product.objects.get(id=product_id)
                
                # Get or create procurement buffer
                buffer, created = ProcurementBuffer.objects.get_or_create(
                    product=product,
                    defaults=self._get_default_buffer_settings(product)
                )
                
                # Calculate needed quantity
                needed_qty = float(requirement_data['total_needed'])
                current_stock = stock_analysis.get(str(product_id), {}).get('current_stock', 0)
                net_needed = max(0, needed_qty - current_stock)
                
                if net_needed > 0:
                    # Calculate market quantity with buffers
                    buffer_calc = buffer.calculate_market_quantity(net_needed)
                    
                    # Get estimated price
                    estimated_price = self._get_estimated_market_price(product)
                    item_cost = buffer_calc['market_quantity'] * float(estimated_price)
                    
                    # Create procurement item
                    procurement_item = MarketProcurementItem.objects.create(
                        recommendation=recommendation,
                        product=product,
                        needed_quantity=net_needed,
                        recommended_quantity=buffer_calc['market_quantity'],
                        estimated_unit_price=estimated_price,
                        estimated_total_cost=item_cost,
                        reasoning=self._generate_reasoning(requirement_data, buffer_calc, current_stock),
                        priority=self._determine_priority(current_stock, needed_qty, product),
                        source_orders=requirement_data['source_orders']
                    )
                    
                    total_cost += Decimal(str(item_cost))
                    
                    # Store buffer calculation in analysis
                    analysis_data['buffer_calculations'][str(product_id)] = {
                        'needed_quantity': float(net_needed),
                        'buffer_rate': float(buffer.total_buffer_rate),
                        'market_quantity': float(buffer_calc['market_quantity']),
                        'market_packs': buffer_calc['market_packs'],
                        'seasonal_multiplier': buffer_calc['seasonal_multiplier']
                    }
                    
            except Product.DoesNotExist:
                logger.error(f"Product {product_id} not found during procurement analysis")
                continue
        
        # Update recommendation totals
        recommendation.total_estimated_cost = total_cost
        recommendation.analysis_data = analysis_data
        recommendation.save()
        
        logger.info(f"Generated recommendation {recommendation.id} with {recommendation.items.count()} items, total cost R{total_cost}")
        
        return recommendation
    
    def _get_upcoming_orders(self, from_date: datetime.date, days_ahead: int = 5) -> List[Order]:
        """Get orders for the next few days or recent orders that need procurement"""
        end_date = from_date + timedelta(days=days_ahead)
        
        # First try to get future orders
        future_orders = Order.objects.filter(
            delivery_date__gte=from_date,
            delivery_date__lte=end_date,
            status__in=['confirmed', 'processing', 'received']  # Include received orderspython manage.py seed_whatsapp_messages --day Tuesday_27_08_2025python manage.py seed_whatsapp_messages --day Tuesday_27_08_2025
        ).prefetch_related('items__product')
        
        # If no future orders, get recent orders (last 30 days) for procurement planning
        if not future_orders.exists():
            recent_start = from_date - timedelta(days=30)
            recent_orders = Order.objects.filter(
                delivery_date__gte=recent_start,
                status__in=['confirmed', 'processing', 'received']
            ).prefetch_related('items__product')
            
            logger.info(f"No future orders found, using {recent_orders.count()} recent orders for procurement planning")
            return list(recent_orders)
        
        return list(future_orders)
    
    def _calculate_product_requirements(self, orders: List[Order]) -> Dict:
        """Calculate total product requirements from orders, including recipe breakdowns"""
        requirements = {}
        
        for order in orders:
            for item in order.items.all():
                product = item.product
                quantity_needed = item.quantity
                
                # Check if product has a recipe (composite product like veggie boxes)
                if hasattr(product, 'product_recipe'):
                    recipe = product.product_recipe
                    # Break down recipe into component ingredients
                    for ingredient_data in recipe.ingredients:
                        ingredient_id = ingredient_data.get('product_id')
                        quantity = Decimal(str(ingredient_data.get('quantity', 0)))
                        
                        # Fetch product to get unit and extract packet size
                        try:
                            ingredient_product = Product.objects.get(id=ingredient_id)
                            unit = ingredient_product.unit
                            
                            # Extract packet size from product name if available
                            try:
                                from whatsapp.services import extract_package_size
                                packet_size_info = extract_package_size(ingredient_product.name)
                                
                                # Calculate ingredient quantity
                                if packet_size_info and unit in ['packet', 'bag', 'box', 'punnet']:
                                    # Product has packet size in name (e.g., "Carrots (250g packet)")
                                    packet_size_value = packet_size_info['size']
                                    packet_size_unit = packet_size_info['original_unit']
                                    
                                    # Convert packet size to kg for calculations
                                    if packet_size_unit == 'g':
                                        packet_size_kg = packet_size_value / 1000
                                    elif packet_size_unit == 'kg':
                                        packet_size_kg = packet_size_value
                                    else:
                                        # For ml/l, assume 1:1 with kg for simplicity
                                        packet_size_kg = packet_size_value
                                    
                                    # Calculate: (packet_count × packet_size) × order_qty
                                    ingredient_qty = quantity * packet_size_kg
                                else:
                                    # No packet size in product name, use quantity as-is
                                    ingredient_qty = quantity
                                    
                            except Exception as e:
                                # If extraction fails, use quantity as-is
                                logger.debug(f"Could not extract packet size for product {ingredient_id}: {e}")
                                ingredient_qty = quantity
                                
                        except Product.DoesNotExist:
                            # Fallback: use quantity as-is if product not found
                            logger.warning(f"Product {ingredient_id} not found, using quantity as-is")
                            ingredient_qty = quantity
                        
                        # Calculate total ingredient needed (recipe qty * order qty)
                        total_ingredient_needed = ingredient_qty * quantity_needed
                        
                        if ingredient_id not in requirements:
                            requirements[ingredient_id] = {
                                'total_needed': Decimal('0'),
                                'source_orders': [],
                                'recipe_breakdown': []
                            }
                        
                        requirements[ingredient_id]['total_needed'] += total_ingredient_needed
                        requirements[ingredient_id]['source_orders'].append(order.id)
                        requirements[ingredient_id]['recipe_breakdown'].append({
                            'parent_product': product.name,
                            'order_id': order.id,
                            'recipe_qty': float(ingredient_qty),
                            'order_qty': float(quantity_needed),
                            'total_needed': float(total_ingredient_needed)
                        })
                else:
                    # Simple product - direct requirement
                    product_id = product.id
                    if product_id not in requirements:
                        requirements[product_id] = {
                            'total_needed': Decimal('0'),
                            'source_orders': [],
                            'recipe_breakdown': []
                        }
                    
                    requirements[product_id]['total_needed'] += quantity_needed
                    requirements[product_id]['source_orders'].append(order.id)
        
        return requirements
    
    def _analyze_current_stock(self, requirements: Dict) -> Dict:
        """Analyze current stock levels for required products"""
        from whatsapp.services import calculate_stock_count_and_weight
        
        stock_analysis = {}
        
        for product_id in requirements.keys():
            try:
                inventory = FinishedInventory.objects.get(product_id=product_id)
                
                # Calculate stock count and weight to get accurate stock level
                stock_calc = calculate_stock_count_and_weight(
                    inventory.available_quantity,
                    inventory.product.unit,
                    None  # packaging_size not available here
                )
                
                # Use count for discrete units, kg for weight units, fallback to available_quantity
                current_stock = (
                    stock_calc.get('available_quantity_count', 0) if not stock_calc.get('stock_stored_in_kg', False)
                    else stock_calc.get('available_quantity_kg', 0)
                ) or float(inventory.available_quantity or 0)
                
                minimum_stock = float(inventory.minimum_level or 0)
                
                stock_analysis[str(product_id)] = {
                    'current_stock': current_stock,
                    'minimum_stock': minimum_stock,
                    'is_low_stock': current_stock <= minimum_stock,
                    'is_out_of_stock': current_stock <= 0
                }
            except FinishedInventory.DoesNotExist:
                stock_analysis[str(product_id)] = {
                    'current_stock': 0,
                    'minimum_stock': 0,
                    'is_low_stock': True,
                    'is_out_of_stock': True
                }
        
        return stock_analysis
    
    def _get_default_buffer_settings(self, product: Product) -> Dict:
        """Get default buffer settings based on product type and business settings"""
        from .models_business_settings import BusinessSettings
        
        # Get business settings
        business_settings = BusinessSettings.get_settings()
        
        # Start with global defaults
        defaults = {
            'spoilage_rate': business_settings.default_spoilage_rate,
            'cutting_waste_rate': business_settings.default_cutting_waste_rate,
            'quality_rejection_rate': business_settings.default_quality_rejection_rate,
            'market_pack_size': business_settings.default_market_pack_size,
            'market_pack_unit': 'kg',
            'is_seasonal': False,
            'peak_season_months': [],
            'peak_season_buffer_multiplier': business_settings.default_peak_season_multiplier
        }
        
        # Override with department-specific settings if available
        if product.department and business_settings.department_buffer_settings:
            dept_settings = business_settings.department_buffer_settings.get(product.department.name)
            if dept_settings:
                for key, value in dept_settings.items():
                    if key in ['spoilage_rate', 'cutting_waste_rate', 'quality_rejection_rate', 
                              'market_pack_size', 'peak_season_buffer_multiplier']:
                        defaults[key] = Decimal(str(value))
                    else:
                        defaults[key] = value
        
        return defaults
    
    def _get_estimated_market_price(self, product: Product) -> Decimal:
        """Get estimated market price for product with supplier priority"""
        try:
            # PRIORITY 1: Check Fambri Internal first (preferred supplier)
            fambri_supplier = self._get_fambri_internal_supplier()
            if fambri_supplier:
                fambri_product = product.supplier_products.filter(supplier=fambri_supplier).first()
                if fambri_product and fambri_product.is_available and fambri_product.stock_quantity > 0:
                    return fambri_product.supplier_price
            
            # PRIORITY 2: Check other suppliers if Fambri not available
            other_suppliers = product.supplier_products.filter(
                is_available=True,
                stock_quantity__gt=0
            ).exclude(supplier=fambri_supplier).order_by('supplier_price')
            
            if other_suppliers.exists():
                return other_suppliers.first().supplier_price
            
            # FALLBACK: Use product's base price with wholesale discount (70% of retail)
            if product.price:
                return product.price * Decimal('0.7')  # 30% wholesale discount
            
            # Final fallback - estimate based on department
            return self._estimate_price_by_department(product)
            
        except Exception as e:
            logger.warning(f"Could not get market price for {product.name}: {e}")
            return Decimal('10.00')  # Safe fallback
    
    def _get_fambri_internal_supplier(self):
        """Get Fambri Farms Internal supplier"""
        try:
            from suppliers.models import Supplier
            return Supplier.objects.filter(name__icontains='Fambri').first()
        except Exception:
            return None
    
    def get_supplier_recommendations(self, product: Product, quantity_needed: Decimal) -> List[Dict]:
        """
        Get supplier recommendations with Fambri Internal priority
        Returns list of suppliers with pricing and availability info
        """
        recommendations = []
        fambri_supplier = self._get_fambri_internal_supplier()
        
        # Get all available suppliers for this product
        supplier_products = product.supplier_products.filter(
            is_available=True
        ).select_related('supplier').order_by('supplier_price')
        
        for sp in supplier_products:
            # Calculate if supplier can fulfill the order
            can_fulfill_full_order = (sp.stock_quantity or 0) >= quantity_needed
            available_quantity = min(sp.stock_quantity or 0, quantity_needed)
            
            # Determine priority
            is_fambri = sp.supplier == fambri_supplier
            priority = 1 if is_fambri else 2
            
            # Calculate total cost
            total_cost = sp.supplier_price * available_quantity
            
            recommendation = {
                'supplier_id': sp.supplier.id,
                'supplier_name': sp.supplier.name,
                'supplier_type': 'internal' if is_fambri else 'external',
                'priority': priority,
                'unit_price': float(sp.supplier_price),
                'available_quantity': float(available_quantity),
                'can_fulfill_full_order': can_fulfill_full_order,
                'total_cost': float(total_cost),
                'lead_time_days': sp.get_effective_lead_time(),
                'quality_rating': float(sp.quality_rating or 0),
                'minimum_order_quantity': sp.minimum_order_quantity or 1,
                'stock_quantity': sp.stock_quantity or 0,
                'last_order_date': sp.last_order_date.isoformat() if sp.last_order_date else None,
            }
            
            recommendations.append(recommendation)
        
        # Sort by priority (Fambri first), then by price
        recommendations.sort(key=lambda x: (x['priority'], x['unit_price']))
        
        return recommendations
    
    def calculate_optimal_supplier_split(self, product: Product, quantity_needed: Decimal) -> Dict:
        """
        Calculate optimal supplier split for a product order
        Returns the best combination of suppliers to fulfill the order
        """
        recommendations = self.get_supplier_recommendations(product, quantity_needed)
        
        if not recommendations:
            return {
                'success': False,
                'error': 'No suppliers available for this product',
                'product_name': product.name,
                'quantity_needed': float(quantity_needed)
            }
        
        # Try single supplier first (preferred)
        for rec in recommendations:
            if rec['can_fulfill_full_order']:
                return {
                    'success': True,
                    'strategy': 'single_supplier',
                    'product_name': product.name,
                    'quantity_needed': float(quantity_needed),
                    'suppliers': [rec],
                    'total_cost': rec['total_cost'],
                    'cost_per_unit': rec['unit_price'],
                    'lead_time_days': rec['lead_time_days'],
                    'quality_score': rec['quality_rating']
                }
        
        # Multi-supplier optimization needed
        return self._calculate_multi_supplier_split(product, quantity_needed, recommendations)
    
    def _calculate_multi_supplier_split(self, product: Product, quantity_needed: Decimal, recommendations: List[Dict]) -> Dict:
        """
        Calculate optimal multi-supplier split using greedy algorithm with Fambri priority
        """
        remaining_quantity = quantity_needed
        selected_suppliers = []
        total_cost = Decimal('0.00')
        
        # Sort by priority (Fambri first), then by price
        sorted_suppliers = sorted(recommendations, key=lambda x: (x['priority'], x['unit_price']))
        
        for supplier in sorted_suppliers:
            if remaining_quantity <= 0:
                break
                
            available_qty = Decimal(str(supplier['available_quantity']))
            if available_qty <= 0:
                continue
            
            # Take what we can from this supplier
            qty_from_supplier = min(remaining_quantity, available_qty)
            supplier_cost = Decimal(str(supplier['unit_price'])) * qty_from_supplier
            
            selected_suppliers.append({
                'supplier_id': supplier['supplier_id'],
                'supplier_name': supplier['supplier_name'],
                'supplier_type': supplier['supplier_type'],
                'priority': supplier['priority'],
                'quantity': float(qty_from_supplier),
                'unit_price': supplier['unit_price'],
                'total_cost': float(supplier_cost),
                'lead_time_days': supplier['lead_time_days'],
                'quality_rating': supplier['quality_rating'],
                'percentage_of_order': float((qty_from_supplier / quantity_needed) * 100)
            })
            
            total_cost += supplier_cost
            remaining_quantity -= qty_from_supplier
        
        # Calculate results
        fulfilled_quantity = quantity_needed - remaining_quantity
        fulfillment_rate = (fulfilled_quantity / quantity_needed) * 100
        
        # Calculate weighted averages
        total_fulfilled = sum(s['quantity'] for s in selected_suppliers)
        avg_price = float(total_cost / fulfilled_quantity) if fulfilled_quantity > 0 else 0
        avg_lead_time = sum(s['lead_time_days'] * s['quantity'] for s in selected_suppliers) / total_fulfilled if total_fulfilled > 0 else 0
        avg_quality = sum((s['quality_rating'] or 0) * s['quantity'] for s in selected_suppliers) / total_fulfilled if total_fulfilled > 0 else 0
        
        return {
            'success': fulfillment_rate >= 100,
            'strategy': 'multi_supplier',
            'product_name': product.name,
            'quantity_needed': float(quantity_needed),
            'quantity_fulfilled': float(fulfilled_quantity),
            'quantity_shortfall': float(remaining_quantity),
            'fulfillment_rate': round(fulfillment_rate, 1),
            'suppliers': selected_suppliers,
            'supplier_count': len(selected_suppliers),
            'total_cost': float(total_cost),
            'cost_per_unit': avg_price,
            'weighted_avg_lead_time': round(avg_lead_time, 1),
            'weighted_avg_quality': round(avg_quality, 2),
            'fambri_percentage': sum(s['percentage_of_order'] for s in selected_suppliers if s['supplier_type'] == 'internal'),
            'external_percentage': sum(s['percentage_of_order'] for s in selected_suppliers if s['supplier_type'] == 'external'),
            'cost_breakdown': {
                'fambri_cost': sum(s['total_cost'] for s in selected_suppliers if s['supplier_type'] == 'internal'),
                'external_cost': sum(s['total_cost'] for s in selected_suppliers if s['supplier_type'] == 'external')
            }
        }
    
    def calculate_order_supplier_optimization(self, order_items: List[Dict]) -> Dict:
        """
        Calculate optimal supplier split for an entire order
        order_items: [{'product_id': int, 'quantity': Decimal}, ...]
        """
        results = {
            'success': True,
            'total_items': len(order_items),
            'items_processed': 0,
            'items_fully_fulfilled': 0,
            'items_partially_fulfilled': 0,
            'items_unfulfilled': 0,
            'total_cost': 0.0,
            'total_fambri_cost': 0.0,
            'total_external_cost': 0.0,
            'fambri_percentage': 0.0,
            'external_percentage': 0.0,
            'supplier_summary': {},
            'item_details': [],
            'procurement_recommendations': []
        }
        
        for item in order_items:
            try:
                product = Product.objects.get(id=item['product_id'])
                quantity = Decimal(str(item['quantity']))
                
                # Calculate optimal split for this item
                split_result = self.calculate_optimal_supplier_split(product, quantity)
                
                results['items_processed'] += 1
                results['total_cost'] += split_result.get('total_cost', 0)
                
                if split_result['success']:
                    if split_result.get('fulfillment_rate', 0) >= 100:
                        results['items_fully_fulfilled'] += 1
                    else:
                        results['items_partially_fulfilled'] += 1
                else:
                    results['items_unfulfilled'] += 1
                
                # Add to supplier summary
                for supplier_info in split_result.get('suppliers', []):
                    supplier_name = supplier_info['supplier_name']
                    if supplier_name not in results['supplier_summary']:
                        results['supplier_summary'][supplier_name] = {
                            'supplier_type': supplier_info['supplier_type'],
                            'total_cost': 0.0,
                            'item_count': 0,
                            'total_quantity': 0.0,
                            'avg_quality': 0.0,
                            'avg_lead_time': 0.0
                        }
                    
                    summary = results['supplier_summary'][supplier_name]
                    summary['total_cost'] += supplier_info['total_cost']
                    summary['item_count'] += 1
                    summary['total_quantity'] += supplier_info['quantity']
                    summary['avg_quality'] = (summary['avg_quality'] + supplier_info['quality_rating']) / 2
                    summary['avg_lead_time'] = (summary['avg_lead_time'] + supplier_info['lead_time_days']) / 2
                
                # Track Fambri vs External costs
                fambri_cost = split_result.get('cost_breakdown', {}).get('fambri_cost', 0)
                external_cost = split_result.get('cost_breakdown', {}).get('external_cost', 0)
                results['total_fambri_cost'] += fambri_cost
                results['total_external_cost'] += external_cost
                
                results['item_details'].append(split_result)
                
            except Product.DoesNotExist:
                results['success'] = False
                results['item_details'].append({
                    'success': False,
                    'error': f'Product with ID {item["product_id"]} not found',
                    'product_id': item['product_id'],
                    'quantity_needed': float(item['quantity'])
                })
            except Exception as e:
                results['success'] = False
                results['item_details'].append({
                    'success': False,
                    'error': str(e),
                    'product_id': item.get('product_id'),
                    'quantity_needed': float(item.get('quantity', 0))
                })
        
        # Calculate final percentages
        if results['total_cost'] > 0:
            results['fambri_percentage'] = round((results['total_fambri_cost'] / results['total_cost']) * 100, 1)
            results['external_percentage'] = round((results['total_external_cost'] / results['total_cost']) * 100, 1)
        
        # Generate procurement recommendations
        results['procurement_recommendations'] = self._generate_procurement_recommendations(results)
        
        return results
    
    def _generate_procurement_recommendations(self, order_results: Dict) -> List[Dict]:
        """Generate actionable procurement recommendations based on order analysis"""
        recommendations = []
        
        # Recommendation 1: Fambri utilization
        fambri_pct = order_results.get('fambri_percentage', 0)
        if fambri_pct < 70:
            recommendations.append({
                'type': 'fambri_utilization',
                'priority': 'high',
                'title': 'Low Fambri Internal Utilization',
                'description': f'Only {fambri_pct}% of order from internal stock. Consider increasing Fambri inventory.',
                'action': 'Review internal stock levels and production capacity'
            })
        elif fambri_pct > 90:
            recommendations.append({
                'type': 'fambri_utilization',
                'priority': 'low',
                'title': 'Excellent Fambri Utilization',
                'description': f'{fambri_pct}% of order fulfilled internally. Great cost efficiency!',
                'action': 'Maintain current stock levels'
            })
        
        # Recommendation 2: Unfulfilled items
        unfulfilled = order_results.get('items_unfulfilled', 0)
        if unfulfilled > 0:
            recommendations.append({
                'type': 'supply_shortage',
                'priority': 'urgent',
                'title': f'{unfulfilled} Items Cannot Be Fulfilled',
                'description': 'Some items have no available suppliers or insufficient stock.',
                'action': 'Contact suppliers immediately or find alternative products'
            })
        
        # Recommendation 3: Supplier diversification
        supplier_count = len(order_results.get('supplier_summary', {}))
        if supplier_count > 3:
            recommendations.append({
                'type': 'supplier_complexity',
                'priority': 'medium',
                'title': f'Order Requires {supplier_count} Suppliers',
                'description': 'Multiple suppliers increase coordination complexity.',
                'action': 'Consider consolidating with fewer suppliers if possible'
            })
        
        # Recommendation 4: Cost optimization
        total_cost = order_results.get('total_cost', 0)
        if total_cost > 1000:
            recommendations.append({
                'type': 'cost_optimization',
                'priority': 'medium',
                'title': 'Large Order - Review Bulk Discounts',
                'description': f'Order total: R{total_cost:.2f}. May qualify for bulk pricing.',
                'action': 'Negotiate bulk discounts with primary suppliers'
            })
        
        return recommendations
    
    def _estimate_price_by_department(self, product: Product) -> Decimal:
        """Estimate price based on product department"""
        if not product.department:
            return Decimal('15.00')
        
        dept_name = product.department.name.lower()
        if 'vegetable' in dept_name:
            return Decimal('12.00')
        elif 'fruit' in dept_name:
            return Decimal('18.00')
        elif 'herb' in dept_name or 'spice' in dept_name:
            return Decimal('25.00')
        elif 'mushroom' in dept_name:
            return Decimal('35.00')
        else:
            return Decimal('15.00')
    
    def _generate_reasoning(self, requirement_data: Dict, buffer_calc: Dict, current_stock: float) -> str:
        """Generate human-readable reasoning for procurement recommendation"""
        needed = float(requirement_data['total_needed'])
        recommended = buffer_calc['market_quantity']
        buffer_rate = buffer_calc['buffer_rate']
        
        reasoning_parts = []
        
        # Stock situation
        if current_stock <= 0:
            reasoning_parts.append("🔴 OUT OF STOCK")
        elif current_stock < needed:
            shortage = needed - current_stock
            reasoning_parts.append(f"📉 Short by {shortage:.1f} units")
        
        # Order requirements
        if requirement_data['source_orders']:
            order_count = len(set(requirement_data['source_orders']))
            reasoning_parts.append(f"📋 {order_count} upcoming orders need {needed:.1f} units")
        
        # Buffer explanation
        if buffer_rate > 0:
            reasoning_parts.append(f"🛡️ {buffer_rate:.1%} buffer for spoilage/waste")
        
        # Market packs
        if buffer_calc.get('market_packs', 1) > 1:
            reasoning_parts.append(f"📦 {buffer_calc['market_packs']} market packs")
        
        # Seasonal adjustment
        if buffer_calc.get('seasonal_multiplier', 1.0) > 1.0:
            reasoning_parts.append(f"🌱 {buffer_calc['seasonal_multiplier']:.1f}x seasonal adjustment")
        
        return " • ".join(reasoning_parts)
    
    def _determine_priority(self, current_stock: float, needed_qty: Decimal, product: Product) -> str:
        """Determine priority level for procurement item"""
        if current_stock <= 0:
            return 'critical'
        elif current_stock < needed_qty:
            return 'high'
        elif hasattr(product, 'procurement_buffer') and current_stock <= product.minimum_stock:
            return 'medium'
        else:
            return 'low'

class RecipeService:
    """
    Service for managing product recipes and ingredient breakdowns
    """
    
    @staticmethod
    def create_veggie_box_recipes():
        """Create sample recipes for veggie box products"""
        
        # Real veggie box recipes based on SHALLOME stock data
        veggie_box_recipes = [
            {
                'product_name': 'Small Veggie Box',
                'ingredients': [
                    # Core vegetables - good variety for small families
                    {'product_name': 'Potatoes', 'quantity': 1.0, 'unit': 'bag'},  # 1 bag potatoes
                    {'product_name': 'Carrots (1kg Packed)', 'quantity': 1.0, 'unit': 'kg'},  # 1kg carrots
                    {'product_name': 'White Onions', 'quantity': 0.5, 'unit': 'kg'},  # 500g onions
                    {'product_name': 'Tomatoes', 'quantity': 1.0, 'unit': 'kg'},  # 1kg tomatoes
                    {'product_name': 'Green Peppers', 'quantity': 0.5, 'unit': 'kg'},  # 500g peppers
                    {'product_name': 'Lettuce Head', 'quantity': 1.0, 'unit': 'head'},  # 1 lettuce head
                    {'product_name': 'Cucumber', 'quantity': 2.0, 'unit': 'each'},  # 2 cucumbers
                    {'product_name': 'Green Beans', 'quantity': 0.5, 'unit': 'kg'},  # 500g green beans
                    # Fresh herbs for flavor
                    {'product_name': 'Parsley', 'quantity': 1.0, 'unit': 'bunch'},  # 1 bunch parsley
                    {'product_name': 'Coriander', 'quantity': 1.0, 'unit': 'bunch'},  # 1 bunch coriander
                ],
                'instructions': 'Assemble fresh seasonal vegetables in small eco-friendly box. Perfect for 2-3 people for a week. Include variety card with storage tips.',
                'prep_time_minutes': 12,
                'yield_quantity': 1,
                'yield_unit': 'box'
            },
            {
                'product_name': 'Large Veggie Box',
                'ingredients': [
                    # Core vegetables - larger quantities for families
                    {'product_name': 'Potatoes', 'quantity': 2.0, 'unit': 'bag'},  # 2 bags potatoes
                    {'product_name': 'Carrots (1kg Packed)', 'quantity': 2.0, 'unit': 'kg'},  # 2kg carrots
                    {'product_name': 'White Onions', 'quantity': 1.0, 'unit': 'kg'},  # 1kg onions
                    {'product_name': 'Red Onions', 'quantity': 0.5, 'unit': 'kg'},  # 500g red onions
                    {'product_name': 'Tomatoes', 'quantity': 2.0, 'unit': 'kg'},  # 2kg tomatoes
                    {'product_name': 'Green Peppers', 'quantity': 0.5, 'unit': 'kg'},  # 500g green peppers
                    {'product_name': 'Red Peppers', 'quantity': 0.5, 'unit': 'kg'},  # 500g red peppers
                    {'product_name': 'Yellow Peppers', 'quantity': 0.5, 'unit': 'kg'},  # 500g yellow peppers
                    # Leafy greens and salads
                    {'product_name': 'Lettuce Head', 'quantity': 2.0, 'unit': 'head'},  # 2 lettuce heads
                    {'product_name': 'Mixed Lettuce', 'quantity': 1.0, 'unit': 'kg'},  # 1kg mixed lettuce
                    {'product_name': 'Baby Spinach', 'quantity': 0.5, 'unit': 'kg'},  # 500g baby spinach
                    # Additional vegetables
                    {'product_name': 'Cucumber', 'quantity': 4.0, 'unit': 'each'},  # 4 cucumbers
                    {'product_name': 'Green Beans', 'quantity': 1.0, 'unit': 'kg'},  # 1kg green beans
                    {'product_name': 'Baby Marrow', 'quantity': 1.0, 'unit': 'kg'},  # 1kg baby marrow
                    {'product_name': 'Broccoli', 'quantity': 1.0, 'unit': 'head'},  # 1 broccoli head
                    {'product_name': 'Cauliflower', 'quantity': 1.0, 'unit': 'head'},  # 1 cauliflower head
                    {'product_name': 'Green Cabbage', 'quantity': 1.0, 'unit': 'head'},  # 1 cabbage head
                    {'product_name': 'Sweet Potatoes', 'quantity': 1.0, 'unit': 'kg'},  # 1kg sweet potatoes
                    {'product_name': 'Beetroot', 'quantity': 0.5, 'unit': 'kg'},  # 500g beetroot
                    # Fresh herbs - generous portions
                    {'product_name': 'Parsley', 'quantity': 2.0, 'unit': 'bunch'},  # 2 bunches parsley
                    {'product_name': 'Coriander', 'quantity': 2.0, 'unit': 'bunch'},  # 2 bunches coriander
                    {'product_name': 'Basil', 'quantity': 1.0, 'unit': 'bunch'},  # 1 bunch basil
                    {'product_name': 'Spring Onions', 'quantity': 0.5, 'unit': 'kg'},  # 500g spring onions
                ],
                'instructions': 'Assemble premium selection of fresh seasonal vegetables in large eco-friendly box. Perfect for families of 4-6 people for a week. Include recipe suggestions and storage guide.',
                'prep_time_minutes': 20,
                'yield_quantity': 1,
                'yield_unit': 'box'
            }
        ]
        
        created_recipes = []
        
        for recipe_data in veggie_box_recipes:
            try:
                # Find the main product
                product = Product.objects.get(name=recipe_data['product_name'])
                
                # Convert ingredients to minimal structure (only product_id + quantity)
                # Everything else (product_name, unit, packet_size) is derived from product_id
                ingredients_with_ids = []
                for ingredient in recipe_data['ingredients']:
                    try:
                        # Accept product_id directly (preferred) or look up by name (backward compatibility)
                        if 'product_id' in ingredient:
                            ingredient_product = Product.objects.get(id=ingredient['product_id'])
                        else:
                            # Backward compatibility: look up by name
                            ingredient_product = Product.objects.get(name=ingredient['product_name'])
                        
                        # Minimal structure: only product_id and quantity required
                        ingredient_dict = {
                            'product_id': ingredient_product.id,  # REQUIRED
                            'quantity': ingredient['quantity']     # REQUIRED
                        }
                        
                        # Optional: Store derived fields for convenience (can be recalculated anytime)
                        # These are not required but stored for backward compatibility and display
                        ingredient_dict['product_name'] = ingredient_product.name
                        ingredient_dict['unit'] = ingredient_product.unit
                        
                        # Extract packet size from product name if available
                        try:
                            from whatsapp.services import extract_package_size
                            packet_size_info = extract_package_size(ingredient_product.name)
                            if packet_size_info:
                                # Store packet size info for calculations
                                if packet_size_info['original_unit'] == 'g':
                                    ingredient_dict['packet_size_value'] = float(packet_size_info['size'] * 1000)
                                else:
                                    ingredient_dict['packet_size_value'] = float(packet_size_info['size'])
                                ingredient_dict['packet_size_unit'] = packet_size_info['original_unit']
                        except Exception as e:
                            # If extraction fails, continue without packet size
                            logger.debug(f"Could not extract packet size from '{ingredient_product.name}': {e}")
                        
                        ingredients_with_ids.append(ingredient_dict)
                    except Product.DoesNotExist:
                        product_identifier = ingredient.get('product_id') or ingredient.get('product_name', 'Unknown')
                        logger.warning(f"Ingredient product '{product_identifier}' not found")
                        continue
                
                # Create or update recipe
                recipe, created = Recipe.objects.update_or_create(
                    product=product,
                    defaults={
                        'ingredients': ingredients_with_ids,
                        'instructions': recipe_data['instructions'],
                        'prep_time_minutes': recipe_data['prep_time_minutes'],
                        'yield_quantity': recipe_data['yield_quantity'],
                        'yield_unit': recipe_data['yield_unit']
                    }
                )
                
                created_recipes.append(recipe)
                logger.info(f"{'Created' if created else 'Updated'} recipe for {product.name}")
                
            except Product.DoesNotExist:
                logger.warning(f"Product '{recipe_data['product_name']}' not found for recipe creation")
                continue
        
        return created_recipes
