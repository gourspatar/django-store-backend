from django.urls import path
from .views import CategoryListCreateView


urlpatterns = [
    path("categories/", CategoryListCreateView.as_view()),
]