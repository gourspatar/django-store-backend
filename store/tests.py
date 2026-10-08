import json
from decimal import Decimal
from unittest import mock

from django.core import mail
from django.test import override_settings

from django.contrib.auth.models import User
from rest_framework.test import APITestCase

from .models import Category, Product, Cart, CartItem, Order


class StoreAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user("buyer", password="pass12345")
        self.other = User.objects.create_user("other", password="pass12345")
        self.seller = User.objects.create_user(
            "seller", password="pass12345", is_staff=True
        )
        self.category = Category.objects.create(name="Shoes")
        self.p1 = Product.objects.create(
            name="Runner", price=Decimal("50.00"), category=self.category
        )
        self.p2 = Product.objects.create(
            name="Boot", price=Decimal("80.50"), category=self.category
        )

    # ---- catalog permissions
    def test_catalog_is_public_to_read(self):
        self.assertEqual(self.client.get("/api/products/").status_code, 200)
        self.assertEqual(self.client.get("/api/categories/").status_code, 200)

    def test_customer_cannot_create_product(self):
        self.client.force_authenticate(self.user)
        r = self.client.post(
            "/api/products/",
            {"name": "X", "price": "1.00", "category": self.category.id},
        )
        self.assertEqual(r.status_code, 403)

    def test_seller_can_create_product(self):
        self.client.force_authenticate(self.seller)
        r = self.client.post(
            "/api/products/",
            {"name": "X", "price": "1.00", "category": self.category.id},
        )
        self.assertEqual(r.status_code, 201)

    def test_product_filter_by_category_and_search(self):
        r = self.client.get(f"/api/products/?category={self.category.id}&search=boot")
        self.assertEqual([p["name"] for p in r.data], ["Boot"])

    # ---- cart
    def test_cart_requires_login(self):
        self.assertIn(self.client.get("/api/cart/").status_code, (401, 403))

    def test_add_to_cart_merges_quantities(self):
        self.client.force_authenticate(self.user)
        self.client.post(
            "/api/cart/items/", {"product": self.p1.id, "quantity": 2}, format="json"
        )
        r = self.client.post(
            "/api/cart/items/", {"product": self.p1.id, "quantity": "3"}, format="json"
        )
        self.assertEqual(r.data["quantity"], 5)

    def test_invalid_quantity_rejected(self):
        self.client.force_authenticate(self.user)
        for bad in (0, -1, "abc", 1.5 * 0):
            r = self.client.post(
                "/api/cart/items/",
                {"product": self.p1.id, "quantity": bad},
                format="json",
            )
            self.assertEqual(r.status_code, 400)

    def test_cart_total(self):
        self.client.force_authenticate(self.user)
        self.client.post(
            "/api/cart/items/", {"product": self.p1.id, "quantity": 2}, format="json"
        )
        self.client.post("/api/cart/items/", {"product": self.p2.id}, format="json")
        r = self.client.get("/api/cart/")
        self.assertEqual(Decimal(str(r.data["total"])), Decimal("180.50"))

    def test_cannot_touch_another_users_cart_item(self):
        cart = Cart.objects.create(user=self.other)
        item = CartItem.objects.create(cart=cart, product=self.p1)
        self.client.force_authenticate(self.user)
        self.assertEqual(
            self.client.delete(f"/api/cart/items/{item.id}/").status_code, 404
        )

    # ---- checkout + orders
    def test_checkout_empty_cart(self):
        self.client.force_authenticate(self.user)
        self.assertEqual(self.client.post("/api/checkout/").status_code, 400)

    def test_checkout_creates_order_and_clears_cart(self):
        self.client.force_authenticate(self.user)
        self.client.post(
            "/api/cart/items/", {"product": self.p1.id, "quantity": 2}, format="json"
        )
        self.client.post(
            "/api/cart/items/", {"product": self.p2.id, "quantity": 1}, format="json"
        )

        r = self.client.post("/api/checkout/")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(Decimal(str(r.data["total"])), Decimal("180.50"))
        self.assertEqual(r.data["status"], "pending")
        self.assertEqual(len(r.data["items"]), 2)
        self.assertEqual(CartItem.objects.filter(cart__user=self.user).count(), 0)

    def test_price_is_frozen_at_purchase(self):
        self.client.force_authenticate(self.user)
        self.client.post("/api/cart/items/", {"product": self.p1.id}, format="json")
        order_id = self.client.post("/api/checkout/").data["id"]
        self.p1.price = Decimal("999.00")
        self.p1.save()
        r = self.client.get(f"/api/orders/{order_id}/")
        self.assertEqual(
            Decimal(r.data["items"][0]["price_at_purchase"]), Decimal("50.00")
        )

    def test_orders_are_private(self):
        order = Order.objects.create(user=self.other, total=Decimal("10.00"))
        self.client.force_authenticate(self.user)
        self.assertEqual(self.client.get(f"/api/orders/{order.id}/").status_code, 404)
        self.assertEqual(len(self.client.get("/api/orders/").data), 0)

    def test_cancel_only_pending(self):
        self.client.force_authenticate(self.user)
        order = Order.objects.create(user=self.user, total=Decimal("10.00"))
        self.assertEqual(
            self.client.post(f"/api/orders/{order.id}/cancel/").status_code, 200
        )
        self.assertEqual(
            self.client.post(f"/api/orders/{order.id}/cancel/").status_code, 400
        )


