from rest_framework import status, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.db import transaction
from .models import User, RestaurantProfile
from .serializers import UserSerializer, RestaurantRegistrationSerializer, CustomerSerializer

@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    serializer = RestaurantRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        user = User.objects.create_user(
            email=serializer.validated_data['email'],
            password=serializer.validated_data['password'],
            first_name=serializer.validated_data['first_name'],
            last_name=serializer.validated_data['last_name'],
            phone=serializer.validated_data.get('phone') or '',
            user_type='restaurant'
        )
        
        RestaurantProfile.objects.create(
            user=user,
            business_name=serializer.validated_data['business_name'],
            address=serializer.validated_data['address'],
            city=serializer.validated_data['city'],
            postal_code=serializer.validated_data['postal_code']
        )
        
        refresh = RefreshToken.for_user(user)
        return Response({
            'user': UserSerializer(user).data,
            'tokens': {
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            }
        }, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    email = request.data.get('email')
    password = request.data.get('password')
    
    user = authenticate(username=email, password=password)
    if user and user.is_active:
        refresh = RefreshToken.for_user(user)
        return Response({
            'user': UserSerializer(user).data,
            'tokens': {
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            }
        })
    
    return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED) 


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profile(request):
    """Return the authenticated user's profile"""
    return Response(UserSerializer(request.user).data)

class CustomerViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing customers (restaurants)
    Provides CRUD operations for customer data
    """
    serializer_class = CustomerSerializer
    permission_classes = [AllowAny]  # Allow access for order processing
    
    def get_queryset(self):
        """Return restaurant and private customer users"""
        return User.objects.filter(user_type__in=['restaurant', 'private']).select_related('restaurantprofile')
    
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """Create a new customer with restaurant profile"""
        try:
            print(f"[accounts] Creating customer with data: {request.data}")
            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                customer = serializer.save()
                print(f"[accounts] Customer created successfully: {customer.email}")
                return Response(
                    CustomerSerializer(customer).data, 
                    status=status.HTTP_201_CREATED
                )
            print(f"[accounts] Validation errors: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print(f"[accounts] Exception creating customer: {str(e)}")
            return Response(
                {'error': f'Failed to create customer: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def list(self, request, *args, **kwargs):
        """List all customers with error handling"""
        try:
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            return Response({
                'customers': serializer.data,
                'count': queryset.count()
            })
        except Exception as e:
            return Response(
                {'error': f'Failed to fetch customers: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def retrieve(self, request, *args, **kwargs):
        """Get a specific customer with error handling"""
        try:
            customer = self.get_object()
            serializer = self.get_serializer(customer)
            return Response(serializer.data)
        except User.DoesNotExist:
            return Response(
                {'error': 'Customer not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to fetch customer: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @transaction.atomic
    def update(self, request, *args, **kwargs):
        """Update customer with error handling"""
        try:
            customer = self.get_object()
            serializer = self.get_serializer(customer, data=request.data, partial=True)
            if serializer.is_valid():
                customer = serializer.save()
                return Response(CustomerSerializer(customer).data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            return Response(
                {'error': 'Customer not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to update customer: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def destroy(self, request, *args, **kwargs):
        """Delete customer with error handling"""
        try:
            customer = self.get_object()
            customer.delete()
            return Response(
                {'message': 'Customer deleted successfully'}, 
                status=status.HTTP_204_NO_CONTENT
            )
        except User.DoesNotExist:
            return Response(
                {'error': 'Customer not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to delete customer: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )