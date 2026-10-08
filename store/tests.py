from decimal import Decimal

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
