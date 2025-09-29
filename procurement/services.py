"""
Fambri-First Procurement Workflow Services
Automated procurement workflows with intelligent supplier selection
"""

from django.db import transaction
from django.utils import timezone
from decimal import Decimal
from typing import Dict, List, Optional
import logging

from products.models import Product
from products.services import ProcurementIntelligenceService
from suppliers.models import Supplier, SupplierProduct
from orders.models import Order, OrderItem
from .models import PurchaseOrder, PurchaseOrderItem
from django.db import models

logger = logging.getLogger(__name__)

class FambriFirstProcurementService:
    """
    Automated procurement service with Fambri-first logic
    """
    
    def __init__(self):
        self.procurement_intelligence = ProcurementIntelligenceService()
        self.fambri_supplier = self._get_fambri_supplier()
    
    def _get_fambri_supplier(self) -> Optional[Supplier]:
        """Get Fambri Farms Internal supplier"""
        try:
            return Supplier.objects.filter(name__icontains='Fambri').first()
        except Exception as e:
            logger.error(f"Error getting Fambri supplier: {e}")
            return None
    
    def create_procurement_from_order(self, order: Order) -> Dict:
        """
        Create procurement recommendations from an order using Fambri-first logic
        """
        try:
            # Prepare order items for optimization
            order_items = []
            for item in order.items.all():
                order_items.append({
                    'product_id': item.product.id,
                    'quantity': item.quantity,
                    'order_item_id': item.id
                })
            
            # Calculate optimal supplier split
            optimization_result = self.procurement_intelligence.calculate_order_supplier_optimization(order_items)
            
            # Generate procurement plan
            procurement_plan = self._generate_procurement_plan(optimization_result, order)
            
            return {
                'success': True,
                'order_id': order.id,
                'order_number': order.order_number,
                'optimization_result': optimization_result,
                'procurement_plan': procurement_plan,
                'fambri_utilization': optimization_result.get('fambri_percentage', 0),
                'cost_savings': self._calculate_cost_savings(optimization_result),
                'recommendations': optimization_result.get('procurement_recommendations', [])
            }
            
        except Exception as e:
            logger.error(f"Error creating procurement from order {order.id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'order_id': order.id
            }
    
    def _generate_procurement_plan(self, optimization_result: Dict, order: Order) -> Dict:
        """Generate detailed procurement plan with purchase orders"""
        plan = {
            'purchase_orders': [],
            'total_suppliers': 0,
            'total_cost': 0.0,
            'fambri_cost': 0.0,
            'external_cost': 0.0,
            'estimated_delivery_date': None
        }
        
        # Group items by supplier
        supplier_items = {}
        for item_detail in optimization_result.get('item_details', []):
            if not item_detail.get('success'):
                continue
                
            for supplier_info in item_detail.get('suppliers', []):
                supplier_id = supplier_info['supplier_id']
                if supplier_id not in supplier_items:
                    supplier_items[supplier_id] = {
                        'supplier_info': supplier_info,
                        'items': []
                    }
                
                supplier_items[supplier_id]['items'].append({
                    'product_name': item_detail['product_name'],
                    'quantity': supplier_info['quantity'],
                    'unit_price': supplier_info['unit_price'],
                    'total_cost': supplier_info['total_cost']
                })
        
        # Create purchase order plans for each supplier
        for supplier_id, supplier_data in supplier_items.items():
            supplier_info = supplier_data['supplier_info']
            items = supplier_data['items']
            
            po_plan = {
                'supplier_id': supplier_id,
                'supplier_name': supplier_info['supplier_name'],
                'supplier_type': supplier_info['supplier_type'],
                'priority': supplier_info['priority'],
                'items': items,
                'total_cost': sum(item['total_cost'] for item in items),
                'lead_time_days': supplier_info['lead_time_days'],
                'quality_rating': supplier_info['quality_rating'],
                'estimated_delivery': self._calculate_delivery_date(supplier_info['lead_time_days'])
            }
            
            plan['purchase_orders'].append(po_plan)
            plan['total_cost'] += po_plan['total_cost']
            
            if supplier_info['supplier_type'] == 'internal':
                plan['fambri_cost'] += po_plan['total_cost']
            else:
                plan['external_cost'] += po_plan['total_cost']
        
        plan['total_suppliers'] = len(supplier_items)
        plan['estimated_delivery_date'] = max(
            po['estimated_delivery'] for po in plan['purchase_orders']
        ) if plan['purchase_orders'] else None
        
        return plan
    
    def _calculate_delivery_date(self, lead_time_days: int) -> str:
        """Calculate estimated delivery date"""
        delivery_date = timezone.now().date() + timezone.timedelta(days=lead_time_days)
        return delivery_date.isoformat()
    
    def _calculate_cost_savings(self, optimization_result: Dict) -> Dict:
        """Calculate cost savings from using Fambri-first logic"""
        total_cost = optimization_result.get('total_cost', 0)
        fambri_cost = optimization_result.get('total_fambri_cost', 0)
        external_cost = optimization_result.get('total_external_cost', 0)
        
        # Estimate cost if all external (worst case)
        estimated_all_external_cost = total_cost * 1.4  # Assume 40% premium for all external
        
        savings = {
            'actual_cost': total_cost,
            'estimated_all_external_cost': estimated_all_external_cost,
            'total_savings': estimated_all_external_cost - total_cost,
            'savings_percentage': ((estimated_all_external_cost - total_cost) / estimated_all_external_cost * 100) if estimated_all_external_cost > 0 else 0,
            'fambri_contribution': fambri_cost,
            'external_contribution': external_cost
        }
        
        return savings
    
    def create_purchase_orders(self, procurement_plan: Dict, order: Order, auto_approve: bool = False) -> Dict:
        """
        Create actual purchase orders from procurement plan
        """
        created_pos = []
        errors = []
        
        try:
            with transaction.atomic():
                for po_plan in procurement_plan.get('purchase_orders', []):
                    try:
                        # Get supplier
                        supplier = Supplier.objects.get(id=po_plan['supplier_id'])
                        
                        # Create purchase order
                        po = PurchaseOrder.objects.create(
                            supplier=supplier,
                            order_reference=order,
                            total_amount=Decimal(str(po_plan['total_cost'])),
                            status='approved' if auto_approve else 'pending',
                            expected_delivery_date=po_plan['estimated_delivery'],
                            notes=f"Auto-generated from order {order.order_number} using Fambri-first logic"
                        )
                        
                        # Create purchase order items
                        for item_plan in po_plan['items']:
                            # Find the product
                            try:
                                product = Product.objects.get(name=item_plan['product_name'])
                                
                                PurchaseOrderItem.objects.create(
                                    purchase_order=po,
                                    product=product,
                                    quantity=Decimal(str(item_plan['quantity'])),
                                    unit_price=Decimal(str(item_plan['unit_price'])),
                                    total_price=Decimal(str(item_plan['total_cost']))
                                )
                            except Product.DoesNotExist:
                                logger.warning(f"Product not found: {item_plan['product_name']}")
                                continue
                        
                        created_pos.append({
                            'po_id': po.id,
                            'po_number': po.po_number,
                            'supplier_name': supplier.name,
                            'total_amount': float(po.total_amount),
                            'status': po.status,
                            'items_count': po.items.count()
                        })
                        
                    except Exception as e:
                        error_msg = f"Error creating PO for supplier {po_plan['supplier_name']}: {str(e)}"
                        errors.append(error_msg)
                        logger.error(error_msg)
                        continue
                
                return {
                    'success': len(created_pos) > 0,
                    'created_purchase_orders': created_pos,
                    'total_pos_created': len(created_pos),
                    'errors': errors,
                    'order_id': order.id
                }
                
        except Exception as e:
            logger.error(f"Error in create_purchase_orders: {e}")
            return {
                'success': False,
                'error': str(e),
                'created_purchase_orders': [],
                'total_pos_created': 0
            }
    
    def process_order_procurement_workflow(self, order: Order, auto_create_pos: bool = False) -> Dict:
        """
        Complete procurement workflow for an order
        1. Analyze order with Fambri-first logic
        2. Generate procurement plan
        3. Optionally create purchase orders
        """
        try:
            # Step 1: Create procurement analysis
            procurement_result = self.create_procurement_from_order(order)
            
            if not procurement_result['success']:
                return procurement_result
            
            # Step 2: Create purchase orders if requested
            po_result = None
            if auto_create_pos:
                po_result = self.create_purchase_orders(
                    procurement_result['procurement_plan'], 
                    order, 
                    auto_approve=False  # Always require manual approval for safety
                )
            
            # Step 3: Compile final result
            workflow_result = {
                'success': True,
                'order_id': order.id,
                'order_number': order.order_number,
                'procurement_analysis': procurement_result,
                'purchase_orders': po_result,
                'workflow_summary': {
                    'fambri_utilization': procurement_result.get('fambri_utilization', 0),
                    'total_cost': procurement_result['optimization_result'].get('total_cost', 0),
                    'suppliers_required': len(procurement_result['procurement_plan']['purchase_orders']),
                    'estimated_savings': procurement_result['cost_savings']['total_savings'],
                    'pos_created': po_result['total_pos_created'] if po_result else 0
                }
            }
            
            return workflow_result
            
        except Exception as e:
            logger.error(f"Error in process_order_procurement_workflow: {e}")
            return {
                'success': False,
                'error': str(e),
                'order_id': order.id
            }
    
    def get_procurement_recommendations_for_low_stock(self) -> Dict:
        """
        Generate procurement recommendations for products with low stock
        using Fambri-first logic
        """
        try:
            # Find products with low stock
            low_stock_products = Product.objects.filter(
                stock_level__lte=models.F('minimum_stock')
            ).select_related('department')
            
            recommendations = []
            total_cost = 0.0
            fambri_cost = 0.0
            
            for product in low_stock_products:
                # Calculate recommended order quantity (2x minimum stock)
                recommended_qty = max(product.minimum_stock * 2, Decimal('10'))
                
                # Get supplier recommendations
                supplier_recs = self.procurement_intelligence.get_supplier_recommendations(
                    product, recommended_qty
                )
                
                if supplier_recs:
                    best_supplier = supplier_recs[0]  # First is best (Fambri-first)
                    
                    recommendation = {
                        'product_id': product.id,
                        'product_name': product.name,
                        'current_stock': float(product.stock_level),
                        'minimum_stock': float(product.minimum_stock),
                        'recommended_quantity': float(recommended_qty),
                        'best_supplier': best_supplier,
                        'estimated_cost': best_supplier['total_cost'],
                        'urgency': 'urgent' if product.stock_level <= 0 else 'high'
                    }
                    
                    recommendations.append(recommendation)
                    total_cost += best_supplier['total_cost']
                    
                    if best_supplier['supplier_type'] == 'internal':
                        fambri_cost += best_supplier['total_cost']
            
            return {
                'success': True,
                'total_products': len(recommendations),
                'total_estimated_cost': total_cost,
                'fambri_cost': fambri_cost,
                'external_cost': total_cost - fambri_cost,
                'fambri_percentage': (fambri_cost / total_cost * 100) if total_cost > 0 else 0,
                'recommendations': recommendations
            }
            
        except Exception as e:
            logger.error(f"Error getting low stock recommendations: {e}")
            return {
                'success': False,
                'error': str(e)
            }