class AuthTests(APITestCase):
    def register(self, **overrides):
        data = {
            "username": "newbie",
            "email": "newbie@example.com",
            "password": "S0me-strong-pass!",
            "password2": "S0me-strong-pass!",
        }
        data.update(overrides)
        return self.client.post("/api/auth/register/", data, format="json")

    def test_register_returns_user_and_tokens(self):
        r = self.register()
        self.assertEqual(r.status_code, 201)
        self.assertIn("access", r.data)
        self.assertIn("refresh", r.data)
        self.assertNotIn("password", r.data["user"])

    def test_register_rejects_mismatch_weak_and_duplicate_email(self):
        self.assertEqual(self.register(password2="different").status_code, 400)
        self.assertEqual(
            self.register(password="123", password2="123").status_code, 400
        )
        self.assertEqual(self.register().status_code, 201)
        self.assertEqual(self.register(username="other").status_code, 400)

    def test_login_and_use_access_token(self):
        self.register()
        r = self.client.post(
            "/api/auth/login/",
            {"username": "newbie", "password": "S0me-strong-pass!"},
            format="json",
        )
        self.assertEqual(r.status_code, 200)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['access']}")
        me = self.client.get("/api/auth/me/")
        self.assertEqual(me.data["username"], "newbie")

    def test_wrong_password_and_no_token(self):
        self.register()
        r = self.client.post(
            "/api/auth/login/",
            {"username": "newbie", "password": "nope"},
            format="json",
        )
        self.assertEqual(r.status_code, 401)
        self.assertEqual(self.client.get("/api/auth/me/").status_code, 401)

    def test_refresh_and_logout_blacklists_token(self):
        tokens = self.register().data
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        r = self.client.post(
            "/api/auth/logout/", {"refresh": tokens["refresh"]}, format="json"
        )
        self.assertEqual(r.status_code, 204)
        self.client.credentials()
        r = self.client.post(
            "/api/auth/refresh/", {"refresh": tokens["refresh"]}, format="json"
        )
        self.assertEqual(r.status_code, 401)


