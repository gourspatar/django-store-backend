from django.contrib import admin

from .models import Category, Product, Cart, CartItem, Order, OrderItem


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "price", "category")
    search_fields = ("name", "description")
    list_filter = ("category",)


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("id", "user")
    search_fields = ("user__username",)
    inlines = [CartItemInline]


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product", "quantity", "price_at_purchase")
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "status", "total", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("user__username", "user__email")
    list_editable = ("status",)
    readonly_fields = (
        "user",
        "total",
        "created_at",
        "paid_at",
        "stripe_session_id",
        "stripe_payment_intent_id",
    )
    inlines = [OrderItemInline]
    actions = ["mark_paid", "mark_shipped", "mark_delivered", "mark_cancelled"]

    @admin.action(description="Mark selected orders as paid")
    def mark_paid(self, request, queryset):
        queryset.update(status="paid")

    @admin.action(description="Mark selected orders as shipped")
    def mark_shipped(self, request, queryset):
        queryset.update(status="shipped")

    @admin.action(description="Mark selected orders as delivered")
    def mark_delivered(self, request, queryset):
        queryset.update(status="delivered")

    @admin.action(description="Mark selected orders as cancelled")
    def mark_cancelled(self, request, queryset):
        queryset.update(status="cancelled")


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "product", "quantity", "price_at_purchase")
