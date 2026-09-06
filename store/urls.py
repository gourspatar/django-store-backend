from django.urls import path
from .views import CategoryListCreateView, CategoryDetailView, ProductListCreateView, ProductDetailView , CartItemCreateView , CartItemUpdateView

urlpatterns = [
    path(
        "categories/",
        CategoryListCreateView.as_view()
    ),
    path(
        "categories/<int:pk>/",
        CategoryDetailView.as_view()
    ),
    path(
        "products/",
        ProductListCreateView.as_view()
    ),
    path(
    "products/<int:pk>/",
    ProductDetailView.as_view()
    ),
    path(
        "cart/items/",
        CartItemCreateView.as_view()
    ),

    path(
    "cart/items/<int:pk>/",
    CartItemUpdateView.as_view()
),
]
