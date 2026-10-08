from django.db import transaction
from django.db.models import Q
from rest_framework import status
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import (
    AllowAny,
    IsAdminUser,
    IsAuthenticated,
    SAFE_METHODS,
    BasePermission,
)
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Category, Product, Cart, CartItem, Order, OrderItem
from .serializers import (
    CategorySerializer,
    ProductSerializer,
    CartItemSerializer,
    OrderSerializer,
)


class IsAdminOrReadOnly(BasePermission):
    """Anyone can browse the catalog; only staff (sellers) can change it."""

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_staff)


def parse_quantity(value, default=None):
    """Return a positive int or None if the value is invalid."""
    if value is None:
        value = default
    if isinstance(value, bool):
        return None
    try:
        quantity = int(value)
    except (TypeError, ValueError):
        return None
    return quantity if quantity > 0 else None


# --------------------------------------------------------------------------
# Categories
# --------------------------------------------------------------------------
class CategoryListCreateView(APIView):
    permission_classes = [IsAdminOrReadOnly]

    def get(self, request):
        categories = Category.objects.all()
        serializer = CategorySerializer(categories, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = CategorySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CategoryDetailView(APIView):
    permission_classes = [IsAdminOrReadOnly]

    def get(self, request, pk):
        category = get_object_or_404(Category, pk=pk)
        return Response(CategorySerializer(category).data)

    def put(self, request, pk):
        category = get_object_or_404(Category, pk=pk)
        serializer = CategorySerializer(category, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        category = get_object_or_404(Category, pk=pk)
        category.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# --------------------------------------------------------------------------
# Products
# --------------------------------------------------------------------------
class ProductListCreateView(APIView):
    permission_classes = [IsAdminOrReadOnly]

    def get(self, request):
        products = Product.objects.select_related("category").order_by("id")

        # Optional filters for a frontend: ?category=<id>&search=<text>
        category_id = request.query_params.get("category")
        if category_id:
            if not category_id.isdigit():
                return Response(
                    {"category": "Must be a category id."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            products = products.filter(category_id=category_id)

        search = request.query_params.get("search")
        if search:
            products = products.filter(
                Q(name__icontains=search) | Q(description__icontains=search)
            )

        serializer = ProductSerializer(products, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = ProductSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProductDetailView(APIView):
    permission_classes = [IsAdminOrReadOnly]

    def get(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        return Response(ProductSerializer(product).data)

    def put(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        serializer = ProductSerializer(product, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        product.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# --------------------------------------------------------------------------
# Cart
# --------------------------------------------------------------------------
def cart_response(cart):
    items = cart.items.select_related("product").order_by("id")
    serializer = CartItemSerializer(items, many=True)
    total = sum(item.product.price * item.quantity for item in items)
    return {"items": serializer.data, "total": total}


class CartView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        return Response(cart_response(cart))

    def delete(self, request):
        """Empty the whole cart."""
        cart, _ = Cart.objects.get_or_create(user=request.user)
        cart.items.all().delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CartItemCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        product_id = request.data.get("product")
        if product_id is None:
            return Response(
                {"error": "Product is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        quantity = parse_quantity(request.data.get("quantity"), default=1)
        if quantity is None:
            return Response(
                {"error": "Quantity must be a positive integer."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            product = get_object_or_404(Product, pk=product_id)
        except (TypeError, ValueError):
            return Response(
                {"error": "Invalid product id."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cart, _ = Cart.objects.get_or_create(user=request.user)

        cart_item, created = CartItem.objects.get_or_create(
            cart=cart, product=product, defaults={"quantity": quantity}
        )
        if not created:
            cart_item.quantity += quantity
            cart_item.save()

        return Response(
            CartItemSerializer(cart_item).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class CartItemUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        cart_item = get_object_or_404(CartItem, pk=pk, cart__user=request.user)

        if request.data.get("quantity") is None:
            return Response(
                {"error": "Quantity is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        quantity = parse_quantity(request.data.get("quantity"))
        if quantity is None:
            return Response(
                {"error": "Quantity must be a positive integer."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cart_item.quantity = quantity
        cart_item.save()
        return Response(CartItemSerializer(cart_item).data)

    def delete(self, request, pk):
        cart_item = get_object_or_404(CartItem, pk=pk, cart__user=request.user)
        cart_item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# --------------------------------------------------------------------------
# Checkout + Orders
# --------------------------------------------------------------------------
class CheckoutView(APIView):
    """Turn the logged-in user's cart into an order, then empty the cart."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        with transaction.atomic():
            cart = Cart.objects.select_for_update().filter(user=request.user).first()
            cart_items = list(cart.items.select_related("product")) if cart else []

            if not cart_items:
                return Response(
                    {"detail": "Cart is empty."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            total = sum(item.product.price * item.quantity for item in cart_items)

            order = Order.objects.create(user=request.user, total=total)

            OrderItem.objects.bulk_create(
                [
                    OrderItem(
                        order=order,
                        product=item.product,
                        quantity=item.quantity,
                        price_at_purchase=item.product.price,
                    )
                    for item in cart_items
                ]
            )

            cart.items.all().delete()

        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)


class OrderListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        orders = (
            Order.objects.filter(user=request.user)
            .prefetch_related("items__product")
            .order_by("-created_at", "-id")
        )
        return Response(OrderSerializer(orders, many=True).data)


class OrderDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        order = get_object_or_404(
            Order.objects.prefetch_related("items__product"),
            pk=pk,
            user=request.user,
        )
        return Response(OrderSerializer(order).data)


class OrderCancelView(APIView):
    """Customers can cancel their own order while it is still pending."""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk, user=request.user)

        if order.status != "pending":
            return Response(
                {
                    "detail": f"Only pending orders can be cancelled (this one is {order.status})."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        order.status = "cancelled"
        order.save(update_fields=["status"])
        return Response(OrderSerializer(order).data)
