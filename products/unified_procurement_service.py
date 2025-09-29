"""
Unified Procurement Service for Fambri Farms
Consolidates all procurement logic into a single, consistent service
Eliminates duplication between ProcurementIntelligenceService and FambriFirstProcurementService
"""

from django.db import transaction
from django.db.models import Sum, Q, F
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
import logging

from .models import Product, ProcurementBuffer, MarketProcurementRecommendation, MarketProcurementItem, Recipe
from orders.models import Order, OrderItem
from inventory.models import FinishedInventory, MarketPrice
from suppliers.models import Supplier, SupplierProduct
from procurement.models import PurchaseOrder, PurchaseOrderItem

logger = logging.getLogger(__name__)

class UnifiedProcurementService:
    """
    Unified procurement service that handles all procurement workflows:
    1. Market recommendations (shopping lists)
    2. Supplier optimization (cost splitting, multi-supplier)
    3. Automated workflows (order-to-PO)
    4. Performance-aware decisions
    """
    
    def __init__(self):
        self.suppliers = self._initialize_suppliers()
        self.fambri_supplier = self.suppliers.get('fambri')
        self.tshwane_market = self.suppliers.get('tshwane_market')
    
    def _initialize_suppliers(self) -> Dict[str, Optional[Supplier]]:
        """Initialize and cache key suppliers"""
        suppliers = {}
        
        try:
            # Fambri Internal (highest priority)
            suppliers['fambri'] = Supplier.objects.filter(name__icontains='Fambri').first()
            
            # Tshwane Market (market fallback)
            suppliers['tshwane_market'], created = Supplier.objects.get_or_create(
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
                
        except Exception as e:
            logger.error(f"Error initializing suppliers: {e}")
            
        return suppliers
    
    # ========================================
    # UNIFIED SUPPLIER LOGIC (NO DUPLICATION)
    # ========================================
    
    def get_supplier_priority_order(self) -> List[Supplier]:
        """Get suppliers in priority order (Fambri first, then others)"""
        suppliers = []
        
        # Priority 1: Fambri Internal
        if self.fambri_supplier:
            suppliers.append(self.fambri_supplier)
        
        # Priority 2: Other active suppliers (excluding Fambri and market)
        other_suppliers = Supplier.objects.filter(
            is_active=True
        ).exclude(
            id__in=[s.id for s in [self.fambri_supplier, self.tshwane_market] if s]
        ).order_by('name')
        
        suppliers.extend(other_suppliers)
        
        # Priority 3: Market (last resort)
        if self.tshwane_market:
            suppliers.append(self.tshwane_market)
            
        return suppliers
    
    def get_best_supplier_for_product(self, product: Product, quantity_needed: Decimal) -> Dict:
        """
        Get the best supplier for a product considering:
        - Fambri-first priority
        - Availability and stock levels
        - Pricing
        - Performance metrics (future enhancement)
        """
        suppliers = self.get_supplier_priority_order()
        best_option = None
        
        for supplier in suppliers:
            # Check if supplier has this product
            supplier_product = product.supplier_products.filter(
                supplier=supplier,
                is_available=True
            ).first()
            
            if not supplier_product:
                continue
            
            # Check stock availability
            available_quantity = supplier_product.stock_quantity or 0
            can_fulfill = available_quantity >= quantity_needed
            
            option = {
                'supplier': supplier,
                'supplier_product': supplier_product,
                'unit_price': supplier_product.supplier_price,
                'available_quantity': available_quantity,
                'can_fulfill_full_order': can_fulfill,
                'fulfillable_quantity': min(available_quantity, quantity_needed),
                'total_cost': supplier_product.supplier_price * min(available_quantity, quantity_needed),
                'lead_time_days': supplier_product.get_effective_lead_time(),
                'quality_rating': supplier_product.quality_rating or Decimal('3.0'),
                'is_fambri': supplier == self.fambri_supplier,
                'priority_score': self._calculate_supplier_priority_score(supplier, supplier_product, can_fulfill)
            }
            
            # Return first viable option (highest priority supplier that can fulfill)
            if can_fulfill:
                return option
            
            # Keep track of best partial option
            if not best_option or option['priority_score'] > best_option['priority_score']:
                best_option = option
        
        # Return best partial option if no one can fulfill completely
        return best_option or self._get_fallback_pricing(product, quantity_needed)
    
    def _calculate_supplier_priority_score(self, supplier: Supplier, supplier_product: SupplierProduct, can_fulfill: bool) -> float:
        """Calculate priority score for supplier selection"""
        score = 0.0
        
        # Fambri gets highest priority
        if supplier == self.fambri_supplier:
            score += 100.0
        
        # Fulfillment capability
        if can_fulfill:
            score += 50.0
        
        # Quality rating
        if supplier_product.quality_rating:
            score += float(supplier_product.quality_rating) * 10
        
        # Price competitiveness (lower price = higher score)
        if supplier_product.supplier_price:
            # Normalize price score (assuming max reasonable price is 1000)
            price_score = max(0, 100 - (float(supplier_product.supplier_price) / 10))
            score += price_score * 0.1
        
        return score
    
    def _get_fallback_pricing(self, product: Product, quantity_needed: Decimal) -> Dict:
        """Fallback pricing when no suppliers are available"""
        estimated_price = product.price * Decimal('0.7') if product.price else Decimal('10.00')
        
        return {
            'supplier': self.tshwane_market,
            'supplier_product': None,
            'unit_price': estimated_price,
            'available_quantity': quantity_needed,  # Assume market can provide
            'can_fulfill_full_order': True,
            'fulfillable_quantity': quantity_needed,
            'total_cost': estimated_price * quantity_needed,
            'lead_time_days': 1,  # Market trip
            'quality_rating': Decimal('3.0'),
            'is_fambri': False,
            'priority_score': 0.0,
            'is_fallback': True
        }
    
    def calculate_optimal_supplier_split(self, product: Product, quantity_needed: Decimal) -> Dict:
        """
        Calculate optimal supplier split for a product when single supplier can't fulfill
        """
        suppliers_data = []
        remaining_quantity = quantity_needed
        total_cost = Decimal('0.00')
        
        # Get all available suppliers for this product
        supplier_products = product.supplier_products.filter(
            is_available=True,
            stock_quantity__gt=0
        ).select_related('supplier').order_by('-supplier__name')  # Fambri first due to naming
        
        # Prioritize Fambri first
        fambri_products = [sp for sp in supplier_products if sp.supplier == self.fambri_supplier]
        other_products = [sp for sp in supplier_products if sp.supplier != self.fambri_supplier]
        ordered_products = fambri_products + other_products
        
        for supplier_product in ordered_products:
            if remaining_quantity <= 0:
                break
                
            available = supplier_product.stock_quantity or 0
            to_order = min(remaining_quantity, available)
            
            if to_order > 0:
                cost = supplier_product.supplier_price * to_order
                total_cost += cost
                
                suppliers_data.append({
                    'supplier_id': supplier_product.supplier.id,
                    'supplier_name': supplier_product.supplier.name,
                    'supplier_type': 'internal' if supplier_product.supplier == self.fambri_supplier else 'external',
                    'quantity': float(to_order),
                    'unit_price': float(supplier_product.supplier_price),
                    'total_cost': float(cost),
                    'quality_rating': float(supplier_product.quality_rating or 3.0),
                    'lead_time_days': supplier_product.get_effective_lead_time(),
                    'is_preferred': supplier_product.supplier == self.fambri_supplier
                })
                
                remaining_quantity -= to_order
        
        # Calculate metrics
        fambri_quantity = sum(s['quantity'] for s in suppliers_data if s['supplier_type'] == 'internal')
        fambri_percentage = (fambri_quantity / float(quantity_needed)) * 100 if quantity_needed > 0 else 0
        
        return {
            'success': True,
            'product_id': product.id,
            'product_name': product.name,
            'total_quantity_needed': float(quantity_needed),
            'total_quantity_available': float(quantity_needed - remaining_quantity),
            'total_cost': float(total_cost),
            'suppliers': suppliers_data,
            'fambri_utilization': round(fambri_percentage, 2),
            'suppliers_required': len(suppliers_data),
            'fully_fulfilled': remaining_quantity <= 0,
            'shortfall': float(remaining_quantity) if remaining_quantity > 0 else 0
        }
    
    # ========================================
    # MARKET RECOMMENDATIONS (UNIFIED)
    # ========================================
    
    def generate_market_recommendation(self, for_date: datetime.date = None, use_historical_dates: bool = True) -> MarketProcurementRecommendation:
        """
        Generate market procurement recommendation using unified supplier logic
        """
        if for_date is None:
            for_date = timezone.now().date()
        
        # Get upcoming orders (same logic as before but with unified supplier awareness)
        upcoming_orders = self._get_upcoming_orders(for_date, use_historical_dates)
        
        # Calculate product requirements with supplier awareness
        product_requirements = self._calculate_product_requirements_with_suppliers(upcoming_orders)
        
        # Analyze current stock
        stock_analysis = self._analyze_current_stock()
        
        # Generate recommendations considering supplier availability
        recommendations = self._generate_supplier_aware_recommendations(
            product_requirements, stock_analysis, for_date
        )
        
        # Create recommendation record
        recommendation = MarketProcurementRecommendation.objects.create(
            for_date=for_date,
            total_estimated_cost=sum(item['estimated_total_cost'] for item in recommendations),
            items_count=len(recommendations),
            reasoning=self._generate_reasoning(recommendations, upcoming_orders),
            karl_time_saving_summary=self._generate_time_saving_summary(recommendations),
            status='pending'
        )
        
        # Create recommendation items with integrated supplier data
        for item_data in recommendations:
            supplier_info = item_data.get('supplier_info')
            
            MarketProcurementItem.objects.create(
                recommendation=recommendation,
                product_id=item_data['product_id'],
                needed_quantity=item_data['needed_quantity'],
                recommended_quantity=item_data['recommended_quantity'],
                estimated_unit_price=item_data['estimated_unit_price'],
                estimated_total_cost=item_data['estimated_total_cost'],
                reasoning=item_data['reasoning'],
                priority=item_data['priority'],
                source_orders=item_data['source_orders'],
                
                # INTEGRATION: Populate supplier fields
                preferred_supplier=supplier_info['supplier'] if supplier_info and not supplier_info.get('is_fallback') else None,
                supplier_product=supplier_info.get('supplier_product') if supplier_info and not supplier_info.get('is_fallback') else None,
                supplier_unit_price=supplier_info['unit_price'] if supplier_info and not supplier_info.get('is_fallback') else None,
                supplier_quality_rating=supplier_info.get('quality_rating') if supplier_info else None,
                supplier_lead_time_days=supplier_info.get('lead_time_days') if supplier_info else None,
                is_fambri_available=supplier_info.get('is_fambri', False) if supplier_info else False,
                procurement_method='fambri' if supplier_info and supplier_info.get('is_fambri') else 'supplier' if supplier_info and not supplier_info.get('is_fallback') else 'market'
            )
        
        return recommendation
    
    def _calculate_product_requirements_with_suppliers(self, upcoming_orders: List[Order]) -> Dict[int, Dict]:
        """Calculate product requirements considering supplier availability"""
        requirements = {}
        
        for order in upcoming_orders:
            for item in order.items.all():
                product_id = item.product.id
                
                if product_id not in requirements:
                    # Get best supplier option for this product
                    supplier_option = self.get_best_supplier_for_product(item.product, item.quantity)
                    
                    requirements[product_id] = {
                        'product': item.product,
                        'total_needed': Decimal('0.00'),
                        'orders': [],
                        'best_supplier': supplier_option,
                        'supplier_available': supplier_option['can_fulfill_full_order'] if supplier_option else False
                    }
                
                requirements[product_id]['total_needed'] += item.quantity
                requirements[product_id]['orders'].append({
                    'order_id': order.id,
                    'order_number': order.order_number,
                    'quantity': item.quantity,
                    'customer': order.customer.business_name if order.customer else 'Unknown'
                })
        
        return requirements
    
    def _generate_supplier_aware_recommendations(self, product_requirements: Dict, stock_analysis: Dict, for_date: datetime.date) -> List[Dict]:
        """Generate recommendations that consider supplier availability"""
        recommendations = []
        
        for product_id, req_data in product_requirements.items():
            product = req_data['product']
            needed_quantity = req_data['total_needed']
            current_stock = stock_analysis.get(product_id, {}).get('current_stock', Decimal('0.00'))
            supplier_option = req_data['best_supplier']
            
            # Calculate net requirement
            net_needed = max(Decimal('0.00'), needed_quantity - current_stock)
            
            if net_needed <= 0:
                continue  # Skip if we have enough stock
            
            # Get buffer settings
            buffer_settings = self._get_default_buffer_settings(product)
            buffer_quantity = net_needed * (buffer_settings['buffer_percentage'] / 100)
            recommended_quantity = net_needed + buffer_quantity
            
            # Use supplier pricing if available, otherwise fallback
            if supplier_option and not supplier_option.get('is_fallback'):
                estimated_price = supplier_option['unit_price']
                supplier_info = f" (via {supplier_option['supplier'].name})"
            else:
                estimated_price = self._estimate_price_by_department(product)
                supplier_info = " (market estimate)"
            
            # Determine priority based on stock level and supplier availability
            if current_stock <= 0:
                priority = 'critical'
            elif current_stock < product.minimum_stock:
                priority = 'high'
            elif not supplier_option or not supplier_option['can_fulfill_full_order']:
                priority = 'medium'  # Supplier constraint
            else:
                priority = 'low'
            
            recommendations.append({
                'product_id': product.id,
                'needed_quantity': net_needed,
                'recommended_quantity': recommended_quantity,
                'estimated_unit_price': estimated_price,
                'estimated_total_cost': estimated_price * recommended_quantity,
                'reasoning': f"Need {net_needed} for upcoming orders, recommend {recommended_quantity} with {buffer_settings['buffer_percentage']}% buffer{supplier_info}",
                'priority': priority,
                'source_orders': [order['order_id'] for order in req_data['orders']],
                'supplier_info': supplier_option
            })
        
        return sorted(recommendations, key=lambda x: {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}[x['priority']])
    
    # ========================================
    # AUTOMATED PROCUREMENT WORKFLOW (UNIFIED)
    # ========================================
    
    def create_procurement_from_order(self, order: Order) -> Dict:
        """
        Create comprehensive procurement analysis for an order using unified logic
        """
        try:
            procurement_plan = {'purchase_orders': []}
            total_cost = Decimal('0.00')
            fambri_cost = Decimal('0.00')
            external_cost = Decimal('0.00')
            
            # Group items by supplier using unified logic
            supplier_groups = {}
            
            for item in order.items.all():
                supplier_option = self.get_best_supplier_for_product(item.product, item.quantity)
                
                if not supplier_option:
                    continue
                
                supplier = supplier_option['supplier']
                if supplier not in supplier_groups:
                    supplier_groups[supplier] = []
                
                item_cost = supplier_option['unit_price'] * item.quantity
                total_cost += item_cost
                
                if supplier_option['is_fambri']:
                    fambri_cost += item_cost
                else:
                    external_cost += item_cost
                
                supplier_groups[supplier].append({
                    'product': item.product,
                    'quantity': item.quantity,
                    'unit_price': supplier_option['unit_price'],
                    'total_cost': item_cost,
                    'supplier_product': supplier_option.get('supplier_product'),
                    'can_fulfill': supplier_option['can_fulfill_full_order']
                })
            
            # Create purchase order plans
            for supplier, items in supplier_groups.items():
                po_total = sum(item['total_cost'] for item in items)
                
                procurement_plan['purchase_orders'].append({
                    'supplier_id': supplier.id,
                    'supplier_name': supplier.name,
                    'supplier_type': 'internal' if supplier == self.fambri_supplier else 'external',
                    'items': items,
                    'total_cost': float(po_total),
                    'estimated_lead_time': max((item['supplier_product'].get_effective_lead_time() if item['supplier_product'] else 1) for item in items)
                })
            
            # Calculate metrics
            fambri_percentage = (fambri_cost / total_cost * 100) if total_cost > 0 else 0
            
            return {
                'success': True,
                'order_id': order.id,
                'procurement_plan': procurement_plan,
                'optimization_result': {
                    'total_cost': float(total_cost),
                    'fambri_cost': float(fambri_cost),
                    'external_cost': float(external_cost),
                    'fambri_utilization': round(fambri_percentage, 2),
                    'suppliers_required': len(supplier_groups)
                },
                'cost_savings': {
                    'fambri_first_savings': float(external_cost * Decimal('0.15')),  # Estimated 15% savings
                    'total_savings': float(external_cost * Decimal('0.15'))
                }
            }
            
        except Exception as e:
            logger.error(f"Error in create_procurement_from_order: {e}")
            return {
                'success': False,
                'error': str(e),
                'order_id': order.id
            }
    
    # ========================================
    # UTILITY METHODS (CONSOLIDATED)
    # ========================================
    
    def _get_upcoming_orders(self, for_date: datetime.date, use_historical_dates: bool = True) -> List[Order]:
        """Get upcoming orders for procurement planning"""
        if use_historical_dates:
            # Look for orders around the target date (historical analysis)
            date_range_start = for_date - timedelta(days=1)
            date_range_end = for_date + timedelta(days=1)
            
            orders = Order.objects.filter(
                order_date__range=[date_range_start, date_range_end],
                status__in=['pending', 'confirmed']
            ).prefetch_related('items__product', 'customer')
        else:
            # Look for future orders from today
            orders = Order.objects.filter(
                order_date__gte=timezone.now().date(),
                order_date__lte=for_date + timedelta(days=7),  # Next week
                status__in=['pending', 'confirmed']
            ).prefetch_related('items__product', 'customer')
        
        return list(orders)
    
    def _analyze_current_stock(self) -> Dict[int, Dict]:
        """Analyze current stock levels"""
        stock_analysis = {}
        
        # Get current stock from products
        products = Product.objects.all()
        
        for product in products:
            stock_analysis[product.id] = {
                'current_stock': product.stock_level,
                'minimum_stock': product.minimum_stock,
                'stock_status': 'critical' if product.stock_level <= 0 else 'low' if product.stock_level < product.minimum_stock else 'adequate'
            }
        
        return stock_analysis
    
    def _get_default_buffer_settings(self, product: Product) -> Dict:
        """Get default buffer settings for a product"""
        # Try to get existing buffer settings
        try:
            buffer = ProcurementBuffer.objects.get(product=product)
            return {
                'buffer_percentage': float(buffer.buffer_percentage),
                'minimum_quantity': float(buffer.minimum_quantity),
                'maximum_quantity': float(buffer.maximum_quantity)
            }
        except ProcurementBuffer.DoesNotExist:
            pass
        
        # Default buffer settings based on product characteristics
        defaults = {
            'buffer_percentage': 20.0,  # 20% buffer
            'minimum_quantity': 5.0,
            'maximum_quantity': 100.0
        }
        
        # Adjust based on product unit
        if product.unit in ['kg', 'bunch']:
            defaults['buffer_percentage'] = 15.0  # Lower buffer for bulk items
        elif product.unit in ['punnet', 'box']:
            defaults['buffer_percentage'] = 25.0  # Higher buffer for packaged items
        
        return defaults
    
    def _estimate_price_by_department(self, product: Product) -> Decimal:
        """Estimate price based on product department"""
        department_estimates = {
            'Fruits': Decimal('25.00'),
            'Vegetables': Decimal('20.00'),
            'Herbs & Spices': Decimal('15.00'),
            'Mushrooms': Decimal('60.00'),
            'Specialty Items': Decimal('35.00')
        }
        
        return department_estimates.get(product.department.name, Decimal('20.00'))
    
    def _generate_reasoning(self, recommendations: List[Dict], upcoming_orders: List[Order]) -> str:
        """Generate reasoning for the procurement recommendation"""
        total_items = len(recommendations)
        total_cost = sum(item['estimated_total_cost'] for item in recommendations)
        critical_items = len([item for item in recommendations if item['priority'] == 'critical'])
        
        reasoning = f"Generated procurement recommendation for {len(upcoming_orders)} upcoming orders. "
        reasoning += f"Identified {total_items} products needed with total estimated cost of R{total_cost:.2f}. "
        
        if critical_items > 0:
            reasoning += f"{critical_items} items are critical (out of stock). "
        
        reasoning += "Recommendations include supplier-aware pricing and Fambri-first prioritization."
        
        return reasoning
    
    def _generate_time_saving_summary(self, recommendations: List[Dict]) -> str:
        """Generate time saving summary"""
        total_items = len(recommendations)
        estimated_time_saved = total_items * 3  # 3 minutes per item saved
        
        return f"Smart procurement saves ~{estimated_time_saved} minutes by pre-calculating quantities and optimal suppliers for {total_items} items."
