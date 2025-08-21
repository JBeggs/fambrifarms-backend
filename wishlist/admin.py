from django.contrib import admin
from .models import Wishlist, WishlistItem

class WishlistItemInline(admin.TabularInline):
    model = WishlistItem
    extra = 0
    readonly_fields = ('added_at',)

@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    inlines = (WishlistItemInline,)
    
    list_display = ('user', 'item_count', 'created_at', 'updated_at')
    search_fields = ('user__email', 'user__restaurantprofile__business_name')
    readonly_fields = ('created_at', 'updated_at')
    
    def item_count(self, obj):
        return obj.items.count()
    item_count.short_description = 'Items'

@admin.register(WishlistItem)
class WishlistItemAdmin(admin.ModelAdmin):
    list_display = ('wishlist', 'product', 'quantity', 'added_at')
    list_filter = ('product__department', 'added_at')
    search_fields = ('wishlist__user__email', 'product__name')
    readonly_fields = ('added_at',) 