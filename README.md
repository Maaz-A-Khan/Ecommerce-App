<div align="center">

# 🛒 OrderHub

**A full-stack e-commerce application built with Django & Raw SQL**

[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Django](https://img.shields.io/badge/Django-5.x-092E20?style=for-the-badge&logo=django&logoColor=white)](https://djangoproject.com)
[![SQLite](https://img.shields.io/badge/SQLite-3-003B57?style=for-the-badge&logo=sqlite&logoColor=white)](https://sqlite.org)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)

*A DBMS course project demonstrating raw SQL operations, transaction management, and relational database design within a modern web application.*

---

[Features](#-features) · [Database Schema](#-database-schema) · [Getting Started](#-getting-started) · [Project Structure](#-project-structure) · [Screenshots](#-screenshots)

</div>

---

## ✨ Features

### 🛍️ Customer Storefront
- **Product Browsing** — View all products with category info and prices
- **Smart Cart** — Per-user cart stored in `localStorage` with quantity selectors (−/+), remove buttons, and real-time totals
- **Checkout with Region Tracking** — City and country captured at checkout for geographic analytics
- **Order History** — Full order history with drill-down to line-item details
- **Bundle Support** — Product bundles are automatically unpacked into individual items with discounted rates

### 🔧 Admin Panel
- **Product Management** — Add products (auto-generated codes: `PRD-001`…) and categories (`CAT-001`…) with delete safety checks
- **Order Tracking** — View all purchase and restock orders with user info and line-item detail
- **Chart of Accounts** — Lazily-created customer accounts + add suppliers (`SUPP-1001`…)
- **Stock & Restocking** — Real-time stock summary with color-coded indicators, one-click restock with auto-fetched product rates

### 🔐 Authentication & Security
- **Role-Based Access** — `customer` and `admin` roles with strict isolation
- **Lazy Account Initialization** — Ledger accounts created only when a customer places their first order
- **Parameterized Queries** — All SQL uses `%s` placeholders to prevent SQL injection
- **CSRF Protection** — Django's built-in CSRF middleware on all forms

### 🗄️ Database Design
- **100% Raw SQL** — No Django ORM for data operations; all queries use `connection.cursor()`
- **Atomic Transactions** — Checkout and restock operations wrapped in `transaction.atomic()`
- **Double-Entry Stock Ledger** — Stock tracked via `issue`/`receive` pattern: `available = SUM(receive) - SUM(issue)`
- **Historical Rate Snapshots** — Order detail stores the price at time of purchase

---

## 📊 Database Schema

The application uses **11 tables** with strict `snake_case` naming:

```mermaid
erDiagram
    region ||--o{ chart_of_account : "region_idno"
    chart_of_account ||--o| user : "account_code"
    user ||--o{ order_master : "user_id"
    category ||--o{ product : "category_code"
    product ||--o{ bundle_item : "product_code"
    product_bundle ||--o{ bundle_item : "bundle_code"
    order_master ||--o{ order_detail : "order_master_idno"
    order_master ||--o{ stock : "order_master_idno"
    product ||--o{ order_detail : "product_code"
    product ||--o{ stock : "product_code"
    warehouse ||--o{ order_detail : "warehouse_code"
    warehouse ||--o{ stock : "warehouse_code"

    region { int idno PK; string city; string country }
    user { int id PK; string username; string name; string role; string account_code FK }
    chart_of_account { string code PK; string name; string account_type; int region_idno FK }
    category { string code PK; string name }
    product { string code PK; string name; decimal rate; string category_code FK }
    product_bundle { string code PK; string name; decimal discount_percentage; bool is_active }
    bundle_item { int idno PK; string bundle_code FK; string product_code FK; int qty_included }
    warehouse { string code PK; string name }
    order_master { int idno PK; int user_id FK; string order_type; string entry_no; date order_date }
    order_detail { int idno PK; int order_master_idno FK; string product_code FK; string warehouse_code FK; int qty; decimal rate }
    stock { int idno PK; int order_master_idno FK; string warehouse_code FK; string product_code FK; int issue; int receive; date date }
```

### Auto-Generated Code Sequences

| Entity | Pattern | Example |
|---|---|---|
| Product | `PRD-XXX` | PRD-001, PRD-002, PRD-003… |
| Category | `CAT-XXX` | CAT-001, CAT-002, CAT-003… |
| Customer Account | `CUST-XXXX` | CUST-1001, CUST-1002… |
| Supplier Account | `SUPP-XXXX` | SUPP-1001, SUPP-1002… |
| Purchase Order | `ORD-XXXXX` | ORD-00001, ORD-00002… |
| Restock Order | `RST-XXXXX` | RST-00001, RST-00002… |

---

## 🚀 Getting Started

### Prerequisites

- Python 3.12+
- pip

### Installation

```bash
# Clone the repository
git clone https://github.com/Maaz-A-Khan/Ecommerce-App.git
cd Ecommerce-App

# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# Install dependencies
pip install django

# Run migrations
cd orderhub
python manage.py makemigrations
python manage.py migrate

# Create an admin user
python manage.py createsuperuser
# When prompted, enter a username, email (optional), and password
# Then go to Django admin (/admin/) and set the user's role to 'admin'

# Start the development server
python manage.py runserver
```

### Initial Setup

After starting the server, you need to configure a few things via Django's built-in admin at `http://127.0.0.1:8000/admin/`:

1. **Set admin role** — Edit your superuser and set `role = admin`
2. **Create a warehouse** — Add at least one warehouse (e.g., code: `WH-01`, name: `Main Warehouse`)
3. **Add categories** — Use the custom admin panel at `/admin-panel/products/`
4. **Add products** — Same page, select a category and enter name + rate
5. **Add a supplier** — Go to `/admin-panel/accounts/` and add a supplier
6. **Restock products** — Go to `/admin-panel/stock/` and place restock orders

Now register a customer account at `/register/` and start shopping!

---

## 📁 Project Structure

```
Ecommerce-App/
├── orderhub/                       # Django project root
│   ├── manage.py
│   ├── db.sqlite3
│   ├── orderhub/                   # Project settings
│   │   ├── settings.py
│   │   ├── urls.py
│   │   └── wsgi.py
│   └── core/                       # Main application
│       ├── models.py               # 11 models (schema definitions)
│       ├── views.py                # 15 views (all raw SQL)
│       ├── urls.py                 # 15 URL patterns
│       ├── admin.py                # Django admin registrations
│       ├── static/
│       │   ├── style.css           # Complete design system (~920 lines)
│       │   └── main.js             # Cart logic & UI rendering
│       └── templates/
│           ├── base.html           # Customer layout (sidebar + topbar)
│           ├── base_auth.html      # Auth layout (login)
│           ├── admin_base.html     # Admin layout
│           ├── register.html       # Glass-card registration page
│           ├── login.html          # Login form
│           ├── dashboard.html      # Customer dashboard
│           ├── products.html       # Product list with qty selectors
│           ├── checkout.html       # Cart + city/country + place order
│           ├── customer_dashboard.html   # Order history
│           ├── customer_order_detail.html # Order drill-down
│           ├── admin_products.html # Products & categories management
│           ├── admin_orders.html   # All orders list
│           ├── admin_order_detail.html   # Admin order drill-down
│           ├── admin_accounts.html # Customers + suppliers
│           └── admin_stock.html    # Stock summary + restock form
└── README.md
```

---

## 🖼️ Screenshots

> Screenshots can be added here after running the application.

| Page | Description |
|---|---|
| Login | Clean card UI on light background |
| Register | Animated gradient background with frosted-glass card |
| Dashboard | Quick-access cards for Products, Checkout, Order History |
| Products | Data table with quantity selectors and Add to Cart |
| Checkout | Cart summary table + city/country fields + Place Order |
| Admin Products | Add/delete products & categories with auto-generated codes |
| Admin Stock | Color-coded stock levels + one-click restock |
| Admin Accounts | Customer & supplier ledger accounts |

---

## 🔑 Key SQL Techniques

| Technique | Usage |
|---|---|
| `COALESCE(SUM(...), 0)` | Null-safe stock aggregation |
| `CAST(SUBSTR(code, N) AS INTEGER)` | Sequential code generation |
| `LOWER(col) = LOWER(%s)` | Case-insensitive region matching |
| `SELECT last_insert_rowid()` | Fetching auto-increment PKs in SQLite |
| `DATE('now')` / `DATETIME('now')` | SQLite date functions |
| Multi-table `JOIN` | Order details with product names + warehouse info |
| `transaction.atomic()` | All-or-nothing checkout & restock operations |

---

## 📝 License

This project is for educational purposes as part of a DBMS course project.

---

<div align="center">
  <sub>Built with ❤️ using Django & Raw SQL</sub>
</div>