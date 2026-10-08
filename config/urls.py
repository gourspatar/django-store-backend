"""
URL configuration for config project.
"""

from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path


def api_root(request):
    """Provide a useful response when the development server root is opened."""
    return JsonResponse(
        {
            "message": "Django Store API",
            "endpoints": {
                "admin": "/admin/",
                "categories": "/api/categories/",
                "products": "/api/products/",
                "cart": "/api/cart/",
                "cart_items": "/api/cart/items/",
                "checkout": "/api/checkout/",
                "orders": "/api/orders/",
            },
        }
    )


urlpatterns = [
    path("", api_root, name="api-root"),
    path("admin/", admin.site.urls),
    path("api/", include("store.urls")),
]
