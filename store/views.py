from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import get_object_or_404

from .models import Category, Product
from .serializers import (
    CategorySerializer,
    ProductSerializer,
    CartItemSerializer,
)
from .models import Category, Product, Cart, CartItem


class CategoryListCreateView(APIView):

    def get(self, request):
        categories = Category.objects.all()
        serializer = CategorySerializer(categories, many=True)

        return Response(serializer.data)

    def post(self, request):
        serializer = CategorySerializer(data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )


class ProductListCreateView(APIView):

    def get(self, request):
        products = Product.objects.all()
        serializer = ProductSerializer(products, many=True)

        return Response(serializer.data)

    def post(self, request):
        serializer = ProductSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )

class ProductDetailView(APIView):

    def get(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        serializer = ProductSerializer(product)

        return Response(serializer.data)

    def put(self, request, pk):
        product = get_object_or_404(Product, pk=pk)

        serializer = ProductSerializer(
            product,
            data=request.data
        )

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )

    def delete(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        product.delete()

        return Response(
            status=status.HTTP_204_NO_CONTENT
        )

class CategoryDetailView(APIView):

    def get(self, request, pk):
        category = get_object_or_404(Category, pk=pk)
        serializer = CategorySerializer(category)

        return Response(serializer.data)

    def put(self, request, pk):
        category = get_object_or_404(Category, pk=pk)
        serializer = CategorySerializer(
            category,
            data=request.data
        )

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )

    def delete(self, request, pk):
        category = get_object_or_404(Category, pk=pk)
        category.delete()

        return Response(
            status=status.HTTP_204_NO_CONTENT
        )


class CartItemCreateView(APIView):

    def post(self, request):
        product_id = request.data.get("product")
        quantity = request.data.get("quantity", 1)

        product = get_object_or_404(Product, pk=product_id)

        cart, created = Cart.objects.get_or_create(
            user=request.user
        )

        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={"quantity": quantity}
        )

        if not created:
            cart_item.quantity += quantity
            cart_item.save()

        serializer = CartItemSerializer(cart_item)

        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED
        )

class CartItemUpdateView(APIView):

    def patch(self, request, pk):
        cart_item = get_object_or_404(
            CartItem,
            pk=pk,
            cart__user=request.user
        )

        quantity = request.data.get("quantity")

        if quantity is None:
            return Response(
                {"error": "Quantity is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            quantity = int(quantity)
        except (TypeError, ValueError):
            return Response(
                {"error": "Quantity must be a positive integer."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if quantity <= 0:
            return Response(
                {"error": "Quantity must be greater than 0."},
                status=status.HTTP_400_BAD_REQUEST
            )

        cart_item.quantity = quantity
        cart_item.save()

        serializer = CartItemSerializer(cart_item)

        return Response(serializer.data)