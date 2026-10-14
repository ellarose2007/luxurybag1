"""Temporary storage: plain Python lists only (NO DATABASE).
Data resets every time the server restarts.
"""
from models import make_user, make_bag, Order

users = []
bags = []
orders = []

_counters = {"user": 0, "bag": 0, "order": 0}


def next_id(kind):
    _counters[kind] += 1
    return _counters[kind]


# ---- generic finders --------------------------------------------------------
def find_user(user_id):
    return next((u for u in users if u.user_id == user_id), None)


def find_user_by_username(username):
    return next((u for u in users if u.username.lower() == username.lower()), None)


def find_bag(bag_id):
    return next((b for b in bags if b.bag_id == bag_id), None)


def find_order(order_id):
    return next((o for o in orders if o.order_id == order_id), None)


# ---- seed data ----------------------------------------------------------------
def seed():
    users.clear(); bags.clear(); orders.clear()
    for k in _counters:
        _counters[k] = 0

    for role, name, uname, pw, email in [
        ("admin", "Maison Admin", "admin", "admin123", "admin@luxbags.ph"),
        ("staff", "Sofia Reyes", "staff", "staff123", "staff@luxbags.ph"),
        ("customer", "Isabella Cruz", "customer", "customer123", "isabella@email.com"),
    ]:
        users.append(make_user(role, next_id("user"), name, uname, pw, email))

    samples = [
        ("Handbag", "Hermès", "Birkin 25", "Noir", "Togo Leather", 685000, 3,
         "Iconic structured tote with palladium hardware."),
        ("Handbag", "Chanel", "Classic Flap Medium", "Beige", "Lambskin", 520000, 5,
         "Quilted flap with the signature interlocking CC clasp."),
        ("Handbag", "Louis Vuitton", "Capucines MM", "Rouge", "Taurillon Leather", 375000, 2,
         "Elegant top handle bag with the LV flower charm."),
        ("Travel Bag", "Louis Vuitton", "Keepall 50", "Monogram", "Coated Canvas", 142000, 6,
         "The classic weekend travel companion."),
        ("Travel Bag", "Goyard", "Bourget GM", "Navy", "Goyardine Canvas", 198000, 1,
         "Hand-painted chevron canvas luggage."),
        ("Backpack", "Prada", "Re-Nylon Backpack", "Black", "Re-Nylon", 98000, 8,
         "Sleek everyday backpack with the enameled triangle logo."),
        ("Backpack", "Gucci", "Ophidia Backpack", "Beige/Ebony", "GG Supreme Canvas", 87000, 0,
         "Heritage web stripe on classic GG canvas."),
    ]
    for cat, brand, model, color, mat, price, stock, desc in samples:
        bags.append(make_bag(cat, next_id("bag"), brand, model, color, mat, price, stock, desc))

    cust = find_user_by_username("customer")
    bag = find_bag(2)
    o = Order(next_id("order"), cust.user_id, cust.full_name, bag, 1, "12 Palm Street, Davao City")
    bag.reduce_stock(1)
    orders.append(o)
