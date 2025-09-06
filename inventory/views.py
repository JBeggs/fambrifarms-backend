from rest_framework import viewsets, status, permissions
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count, Sum, F
from django.utils import timezone
from decimal import Decimal
from datetime import datetime, timedelta

from .models import (
    UnitOfMeasure, RawMaterial, RawMaterialBatch, ProductionRecipe,
    RecipeIngredient, FinishedInventory, StockMovement, ProductionBatch,
    StockAlert
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
    ProductionCompleteSerializer, StockAdjustmentSerializer
)
from products.models import Product


class UnitOfMeasureViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = UnitOfMeasure.objects.all()
    serializer_class = UnitOfMeasureSerializer
    permission_classes = []  # Public endpoint for reference data
    pagination_class = None  # Disable pagination for reference data
    
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
    inventory = FinishedInventory.objects.select_related(
        'product__department'
    ).all()
    
    stock_data = []
    for inv in inventory:
        stock_data.append({
            'product_id': inv.product.id,
            'product_name': inv.product.name,
            'department': inv.product.department.name,
            'available_quantity': inv.available_quantity,
            'reserved_quantity': inv.reserved_quantity,
            'reorder_level': inv.reorder_level,
            'needs_production': inv.needs_production,
            'average_cost': inv.average_cost
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
    serializer = StockAdjustmentSerializer(data=request.data)
    
    if serializer.is_valid():
        data = serializer.validated_data
        movement_type = data['adjustment_type']
        quantity = data['quantity']
        reason = data['reason']
        notes = data.get('notes') or ''
        
        try:
            if movement_type in ['finished_adjust', 'finished_waste']:
                # Finished inventory adjustment
                product = Product.objects.get(id=data['product_id'])
                inventory = FinishedInventory.objects.get(product=product)
                
                if movement_type == 'finished_adjust':
                    inventory.available_quantity += quantity
                else:  # waste
                    inventory.available_quantity -= quantity
                
                inventory.save()
                
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
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
