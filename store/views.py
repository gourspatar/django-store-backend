import logging
from decimal import ROUND_HALF_UP, Decimal

import stripe
from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
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
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Category, Product, Cart, CartItem, Order, OrderItem
from .serializers import (
    CategorySerializer,
    ProductSerializer,
    CartItemSerializer,
    OrderSerializer,
    RegisterSerializer,
    UserSerializer,
)

logger = logging.getLogger(__name__)


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
# Authentication (JWT)
# Login / refresh are provided by simplejwt's TokenObtainPairView and
# TokenRefreshView (see urls.py).
# --------------------------------------------------------------------------
class RegisterView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "user": UserSerializer(user).data,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            },
            status=status.HTTP_201_CREATED,
        )


class MeView(APIView):
    """Who am I? Handy for a frontend to check a stored token is still valid."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)


class LogoutView(APIView):
    """Blacklist the refresh token so it can't be used again."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        token = request.data.get("refresh")
        if not token:
            return Response(
                {"detail": "Refresh token is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            RefreshToken(token).blacklist()
        except TokenError:
            return Response(
                {"detail": "Invalid or expired token."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


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

        # Stop the customer paying for an order that no longer exists.
        if order.stripe_session_id and settings.STRIPE_SECRET_KEY:
            try:
                stripe.checkout.Session.expire(
                    order.stripe_session_id, api_key=settings.STRIPE_SECRET_KEY
                )
            except stripe.StripeError:
                logger.warning("Could not expire Stripe session for order %s", order.id)

        return Response(OrderSerializer(order).data)


# --------------------------------------------------------------------------
# Stripe payments
# --------------------------------------------------------------------------
def to_cents(amount):
    """Decimal('12.34') -> 1234 (Stripe wants the smallest currency unit)."""
    return int((Decimal(amount) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def send_order_confirmation(order_id):
    """Email the customer a receipt. Failures are logged, never raised."""
    try:
        order = (
            Order.objects.select_related("user")
            .prefetch_related("items__product")
            .get(pk=order_id)
        )
        if not order.user.email:
            return
        lines = "\n".join(
            f"  - {i.product.name} x {i.quantity} @ {i.price_at_purchase}"
            for i in order.items.all()
        )
        send_mail(
            subject=f"Order #{order.id} confirmed",
            message=(
                f"Hi {order.user.username},\n\n"
                f"Thanks for your purchase! We received your payment.\n\n"
                f"Order #{order.id}\n{lines}\n\n"
                f"Total paid: {order.total} {settings.STRIPE_CURRENCY.upper()}\n"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[order.user.email],
        )
    except Exception:
        logger.exception("Failed to send confirmation email for order %s", order_id)


def mark_order_paid(order_id, session):
    """
    Idempotent: Stripe may deliver the same webhook several times.
    Returns True if this call changed the order to paid.
    """
    with transaction.atomic():
        order = Order.objects.select_for_update().filter(pk=order_id).first()
        if order is None:
            logger.error("Stripe payment for unknown order %s", order_id)
            return False
        if order.status == "paid":
            return False
        if order.status != "pending":
            # e.g. cancelled while the customer was on the Stripe page.
            logger.error(
                "Order %s was paid but is %s - refund needed (session %s)",
                order.id,
                order.status,
                session["id"],
            )
            return False
        if session.get("amount_total") != to_cents(order.total):
            logger.error(
                "Amount mismatch on order %s (session %s)", order.id, session["id"]
            )
            return False

        order.status = "paid"
        order.paid_at = timezone.now()
        order.stripe_session_id = session["id"]
        order.stripe_payment_intent_id = session.get("payment_intent") or ""
        order.save(
            update_fields=[
                "status",
                "paid_at",
                "stripe_session_id",
                "stripe_payment_intent_id",
            ]
        )
        transaction.on_commit(lambda: send_order_confirmation(order.id))
    return True


class OrderPayView(APIView):
    """Create (or reuse) a Stripe Checkout Session for a pending order."""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if not settings.STRIPE_SECRET_KEY:
            return Response(
                {"detail": "Payments are not configured."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        order = get_object_or_404(
            Order.objects.prefetch_related("items__product"),
            pk=pk,
            user=request.user,
        )
        if order.status != "pending":
            return Response(
                {
                    "detail": f"Only pending orders can be paid (this one is {order.status})."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        api_key = settings.STRIPE_SECRET_KEY
        try:
            # Reuse a still-open session so the customer can't end up with two.
            if order.stripe_session_id:
                existing = stripe.checkout.Session.retrieve(
                    order.stripe_session_id, api_key=api_key
                )
                if existing.status == "open":
                    return Response(
                        {"checkout_url": existing.url, "session_id": existing.id}
                    )

            session = stripe.checkout.Session.create(
                api_key=api_key,
                mode="payment",
                line_items=[
                    {
                        "quantity": item.quantity,
                        "price_data": {
                            "currency": settings.STRIPE_CURRENCY,
                            "unit_amount": to_cents(item.price_at_purchase),
                            "product_data": {"name": item.product.name},
                        },
                    }
                    for item in order.items.all()
                ],
                client_reference_id=str(order.id),
                metadata={"order_id": str(order.id)},
                customer_email=request.user.email or None,
                success_url=settings.STRIPE_SUCCESS_URL,
                cancel_url=settings.STRIPE_CANCEL_URL,
            )
        except stripe.StripeError:
            logger.exception("Stripe error creating session for order %s", order.id)
            return Response(
                {"detail": "Could not start payment. Please try again."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        order.stripe_session_id = session.id
        order.save(update_fields=["stripe_session_id"])
        return Response(
            {"checkout_url": session.url, "session_id": session.id},
            status=status.HTTP_201_CREATED,
        )


@method_decorator(csrf_exempt, name="dispatch")
class StripeWebhookView(APIView):
    """
    Stripe calls this after a payment. This - not the browser redirect - is
    what marks an order as paid, so it can't be faked by the customer.
    The signature header proves the request really came from Stripe.
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        signature = request.META.get("HTTP_STRIPE_SIGNATURE", "")
        try:
            event = stripe.Webhook.construct_event(
                request.body, signature, settings.STRIPE_WEBHOOK_SECRET
            )
        except (ValueError, stripe.SignatureVerificationError):
            return Response(status=status.HTTP_400_BAD_REQUEST)

        if event["type"] in (
            "checkout.session.completed",
            "checkout.session.async_payment_succeeded",
        ):
            session = event["data"]["object"]
            if session.get("payment_status") == "paid":
                order_id = (session.get("metadata") or {}).get("order_id")
                if order_id:
                    mark_order_paid(order_id, session)

        # Always 200 for events we don't care about so Stripe stops retrying.
        return Response({"received": True})
