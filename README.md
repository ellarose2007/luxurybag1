# Luxury Bag Management System

Multi-user web system built with **Python Flask + OOP**. Data is kept in **Python lists only (no database)**, so it resets whenever the server restarts.

## Run

```
pip install -r requirements.txt
python app.py
```
Open http://127.0.0.1:5000

## Demo accounts

| Role     | Username   | Password     |
|----------|------------|--------------|
| Admin    | admin      | admin123     |
| Staff    | staff      | staff123     |
| Customer | customer   | customer123  |

## Requirements checklist

| Requirement | Where |
|---|---|
| 3 user roles | Admin, Staff, Customer, each with different access |
| Login & role-based access | `/login`, `permission_required` decorator in `app.py`; each role has its own dashboard |
| CRUD | Bags (admin/staff), Users (admin), Orders (staff/admin manage, customers place and cancel) |
| Python OOP | `models.py` (see below) |
| Temporary storage | `storage.py` uses lists: `users`, `bags`, `orders` |
| Flask + HTML/CSS | `app.py`, `templates/`, `static/style.css` |
| Page design | Shared layout, sidebar, consistent luxury theme |
| Validation & error handling | `validators.py`, flash messages, 403/404/405/500 pages |

## OOP map (`models.py`)

- **Functions**: `make_bag()`, `make_user()`, `peso()` helpers
- **Encapsulation**: private `__password_hash` in `User`, private `__stock` in `Bag` (accessed via methods/properties)
- **Inheritance**: `Admin`, `Staff`, `Customer` extend `User`; `Handbag`, `TravelBag`, `Backpack` extend `Bag`
- **Polymorphism**: `permissions()` and `dashboard_endpoint()` differ per role; `care_tip()` and `service_fee()` differ per bag type

## Roles

- **Admin**: dashboard with reports, manage users, bags and orders
- **Staff**: manage bag inventory and order status
- **Customer**: browse shop, place orders, view/cancel own orders
