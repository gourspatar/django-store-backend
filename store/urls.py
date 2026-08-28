from django.urls import path
from .views import CategoryListCreateView, ProductListCreateView

urlpatterns = [
    path("categories/", CategoryListCreateView.as_view()),
    path("products/", ProductListCreateView.as_view()),
]