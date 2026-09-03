# 🛒 Django E-Commerce Store Backend

A backend for an e-commerce store built with **Django, Django REST Framework, and PostgreSQL**.

The project provides a seller/admin dashboard through Django Admin and REST API endpoints for a future frontend application.

---

## 🚀 Tech Stack

* **Python**
* **Django**
* **Django REST Framework (DRF)**
* **PostgreSQL**
* **Django ORM**
* **psycopg**
* **Git & GitHub**

---

# 📌 Project Progress

## Stage 4 — Django + Django REST Framework

### 4.1 — Django Project Setup ✅

Completed:

* Created Python virtual environment
* Installed Django
* Installed Django REST Framework
* Created Django project
* Understood Django project vs app structure
* Configured and ran the Django development server

---

## 4.2 — Store App ✅

Created the `store` Django application.

Configured the application inside:

```python
INSTALLED_APPS
```

Basic project structure:

```text
django-store-backend/
│
├── manage.py
│
├── config/
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
│
└── store/
    ├── admin.py
    ├── apps.py
    ├── models.py
    ├── serializers.py
    ├── views.py
    ├── urls.py
    ├── tests.py
    └── migrations/
```

---

# 🗄️ 4.3 — Database Models ✅

Connected Django to **PostgreSQL**.

### Category Model

Created a `Category` model containing:

* `id`
* `name`
* `description`

### Product Model

Created a `Product` model containing:

* `id`
* `name`
* `description`
* `price`
* `category`

### Relationship

Implemented a **many-to-one relationship**:

```text
Category
   │
   ├── Product
   ├── Product
   └── Product
```

Using Django's:

```python
ForeignKey
```

Products belong to a category.

### Migrations

Created and applied Django migrations:

```text
0001_initial
0002_product
```

Database structure:

```text
PostgreSQL
│
├── store_category
│
└── store_product
       │
       └── category_id
```

---

# 👨‍💼 4.4 — Django Admin / Seller Dashboard ✅

Configured Django Admin as the seller management dashboard.

### Completed

* Created Django superuser
* Registered `Category`
* Registered `Product`
* Customized admin interface
* Added product table columns
* Added product search
* Added category filtering
* Added category search
* Added and managed store data through Django Admin

### Product Admin

The product dashboard displays:

```text
ID | Name | Price | Category
```

Products can be searched by:

* Name
* Description

Products can also be filtered by:

* Category

Seller workflow:

```text
Seller
   ↓
Django Admin
   ↓
Django ORM
   ↓
PostgreSQL
```

---

# 🔌 4.5 — Django REST Framework Basics ✅

Introduced Django REST Framework and created the first REST API endpoints.

### Serializers

Created:

```text
CategorySerializer
ProductSerializer
```

Using:

```python
serializers.ModelSerializer
```

### API Views

Implemented DRF `APIView` classes for:

* Categories
* Products

### API URLs

Configured:

```text
/api/categories/
/api/products/
```

### GET & POST

Implemented:

```text
GET  /api/categories/
POST /api/categories/

GET  /api/products/
POST /api/products/
```

The APIs communicate with PostgreSQL through the Django ORM.

---

# 🔄 4.6 — Product & Category CRUD APIs ✅

Implemented complete CRUD functionality.

## Category API

### List Categories

```http
GET /api/categories/
```

### Create Category

```http
POST /api/categories/
```

### Get Category

```http
GET /api/categories/<id>/
```

### Update Category

```http
PUT /api/categories/<id>/
```

### Delete Category

```http
DELETE /api/categories/<id>/
```

---

## Product API

### List Products

```http
GET /api/products/
```

### Create Product

```http
POST /api/products/
```

### Get Product

```http
GET /api/products/<id>/
```

### Update Product

```http
PUT /api/products/<id>/
```

### Delete Product

```http
DELETE /api/products/<id>/
```

---

# ✅ Validation

Implemented serializer-based validation for API requests.

Invalid requests return:

```text
400 Bad Request
```

Examples include:

* Missing required fields
* Invalid product data
* Non-existent category IDs

---

# 🌐 HTTP Status Codes

The API currently uses appropriate HTTP status codes:

| Status            | Meaning                       |
| ----------------- | ----------------------------- |
| `200 OK`          | Successful GET/PUT            |
| `201 Created`     | Successfully created resource |
| `204 No Content`  | Successfully deleted resource |
| `400 Bad Request` | Invalid request/data          |
| `404 Not Found`   | Resource doesn't exist        |

---

# 🏗️ Current Architecture

```text
                    Client / Frontend
                           │
                           ↓
                    Django REST API
                           │
                 ┌─────────┴─────────┐
                 ↓                   ↓
              URLs                 Admin
                 │                   │
                 ↓                   ↓
              Views              Seller
                 │
                 ↓
             Serializers
                 │
                 ↓
            Django ORM
                 │
                 ↓
             PostgreSQL
```

---

# 📡 Current API

```text
CATEGORY
────────────────────────────────

GET     /api/categories/
POST    /api/categories/
GET     /api/categories/<id>/
PUT     /api/categories/<id>/
DELETE  /api/categories/<id/>


PRODUCT
────────────────────────────────

GET     /api/products/
POST    /api/products/
GET     /api/products/<id>/
PUT     /api/products/<id>/
DELETE  /api/products/<id/>
```

---

# 🧪 Testing Completed

The following functionality has been manually tested:

* Django development server
* PostgreSQL connection
* Database migrations
* Category creation
* Product creation
* Category → Product relationship
* Django Admin login
* Category management
* Product management
* Admin search
* Admin filtering
* Category GET
* Category POST
* Category PUT
* Category DELETE
* Product GET
* Product POST
* Product PUT
* Product DELETE
* API validation
* 404 handling
* HTTP status codes

---

# 📂 Important Files

```text
config/
│
├── settings.py       # Django configuration + PostgreSQL
└── urls.py           # Main URL configuration


store/
│
├── admin.py          # Seller/Admin dashboard
├── models.py         # Category + Product models
├── serializers.py    # API serializers
├── views.py          # API logic
├── urls.py           # Store API routes
└── migrations/       # Database migrations
```

---

# 🔑 Key Concepts Learned

Through this stage, the project introduced:

* Django project structure
* Django applications
* Django ORM
* Django models
* ForeignKey relationships
* PostgreSQL integration
* Django migrations
* Django Admin
* DRF serializers
* DRF APIView
* REST API design
* CRUD operations
* Request validation
* HTTP status codes
* 404 error handling
* API-to-database flow

---

# 📈 Progress

```text
Stage 4
│
├── 4.1 Django Project Setup       ✅
├── 4.2 Store App                  ✅
├── 4.3 Database Models            ✅
├── 4.4 Django Admin               ✅
├── 4.5 DRF Basics                 ✅
└── 4.6 Product & Category CRUD    ✅
```

---

# 🔜 Next Steps

The store backend can now be expanded with additional e-commerce functionality such as:

* Shopping cart
* Cart items
* Orders
* Order items
* User authentication
* Permissions
* More advanced API functionality
* API documentation
* Testing
* Deployment
* Frontend integration

---

## 🎯 Project Goal

The long-term goal is to turn this into a production-style **Django e-commerce backend** with:

```text
Products
Categories
Shopping Cart
Orders
Authentication
Seller Dashboard
REST APIs
PostgreSQL
```

The API layer will provide the foundation for a future frontend application.
