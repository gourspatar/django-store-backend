from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import (
    RegisterView,
    MeView,
    LogoutView,
    OrderPayView,
    StripeWebhookView,
    CategoryListCreateView,
    CategoryDetailView,
    ProductListCreateView,
    ProductDetailView,
    CartView,
    CartItemCreateView,
    CartItemUpdateView,
    CheckoutView,
    OrderListView,
    OrderDetailView,
    OrderCancelView,
)

urlpatterns = [
    # Auth (JWT)
    path("auth/register/", RegisterView.as_view(), name="auth-register"),
    path("auth/login/", TokenObtainPairView.as_view(), name="auth-login"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="auth-refresh"),
    path("auth/logout/", LogoutView.as_view(), name="auth-logout"),
    path("auth/me/", MeView.as_view(), name="auth-me"),
    # Categories
    path("categories/", CategoryListCreateView.as_view(), name="category-list"),
    path("categories/<int:pk>/", CategoryDetailView.as_view(), name="category-detail"),
    # Products
    path("products/", ProductListCreateView.as_view(), name="product-list"),
    path("products/<int:pk>/", ProductDetailView.as_view(), name="product-detail"),
    # Cart
    path("cart/", CartView.as_view(), name="cart"),
    path("cart/items/", CartItemCreateView.as_view(), name="cart-item-add"),
    path("cart/items/<int:pk>/", CartItemUpdateView.as_view(), name="cart-item-update"),
    # Checkout + Orders
    path("checkout/", CheckoutView.as_view(), name="checkout"),
    path("orders/", OrderListView.as_view(), name="order-list"),
    path("orders/<int:pk>/", OrderDetailView.as_view(), name="order-detail"),
    path("orders/<int:pk>/cancel/", OrderCancelView.as_view(), name="order-cancel"),
    # Stripe payments
    path("orders/<int:pk>/pay/", OrderPayView.as_view(), name="order-pay"),
    path("stripe/webhook/", StripeWebhookView.as_view(), name="stripe-webhook"),
]
