from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from .models import User, RestaurantProfile
from .serializers import UserSerializer, RestaurantRegistrationSerializer

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
            phone=serializer.validated_data.get('phone', ''),
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