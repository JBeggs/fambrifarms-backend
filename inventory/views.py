from rest_framework import viewsets, status, permissions
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count, Sum, F, Avg
from django.db import models
from django.utils import timezone
from decimal import Decimal
from datetime import datetime, timedelta

from .models import (
    UnitOfMeasure, RawMaterial, RawMaterialBatch, ProductionRecipe,
    RecipeIngredient, FinishedInventory, StockMovement, ProductionBatch,
    StockAlert, StockAnalysis, StockAnalysisItem, MarketPrice, 
    ProcurementRecommendation, PriceAlert, PricingRule, CustomerPriceList,
    CustomerPriceListItem, WeeklyPriceReport, InvoicePhoto, ExtractedInvoiceData,
    SupplierProductMapping
)
from .serializers import (
    UnitOfMeasureSerializer, RawMaterialListSerializer, RawMaterialDetailSerializer,
    RawMaterialBatchListSerializer, RawMaterialBatchDetailSerializer,
    ProductionRecipeListSerializer, ProductionRecipeDetailSerializer,
    RecipeIngredientSerializer, FinishedInventorySerializer,
    StockMovementSerializer, ProductionBatchListSerializer,
    ProductionBatchDetailSerializer, StockAlertSerializer,
    InventoryDashboardSerializer, StockLevelSerializer,
    StockReservationSerializer, ProductionStartSerializer,
    ProductionCompleteSerializer, StockAdjustmentSerializer,
    StockAnalysisListSerializer, StockAnalysisDetailSerializer,
    StockAnalysisCreateSerializer, StockAnalysisItemSerializer,
    MarketPriceSerializer, MarketPriceCreateSerializer,
    ProcurementRecommendationSerializer, ProcurementRecommendationCreateSerializer,
    ProcurementRecommendationListSerializer, PriceAlertSerializer, 
    PriceAlertCreateSerializer, PricingRuleSerializer, PricingRuleCreateSerializer,
    CustomerPriceListSerializer, CustomerPriceListDetailSerializer,
    CustomerPriceListCreateSerializer, CustomerPriceListItemSerializer,
    WeeklyPriceReportSerializer, WeeklyPriceReportCreateSerializer,
    MarketPriceWithCustomerImpactSerializer
)
from products.models import Product


class UnitOfMeasureViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = UnitOfMeasure.objects.all()
    serializer_class = UnitOfMeasureSerializer
    permission_classes = []
    pagination_class = None
    
    def get_queryset(self):
        queryset = UnitOfMeasure.objects.all()
        is_active = self.request.query_params.get('is_active')  # None means no filter
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        return queryset


class RawMaterialViewSet(viewsets.ModelViewSet):
    queryset = RawMaterial.objects.all()
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return RawMaterialListSerializer
        return RawMaterialDetailSerializer
    
    def get_queryset(self):
        queryset = RawMaterial.objects.all()
        
        # Filter by active status
        is_active = self.request.query_params.get('is_active')  # None means no filter
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        # Filter by needs reorder
        needs_reorder = self.request.query_params.get('needs_reorder')  # None means no filter
        if needs_reorder is not None:
            if needs_reorder.lower() == 'true':
                queryset = queryset.filter(
                    current_stock_level__lte=F('reorder_level')
                )
        
        # Search by name or SKU
        search = self.request.query_params.get('search')  # None means no filter
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(sku__icontains=search)
            )
        
        return queryset.order_by('name')
    
    @action(detail=True, methods=['get'])
    def batches(self, request, pk=None):
        """Get all batches for this raw material"""
        raw_material = self.get_object()
        batches = raw_material.batches.filter(is_active=True).order_by('-received_date')
        serializer = RawMaterialBatchListSerializer(batches, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def low_stock(self, request):
        """Get raw materials that need reordering"""
        queryset = self.get_queryset().filter(
            current_stock_level__lte=F('reorder_level'),
            is_active=True
        )
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class RawMaterialBatchViewSet(viewsets.ModelViewSet):
    queryset = RawMaterialBatch.objects.all()
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return RawMaterialBatchListSerializer
        return RawMaterialBatchDetailSerializer
    
    def get_queryset(self):
        queryset = RawMaterialBatch.objects.select_related(
            'raw_material', 'supplier'
        ).all()
        
        # Filter by raw material
        raw_material_id = self.request.query_params.get('raw_material')  # None means no filter
        if raw_material_id:
            queryset = queryset.filter(raw_material_id=raw_material_id)
        
        # Filter by supplier
        supplier_id = self.request.query_params.get('supplier')  # None means no filter
        if supplier_id:
            queryset = queryset.filter(supplier_id=supplier_id)
        
        # Filter by expiry status
        expiry_status = self.request.query_params.get('expiry_status')  # None means no filter
        if expiry_status == 'expired':
            queryset = queryset.filter(expiry_date__lt=timezone.now().date())
        elif expiry_status == 'expiring_soon':
            soon_date = timezone.now().date() + timedelta(days=7)
            queryset = queryset.filter(
                expiry_date__gte=timezone.now().date(),
                expiry_date__lte=soon_date
            )
        
        # Filter by availability
        has_stock = self.request.query_params.get('has_stock')  # None means no filter
        if has_stock is not None:
            if has_stock.lower() == 'true':
                queryset = queryset.filter(available_quantity__gt=0)
            else:
                queryset = queryset.filter(available_quantity=0)
        
        return queryset.order_by('-received_date')
    
    @action(detail=False, methods=['get'])
    def expiring_soon(self, request):
        """Get batches expiring within 7 days"""
        soon_date = timezone.now().date() + timedelta(days=7)
        queryset = self.get_queryset().filter(
            expiry_date__gte=timezone.now().date(),
            expiry_date__lte=soon_date,
            available_quantity__gt=0,
            is_active=True
        )
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class ProductionRecipeViewSet(viewsets.ModelViewSet):
    queryset = ProductionRecipe.objects.all()
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ProductionRecipeListSerializer
        return ProductionRecipeDetailSerializer
    
    def get_queryset(self):
        queryset = ProductionRecipe.objects.select_related(
            'product', 'output_unit', 'created_by'
        ).prefetch_related('ingredients__raw_material').all()
        
        # Filter by product
        product_id = self.request.query_params.get('product')  # None means no filter
        if product_id:
            queryset = queryset.filter(product_id=product_id)
        
        # Filter by active status
        is_active = self.request.query_params.get('is_active')  # None means no filter
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        return queryset.order_by('-created_at')
    
    @action(detail=True, methods=['post'])
    def add_ingredient(self, request, pk=None):
        """Add an ingredient to the recipe"""
        recipe = self.get_object()
        serializer = RecipeIngredientSerializer(data=request.data)
        
        if serializer.is_valid():
            serializer.save(recipe=recipe)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['delete'])
    def remove_ingredient(self, request, pk=None):
        """Remove an ingredient from the recipe"""
        recipe = self.get_object()
        ingredient_id = request.data.get('ingredient_id')
        
        try:
            ingredient = RecipeIngredient.objects.get(id=ingredient_id, recipe=recipe)
            ingredient.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except RecipeIngredient.DoesNotExist:
            return Response(
                {'error': 'Ingredient not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )


class FinishedInventoryViewSet(viewsets.ModelViewSet):
    queryset = FinishedInventory.objects.all()
    serializer_class = FinishedInventorySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = FinishedInventory.objects.select_related(
            'product__department'
        ).all()
        
        # Filter by department
        department_id = self.request.query_params.get('department')  # None means no filter
        if department_id:
            queryset = queryset.filter(product__department_id=department_id)
        
        # Filter by low stock
        low_stock = self.request.query_params.get('low_stock')  # None means no filter
        if low_stock is not None and low_stock.lower() == 'true':
            queryset = queryset.filter(available_quantity__lte=F('reorder_level'))
        
        # Filter by needs production
        needs_production = self.request.query_params.get('needs_production')  # None means no filter
        if needs_production is not None and needs_production.lower() == 'true':
            queryset = queryset.filter(available_quantity__lte=F('reorder_level'))
        
        return queryset.order_by('product__name')
    
    @action(detail=False, methods=['get'])
    def low_stock(self, request):
        """Get products with low stock"""
        queryset = self.get_queryset().filter(
            available_quantity__lte=F('reorder_level')
        )
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get inventory summary by department"""
        from products.models import Department
        
        departments = Department.objects.filter(is_active=True)
        summary = []
        
        for dept in departments:
            dept_inventory = self.get_queryset().filter(product__department=dept)
            
            summary.append({
                'department_id': dept.id,
                'department_name': dept.name,
                'total_products': dept_inventory.count(),
                'low_stock_count': dept_inventory.filter(
                    available_quantity__lte=F('reorder_level')
                ).count(),
                'total_value': dept_inventory.aggregate(
                    total=Sum(F('available_quantity') * F('average_cost'))
                )['total'] or Decimal('0.00')
            })
        
        return Response(summary)


class StockMovementViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = StockMovement.objects.all()
    serializer_class = StockMovementSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = StockMovement.objects.select_related(
            'user', 'raw_material', 'product', 'raw_material_batch'
        ).all()
        
        # Filter by movement type
        movement_type = self.request.query_params.get('movement_type')  # None means no filter
        if movement_type:
            queryset = queryset.filter(movement_type=movement_type)
        
        # Filter by product
        product_id = self.request.query_params.get('product')  # None means no filter
        if product_id:
            queryset = queryset.filter(product_id=product_id)
        
        # Filter by raw material
        raw_material_id = self.request.query_params.get('raw_material')  # None means no filter
        if raw_material_id:
            queryset = queryset.filter(raw_material_id=raw_material_id)
        
        # Filter by date range
        date_from = self.request.query_params.get('date_from')  # None means no filter
        date_to = self.request.query_params.get('date_to')  # None means no filter
        
        if date_from:
            queryset = queryset.filter(timestamp__gte=date_from)
        if date_to:
            queryset = queryset.filter(timestamp__lte=date_to)
        
        return queryset.order_by('-timestamp')


class ProductionBatchViewSet(viewsets.ModelViewSet):
    queryset = ProductionBatch.objects.all()
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ProductionBatchListSerializer
        return ProductionBatchDetailSerializer
    
    def get_queryset(self):
        queryset = ProductionBatch.objects.select_related(
            'recipe__product', 'planned_by', 'produced_by'
        ).all()
        
        # Filter by status
        status_filter = self.request.query_params.get('status')  # None means no filter
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by product
        product_id = self.request.query_params.get('product')  # None means no filter
        if product_id:
            queryset = queryset.filter(recipe__product_id=product_id)
        
        # Filter by date range
        date_from = self.request.query_params.get('date_from')  # None means no filter
        date_to = self.request.query_params.get('date_to')  # None means no filter
        
        if date_from:
            queryset = queryset.filter(planned_date__gte=date_from)
        if date_to:
            queryset = queryset.filter(planned_date__lte=date_to)
        
        return queryset.order_by('-planned_date')
    
    @action(detail=True, methods=['post'])
    def start_production(self, request, pk=None):
        """Start a production batch"""
        batch = self.get_object()
        serializer = ProductionStartSerializer(data=request.data)
        
        if serializer.is_valid():
            if batch.status != 'planned':
                return Response(
                    {'error': 'Only planned batches can be started'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            batch.status = 'in_progress'
            batch.started_at = serializer.validated_data.get(
                'actual_start_time', timezone.now()
            )
            batch.produced_by = request.user
            
            if serializer.validated_data.get('notes'):
                batch.notes += f"\nStarted: {serializer.validated_data['notes']}"
            
            batch.save()
            
            return Response(
                ProductionBatchDetailSerializer(batch).data,
                status=status.HTTP_200_OK
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def complete_production(self, request, pk=None):
        """Complete a production batch"""
        batch = self.get_object()
        serializer = ProductionCompleteSerializer(data=request.data)
        
        if serializer.is_valid():
            if batch.status != 'in_progress':
                return Response(
                    {'error': 'Only in-progress batches can be completed'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Update batch with completion data
            batch.status = 'completed'
            batch.actual_quantity = serializer.validated_data['actual_quantity']
            waste_quantity = serializer.validated_data.get('waste_quantity')
            batch.waste_quantity = waste_quantity if waste_quantity is not None else 0
            batch.completed_at = serializer.validated_data.get(
                'actual_completion_time', timezone.now()
            )
            labor_cost = serializer.validated_data.get('labor_cost')
            batch.labor_cost = labor_cost if labor_cost is not None else 0
            overhead_cost = serializer.validated_data.get('overhead_cost')
            batch.overhead_cost = overhead_cost if overhead_cost is not None else 0
            
            if serializer.validated_data.get('notes'):
                batch.notes += f"\nCompleted: {serializer.validated_data['notes']}"
            
            batch.save()
            
            # The signals will handle updating finished inventory
            
            return Response(
                ProductionBatchDetailSerializer(batch).data,
                status=status.HTTP_200_OK
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class StockAlertViewSet(viewsets.ModelViewSet):
    queryset = StockAlert.objects.all()
    serializer_class = StockAlertSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = StockAlert.objects.select_related(
            'raw_material', 'product', 'raw_material_batch', 'acknowledged_by'
        ).all()
        
        # Filter by alert type
        alert_type = self.request.query_params.get('alert_type')  # None means no filter
        if alert_type:
            queryset = queryset.filter(alert_type=alert_type)
        
        # Filter by severity
        severity = self.request.query_params.get('severity')  # None means no filter
        if severity:
            queryset = queryset.filter(severity=severity)
        
        # Filter by active status
        is_active = self.request.query_params.get('is_active')  # None means no filter
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        # Filter by acknowledged status
        is_acknowledged = self.request.query_params.get('is_acknowledged')  # None means no filter
        if is_acknowledged is not None:
            queryset = queryset.filter(is_acknowledged=is_acknowledged.lower() == 'true')
        
        return queryset.order_by('-created_at')
    
    @action(detail=True, methods=['post'])
    def acknowledge(self, request, pk=None):
        """Acknowledge an alert"""
        alert = self.get_object()
        alert.acknowledge(request.user)
        
        return Response(
            self.get_serializer(alert).data,
            status=status.HTTP_200_OK
        )
    
    @action(detail=False, methods=['post'])
    def acknowledge_multiple(self, request):
        """Acknowledge multiple alerts"""
        alert_ids = request.data.get('alert_ids')
        if alert_ids is None:
            alert_ids = []
        
        if not alert_ids:
            return Response(
                {'error': 'alert_ids required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        alerts = StockAlert.objects.filter(id__in=alert_ids)
        
        for alert in alerts:
            alert.acknowledge(request.user)
        
        return Response(
            {'acknowledged': len(alerts)},
            status=status.HTTP_200_OK
        )


# Dashboard and Action Views
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def inventory_dashboard(request):
    """Get inventory dashboard summary"""
    from datetime import date, timedelta
    
    # Calculate summary statistics
    dashboard_data = {
        'total_products': FinishedInventory.objects.count(),
        'total_raw_materials': RawMaterial.objects.filter(is_active=True).count(),
        'low_stock_alerts': StockAlert.objects.filter(
            alert_type__in=['low_stock', 'out_of_stock'],
            is_active=True,
            is_acknowledged=False
        ).count(),
        'expiring_batches': RawMaterialBatch.objects.filter(
            expiry_date__lte=date.today() + timedelta(days=7),
            expiry_date__gte=date.today(),
            available_quantity__gt=0,
            is_active=True
        ).count(),
        'active_production_batches': ProductionBatch.objects.filter(
            status='in_progress'
        ).count(),
        'total_stock_value': FinishedInventory.objects.aggregate(
            total=Sum(F('available_quantity') * F('average_cost'))
        )['total'] or Decimal('0.00')
    }
    
    serializer = InventoryDashboardSerializer(dashboard_data)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def stock_levels(request):
    """Get current stock levels for all products"""
    from products.models import Product
    
    # Get all products with their inventory data (if it exists)
    products = Product.objects.select_related('department').all()
    
    stock_data = []
    for product in products:
        # Get the FinishedInventory record if it exists
        try:
            inventory = getattr(product, 'inventory', None)
            if inventory:
                available_quantity = inventory.available_quantity
                reserved_quantity = inventory.reserved_quantity
                minimum_level = inventory.minimum_level
                reorder_level = inventory.reorder_level
                needs_production = inventory.needs_production
                average_cost = inventory.average_cost
            else:
                # Use product stock_level if no FinishedInventory record exists
                available_quantity = product.stock_level or 0
                reserved_quantity = 0
                minimum_level = 5
                reorder_level = 10
                needs_production = False
                average_cost = product.price
        except Exception:
            # Fallback to product stock_level
            available_quantity = product.stock_level or 0
            reserved_quantity = 0
            minimum_level = 5
            reorder_level = 10
            needs_production = False
            average_cost = product.price
        
        stock_data.append({
            'product_id': product.id,
            'product_name': product.name,
            'department': product.department.name,
            'unit': product.unit,  # Use the correct unit field from Product model
            'available_quantity': available_quantity,
            'reserved_quantity': reserved_quantity,
            'minimum_level': minimum_level,
            'reorder_level': reorder_level,
            'needs_production': needs_production,
            'average_cost': average_cost
        })
    
    serializer = StockLevelSerializer(stock_data, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reserve_stock(request):
    """Reserve stock for an order"""
    serializer = StockReservationSerializer(data=request.data)
    
    if serializer.is_valid():
        try:
            product = Product.objects.get(id=serializer.validated_data['product_id'])
            inventory = FinishedInventory.objects.get(product=product)
            
            quantity = serializer.validated_data['quantity']
            
            if inventory.reserve_stock(quantity):
                # Create stock movement record
                StockMovement.objects.create(
                    movement_type='finished_reserve',
                    reference_number=serializer.validated_data['reference_number'],
                    product=product,
                    quantity=quantity,
                    user=request.user,
                    notes=serializer.validated_data.get('notes') or ''
                )
                
                return Response(
                    FinishedInventorySerializer(inventory).data,
                    status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {'error': f'Insufficient stock. Available: {inventory.available_quantity}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        except (Product.DoesNotExist, FinishedInventory.DoesNotExist):
            return Response(
                {'error': 'Product or inventory not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def stock_adjustment(request):
    """Manual stock adjustment"""
    import logging
    logger = logging.getLogger('inventory')
    
    logger.info(f"Stock adjustment request received: {request.data}")
    serializer = StockAdjustmentSerializer(data=request.data)
    
    if serializer.is_valid():
        data = serializer.validated_data
        movement_type = data['adjustment_type']
        quantity = data['quantity']
        reason = data['reason']
        notes = data.get('notes') or ''
        
        logger.debug(f"Validated data: movement_type={movement_type}, quantity={quantity}, reason={reason}")
        
        try:
            if movement_type in ['finished_adjust', 'finished_waste']:
                # Finished inventory adjustment
                product = Product.objects.get(id=data['product_id'])
                
                # Get or create FinishedInventory record
                inventory, created = FinishedInventory.objects.get_or_create(
                    product=product,
                    defaults={
                        'available_quantity': product.stock_level or 0,
                        'reserved_quantity': 0,
                        'minimum_level': 10,  # Default minimum level
                        'reorder_level': 20,  # Default reorder level
                        'average_cost': product.price or 0,
                    }
                )
                
                if created:
                    logger.info(f"Created new FinishedInventory record for product {product.name} (ID: {product.id})")
                
                logger.info(f"Adjusting stock for product {product.name} (ID: {product.id})")
                logger.debug(f"Before adjustment - Product stock: {product.stock_level}, Inventory available: {inventory.available_quantity}")
                
                # Update FinishedInventory first, then sync Product
                if movement_type == 'finished_adjust':
                    inventory.available_quantity += quantity
                else:  # waste
                    inventory.available_quantity -= quantity
                
                # Sync Product stock_level to match FinishedInventory
                product.stock_level = inventory.available_quantity
                
                # Save both models
                inventory.save()
                product.save()
                
                logger.info(f"Stock adjustment completed. New levels - Product: {product.stock_level}, Inventory: {inventory.available_quantity}")
                
                # Create movement record
                StockMovement.objects.create(
                    movement_type=movement_type,
                    reference_number=f"ADJ-{timezone.now().strftime('%Y%m%d%H%M%S')}",
                    product=product,
                    quantity=quantity,
                    user=request.user,
                    notes=f"Reason: {reason}. {notes}".strip()
                )
                
                return Response(
                    FinishedInventorySerializer(inventory).data,
                    status=status.HTTP_200_OK
                )
            
            elif movement_type in ['raw_adjust', 'raw_waste']:
                # Raw material adjustment
                raw_material = RawMaterial.objects.get(id=data['raw_material_id'])
                batch_id = data.get('batch_id')
                
                if batch_id:
                    batch = RawMaterialBatch.objects.get(
                        id=batch_id, raw_material=raw_material
                    )
                    
                    if movement_type == 'raw_adjust':
                        batch.available_quantity += quantity
                    else:  # waste
                        batch.available_quantity -= quantity
                    
                    batch.save()
                    
                    # Create movement record
                    StockMovement.objects.create(
                        movement_type=movement_type,
                        reference_number=f"ADJ-{timezone.now().strftime('%Y%m%d%H%M%S')}",
                        raw_material=raw_material,
                        raw_material_batch=batch,
                        quantity=quantity,
                        user=request.user,
                        notes=f"Reason: {reason}. {notes}".strip()
                    )
                    
                    return Response(
                        RawMaterialBatchDetailSerializer(batch).data,
                        status=status.HTTP_200_OK
                    )
                else:
                    return Response(
                        {'error': 'batch_id required for raw material adjustments'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
        
        except Exception as e:
            logger.error(f"Inventory adjustment failed: {str(e)}")
            return Response(
                {
                    'error': 'Unable to adjust inventory',
                    'message': 'An error occurred while adjusting inventory levels. Please verify your input and try again.',
                    'details': str(e)
                },
                status=status.HTTP_400_BAD_REQUEST
            )
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class StockAnalysisViewSet(viewsets.ModelViewSet):
    """ViewSet for Stock Analysis operations"""
    queryset = StockAnalysis.objects.all()
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return StockAnalysisListSerializer
        elif self.action == 'create':
            return StockAnalysisCreateSerializer
        return StockAnalysisDetailSerializer
    
    def get_queryset(self):
        queryset = StockAnalysis.objects.select_related('created_by').prefetch_related(
            'items__product__department',
            'items__suggested_supplier'
        )
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(analysis_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(analysis_date__lte=end_date)
        
        return queryset.order_by('-analysis_date')
    
    def perform_create(self, serializer):
        """Set the created_by user when creating analysis"""
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def run_analysis(self, request, pk=None):
        """Run the stock analysis calculation"""
        analysis = self.get_object()
        
        if analysis.status != 'analyzing':
            return Response(
                {'error': 'Analysis must be in analyzing status to run'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Import here to avoid circular imports
            from orders.models import Order, OrderItem
            
            # Get orders in the analysis period
            orders = Order.objects.filter(
                order_date__gte=analysis.order_period_start,
                order_date__lte=analysis.order_period_end,
                status__in=['received', 'parsed', 'confirmed']  # Active orders
            ).prefetch_related('items__product')
            
            # Calculate totals
            total_orders_value = Decimal('0.00')
            total_stock_value = Decimal('0.00')
            product_demands = {}  # product_id -> total_quantity
            
            # Aggregate demand by product
            for order in orders:
                for item in order.items.all():
                    if item.product:
                        product_id = item.product.id
                        if product_id not in product_demands:
                            product_demands[product_id] = {
                                'product': item.product,
                                'total_quantity': Decimal('0.00'),
                                'total_value': Decimal('0.00')
                            }
                        
                        quantity = item.quantity or Decimal('0.00')
                        unit_price = item.unit_price or Decimal('0.00')
                        
                        product_demands[product_id]['total_quantity'] += quantity
                        product_demands[product_id]['total_value'] += (quantity * unit_price)
                        total_orders_value += (quantity * unit_price)
            
            # Clear existing analysis items
            analysis.items.all().delete()
            
            # Create analysis items for each product
            fulfillment_count = 0
            total_products = len(product_demands)
            
            for product_id, demand_data in product_demands.items():
                product = demand_data['product']
                total_ordered = demand_data['total_quantity']
                
                # Get available stock
                try:
                    inventory = FinishedInventory.objects.get(product=product)
                    available_stock = inventory.available_quantity or Decimal('0.00')
                    unit_price = inventory.average_cost or Decimal('0.00')
                except FinishedInventory.DoesNotExist:
                    available_stock = Decimal('0.00')
                    unit_price = Decimal('0.00')
                
                total_stock_value += (available_stock * unit_price)
                
                # Calculate shortfall
                shortfall = max(Decimal('0.00'), total_ordered - available_stock)
                
                # Determine suggested supplier (simplified - pick first active supplier)
                from suppliers.models import Supplier
                suggested_supplier = Supplier.objects.filter(is_active=True).first()
                
                # Create analysis item
                StockAnalysisItem.objects.create(
                    analysis=analysis,
                    product=product,
                    total_ordered_quantity=total_ordered,
                    available_stock_quantity=available_stock,
                    unit_price=unit_price,
                    suggested_order_quantity=shortfall * Decimal('1.2') if shortfall > 0 else None,  # 20% buffer
                    suggested_supplier=suggested_supplier
                )
                
                # Count fulfilled items
                if shortfall == 0:
                    fulfillment_count += 1
            
            # Update analysis totals
            analysis.total_orders_value = total_orders_value
            analysis.total_stock_value = total_stock_value
            analysis.fulfillment_percentage = (
                (fulfillment_count / total_products * 100) if total_products > 0 else Decimal('100.00')
            )
            analysis.status = 'completed'
            analysis.save()
            
            return Response(
                StockAnalysisDetailSerializer(analysis).data,
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            analysis.status = 'action_required'
            analysis.notes = f"Analysis failed: {str(e)}"
            analysis.save()
            
            return Response(
                {'error': f'Analysis failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def analyze_current_period(self, request):
        """Create and run analysis for current Monday-Thursday period"""
        from datetime import date, timedelta
        
        # Find current or next Monday
        today = date.today()
        days_since_monday = today.weekday()  # Monday = 0
        
        if days_since_monday <= 3:  # Monday to Thursday
            monday = today - timedelta(days=days_since_monday)
        else:  # Friday to Sunday
            monday = today + timedelta(days=(7 - days_since_monday))
        
        thursday = monday + timedelta(days=3)
        
        # Check if analysis already exists for this period
        existing = StockAnalysis.objects.filter(
            order_period_start=monday,
            order_period_end=thursday
        ).first()
        
        if existing:
            return Response(
                StockAnalysisDetailSerializer(existing).data,
                status=status.HTTP_200_OK
            )
        
        # Create new analysis
        analysis = StockAnalysis.objects.create(
            order_period_start=monday,
            order_period_end=thursday,
            status='analyzing',
            total_orders_value=Decimal('0.00'),
            total_stock_value=Decimal('0.00'),
            fulfillment_percentage=Decimal('0.00'),
            created_by=request.user,
            notes=f"Auto-generated analysis for {monday} to {thursday}"
        )
        
        # Run the analysis
        return self.run_analysis(request, pk=analysis.pk)


# Market Price and Procurement Intelligence ViewSets

class MarketPriceViewSet(viewsets.ModelViewSet):
    """ViewSet for market price tracking and analysis"""
    
    queryset = MarketPrice.objects.all()
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return MarketPriceCreateSerializer
        return MarketPriceSerializer
    
    def get_queryset(self):
        queryset = MarketPrice.objects.select_related('matched_product').order_by('-invoice_date', '-created_at')
        
        # Filter by supplier
        supplier = self.request.query_params.get('supplier')
        if supplier:
            queryset = queryset.filter(supplier_name__icontains=supplier)
        
        # Filter by product
        product = self.request.query_params.get('product')
        if product:
            queryset = queryset.filter(
                models.Q(product_name__icontains=product) |
                models.Q(matched_product__name__icontains=product)
            )
        
        # Filter by date range
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        if date_from:
            queryset = queryset.filter(invoice_date__gte=date_from)
        if date_to:
            queryset = queryset.filter(invoice_date__lte=date_to)
        
        # Filter by active status
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        return queryset
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def bulk_import(self, request):
        """Bulk import market prices from invoice data"""
        data = request.data
        
        if not isinstance(data, list):
            return Response(
                {'error': 'Expected a list of market price records'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        created_prices = []
        errors = []
        
        for i, price_data in enumerate(data):
            serializer = MarketPriceCreateSerializer(data=price_data)
            if serializer.is_valid():
                try:
                    price = serializer.save()
                    created_prices.append(MarketPriceSerializer(price).data)
                except Exception as e:
                    errors.append(f"Row {i+1}: {str(e)}")
            else:
                errors.append(f"Row {i+1}: {serializer.errors}")
        
        return Response({
            'created_count': len(created_prices),
            'error_count': len(errors),
            'created_prices': created_prices,
            'errors': errors
        }, status=status.HTTP_201_CREATED if created_prices else status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def price_trends(self, request):
        """Analyze price trends for products"""
        product_id = request.query_params.get('product_id')
        days_param = request.query_params.get('days')
        
        if not product_id:
            return Response(
                {'error': 'product_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if days_param is None:
            return Response(
                {'error': 'days parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            days = int(days_param)
            if days <= 0:
                return Response(
                    {'error': 'days must be a positive integer'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except ValueError:
            return Response(
                {'error': 'days must be a valid integer'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        from datetime import date, timedelta
        from django.db.models import Avg, Min, Max, Count
        
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        
        # Get price data for the product
        prices = MarketPrice.objects.filter(
            matched_product_id=product_id,
            invoice_date__gte=start_date,
            is_active=True
        ).order_by('invoice_date')
        
        if not prices.exists():
            return Response(
                {'error': 'No price data found for this product in the specified period'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Calculate statistics
        stats = prices.aggregate(
            avg_price=Avg('unit_price_incl_vat'),
            min_price=Min('unit_price_incl_vat'),
            max_price=Max('unit_price_incl_vat'),
            data_points=Count('id')
        )
        
        # Calculate trend
        price_list = list(prices.values_list('unit_price_incl_vat', flat=True))
        if len(price_list) > 1:
            first_half = price_list[:len(price_list)//2]
            second_half = price_list[len(price_list)//2:]
            
            avg_first = sum(first_half) / len(first_half)
            avg_second = sum(second_half) / len(second_half)
            
            trend_percentage = ((avg_second - avg_first) / avg_first) * 100
            
            if trend_percentage > 5:
                trend = 'rising'
            elif trend_percentage < -5:
                trend = 'falling'
            elif abs(trend_percentage) > 15:
                trend = 'volatile'
            else:
                trend = 'stable'
        else:
            trend = 'stable'
            trend_percentage = 0
        
        # Get recent prices
        recent_prices = MarketPriceSerializer(prices[:10], many=True).data
        
        return Response({
            'product_id': product_id,
            'period': f"{start_date} to {end_date}",
            'statistics': stats,
            'trend': trend,
            'trend_percentage': round(trend_percentage, 2),
            'recent_prices': recent_prices
        })


class ProcurementRecommendationViewSet(viewsets.ModelViewSet):
    """ViewSet for procurement recommendations"""
    
    queryset = ProcurementRecommendation.objects.all()
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ProcurementRecommendationListSerializer
        elif self.action == 'create':
            return ProcurementRecommendationCreateSerializer
        return ProcurementRecommendationSerializer
    
    def get_queryset(self):
        queryset = ProcurementRecommendation.objects.select_related(
            'product', 'recommended_supplier', 'stock_analysis', 'created_by'
        ).order_by('-urgency_level', 'recommended_order_date')
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by urgency
        urgency = self.request.query_params.get('urgency')
        if urgency:
            queryset = queryset.filter(urgency_level=urgency)
        
        # Filter by overdue
        overdue = self.request.query_params.get('overdue')
        if overdue and overdue.lower() == 'true':
            from datetime import date
            queryset = queryset.filter(
                recommended_order_date__lt=date.today(),
                status='pending'
            )
        
        # Filter by product
        product = self.request.query_params.get('product')
        if product:
            queryset = queryset.filter(product__name__icontains=product)
        
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def approve(self, request, pk=None):
        """Approve a procurement recommendation"""
        recommendation = self.get_object()
        recommendation.status = 'approved'
        recommendation.save()
        
        return Response(
            ProcurementRecommendationSerializer(recommendation).data,
            status=status.HTTP_200_OK
        )
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def reject(self, request, pk=None):
        """Reject a procurement recommendation"""
        recommendation = self.get_object()
        recommendation.status = 'rejected'
        recommendation.notes = request.data.get('reason', recommendation.notes)
        recommendation.save()
        
        return Response(
            ProcurementRecommendationSerializer(recommendation).data,
            status=status.HTTP_200_OK
        )
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def generate_from_analysis(self, request):
        """Generate procurement recommendations from stock analysis"""
        analysis_id = request.data.get('analysis_id')
        
        if not analysis_id:
            return Response(
                {'error': 'analysis_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            analysis = StockAnalysis.objects.get(id=analysis_id)
        except StockAnalysis.DoesNotExist:
            return Response(
                {'error': 'Stock analysis not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Generate recommendations for items needing procurement
        recommendations = []
        
        for item in analysis.items_needing_procurement.all():
            # Get latest market price
            latest_price = MarketPrice.objects.filter(
                matched_product=item.product,
                is_active=True
            ).order_by('-invoice_date').first()
            
            # Calculate 30-day average price
            from datetime import date, timedelta
            thirty_days_ago = date.today() - timedelta(days=30)
            avg_price = MarketPrice.objects.filter(
                matched_product=item.product,
                invoice_date__gte=thirty_days_ago,
                is_active=True
            ).aggregate(avg_price=models.Avg('unit_price_incl_vat'))['avg_price']
            
            # Determine recommended order date based on urgency
            from datetime import date, timedelta
            if item.urgency_level == 'urgent':
                order_date = date.today()
            elif item.urgency_level == 'high':
                order_date = date.today() + timedelta(days=1)
            elif item.urgency_level == 'medium':
                order_date = date.today() + timedelta(days=3)
            else:
                order_date = date.today() + timedelta(days=7)
            
            # Create recommendation
            recommendation = ProcurementRecommendation.objects.create(
                stock_analysis=analysis,
                product=item.product,
                recommended_quantity=item.suggested_order_quantity or item.shortfall_quantity,
                recommended_supplier=item.suggested_supplier,
                current_market_price=latest_price.unit_price_incl_vat if latest_price else None,
                average_market_price_30d=avg_price,
                urgency_level=item.urgency_level,
                recommended_order_date=order_date,
                created_by=request.user,
                notes=f"Auto-generated from stock analysis {analysis.id}"
            )
            
            recommendations.append(recommendation)
        
        return Response({
            'generated_count': len(recommendations),
            'recommendations': ProcurementRecommendationSerializer(recommendations, many=True).data
        }, status=status.HTTP_201_CREATED)


class PriceAlertViewSet(viewsets.ModelViewSet):
    """ViewSet for price alerts and volatility monitoring"""
    
    queryset = PriceAlert.objects.all()
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return PriceAlertCreateSerializer
        return PriceAlertSerializer
    
    def get_queryset(self):
        queryset = PriceAlert.objects.select_related(
            'product', 'acknowledged_by'
        ).order_by('-alert_triggered_at')
        
        # Filter by acknowledgment status
        acknowledged = self.request.query_params.get('acknowledged')
        if acknowledged is not None:
            queryset = queryset.filter(is_acknowledged=acknowledged.lower() == 'true')
        
        # Filter by alert type
        alert_type = self.request.query_params.get('alert_type')
        if alert_type:
            queryset = queryset.filter(alert_type=alert_type)
        
        # Filter by product
        product = self.request.query_params.get('product')
        if product:
            queryset = queryset.filter(product__name__icontains=product)
        
        return queryset
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def acknowledge(self, request, pk=None):
        """Acknowledge a price alert"""
        alert = self.get_object()
        alert.acknowledge(request.user)
        
        return Response(
            PriceAlertSerializer(alert).data,
            status=status.HTTP_200_OK
        )
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def acknowledge_all(self, request):
        """Acknowledge all unacknowledged alerts"""
        alerts = PriceAlert.objects.filter(is_acknowledged=False)
        count = 0
        
        for alert in alerts:
            alert.acknowledge(request.user)
            count += 1
        
        return Response({
            'acknowledged_count': count,
            'message': f'Acknowledged {count} alerts'
        }, status=status.HTTP_200_OK)


# Dynamic Price Management ViewSets

class PricingRuleViewSet(viewsets.ModelViewSet):
    """ViewSet for pricing rules management"""
    
    queryset = PricingRule.objects.all()
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return PricingRuleCreateSerializer
        return PricingRuleSerializer
    
    def get_queryset(self):
        queryset = PricingRule.objects.select_related('created_by').order_by('-created_at')
        
        # Filter by customer segment
        segment = self.request.query_params.get('segment')
        if segment:
            queryset = queryset.filter(customer_segment=segment)
        
        # Filter by active status
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        # Filter by effectiveness (current date)
        effective = self.request.query_params.get('effective')
        if effective and effective.lower() == 'true':
            from datetime import date
            today = date.today()
            queryset = queryset.filter(
                is_active=True,
                effective_from__lte=today
            ).filter(
                models.Q(effective_until__isnull=True) | 
                models.Q(effective_until__gte=today)
            )
        
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def test_markup(self, request, pk=None):
        """Test markup calculation for a pricing rule"""
        rule = self.get_object()
        
        # Get test parameters - require explicit values
        market_price_str = request.data.get('market_price')
        volatility_level = request.data.get('volatility_level')
        
        if market_price_str is None:
            return Response(
                {'error': 'market_price parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if volatility_level is None:
            return Response(
                {'error': 'volatility_level parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            market_price = Decimal(market_price_str)
            if market_price <= 0:
                return Response(
                    {'error': 'market_price must be greater than 0'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except (ValueError, TypeError):
            return Response(
                {'error': 'market_price must be a valid decimal number'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        valid_volatility_levels = ['stable', 'volatile', 'highly_volatile', 'extremely_volatile']
        if volatility_level not in valid_volatility_levels:
            return Response(
                {'error': f'volatility_level must be one of: {", ".join(valid_volatility_levels)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Calculate markup
        markup_percentage = rule.calculate_markup(None, market_price, volatility_level)
        customer_price = market_price * (1 + markup_percentage / 100)
        margin_amount = customer_price - market_price
        
        return Response({
            'rule_name': rule.name,
            'market_price': market_price,
            'volatility_level': volatility_level,
            'markup_percentage': markup_percentage,
            'customer_price': customer_price,
            'margin_amount': margin_amount,
            'calculation_breakdown': {
                'base_markup': rule.base_markup_percentage,
                'volatility_adjustment': rule.volatility_adjustment if volatility_level in ['volatile', 'rising'] else 0,
                'trend_multiplier': rule.trend_multiplier,
                'seasonal_adjustment': rule.seasonal_adjustment,
                'minimum_margin_applied': markup_percentage == rule.minimum_margin_percentage
            }
        })


class CustomerPriceListViewSet(viewsets.ModelViewSet):
    """ViewSet for customer price lists"""
    
    queryset = CustomerPriceList.objects.all()
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return CustomerPriceListDetailSerializer
        elif self.action == 'create':
            return CustomerPriceListCreateSerializer
        return CustomerPriceListSerializer
    
    def get_queryset(self):
        queryset = CustomerPriceList.objects.select_related(
            'customer', 'pricing_rule', 'generated_by'
        ).order_by('-generated_at')
        
        # Filter by customer
        customer_id = self.request.query_params.get('customer')
        if customer_id:
            queryset = queryset.filter(customer_id=customer_id)
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by current/active lists
        current = self.request.query_params.get('current')
        if current and current.lower() == 'true':
            from datetime import date
            today = date.today()
            queryset = queryset.filter(
                effective_from__lte=today,
                effective_until__gte=today
            )
        
        # Filter by pricing rule segment
        segment = self.request.query_params.get('segment')
        if segment:
            queryset = queryset.filter(pricing_rule__customer_segment=segment)
        
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(generated_by=self.request.user)
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def generate_from_market_data(self, request):
        """Generate customer price lists from latest market data"""
        customer_ids = request.data.get('customer_ids', [])
        pricing_rule_id = request.data.get('pricing_rule_id')
        market_data_date = request.data.get('market_data_date')
        
        if not customer_ids or not pricing_rule_id:
            return Response(
                {'error': 'customer_ids and pricing_rule_id are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            pricing_rule = PricingRule.objects.get(id=pricing_rule_id)
        except PricingRule.DoesNotExist:
            return Response(
                {'error': 'Pricing rule not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Parse market data date
        if market_data_date:
            from datetime import datetime
            try:
                market_date = datetime.strptime(market_data_date, '%Y-%m-%d').date()
            except ValueError:
                return Response(
                    {'error': 'Invalid date format. Use YYYY-MM-DD'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            from datetime import date
            market_date = date.today()
        
        generated_lists = []
        errors = []
        
        for customer_id in customer_ids:
            try:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                customer = User.objects.get(id=customer_id)
                
                # Create price list
                from datetime import date, timedelta
                effective_from = date.today()
                effective_until = effective_from + timedelta(days=7)  # Weekly price lists
                
                # Generate customer name for price list
                customer_display_name = customer.get_full_name() or customer.email.split('@')[0]
                
                price_list = CustomerPriceList.objects.create(
                    customer=customer,
                    pricing_rule=pricing_rule,
                    list_name=f"Weekly Price List - {customer_display_name} - {effective_from}",
                    effective_from=effective_from,
                    effective_until=effective_until,
                    based_on_market_data=market_date,
                    generated_by=request.user,
                    notes=f"Auto-generated from market data dated {market_date}"
                )
                
                # Generate price list items from market data
                items_created = self._generate_price_list_items(price_list, market_date)
                
                # Update statistics
                price_list.total_products = items_created
                if items_created > 0:
                    avg_markup = price_list.items.aggregate(
                        avg=models.Avg('markup_percentage')
                    )['avg'] or Decimal('0.00')
                    total_value = price_list.items.aggregate(
                        total=models.Sum('customer_price_incl_vat')
                    )['total'] or Decimal('0.00')
                    
                    price_list.average_markup_percentage = avg_markup
                    price_list.total_list_value = total_value
                    price_list.status = 'generated'
                
                price_list.save()
                generated_lists.append(CustomerPriceListSerializer(price_list).data)
                
            except Exception as e:
                errors.append(f"Customer {customer_id}: {str(e)}")
        
        return Response({
            'generated_count': len(generated_lists),
            'error_count': len(errors),
            'generated_lists': generated_lists,
            'errors': errors
        }, status=status.HTTP_201_CREATED if generated_lists else status.HTTP_400_BAD_REQUEST)
    
    def _generate_price_list_items(self, price_list, market_date):
        """Generate price list items from market data or product base prices"""
        items_created = 0
        
        # Debug: Check total market prices available
        total_market_prices = MarketPrice.objects.filter(
            invoice_date__lte=market_date,
            is_active=True
        ).count()
        
        matched_market_prices = MarketPrice.objects.filter(
            invoice_date__lte=market_date,
            is_active=True,
            matched_product__isnull=False
        ).count()
        
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Market price analysis: Total={total_market_prices}, Matched={matched_market_prices}")
        
        # ENHANCEMENT: Fallback to product base prices if no market data available
        if matched_market_prices == 0:
            logger.info("No market price data found, using product base prices as fallback")
            return self._generate_price_list_items_from_products(price_list)
        
        # Get latest market prices for the date
        market_prices = MarketPrice.objects.filter(
            invoice_date__lte=market_date,
            is_active=True,
            matched_product__isnull=False
        ).select_related('matched_product').order_by('matched_product', '-invoice_date')
        
        # Get unique products with their latest prices
        seen_products = set()
        for market_price in market_prices:
            if market_price.matched_product.id in seen_products:
                continue
            seen_products.add(market_price.matched_product.id)
            
            # Calculate volatility level
            volatility_level = self._calculate_product_volatility(market_price.matched_product)
            
            # Calculate markup using pricing rule
            markup_percentage = price_list.pricing_rule.calculate_markup(
                market_price.matched_product,
                market_price.unit_price_incl_vat,
                volatility_level
            )
            
            # Calculate customer prices
            customer_price_excl_vat = market_price.unit_price_excl_vat * (1 + markup_percentage / 100)
            customer_price_incl_vat = market_price.unit_price_incl_vat * (1 + markup_percentage / 100)
            
            # Get previous price for comparison
            previous_price = None
            previous_item = CustomerPriceListItem.objects.filter(
                price_list__customer=price_list.customer,
                product=market_price.matched_product,
                price_list__effective_from__lt=price_list.effective_from
            ).order_by('-price_list__effective_from').first()
            
            if previous_item:
                previous_price = previous_item.customer_price_incl_vat
            
            # Calculate price change
            price_change_percentage = Decimal('0.00')
            if previous_price and previous_price > 0:
                price_change_percentage = ((customer_price_incl_vat - previous_price) / previous_price) * 100
            
            # Create price list item
            CustomerPriceListItem.objects.create(
                price_list=price_list,
                product=market_price.matched_product,
                market_price_excl_vat=market_price.unit_price_excl_vat,
                market_price_incl_vat=market_price.unit_price_incl_vat,
                market_price_date=market_price.invoice_date,
                markup_percentage=markup_percentage,
                customer_price_excl_vat=customer_price_excl_vat,
                customer_price_incl_vat=customer_price_incl_vat,
                previous_price=previous_price,
                price_change_percentage=price_change_percentage,
                unit_of_measure=market_price.quantity_unit,
                product_category=market_price.matched_product.department.name if market_price.matched_product.department else '',
                is_volatile=volatility_level in ['volatile', 'highly_volatile', 'extremely_volatile'],
                is_premium=markup_percentage > 50
            )
            items_created += 1
        
        logger.info(f"Created {items_created} price list items for customer {price_list.customer.email}")
        
        return items_created
    
    def _generate_price_list_items_from_products(self, price_list):
        """Generate price list items from product base prices (fallback when no market data)"""
        items_created = 0
        
        # Get all active products
        from products.models import Product
        products = Product.objects.filter(is_active=True)[:50]  # Limit to 50 products for testing
        
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Creating price list items from {products.count()} products")
        
        for product in products:
            try:
                # Use product base price as market price
                market_price_excl_vat = product.price
                market_price_incl_vat = product.price * Decimal('1.15')  # Add 15% VAT
                
                # Calculate markup using pricing rule
                markup_percentage = price_list.pricing_rule.base_markup_percentage
                
                # Calculate customer prices
                customer_price_excl_vat = market_price_excl_vat * (1 + markup_percentage / 100)
                customer_price_incl_vat = market_price_incl_vat * (1 + markup_percentage / 100)
                
                # Create price list item
                CustomerPriceListItem.objects.create(
                    price_list=price_list,
                    product=product,
                    market_price_excl_vat=market_price_excl_vat,
                    market_price_incl_vat=market_price_incl_vat,
                    market_price_date=price_list.effective_from,
                    markup_percentage=markup_percentage,
                    customer_price_excl_vat=customer_price_excl_vat,
                    customer_price_incl_vat=customer_price_incl_vat,
                    unit_of_measure=product.unit,
                    product_category=product.department.name if product.department else 'General',
                    is_volatile=False,
                    is_seasonal=False,
                    is_premium=False
                )
                
                items_created += 1
                
            except Exception as e:
                logger.error(f"Error creating price list item for product {product.name}: {e}")
                continue
        
        logger.info(f"Created {items_created} price list items from product base prices")
        return items_created
    
    def _calculate_product_volatility(self, product):
        """Calculate volatility level for a product"""
        from datetime import date, timedelta
        thirty_days_ago = date.today() - timedelta(days=30)
        
        prices = MarketPrice.objects.filter(
            matched_product=product,
            invoice_date__gte=thirty_days_ago,
            is_active=True
        ).values_list('unit_price_incl_vat', flat=True)
        
        if len(prices) < 2:
            return 'stable'
        
        prices_list = list(prices)
        min_price = min(prices_list)
        max_price = max(prices_list)
        
        if min_price > 0:
            volatility = ((max_price - min_price) / min_price) * 100
            
            if volatility > 50:
                return 'extremely_volatile'
            elif volatility > 25:
                return 'highly_volatile'
            elif volatility > 10:
                return 'volatile'
        
        return 'stable'
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def activate(self, request, pk=None):
        """Activate a price list"""
        price_list = self.get_object()
        price_list.activate()
        
        return Response(
            CustomerPriceListSerializer(price_list).data,
            status=status.HTTP_200_OK
        )
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def send_to_customer(self, request, pk=None):
        """Mark price list as sent to customer"""
        price_list = self.get_object()
        price_list.status = 'sent'
        price_list.sent_at = timezone.now()
        price_list.save()
        
        return Response(
            CustomerPriceListSerializer(price_list).data,
            status=status.HTTP_200_OK
        )
    
    def update(self, request, *args, **kwargs):
        """Update price list and regenerate prices if pricing rule changed"""
        from decimal import Decimal
        from django.db import models
        
        price_list = self.get_object()
        old_pricing_rule_id = price_list.pricing_rule_id
        
        # Perform the standard update
        response = super().update(request, *args, **kwargs)
        
        # Check if pricing rule was changed
        updated_price_list = self.get_object()
        if updated_price_list.pricing_rule_id != old_pricing_rule_id:
            # Clear existing items
            updated_price_list.items.all().delete()
            
            # Regenerate items with new pricing rule
            items_created = self._generate_price_list_items(updated_price_list, None)
            
            # Update totals
            updated_price_list.total_products = items_created
            if items_created > 0:
                avg_markup = updated_price_list.items.aggregate(
                    avg=models.Avg('markup_percentage')
                )['avg'] or Decimal('0.00')
                total_value = updated_price_list.items.aggregate(
                    total=models.Sum('customer_price_incl_vat')
                )['total'] or Decimal('0.00')
                
                updated_price_list.average_markup_percentage = avg_markup
                updated_price_list.total_list_value = total_value
            updated_price_list.save()
            
            # Return updated data
            serializer = self.get_serializer(updated_price_list)
            return Response(serializer.data)
        
        return response

    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def items(self, request, pk=None):
        """Get items for a specific price list"""
        price_list = self.get_object()
        items = price_list.items.all().select_related('product').order_by('product__name')
        serializer = CustomerPriceListItemSerializer(items, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class WeeklyPriceReportViewSet(viewsets.ModelViewSet):
    """ViewSet for weekly price reports"""
    
    queryset = WeeklyPriceReport.objects.all()
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return WeeklyPriceReportCreateSerializer
        return WeeklyPriceReportSerializer
    
    def get_queryset(self):
        queryset = WeeklyPriceReport.objects.select_related('generated_by').order_by('-report_week_start')
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by year
        year = self.request.query_params.get('year')
        if year:
            queryset = queryset.filter(report_week_start__year=year)
        
        # Filter by week number
        week = self.request.query_params.get('week')
        if week:
            queryset = queryset.filter(report_week_start__week=week)
        
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(generated_by=self.request.user)
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def generate_current_week(self, request):
        """Generate report for current week"""
        from datetime import date, timedelta
        
        # Get current Monday
        today = date.today()
        monday = today - timedelta(days=today.weekday())
        sunday = monday + timedelta(days=6)
        
        # Check if report already exists
        existing = WeeklyPriceReport.objects.filter(
            report_week_start=monday,
            report_week_end=sunday
        ).first()
        
        if existing:
            return Response(
                WeeklyPriceReportSerializer(existing).data,
                status=status.HTTP_200_OK
            )
        
        # Create new report
        week_number = monday.isocalendar()[1]
        report = WeeklyPriceReport.objects.create(
            report_name=f"Weekly Price Report - Week {week_number}, {monday.year}",
            report_week_start=monday,
            report_week_end=sunday,
            generated_by=request.user,
            status='generating'
        )
        
        # Generate report data
        self._generate_report_data(report)
        
        return Response(
            WeeklyPriceReportSerializer(report).data,
            status=status.HTTP_201_CREATED
        )
    
    def _generate_report_data(self, report):
        """Generate comprehensive report data"""
        from datetime import timedelta
        
        # Market data analysis
        market_prices = MarketPrice.objects.filter(
            invoice_date__range=[report.report_week_start, report.report_week_end],
            is_active=True
        )
        
        report.total_market_prices_analyzed = market_prices.count()
        
        # Calculate volatility
        volatilities = []
        most_volatile_product = ""
        most_volatile_percentage = Decimal('0.00')
        
        for product_name in market_prices.values_list('product_name', flat=True).distinct():
            product_prices = market_prices.filter(product_name=product_name)
            if product_prices.count() >= 2:
                prices = list(product_prices.values_list('unit_price_incl_vat', flat=True))
                min_price = min(prices)
                max_price = max(prices)
                
                if min_price > 0:
                    volatility = ((max_price - min_price) / min_price) * 100
                    volatilities.append(volatility)
                    
                    if volatility > most_volatile_percentage:
                        most_volatile_percentage = volatility
                        most_volatile_product = product_name
        
        report.average_market_volatility = sum(volatilities) / len(volatilities) if volatilities else Decimal('0.00')
        report.most_volatile_product = most_volatile_product
        report.most_volatile_percentage = most_volatile_percentage
        
        # Customer pricing analysis
        price_lists = CustomerPriceList.objects.filter(
            generated_at__range=[report.report_week_start, report.report_week_end + timedelta(days=1)]
        )
        
        report.total_price_lists_generated = price_lists.count()
        report.total_customers_affected = price_lists.values('customer').distinct().count()
        
        # Calculate average price increase
        price_increases = []
        for price_list in price_lists:
            items_with_increases = price_list.items.filter(price_change_percentage__gt=0)
            if items_with_increases.exists():
                avg_increase = items_with_increases.aggregate(
                    avg=models.Avg('price_change_percentage')
                )['avg']
                if avg_increase:
                    price_increases.append(avg_increase)
        
        report.average_price_increase = sum(price_increases) / len(price_increases) if price_increases else Decimal('0.00')
        
        # Procurement analysis
        procurement_recs = ProcurementRecommendation.objects.filter(
            created_at__range=[report.report_week_start, report.report_week_end + timedelta(days=1)]
        )
        
        report.total_procurement_recommendations = procurement_recs.count()
        report.estimated_procurement_cost = procurement_recs.aggregate(
            total=models.Sum('estimated_total_cost')
        )['total'] or Decimal('0.00')
        report.potential_savings_identified = procurement_recs.aggregate(
            total=models.Sum('potential_savings')
        )['total'] or Decimal('0.00')
        
        # Generate key insights
        insights = []
        
        if most_volatile_percentage > 50:
            insights.append(f"Extreme volatility detected: {most_volatile_product} showed {most_volatile_percentage:.1f}% price variation")
        
        if report.average_price_increase > 10:
            insights.append(f"Significant price increases: Average customer price increase of {report.average_price_increase:.1f}%")
        
        if report.potential_savings_identified > 1000:
            insights.append(f"Major savings opportunity: R{report.potential_savings_identified:.2f} in potential procurement savings identified")
        
        if report.total_customers_affected > 0:
            insights.append(f"Customer impact: {report.total_customers_affected} customers received updated price lists")
        
        report.key_insights = insights
        report.status = 'completed'
        report.save()


# Enhanced Market Price ViewSet with Customer Impact

class EnhancedMarketPriceViewSet(MarketPriceViewSet):
    """Enhanced market price ViewSet with customer pricing impact"""
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return MarketPriceWithCustomerImpactSerializer
        return super().get_serializer_class()
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def volatility_dashboard(self, request):
        """Get market volatility dashboard data"""
        from datetime import date, timedelta
        
        # Get date range
        days = int(request.query_params.get('days', 30))
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        
        # Analyze volatility by product
        volatility_data = []
        
        products_with_prices = MarketPrice.objects.filter(
            invoice_date__gte=start_date,
            is_active=True,
            matched_product__isnull=False
        ).values('matched_product__name').distinct()
        
        for product_data in products_with_prices:
            product_name = product_data['matched_product__name']
            
            prices = MarketPrice.objects.filter(
                matched_product__name=product_name,
                invoice_date__gte=start_date,
                is_active=True
            ).order_by('invoice_date')
            
            if prices.count() >= 2:
                price_values = list(prices.values_list('unit_price_incl_vat', flat=True))
                min_price = min(price_values)
                max_price = max(price_values)
                
                if min_price > 0:
                    volatility = ((max_price - min_price) / min_price) * 100
                    
                    # Get affected customers
                    affected_customers = CustomerPriceListItem.objects.filter(
                        product__name=product_name,
                        price_list__status='active'
                    ).count()
                    
                    volatility_data.append({
                        'product_name': product_name,
                        'min_price': min_price,
                        'max_price': max_price,
                        'volatility_percentage': round(volatility, 2),
                        'volatility_level': self._get_volatility_level(volatility),
                        'affected_customers': affected_customers,
                        'price_points': len(price_values)
                    })
        
        # Sort by volatility
        volatility_data.sort(key=lambda x: x['volatility_percentage'], reverse=True)
        
        return Response({
            'period': f"{start_date} to {end_date}",
            'total_products_analyzed': len(volatility_data),
            'high_volatility_products': [p for p in volatility_data if p['volatility_percentage'] > 25],
            'volatility_data': volatility_data[:20]  # Top 20 most volatile
        })
    
    def _get_volatility_level(self, volatility):
        """Get volatility level classification"""
        if volatility > 50:
            return 'extremely_volatile'
        elif volatility > 25:
            return 'highly_volatile'
        elif volatility > 10:
            return 'volatile'
        else:
            return 'stable'


# Invoice Processing Views

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_invoice_upload_status(request):
    """
    Check if invoices can be uploaded for today or if stock processing is ready
    """
    today = timezone.now().date()
    
    # Check if there are any uploaded invoices for today
    uploaded_invoices = InvoicePhoto.objects.filter(
        invoice_date=today,
        status__in=['uploaded', 'processing', 'extracted']
    )
    
    # Check if there are completed invoices ready for stock processing
    completed_invoices = InvoicePhoto.objects.filter(
        invoice_date=today,
        status='completed'
    )
    
    if completed_invoices.exists():
        # Ready for stock processing
        return Response({
            'status': 'ready_for_stock_processing',
            'message': 'Invoices processed - ready to process stock received',
            'button_text': 'Process Stock Received',
            'completed_invoices': completed_invoices.count(),
            'action': 'process_stock'
        })
    
    elif uploaded_invoices.exists():
        # Invoices uploaded but not yet completed
        return Response({
            'status': 'invoices_pending',
            'message': 'Invoices uploaded - processing in progress',
            'button_text': 'Processing Invoices...',
            'pending_invoices': uploaded_invoices.count(),
            'action': 'wait'
        })
    
    else:
        # Ready to upload invoices
        return Response({
            'status': 'ready_for_upload',
            'message': 'Ready to upload invoices for today',
            'button_text': 'Upload Invoices for Day',
            'action': 'upload_invoices'
        })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_invoice_photo(request):
    """
    Upload invoice photo for processing
    """
    try:
        # Get form data
        supplier_id = request.data.get('supplier_id')
        invoice_date = request.data.get('invoice_date', timezone.now().date())
        photo = request.FILES.get('photo')
        notes = request.data.get('notes', '')
        
        if not supplier_id or not photo:
            return Response({
                'error': 'supplier_id and photo are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get supplier
        from suppliers.models import Supplier
        try:
            supplier = Supplier.objects.get(id=supplier_id)
        except Supplier.DoesNotExist:
            return Response({
                'error': 'Supplier not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Create invoice photo record
        invoice_photo = InvoicePhoto.objects.create(
            supplier=supplier,
            invoice_date=invoice_date,
            uploaded_by=request.user,
            photo=photo,
            original_filename=photo.name,
            file_size=photo.size,
            notes=notes
        )
        
        return Response({
            'status': 'success',
            'message': f'Invoice uploaded successfully for {supplier.name}',
            'invoice_id': invoice_photo.id,
            'next_step': 'Process invoice with: python manage.py process_invoices --invoice-id ' + str(invoice_photo.id)
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response({
            'error': f'Upload failed: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_pending_invoices(request):
    """
    Get list of invoices that need processing
    """
    pending_invoices = InvoicePhoto.objects.filter(
        status__in=['uploaded', 'processing', 'extracted']
    ).select_related('supplier', 'uploaded_by')
    
    invoice_data = []
    for invoice in pending_invoices:
        invoice_data.append({
            'id': invoice.id,
            'supplier': invoice.supplier.name,
            'invoice_date': invoice.invoice_date,
            'status': invoice.status,
            'uploaded_by': invoice.uploaded_by.email,
            'created_at': invoice.created_at,
            'notes': invoice.notes
        })
    
    return Response({
        'pending_invoices': invoice_data,
        'count': len(invoice_data)
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_extracted_invoice_data(request, invoice_id):
    """
    Get extracted invoice data for weight input
    """
    try:
        invoice = InvoicePhoto.objects.get(id=invoice_id, status='extracted')
        extracted_items = invoice.extracted_items.all().order_by('line_number')
        
        items_data = []
        for item in extracted_items:
            items_data.append({
                'id': item.id,
                'line_number': item.line_number,
                'product_code': item.product_code,
                'product_description': item.product_description,
                'quantity': float(item.quantity),
                'unit': item.unit,
                'unit_price': float(item.unit_price),
                'line_total': float(item.line_total),
                'actual_weight_kg': float(item.actual_weight_kg) if item.actual_weight_kg else None,
                'needs_weight_input': item.needs_weight_input,
                'needs_product_matching': item.needs_product_matching
            })
        
        return Response({
            'invoice_id': invoice.id,
            'supplier': invoice.supplier.name,
            'invoice_date': invoice.invoice_date,
            'items': items_data
        })
        
    except InvoicePhoto.DoesNotExist:
        return Response({
            'error': 'Invoice not found or not ready for weight input'
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_invoice_weights(request, invoice_id):
    """
    Update weights for extracted invoice items
    """
    try:
        invoice = InvoicePhoto.objects.get(id=invoice_id, status='extracted')
        weights_data = request.data.get('weights', [])
        
        updated_items = []
        errors = []
        
        for weight_entry in weights_data:
            try:
                item_id = weight_entry.get('item_id')
                weight_kg = weight_entry.get('weight_kg')
                
                if not item_id or weight_kg is None:
                    errors.append('Missing item_id or weight_kg')
                    continue
                
                extracted_item = ExtractedInvoiceData.objects.get(
                    id=item_id, 
                    invoice_photo=invoice
                )
                
                extracted_item.actual_weight_kg = Decimal(str(weight_kg))
                extracted_item.needs_weight_input = False
                extracted_item.save()
                
                # Calculate price per kg
                price_per_kg = extracted_item.calculated_price_per_kg
                
                updated_items.append({
                    'item_id': item_id,
                    'product_description': extracted_item.product_description,
                    'weight_kg': float(weight_kg),
                    'price_per_kg': float(price_per_kg) if price_per_kg else None
                })
                
            except ExtractedInvoiceData.DoesNotExist:
                errors.append(f'Item {item_id} not found')
            except Exception as e:
                errors.append(f'Error updating item {item_id}: {str(e)}')
        
        # Check if all items have weights and can move to product matching
        remaining_items = invoice.extracted_items.filter(needs_weight_input=True)
        if not remaining_items.exists():
            # All weights added - ready for product matching
            invoice.status = 'extracted'  # Keep as extracted until product matching is done
            invoice.save()
        
        return Response({
            'status': 'success',
            'updated_items': updated_items,
            'errors': errors,
            'ready_for_product_matching': not remaining_items.exists(),
            'message': f'Updated weights for {len(updated_items)} items'
        })
        
    except InvoicePhoto.DoesNotExist:
        return Response({
            'error': 'Invoice not found'
        }, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def process_invoice_complete(request, invoice_id):
    """
    Complete invoice processing with weights and product matches
    """
    try:
        invoice = InvoicePhoto.objects.get(id=invoice_id, status='extracted')
        processed_data = request.data.get('processed_data', [])
        
        updated_items = []
        errors = []
        created_mappings = []
        
        for item_data in processed_data:
            try:
                item_id = item_data.get('item_id')
                weight_kg = item_data.get('weight_kg')
                product_matches = item_data.get('product_matches', [])
                
                if not item_id or weight_kg is None:
                    errors.append('Missing item_id or weight_kg')
                    continue
                
                extracted_item = ExtractedInvoiceData.objects.get(
                    id=item_id, 
                    invoice_photo=invoice
                )
                
                # Update weight
                extracted_item.actual_weight_kg = Decimal(str(weight_kg))
                extracted_item.needs_weight_input = False
                extracted_item.save()
                
                # Process product matches
                for match_data in product_matches:
                    try:
                        product_id = match_data.get('product_id')
                        pricing_strategy = match_data.get('pricing_strategy', 'per_kg')
                        quantity = match_data.get('quantity', 1)
                        package_size_kg = match_data.get('package_size_kg')
                        
                        if not product_id:
                            continue
                        
                        from products.models import Product
                        product = Product.objects.get(id=product_id)
                        
                        # Create or update supplier product mapping
                        mapping, created = SupplierProductMapping.objects.get_or_create(
                            supplier=invoice.supplier,
                            supplier_product_code=extracted_item.product_code or '',
                            supplier_product_description=extracted_item.product_description,
                            defaults={
                                'our_product': product,
                                'pricing_strategy': pricing_strategy,
                                'package_size_kg': package_size_kg,
                                'units_per_package': int(quantity) if pricing_strategy == 'per_unit' else None,
                                'created_by': request.user,
                                'notes': f'Auto-created from invoice processing on {invoice.invoice_date}',
                            }
                        )
                        
                        if not created:
                            # Update existing mapping
                            mapping.our_product = product
                            mapping.pricing_strategy = pricing_strategy
                            mapping.package_size_kg = package_size_kg
                            mapping.units_per_package = int(quantity) if pricing_strategy == 'per_unit' else None
                            mapping.is_active = True
                            mapping.save()
                        
                        # Link the mapping to the extracted item
                        extracted_item.supplier_mapping = mapping
                        extracted_item.needs_product_matching = False
                        extracted_item.is_processed = True
                        extracted_item.save()
                        
                        created_mappings.append({
                            'product_name': product.name,
                            'pricing_strategy': pricing_strategy,
                            'quantity': quantity,
                            'package_size_kg': float(package_size_kg) if package_size_kg else None,
                            'created': created,
                        })
                        
                    except Product.DoesNotExist:
                        errors.append(f'Product {product_id} not found')
                    except Exception as e:
                        errors.append(f'Error processing product match: {str(e)}')
                
                updated_items.append({
                    'item_id': item_id,
                    'product_description': extracted_item.product_description,
                    'weight_kg': float(weight_kg),
                    'price_per_kg': float(extracted_item.calculated_price_per_kg) if extracted_item.calculated_price_per_kg else None,
                    'product_matches': len(product_matches),
                })
                
            except ExtractedInvoiceData.DoesNotExist:
                errors.append(f'Item {item_id} not found')
            except Exception as e:
                errors.append(f'Error processing item {item_id}: {str(e)}')
        
        # Check if all items are processed
        remaining_items = invoice.extracted_items.filter(
            needs_weight_input=True
        ).union(
            invoice.extracted_items.filter(needs_product_matching=True)
        )
        
        if not remaining_items.exists():
            # All items processed - mark invoice as completed
            invoice.status = 'completed'
            invoice.save()
        
        return Response({
            'status': 'success',
            'updated_items': updated_items,
            'created_mappings': created_mappings,
            'errors': errors,
            'invoice_completed': not remaining_items.exists(),
            'message': f'Processed {len(updated_items)} items with {len(created_mappings)} product mappings'
        })
        
    except InvoicePhoto.DoesNotExist:
        return Response({
            'error': 'Invoice not found or not ready for processing'
        }, status=status.HTTP_404_NOT_FOUND)


def _update_product_pricing_from_invoice(invoice, created_mappings):
    """
    Update product pricing based on new supplier costs from processed invoice
    """
    from products.models import Product
    from suppliers.models import SupplierProduct
    from decimal import Decimal
    
    pricing_updates = []
    
    try:
        # Get business settings for markup
        from settings.models import BusinessSettings
        business_settings = BusinessSettings.objects.first()
        default_markup = business_settings.default_base_markup if business_settings else Decimal('0.25')  # 25% default
        
        for mapping_info in created_mappings:
            try:
                # Find the corresponding extracted item and mapping
                mapping = SupplierProductMapping.objects.filter(
                    supplier=invoice.supplier,
                    our_product__name=mapping_info['product_name']
                ).first()
                
                if not mapping:
                    continue
                
                extracted_item = mapping.extractedinvoicedata_set.filter(
                    invoice_photo=invoice
                ).first()
                
                if not extracted_item or not extracted_item.actual_weight_kg:
                    continue
                
                # Calculate new supplier price based on pricing strategy
                new_supplier_price = None
                
                if mapping.pricing_strategy == 'per_kg':
                    # Price per kg = line_total / actual_weight_kg
                    new_supplier_price = extracted_item.line_total / extracted_item.actual_weight_kg
                    
                elif mapping.pricing_strategy == 'per_package' and mapping.package_size_kg:
                    # Price per kg = unit_price / package_size_kg
                    new_supplier_price = extracted_item.unit_price / mapping.package_size_kg
                    
                elif mapping.pricing_strategy == 'per_unit' and mapping.units_per_package:
                    # Price per unit = unit_price / units_per_package
                    # Then convert to per kg if we know the weight per unit
                    unit_price = extracted_item.unit_price / mapping.units_per_package
                    if extracted_item.actual_weight_kg:
                        # Estimate weight per unit
                        weight_per_unit = extracted_item.actual_weight_kg / (extracted_item.quantity * mapping.units_per_package)
                        new_supplier_price = unit_price / weight_per_unit if weight_per_unit > 0 else None
                
                if new_supplier_price and new_supplier_price > 0:
                    # Update or create supplier product
                    supplier_product, created = SupplierProduct.objects.get_or_create(
                        supplier=invoice.supplier,
                        name=extracted_item.product_description,
                        defaults={
                            'supplier_price': new_supplier_price,
                            'unit': 'kg',
                            'supplier_category_code': 'FRESH',
                        }
                    )
                    
                    if not created:
                        # Update existing supplier product price
                        old_price = supplier_product.supplier_price
                        supplier_product.supplier_price = new_supplier_price
                        supplier_product.save()
                    else:
                        old_price = Decimal('0.00')
                    
                    # Calculate new retail price with markup
                    new_retail_price = new_supplier_price * (1 + default_markup)
                    
                    # Update our product price
                    product = mapping.our_product
                    old_retail_price = product.price
                    product.price = new_retail_price
                    product.save()
                    
                    pricing_updates.append({
                        'product_name': product.name,
                        'supplier_product': extracted_item.product_description,
                        'pricing_strategy': mapping.pricing_strategy,
                        'old_supplier_price': float(old_price),
                        'new_supplier_price': float(new_supplier_price),
                        'old_retail_price': float(old_retail_price),
                        'new_retail_price': float(new_retail_price),
                        'markup_percentage': float(default_markup * 100),
                        'price_change_percentage': float(((new_retail_price - old_retail_price) / old_retail_price * 100) if old_retail_price > 0 else 0),
                    })
                    
            except Exception as e:
                # Log error but continue processing other items
                print(f"Error updating pricing for {mapping_info.get('product_name', 'unknown')}: {e}")
                continue
        
        return pricing_updates
        
    except Exception as e:
        print(f"Error in pricing update process: {e}")
        return []


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def process_stock_received(request):
    """
    Process stock received based on completed invoices
    """
    today = timezone.now().date()
    
    # Get completed invoices for today
    completed_invoices = InvoicePhoto.objects.filter(
        invoice_date=today,
        status='completed'
    ).prefetch_related('extracted_items__supplier_mapping')
    
    if not completed_invoices.exists():
        return Response({
            'error': 'No completed invoices found for today'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Process each invoice's extracted data
    processed_items = []
    errors = []
    
    for invoice in completed_invoices:
        for extracted_item in invoice.extracted_items.all():
            try:
                if extracted_item.supplier_mapping and extracted_item.actual_weight_kg:
                    # Update product pricing based on Karl's mapping decision
                    final_price = extracted_item.final_unit_price
                    if final_price:
                        # Update the product's supplier price
                        # This would update SupplierProduct model
                        processed_items.append({
                            'product': extracted_item.supplier_mapping.our_product.name,
                            'new_price': float(final_price),
                            'strategy': extracted_item.supplier_mapping.pricing_strategy
                        })
                    
                    # Mark as processed
                    extracted_item.is_processed = True
                    extracted_item.save()
                    
            except Exception as e:
                errors.append(f'Error processing {extracted_item}: {str(e)}')
    
    return Response({
        'status': 'success',
        'processed_items': processed_items,
        'errors': errors,
        'message': f'Processed {len(processed_items)} items from {len(completed_invoices)} invoices'
    })
