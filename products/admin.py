from django.contrib import admin
from .models import (
    Department, Product, CompanyInfo, PageContent, BusinessHours, 
    TeamMember, FAQ, Testimonial
)

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'description')
    prepopulated_fields = {'name': ('name',)}

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'department', 'price', 'unit', 'is_active')
    list_filter = ('department', 'is_active')
    search_fields = ('name', 'description')
    list_editable = ('price', 'is_active')
    readonly_fields = ('id',)


# CMS Admin Classes
@admin.register(CompanyInfo)
class CompanyInfoAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone_primary', 'email', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'email')
    fieldsets = [
        ('Basic Information', {
            'fields': ['name', 'tagline', 'description']
        }),
        ('Contact Details', {
            'fields': ['phone_primary', 'phone_secondary', 'email', 'whatsapp', 'address']
        }),
        ('Settings', {
            'fields': ['is_active']
        })
    ]
    readonly_fields = ('created_at', 'updated_at')

    def get_readonly_fields(self, request, obj=None):
        if obj:  # Editing an existing object
            return self.readonly_fields + ('created_at', 'updated_at')
        return self.readonly_fields


@admin.register(PageContent)
class PageContentAdmin(admin.ModelAdmin):
    list_display = ('page', 'title', 'is_active', 'updated_at')
    list_filter = ('page', 'is_active')
    search_fields = ('title', 'content')
    fieldsets = [
        ('Page Information', {
            'fields': ['page', 'title', 'subtitle', 'meta_description']
        }),
        ('Hero Section', {
            'fields': ['hero_title', 'hero_subtitle'],
            'classes': ['collapse']
        }),
        ('Content', {
            'fields': ['content']
        }),
        ('Settings', {
            'fields': ['is_active']
        })
    ]
    readonly_fields = ('created_at', 'updated_at')

    def get_readonly_fields(self, request, obj=None):
        if obj:  # Editing an existing object
            return self.readonly_fields + ('created_at', 'updated_at')
        return self.readonly_fields


@admin.register(BusinessHours)
class BusinessHoursAdmin(admin.ModelAdmin):
    list_display = ('day', 'is_open', 'open_time', 'close_time', 'special_note')
    list_filter = ('is_open',)
    list_editable = ('is_open', 'open_time', 'close_time', 'special_note')
    ordering = ['day']


@admin.register(TeamMember)
class TeamMemberAdmin(admin.ModelAdmin):
    list_display = ('name', 'position', 'email', 'is_active', 'order')
    list_filter = ('is_active', 'position')
    search_fields = ('name', 'position', 'bio')
    list_editable = ('order', 'is_active')
    ordering = ['order', 'name']

    fieldsets = [
        ('Basic Information', {
            'fields': ['name', 'position', 'bio', 'image']
        }),
        ('Contact Details', {
            'fields': ['email', 'phone']
        }),
        ('Settings', {
            'fields': ['is_active', 'order']
        })
    ]


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ('question', 'category', 'is_active', 'order')
    list_filter = ('category', 'is_active')
    search_fields = ('question', 'answer')
    list_editable = ('order', 'is_active')
    ordering = ['order', 'question']

    fieldsets = [
        ('FAQ Information', {
            'fields': ['question', 'answer', 'category']
        }),
        ('Settings', {
            'fields': ['is_active', 'order']
        })
    ]


@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ('customer_name', 'restaurant_name', 'rating', 'is_featured', 'is_active', 'created_at')
    list_filter = ('rating', 'is_featured', 'is_active', 'created_at')
    search_fields = ('customer_name', 'restaurant_name', 'content')
    list_editable = ('is_featured', 'is_active')
    ordering = ['-created_at']

    fieldsets = [
        ('Customer Information', {
            'fields': ['customer_name', 'restaurant_name']
        }),
        ('Testimonial Content', {
            'fields': ['content', 'rating']
        }),
        ('Settings', {
            'fields': ['is_featured', 'is_active']
        })
    ]
    readonly_fields = ('created_at',) 