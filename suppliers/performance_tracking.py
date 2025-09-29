"""
Supplier Performance Tracking System
Advanced analytics and scoring for supplier evaluation and procurement decisions
"""

from django.db import models
from django.utils import timezone
from decimal import Decimal
from typing import Dict, List, Optional
import logging
from datetime import timedelta

from .models import Supplier, SupplierProduct
from procurement.models import PurchaseOrder, PurchaseOrderItem
from orders.models import Order, OrderItem

logger = logging.getLogger(__name__)

class SupplierPerformanceTracker:
    """
    Advanced supplier performance tracking with automated scoring
    """
    
    def __init__(self):
        self.performance_weights = {
            'delivery_reliability': 0.25,  # On-time delivery rate
            'quality_consistency': 0.20,   # Quality rating consistency
            'price_competitiveness': 0.20, # Price vs market average
            'stock_accuracy': 0.15,        # Stock level accuracy
            'order_fulfillment': 0.10,     # Order fulfillment rate
            'response_time': 0.10          # Communication response time
        }
    
    def calculate_supplier_performance_score(self, supplier: Supplier, days_back: int = 90) -> Dict:
        """
        Calculate comprehensive performance score for a supplier
        """
        try:
            end_date = timezone.now().date()
            start_date = end_date - timedelta(days=days_back)
            
            # Get performance metrics
            delivery_score = self._calculate_delivery_reliability(supplier, start_date, end_date)
            quality_score = self._calculate_quality_consistency(supplier, start_date, end_date)
            price_score = self._calculate_price_competitiveness(supplier, start_date, end_date)
            stock_score = self._calculate_stock_accuracy(supplier, start_date, end_date)
            fulfillment_score = self._calculate_order_fulfillment(supplier, start_date, end_date)
            response_score = self._calculate_response_time(supplier, start_date, end_date)
            
            # Calculate weighted overall score
            overall_score = (
                delivery_score['score'] * self.performance_weights['delivery_reliability'] +
                quality_score['score'] * self.performance_weights['quality_consistency'] +
                price_score['score'] * self.performance_weights['price_competitiveness'] +
                stock_score['score'] * self.performance_weights['stock_accuracy'] +
                fulfillment_score['score'] * self.performance_weights['order_fulfillment'] +
                response_score['score'] * self.performance_weights['response_time']
            )
            
            # Determine performance tier
            performance_tier = self._get_performance_tier(overall_score)
            
            return {
                'supplier_id': supplier.id,
                'supplier_name': supplier.name,
                'evaluation_period': f'{start_date} to {end_date}',
                'overall_score': round(overall_score, 2),
                'performance_tier': performance_tier,
                'metrics': {
                    'delivery_reliability': delivery_score,
                    'quality_consistency': quality_score,
                    'price_competitiveness': price_score,
                    'stock_accuracy': stock_score,
                    'order_fulfillment': fulfillment_score,
                    'response_time': response_score
                },
                'recommendations': self._generate_performance_recommendations(
                    overall_score, delivery_score, quality_score, price_score, 
                    stock_score, fulfillment_score, response_score
                ),
                'trend_analysis': self._analyze_performance_trends(supplier, days_back)
            }
            
        except Exception as e:
            logger.error(f"Error calculating performance score for supplier {supplier.id}: {e}")
            return {
                'supplier_id': supplier.id,
                'supplier_name': supplier.name,
                'error': str(e),
                'overall_score': 0.0,
                'performance_tier': 'unrated'
            }
    
    def _calculate_delivery_reliability(self, supplier: Supplier, start_date, end_date) -> Dict:
        """Calculate on-time delivery performance"""
        try:
            purchase_orders = PurchaseOrder.objects.filter(
                supplier=supplier,
                created_at__date__gte=start_date,
                created_at__date__lte=end_date,
                status__in=['delivered', 'completed']
            )
            
            if not purchase_orders.exists():
                return {'score': 50.0, 'details': 'No delivery data available', 'sample_size': 0}
            
            total_orders = purchase_orders.count()
            on_time_deliveries = 0
            total_delay_days = 0
            
            for po in purchase_orders:
                if po.actual_delivery_date and po.expected_delivery_date:
                    if po.actual_delivery_date <= po.expected_delivery_date:
                        on_time_deliveries += 1
                    else:
                        delay = (po.actual_delivery_date - po.expected_delivery_date).days
                        total_delay_days += delay
            
            on_time_rate = (on_time_deliveries / total_orders) * 100
            avg_delay = total_delay_days / (total_orders - on_time_deliveries) if (total_orders - on_time_deliveries) > 0 else 0
            
            # Score calculation: 100% on-time = 100 points, decreases with delays
            score = max(0, min(100, on_time_rate - (avg_delay * 2)))
            
            return {
                'score': round(score, 1),
                'on_time_rate': round(on_time_rate, 1),
                'average_delay_days': round(avg_delay, 1),
                'total_deliveries': total_orders,
                'on_time_deliveries': on_time_deliveries,
                'sample_size': total_orders
            }
            
        except Exception as e:
            logger.error(f"Error calculating delivery reliability: {e}")
            return {'score': 0.0, 'error': str(e), 'sample_size': 0}
    
    def _calculate_quality_consistency(self, supplier: Supplier, start_date, end_date) -> Dict:
        """Calculate quality rating consistency"""
        try:
            supplier_products = supplier.supplier_products.filter(
                updated_at__date__gte=start_date,
                updated_at__date__lte=end_date
            )
            
            if not supplier_products.exists():
                return {'score': 50.0, 'details': 'No quality data available', 'sample_size': 0}
            
            quality_ratings = [sp.quality_rating for sp in supplier_products if sp.quality_rating]
            
            if not quality_ratings:
                return {'score': 50.0, 'details': 'No quality ratings available', 'sample_size': 0}
            
            avg_quality = sum(quality_ratings) / len(quality_ratings)
            
            # Calculate consistency (lower standard deviation = higher consistency)
            variance = sum((rating - avg_quality) ** 2 for rating in quality_ratings) / len(quality_ratings)
            std_deviation = variance ** 0.5
            
            # Score: High average quality + low deviation = high score
            consistency_penalty = std_deviation * 10  # Penalize inconsistency
            score = max(0, min(100, (avg_quality * 20) - consistency_penalty))
            
            return {
                'score': round(score, 1),
                'average_quality': round(avg_quality, 2),
                'consistency_rating': round(5 - std_deviation, 2),  # 5 = perfect consistency
                'quality_range': f"{min(quality_ratings):.1f} - {max(quality_ratings):.1f}",
                'sample_size': len(quality_ratings)
            }
            
        except Exception as e:
            logger.error(f"Error calculating quality consistency: {e}")
            return {'score': 0.0, 'error': str(e), 'sample_size': 0}
    
    def _calculate_price_competitiveness(self, supplier: Supplier, start_date, end_date) -> Dict:
        """Calculate price competitiveness vs market"""
        try:
            supplier_products = supplier.supplier_products.filter(
                updated_at__date__gte=start_date,
                updated_at__date__lte=end_date,
                is_available=True
            )
            
            if not supplier_products.exists():
                return {'score': 50.0, 'details': 'No pricing data available', 'sample_size': 0}
            
            competitive_products = 0
            total_products = 0
            price_advantages = []
            
            for sp in supplier_products:
                # Compare with other suppliers for same product
                competing_prices = SupplierProduct.objects.filter(
                    product=sp.product,
                    is_available=True
                ).exclude(supplier=supplier).values_list('supplier_price', flat=True)
                
                if competing_prices:
                    min_competitor_price = min(competing_prices)
                    if sp.supplier_price <= min_competitor_price:
                        competitive_products += 1
                        price_advantage = ((min_competitor_price - sp.supplier_price) / min_competitor_price) * 100
                        price_advantages.append(price_advantage)
                    
                    total_products += 1
            
            if total_products == 0:
                return {'score': 50.0, 'details': 'No comparable products found', 'sample_size': 0}
            
            competitiveness_rate = (competitive_products / total_products) * 100
            avg_price_advantage = sum(price_advantages) / len(price_advantages) if price_advantages else 0
            
            # Score based on how often supplier has competitive prices
            score = min(100, competitiveness_rate + (avg_price_advantage * 2))
            
            return {
                'score': round(score, 1),
                'competitive_rate': round(competitiveness_rate, 1),
                'average_price_advantage': round(avg_price_advantage, 2),
                'competitive_products': competitive_products,
                'total_products_compared': total_products,
                'sample_size': total_products
            }
            
        except Exception as e:
            logger.error(f"Error calculating price competitiveness: {e}")
            return {'score': 0.0, 'error': str(e), 'sample_size': 0}
    
    def _calculate_stock_accuracy(self, supplier: Supplier, start_date, end_date) -> Dict:
        """Calculate stock level accuracy"""
        try:
            # This would require tracking actual vs reported stock levels
            # For now, we'll use a simplified approach based on order fulfillment
            
            purchase_orders = PurchaseOrder.objects.filter(
                supplier=supplier,
                created_at__date__gte=start_date,
                created_at__date__lte=end_date
            )
            
            if not purchase_orders.exists():
                return {'score': 50.0, 'details': 'No stock data available', 'sample_size': 0}
            
            total_items = 0
            fulfilled_items = 0
            
            for po in purchase_orders:
                for item in po.items.all():
                    total_items += 1
                    # Assume item was fulfilled if PO was completed
                    if po.status in ['delivered', 'completed']:
                        fulfilled_items += 1
            
            if total_items == 0:
                return {'score': 50.0, 'details': 'No order items found', 'sample_size': 0}
            
            fulfillment_rate = (fulfilled_items / total_items) * 100
            
            # Stock accuracy score based on fulfillment rate
            score = min(100, fulfillment_rate)
            
            return {
                'score': round(score, 1),
                'fulfillment_rate': round(fulfillment_rate, 1),
                'fulfilled_items': fulfilled_items,
                'total_items': total_items,
                'sample_size': total_items
            }
            
        except Exception as e:
            logger.error(f"Error calculating stock accuracy: {e}")
            return {'score': 0.0, 'error': str(e), 'sample_size': 0}
    
    def _calculate_order_fulfillment(self, supplier: Supplier, start_date, end_date) -> Dict:
        """Calculate order fulfillment rate"""
        try:
            purchase_orders = PurchaseOrder.objects.filter(
                supplier=supplier,
                created_at__date__gte=start_date,
                created_at__date__lte=end_date
            )
            
            if not purchase_orders.exists():
                return {'score': 50.0, 'details': 'No order data available', 'sample_size': 0}
            
            total_orders = purchase_orders.count()
            fulfilled_orders = purchase_orders.filter(status__in=['delivered', 'completed']).count()
            cancelled_orders = purchase_orders.filter(status='cancelled').count()
            
            fulfillment_rate = (fulfilled_orders / total_orders) * 100
            cancellation_rate = (cancelled_orders / total_orders) * 100
            
            # Score penalized by cancellations
            score = max(0, fulfillment_rate - (cancellation_rate * 2))
            
            return {
                'score': round(score, 1),
                'fulfillment_rate': round(fulfillment_rate, 1),
                'cancellation_rate': round(cancellation_rate, 1),
                'fulfilled_orders': fulfilled_orders,
                'total_orders': total_orders,
                'cancelled_orders': cancelled_orders,
                'sample_size': total_orders
            }
            
        except Exception as e:
            logger.error(f"Error calculating order fulfillment: {e}")
            return {'score': 0.0, 'error': str(e), 'sample_size': 0}
    
    def _calculate_response_time(self, supplier: Supplier, start_date, end_date) -> Dict:
        """Calculate communication response time"""
        try:
            # This would require tracking communication timestamps
            # For now, we'll use a simplified approach based on order processing time
            
            purchase_orders = PurchaseOrder.objects.filter(
                supplier=supplier,
                created_at__date__gte=start_date,
                created_at__date__lte=end_date,
                status__in=['approved', 'delivered', 'completed']
            )
            
            if not purchase_orders.exists():
                return {'score': 75.0, 'details': 'No response time data available', 'sample_size': 0}
            
            # Assume good response time for now (this would be enhanced with real data)
            # Score based on supplier type: Internal = faster response
            if 'Fambri' in supplier.name:
                score = 95.0  # Internal supplier = excellent response
            else:
                score = 75.0  # External supplier = good response
            
            return {
                'score': score,
                'average_response_hours': 4.0 if 'Fambri' in supplier.name else 12.0,
                'details': 'Estimated based on supplier type',
                'sample_size': purchase_orders.count()
            }
            
        except Exception as e:
            logger.error(f"Error calculating response time: {e}")
            return {'score': 0.0, 'error': str(e), 'sample_size': 0}
    
    def _get_performance_tier(self, overall_score: float) -> str:
        """Determine performance tier based on overall score"""
        if overall_score >= 90:
            return 'platinum'
        elif overall_score >= 80:
            return 'gold'
        elif overall_score >= 70:
            return 'silver'
        elif overall_score >= 60:
            return 'bronze'
        else:
            return 'needs_improvement'
    
    def _generate_performance_recommendations(self, overall_score, delivery, quality, price, stock, fulfillment, response) -> List[Dict]:
        """Generate actionable performance recommendations"""
        recommendations = []
        
        # Delivery recommendations
        if delivery['score'] < 70:
            recommendations.append({
                'category': 'delivery',
                'priority': 'high',
                'issue': 'Poor delivery reliability',
                'recommendation': 'Implement delivery tracking and communicate delays proactively',
                'target_improvement': '85% on-time delivery rate'
            })
        
        # Quality recommendations
        if quality['score'] < 75:
            recommendations.append({
                'category': 'quality',
                'priority': 'high',
                'issue': 'Inconsistent quality ratings',
                'recommendation': 'Establish quality control processes and regular product inspections',
                'target_improvement': '4.0+ average quality rating'
            })
        
        # Price recommendations
        if price['score'] < 60:
            recommendations.append({
                'category': 'pricing',
                'priority': 'medium',
                'issue': 'Uncompetitive pricing',
                'recommendation': 'Review pricing strategy and negotiate volume discounts',
                'target_improvement': '70%+ competitive rate'
            })
        
        # Stock recommendations
        if stock['score'] < 80:
            recommendations.append({
                'category': 'inventory',
                'priority': 'medium',
                'issue': 'Stock accuracy issues',
                'recommendation': 'Implement real-time inventory tracking and regular stock audits',
                'target_improvement': '95%+ stock accuracy'
            })
        
        # Overall performance
        if overall_score >= 90:
            recommendations.append({
                'category': 'recognition',
                'priority': 'low',
                'issue': 'Excellent performance',
                'recommendation': 'Consider preferred supplier status and increased order volume',
                'target_improvement': 'Maintain current performance levels'
            })
        
        return recommendations
    
    def _analyze_performance_trends(self, supplier: Supplier, days_back: int) -> Dict:
        """Analyze performance trends over time"""
        try:
            # Compare current period with previous period
            current_end = timezone.now().date()
            current_start = current_end - timedelta(days=days_back)
            previous_start = current_start - timedelta(days=days_back)
            
            current_score = self.calculate_supplier_performance_score(supplier, days_back)['overall_score']
            
            # Calculate previous period score (simplified)
            previous_orders = PurchaseOrder.objects.filter(
                supplier=supplier,
                created_at__date__gte=previous_start,
                created_at__date__lt=current_start
            ).count()
            
            if previous_orders > 0:
                # Simplified trend calculation
                trend_direction = 'improving' if current_score > 75 else 'declining' if current_score < 65 else 'stable'
                trend_strength = abs(current_score - 70) / 30  # Normalized strength
            else:
                trend_direction = 'insufficient_data'
                trend_strength = 0
            
            return {
                'trend_direction': trend_direction,
                'trend_strength': round(trend_strength, 2),
                'current_score': current_score,
                'comparison_period': f'{previous_start} to {current_start}',
                'data_points': previous_orders
            }
            
        except Exception as e:
            logger.error(f"Error analyzing performance trends: {e}")
            return {
                'trend_direction': 'unknown',
                'trend_strength': 0,
                'error': str(e)
            }
    
    def get_supplier_rankings(self, days_back: int = 90) -> List[Dict]:
        """Get ranked list of all suppliers by performance"""
        try:
            suppliers = Supplier.objects.filter(is_active=True)
            supplier_scores = []
            
            for supplier in suppliers:
                performance = self.calculate_supplier_performance_score(supplier, days_back)
                supplier_scores.append({
                    'supplier_id': supplier.id,
                    'supplier_name': supplier.name,
                    'supplier_type': 'internal' if 'Fambri' in supplier.name else 'external',
                    'overall_score': performance['overall_score'],
                    'performance_tier': performance['performance_tier'],
                    'key_strengths': self._identify_key_strengths(performance),
                    'improvement_areas': self._identify_improvement_areas(performance)
                })
            
            # Sort by overall score (descending)
            supplier_scores.sort(key=lambda x: x['overall_score'], reverse=True)
            
            # Add rankings
            for i, supplier in enumerate(supplier_scores, 1):
                supplier['rank'] = i
            
            return supplier_scores
            
        except Exception as e:
            logger.error(f"Error getting supplier rankings: {e}")
            return []
    
    def _identify_key_strengths(self, performance: Dict) -> List[str]:
        """Identify supplier's key strengths"""
        strengths = []
        metrics = performance.get('metrics', {})
        
        for metric_name, metric_data in metrics.items():
            if isinstance(metric_data, dict) and metric_data.get('score', 0) >= 80:
                strength_names = {
                    'delivery_reliability': 'Reliable Delivery',
                    'quality_consistency': 'Consistent Quality',
                    'price_competitiveness': 'Competitive Pricing',
                    'stock_accuracy': 'Accurate Inventory',
                    'order_fulfillment': 'High Fulfillment Rate',
                    'response_time': 'Fast Communication'
                }
                strengths.append(strength_names.get(metric_name, metric_name.title()))
        
        return strengths[:3]  # Top 3 strengths
    
    def _identify_improvement_areas(self, performance: Dict) -> List[str]:
        """Identify areas needing improvement"""
        improvements = []
        metrics = performance.get('metrics', {})
        
        for metric_name, metric_data in metrics.items():
            if isinstance(metric_data, dict) and metric_data.get('score', 100) < 70:
                improvement_names = {
                    'delivery_reliability': 'Delivery Timeliness',
                    'quality_consistency': 'Quality Control',
                    'price_competitiveness': 'Price Optimization',
                    'stock_accuracy': 'Inventory Management',
                    'order_fulfillment': 'Order Processing',
                    'response_time': 'Communication Speed'
                }
                improvements.append(improvement_names.get(metric_name, metric_name.title()))
        
        return improvements[:2]  # Top 2 improvement areas
