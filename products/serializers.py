from rest_framework import serializers
from .models import (
    Product, Department, CompanyInfo, PageContent, BusinessHours, 
    TeamMember, FAQ, Testimonial
)

class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ['id', 'name', 'description', 'color', 'is_active']

class ProductSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source='department.name', read_only=True)
    department_color = serializers.CharField(source='department.color', read_only=True)
    
    # Inventory information
    available_quantity = serializers.SerializerMethodField()
    reserved_quantity = serializers.SerializerMethodField()
    needs_production = serializers.SerializerMethodField()
    supplier_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'description', 'department', 'department_name', 
            'department_color', 'price', 'unit', 'is_active',
            'available_quantity', 'reserved_quantity', 'needs_production', 'supplier_count'
        ]
    
    def get_available_quantity(self, obj):
        try:
            return obj.inventory.available_quantity
        except:
            return 0
    
    def get_reserved_quantity(self, obj):
        try:
            return obj.inventory.reserved_quantity
        except:
            return 0
    
    def get_needs_production(self, obj):
        try:
            return obj.inventory.needs_production
        except:
            return False
    
    def get_supplier_count(self, obj):
        return obj.suppliers.filter(is_available=True).count()


# CMS Serializers
class CompanyInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyInfo
        fields = [
            'id', 'name', 'tagline', 'description', 'phone_primary', 'phone_secondary',
            'email', 'address', 'whatsapp', 'is_active', 'created_at', 'updated_at'
        ]


class PageContentSerializer(serializers.ModelSerializer):
    class Meta:
        model = PageContent
        fields = [
            'id', 'page', 'title', 'subtitle', 'content', 'hero_title', 'hero_subtitle',
            'meta_description', 'is_active', 'created_at', 'updated_at'
        ]


class BusinessHoursSerializer(serializers.ModelSerializer):
    day_display = serializers.CharField(source='get_day_display', read_only=True)
    
    class Meta:
        model = BusinessHours
        fields = [
            'id', 'day', 'day_display', 'is_open', 'open_time', 'close_time', 'special_note'
        ]


class TeamMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = TeamMember
        fields = [
            'id', 'name', 'position', 'bio', 'email', 'phone', 'image', 'is_active', 'order'
        ]


class FAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQ
        fields = [
            'id', 'question', 'answer', 'category', 'is_active', 'order'
        ]


class TestimonialSerializer(serializers.ModelSerializer):
    class Meta:
        model = Testimonial
        fields = [
            'id', 'customer_name', 'restaurant_name', 'content', 'rating', 
            'is_featured', 'is_active', 'created_at'
        ] 