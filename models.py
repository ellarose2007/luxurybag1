"""OOP models for the Luxury Bag Management System.

Concepts demonstrated
- Encapsulation : private attributes (__password_hash, __stock) behind properties/methods
- Inheritance   : Admin / Staff / Customer extend User; Handbag / TravelBag / Backpack extend Bag
- Polymorphism  : the same methods (permissions, dashboard_endpoint, care_tip, service_fee)
                  behave differently depending on the subclass
- Functions     : small helper functions at the bottom of the file
"""
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash


# ----------------------------------------------------------------------------
# USERS  (3 roles)
# ----------------------------------------------------------------------------
class User:
    role = "user"
    role_title = "User"

    def __init__(self, user_id, full_name, username, password, email=""):
        self.user_id = user_id
        self.full_name = full_name
        self.username = username
        self.email = email
        self.__password_hash = generate_password_hash(password)  # encapsulated

    # --- encapsulation -----------------------------------------------------
    def check_password(self, password):
        return check_password_hash(self.__password_hash, password)

    def set_password(self, new_password):
        self.__password_hash = generate_password_hash(new_password)

    # --- polymorphic interface (overridden by subclasses) -------------------
    def permissions(self):
        return []

    def dashboard_endpoint(self):
        return "login"

    def can(self, permission):
        return permission in self.permissions()


class Admin(User):
    role = "admin"
    role_title = "Administrator"

    def permissions(self):
        return ["manage_users", "manage_bags", "manage_orders", "view_reports"]

    def dashboard_endpoint(self):
        return "admin_dashboard"


class Staff(User):
    role = "staff"
    role_title = "Inventory Staff"

    def permissions(self):
        return ["manage_bags", "manage_orders"]

    def dashboard_endpoint(self):
        return "staff_dashboard"


class Customer(User):
    role = "customer"
    role_title = "Customer"

    def permissions(self):
        return ["browse_bags", "place_orders"]

    def dashboard_endpoint(self):
        return "customer_dashboard"


ROLE_CLASSES = {"admin": Admin, "staff": Staff, "customer": Customer}


# ----------------------------------------------------------------------------
# BAGS
# ----------------------------------------------------------------------------
class Bag:
    category = "Bag"
    service_rate = 0.02  # authentication / insurance fee as % of price

    def __init__(self, bag_id, brand, model, color, material, price, stock, description=""):
        self.bag_id = bag_id
        self.brand = brand
        self.model = model
        self.color = color
        self.material = material
        self.price = price
        self.description = description
        self.__stock = stock  # encapsulated

    # --- encapsulation -----------------------------------------------------
    @property
    def stock(self):
        return self.__stock

    @stock.setter
    def stock(self, value):
        if value < 0:
            raise ValueError("Stock cannot be negative.")
        self.__stock = value

    def reduce_stock(self, qty):
        if qty > self.__stock:
            raise ValueError("Not enough stock available.")
        self.__stock -= qty

    def add_stock(self, qty):
        self.__stock += qty

    # --- polymorphic interface ----------------------------------------------
    def care_tip(self):
        return "Store in a dust bag away from direct sunlight."

    def service_fee(self):
        return round(self.price * self.service_rate, 2)

    @property
    def status(self):
        if self.__stock == 0:
            return "Out of Stock"
        if self.__stock <= 2:
            return "Low Stock"
        return "In Stock"


class Handbag(Bag):
    category = "Handbag"
    service_rate = 0.03

    def care_tip(self):
        return "Stuff lightly with tissue paper and keep the handles supported."


class TravelBag(Bag):
    category = "Travel Bag"
    service_rate = 0.015

    def care_tip(self):
        return "Wipe with a damp cloth after trips and air out before storage."


class Backpack(Bag):
    category = "Backpack"
    service_rate = 0.01

    def care_tip(self):
        return "Empty all pockets and avoid overloading to keep its shape."


BAG_CLASSES = {"Handbag": Handbag, "Travel Bag": TravelBag, "Backpack": Backpack}


# ----------------------------------------------------------------------------
# ORDERS
# ----------------------------------------------------------------------------
class Order:
    STATUSES = ["Pending", "Confirmed", "Shipped", "Completed", "Cancelled"]

    def __init__(self, order_id, customer_id, customer_name, bag, quantity, address):
        self.order_id = order_id
        self.customer_id = customer_id
        self.customer_name = customer_name
        self.bag_id = bag.bag_id
        self.bag_name = f"{bag.brand} {bag.model}"
        self.quantity = quantity
        self.address = address
        self.unit_price = bag.price
        self.service_fee = bag.service_fee() * quantity
        self.status = "Pending"
        self.created_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    @property
    def total(self):
        return round(self.unit_price * self.quantity + self.service_fee, 2)


# ----------------------------------------------------------------------------
# helper functions
# ----------------------------------------------------------------------------
def make_bag(category, bag_id, brand, model, color, material, price, stock, description=""):
    """Factory: builds the right Bag subclass for the chosen category."""
    cls = BAG_CLASSES.get(category, Bag)
    return cls(bag_id, brand, model, color, material, price, stock, description)


def make_user(role, user_id, full_name, username, password, email=""):
    cls = ROLE_CLASSES[role]
    return cls(user_id, full_name, username, password, email)


def peso(value):
    return f"₱{value:,.2f}"