@override_settings(
    STRIPE_SECRET_KEY="sk_test_dummy",
    STRIPE_WEBHOOK_SECRET="whsec_dummy",
    STRIPE_CURRENCY="usd",
)
class StripePaymentTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            "buyer", email="buyer@example.com", password="pass12345"
        )
        self.other = User.objects.create_user("other", password="pass12345")
        category = Category.objects.create(name="Shoes")
        self.p1 = Product.objects.create(
            name="Runner", price=Decimal("50.00"), category=category
        )
        self.order = Order.objects.create(user=self.user, total=Decimal("100.00"))
        self.order.items.create(
            product=self.p1, quantity=2, price_at_purchase=Decimal("50.00")
        )
        self.url = f"/api/orders/{self.order.id}/pay/"

    def fake_session(self, status_="open"):
        s = mock.Mock()
        s.id, s.url, s.status = (
            "cs_test_123",
            "https://checkout.stripe.com/c/pay/cs_test_123",
            status_,
        )
        return s

    # ---- creating the session
    def test_pay_requires_login(self):
        self.assertEqual(self.client.post(self.url).status_code, 401)

    @mock.patch("store.views.stripe.checkout.Session.create")
    def test_pay_creates_session_with_correct_amounts(self, create):
        create.return_value = self.fake_session()
        self.client.force_authenticate(self.user)
        r = self.client.post(self.url)
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data["checkout_url"], create.return_value.url)
        kwargs = create.call_args.kwargs
        self.assertEqual(kwargs["metadata"], {"order_id": str(self.order.id)})
        line = kwargs["line_items"][0]
        self.assertEqual(line["quantity"], 2)
        self.assertEqual(line["price_data"]["unit_amount"], 5000)
        self.order.refresh_from_db()
        self.assertEqual(self.order.stripe_session_id, "cs_test_123")

    @mock.patch("store.views.stripe.checkout.Session.retrieve")
    @mock.patch("store.views.stripe.checkout.Session.create")
    def test_pay_reuses_open_session(self, create, retrieve):
        self.order.stripe_session_id = "cs_test_123"
        self.order.save()
        retrieve.return_value = self.fake_session("open")
        self.client.force_authenticate(self.user)
        r = self.client.post(self.url)
        self.assertEqual(r.status_code, 200)
        create.assert_not_called()

    def test_cannot_pay_someone_elses_or_non_pending_order(self):
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.post(self.url).status_code, 404)
        self.client.force_authenticate(self.user)
        self.order.status = "paid"
        self.order.save()
        self.assertEqual(self.client.post(self.url).status_code, 400)

    @override_settings(STRIPE_SECRET_KEY="")
    def test_pay_without_stripe_key(self):
        self.client.force_authenticate(self.user)
        self.assertEqual(self.client.post(self.url).status_code, 503)

    # ---- webhook
    def event(self, amount=10000, payment_status="paid", order_id=None):
        return {
            "id": "evt_1",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_test_123",
                    "payment_status": payment_status,
                    "amount_total": amount,
                    "payment_intent": "pi_123",
                    "metadata": {"order_id": str(order_id or self.order.id)},
                }
            },
        }

    def post_webhook(self, event):
        # Bypass signature maths: construct_event is tested by Stripe itself.
        with mock.patch(
            "store.views.stripe.Webhook.construct_event", return_value=event
        ):
            return self.client.post(
                "/api/stripe/webhook/",
                data=json.dumps(event),
                content_type="application/json",
                HTTP_STRIPE_SIGNATURE="t=1,v1=fake",
            )

    def test_webhook_rejects_bad_signature(self):
        r = self.client.post(
            "/api/stripe/webhook/",
            data="{}",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="bad",
        )
        self.assertEqual(r.status_code, 400)

    def test_webhook_marks_paid_and_sends_confirmation_email(self):
        with self.captureOnCommitCallbacks(execute=True):
            r = self.post_webhook(self.event())
        self.assertEqual(r.status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "paid")
        self.assertIsNotNone(self.order.paid_at)
        self.assertEqual(self.order.stripe_payment_intent_id, "pi_123")
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(f"Order #{self.order.id}", mail.outbox[0].subject)
        self.assertEqual(mail.outbox[0].to, ["buyer@example.com"])

    def test_webhook_is_idempotent(self):
        with self.captureOnCommitCallbacks(execute=True):
            self.post_webhook(self.event())
            self.post_webhook(self.event())
        self.assertEqual(len(mail.outbox), 1)

    def test_webhook_ignores_unpaid_and_wrong_amount(self):
        self.post_webhook(self.event(payment_status="unpaid"))
        self.post_webhook(self.event(amount=1))
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "pending")

    def test_webhook_does_not_resurrect_cancelled_order(self):
        self.order.status = "cancelled"
        self.order.save()
        self.post_webhook(self.event())
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "cancelled")

    def test_full_flow_order_shows_paid_to_customer(self):
        self.post_webhook(self.event())
        self.client.force_authenticate(self.user)
        r = self.client.get(f"/api/orders/{self.order.id}/")
        self.assertEqual(r.data["status"], "paid")
