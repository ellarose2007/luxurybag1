"""Luxury Bag Management System - Flask backend."""
from functools import wraps

from flask import (Flask, render_template, request, redirect, url_for,
                   session, flash, abort)

import storage
import validators as v
from models import (BAG_CLASSES, Order, make_bag, make_user, peso)

app = Flask(__name__)
app.secret_key = "change-this-secret-key-before-deploying"
app.jinja_env.filters["peso"] = peso

storage.seed()


# ----------------------------------------------------------------------------
# Auth helpers
# ----------------------------------------------------------------------------
def current_user():
    uid = session.get("user_id")
    return storage.find_user(uid) if uid else None


@app.context_processor
def inject_globals():
    return {"me": current_user(), "categories": list(BAG_CLASSES)}


def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not current_user():
            flash("Please log in to continue.", "error")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapper


def permission_required(permission):
    """Role-based access: user's role class decides what is allowed."""
    def decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            user = current_user()
            if not user:
                flash("Please log in to continue.", "error")
                return redirect(url_for("login"))
            if not user.can(permission):
                abort(403)
            return view(*args, **kwargs)
        return wrapper
    return decorator


# ----------------------------------------------------------------------------
# Login / logout / register
# ----------------------------------------------------------------------------
@app.route("/")
def index():
    user = current_user()
    return redirect(url_for(user.dashboard_endpoint())) if user else redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if not username or not password:
            flash("Please enter both username and password.", "error")
            return render_template("login.html", username=username)
        user = storage.find_user_by_username(username)
        if user and user.check_password(password):
            session.clear()
            session["user_id"] = user.user_id
            flash(f"Welcome back, {user.full_name}!", "success")
            return redirect(url_for(user.dashboard_endpoint()))
        flash("Invalid username or password.", "error")
        return render_template("login.html", username=username)
    if current_user():
        return redirect(url_for("index"))
    return render_template("login.html", username="")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    form = request.form
    if request.method == "POST":
        errors = []
        name, e = v.required(form.get("full_name"), "Full name"); errors.append(e)
        uname, e = v.validate_username(form.get("username")); errors.append(e)
        email, e = v.validate_email(form.get("email")); errors.append(e)
        pw, e = v.validate_password(form.get("password")); errors.append(e)
        if pw != form.get("confirm"):
            errors.append("Passwords do not match.")
        if not any(errors) and storage.find_user_by_username(uname):
            errors.append("That username is already taken.")
        errors = [e for e in errors if e]
        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("register.html", form=form)
        storage.users.append(make_user("customer", storage.next_id("user"), name, uname, pw, email))
        flash("Account created! You can now log in.", "success")
        return redirect(url_for("login"))
    return render_template("register.html", form={})


# ----------------------------------------------------------------------------
# Dashboards (one per role)
# ----------------------------------------------------------------------------
def inventory_stats():
    return {
        "total_bags": len(storage.bags),
        "units": sum(b.stock for b in storage.bags),
        "low": sum(1 for b in storage.bags if b.status == "Low Stock"),
        "out": sum(1 for b in storage.bags if b.status == "Out of Stock"),
        "value": sum(b.price * b.stock for b in storage.bags),
        "pending": sum(1 for o in storage.orders if o.status == "Pending"),
    }


@app.route("/admin")
@permission_required("view_reports")
def admin_dashboard():
    revenue = sum(o.total for o in storage.orders if o.status == "Completed")
    return render_template("admin_dashboard.html", stats=inventory_stats(),
                           users_count=len(storage.users), orders_count=len(storage.orders),
                           revenue=revenue, recent=storage.orders[-5:][::-1])


@app.route("/staff")
@permission_required("manage_bags")
def staff_dashboard():
    if current_user().role == "admin":
        return redirect(url_for("admin_dashboard"))
    attention = [b for b in storage.bags if b.status != "In Stock"]
    return render_template("staff_dashboard.html", stats=inventory_stats(), attention=attention,
                           pending=[o for o in storage.orders if o.status == "Pending"])


@app.route("/customer")
@permission_required("browse_bags")
def customer_dashboard():
    mine = [o for o in storage.orders if o.customer_id == current_user().user_id]
    featured = [b for b in storage.bags if b.stock > 0][:3]
    return render_template("customer_dashboard.html", orders=mine[::-1][:5], featured=featured,
                           spent=sum(o.total for o in mine if o.status != "Cancelled"))


# ----------------------------------------------------------------------------
# BAGS - CRUD (admin + staff)
# ----------------------------------------------------------------------------
def read_bag_form(form):
    errors = []
    brand, e = v.required(form.get("brand"), "Brand", 40); errors.append(e)
    model, e = v.required(form.get("model"), "Model", 60); errors.append(e)
    color, e = v.required(form.get("color"), "Color", 30); errors.append(e)
    material, e = v.required(form.get("material"), "Material", 40); errors.append(e)
    price, e = v.parse_price(form.get("price")); errors.append(e)
    stock, e = v.parse_int(form.get("stock"), "Stock", 0, 10000); errors.append(e)
    category = form.get("category")
    if category not in BAG_CLASSES:
        errors.append("Please choose a valid category.")
    description = (form.get("description") or "").strip()[:300]
    return [e for e in errors if e], dict(category=category, brand=brand, model=model, color=color,
                                          material=material, price=price, stock=stock,
                                          description=description)


@app.route("/bags")
@permission_required("manage_bags")
def bags_list():
    q = request.args.get("q", "").strip().lower()
    cat = request.args.get("category", "")
    items = [b for b in storage.bags
             if (not q or q in f"{b.brand} {b.model} {b.color}".lower())
             and (not cat or b.category == cat)]
    return render_template("bags_list.html", bags=items, q=q, cat=cat)


@app.route("/bags/add", methods=["GET", "POST"])
@permission_required("manage_bags")
def bag_add():
    if request.method == "POST":
        errors, data = read_bag_form(request.form)
        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("bag_form.html", bag=request.form, mode="Add")
        bag = make_bag(data["category"], storage.next_id("bag"), data["brand"], data["model"],
                       data["color"], data["material"], data["price"], data["stock"], data["description"])
        storage.bags.append(bag)
        flash(f"{bag.brand} {bag.model} added to inventory.", "success")
        return redirect(url_for("bags_list"))
    return render_template("bag_form.html", bag={}, mode="Add")


@app.route("/bags/<int:bag_id>/edit", methods=["GET", "POST"])
@permission_required("manage_bags")
def bag_edit(bag_id):
    bag = storage.find_bag(bag_id)
    if not bag:
        abort(404)
    if request.method == "POST":
        errors, data = read_bag_form(request.form)
        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("bag_form.html", bag=request.form, mode="Update", bag_id=bag_id)
        # category change => rebuild with correct subclass (polymorphism)
        new_bag = make_bag(data["category"], bag.bag_id, data["brand"], data["model"], data["color"],
                           data["material"], data["price"], data["stock"], data["description"])
        storage.bags[storage.bags.index(bag)] = new_bag
        flash("Bag updated successfully.", "success")
        return redirect(url_for("bags_list"))
    form = dict(category=bag.category, brand=bag.brand, model=bag.model, color=bag.color,
                material=bag.material, price=bag.price, stock=bag.stock, description=bag.description)
    return render_template("bag_form.html", bag=form, mode="Update", bag_id=bag_id)


@app.route("/bags/<int:bag_id>/delete", methods=["POST"])
@permission_required("manage_bags")
def bag_delete(bag_id):
    bag = storage.find_bag(bag_id)
    if not bag:
        abort(404)
    if any(o.bag_id == bag_id and o.status in ("Pending", "Confirmed", "Shipped") for o in storage.orders):
        flash("Cannot delete a bag that has active orders.", "error")
        return redirect(url_for("bags_list"))
    storage.bags.remove(bag)
    flash("Bag deleted.", "success")
    return redirect(url_for("bags_list"))


# ----------------------------------------------------------------------------
# USERS - CRUD (admin only)
# ----------------------------------------------------------------------------
@app.route("/users")
@permission_required("manage_users")
def users_list():
    return render_template("users_list.html", users=storage.users)


@app.route("/users/add", methods=["GET", "POST"])
@permission_required("manage_users")
def user_add():
    if request.method == "POST":
        f = request.form
        errors = []
        name, e = v.required(f.get("full_name"), "Full name"); errors.append(e)
        uname, e = v.validate_username(f.get("username")); errors.append(e)
        email, e = v.validate_email(f.get("email")); errors.append(e)
        pw, e = v.validate_password(f.get("password")); errors.append(e)
        role = f.get("role")
        if role not in ("admin", "staff", "customer"):
            errors.append("Please choose a valid role.")
        if not any(errors) and storage.find_user_by_username(uname):
            errors.append("That username is already taken.")
        errors = [e for e in errors if e]
        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("user_form.html", u=f, mode="Add")
        storage.users.append(make_user(role, storage.next_id("user"), name, uname, pw, email))
        flash("User added.", "success")
        return redirect(url_for("users_list"))
    return render_template("user_form.html", u={}, mode="Add")


@app.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
@permission_required("manage_users")
def user_edit(user_id):
    user = storage.find_user(user_id)
    if not user:
        abort(404)
    if request.method == "POST":
        f = request.form
        errors = []
        name, e = v.required(f.get("full_name"), "Full name"); errors.append(e)
        uname, e = v.validate_username(f.get("username")); errors.append(e)
        email, e = v.validate_email(f.get("email")); errors.append(e)
        role = f.get("role")
        if role not in ("admin", "staff", "customer"):
            errors.append("Please choose a valid role.")
        new_pw = f.get("password", "")
        if new_pw:
            _, e = v.validate_password(new_pw); errors.append(e)
        other = storage.find_user_by_username(uname) if uname else None
        if other and other.user_id != user_id:
            errors.append("That username is already taken.")
        if user_id == current_user().user_id and role != "admin":
            errors.append("You cannot remove your own admin role.")
        errors = [e for e in errors if e]
        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("user_form.html", u=f, mode="Update", user_id=user_id)
        # rebuild when role changes so the correct subclass (permissions) applies
        updated = make_user(role, user.user_id, name, uname, new_pw or "temporary-pass", email)
        if not new_pw:
            updated._User__password_hash = user._User__password_hash  # keep old password
        storage.users[storage.users.index(user)] = updated
        flash("User updated.", "success")
        return redirect(url_for("users_list"))
    form = dict(full_name=user.full_name, username=user.username, email=user.email, role=user.role)
    return render_template("user_form.html", u=form, mode="Update", user_id=user_id)


@app.route("/users/<int:user_id>/delete", methods=["POST"])
@permission_required("manage_users")
def user_delete(user_id):
    user = storage.find_user(user_id)
    if not user:
        abort(404)
    if user_id == current_user().user_id:
        flash("You cannot delete your own account.", "error")
        return redirect(url_for("users_list"))
    storage.users.remove(user)
    flash("User deleted.", "success")
    return redirect(url_for("users_list"))


# ----------------------------------------------------------------------------
# ORDERS - staff/admin manage
# ----------------------------------------------------------------------------
@app.route("/orders")
@permission_required("manage_orders")
def orders_list():
    status = request.args.get("status", "")
    items = [o for o in storage.orders if not status or o.status == status]
    return render_template("orders_list.html", orders=items[::-1], status=status, statuses=Order.STATUSES)


@app.route("/orders/<int:order_id>/status", methods=["POST"])
@permission_required("manage_orders")
def order_status(order_id):
    order = storage.find_order(order_id)
    if not order:
        abort(404)
    new = request.form.get("status")
    if new not in Order.STATUSES:
        flash("Invalid status.", "error")
        return redirect(url_for("orders_list"))
    if order.status == "Cancelled":
        flash("Cancelled orders cannot be changed.", "error")
        return redirect(url_for("orders_list"))
    if new == "Cancelled" and order.status != "Cancelled":
        bag = storage.find_bag(order.bag_id)
        if bag:
            bag.add_stock(order.quantity)  # return stock
    order.status = new
    flash(f"Order #{order.order_id} marked as {new}.", "success")
    return redirect(url_for("orders_list"))


@app.route("/orders/<int:order_id>/delete", methods=["POST"])
@permission_required("manage_orders")
def order_delete(order_id):
    order = storage.find_order(order_id)
    if not order:
        abort(404)
    if order.status not in ("Completed", "Cancelled"):
        flash("Only completed or cancelled orders can be deleted.", "error")
        return redirect(url_for("orders_list"))
    storage.orders.remove(order)
    flash("Order record deleted.", "success")
    return redirect(url_for("orders_list"))


# ----------------------------------------------------------------------------
# CUSTOMER - shop + my orders
# ----------------------------------------------------------------------------
@app.route("/shop")
@permission_required("browse_bags")
def shop():
    q = request.args.get("q", "").strip().lower()
    cat = request.args.get("category", "")
    items = [b for b in storage.bags
             if (not q or q in f"{b.brand} {b.model} {b.color}".lower())
             and (not cat or b.category == cat)]
    return render_template("shop.html", bags=items, q=q, cat=cat)


@app.route("/shop/<int:bag_id>/order", methods=["GET", "POST"])
@permission_required("place_orders")
def place_order(bag_id):
    bag = storage.find_bag(bag_id)
    if not bag:
        abort(404)
    if request.method == "POST":
        qty, e1 = v.parse_int(request.form.get("quantity"), "Quantity", 1, 10)
        address, e2 = v.required(request.form.get("address"), "Delivery address", 150)
        errors = [e for e in (e1, e2) if e]
        if not errors and bag.stock < qty:
            errors.append(f"Only {bag.stock} unit(s) available.")
        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("order_form.html", bag=bag, form=request.form)
        user = current_user()
        order = Order(storage.next_id("order"), user.user_id, user.full_name, bag, qty, address)
        bag.reduce_stock(qty)
        storage.orders.append(order)
        flash(f"Order #{order.order_id} placed successfully!", "success")
        return redirect(url_for("my_orders"))
    return render_template("order_form.html", bag=bag, form={})


@app.route("/my-orders")
@permission_required("place_orders")
def my_orders():
    mine = [o for o in storage.orders if o.customer_id == current_user().user_id]
    return render_template("my_orders.html", orders=mine[::-1])


@app.route("/my-orders/<int:order_id>/cancel", methods=["POST"])
@permission_required("place_orders")
def cancel_order(order_id):
    order = storage.find_order(order_id)
    if not order or order.customer_id != current_user().user_id:
        abort(404)
    if order.status != "Pending":
        flash("Only pending orders can be cancelled.", "error")
        return redirect(url_for("my_orders"))
    bag = storage.find_bag(order.bag_id)
    if bag:
        bag.add_stock(order.quantity)
    order.status = "Cancelled"
    flash(f"Order #{order.order_id} cancelled.", "success")
    return redirect(url_for("my_orders"))


# ----------------------------------------------------------------------------
# Error handling
# ----------------------------------------------------------------------------
@app.errorhandler(403)
def forbidden(_):
    return render_template("error.html", code=403, title="Access Denied",
                           message="Your role does not have permission to open this page."), 403


@app.errorhandler(404)
def not_found(_):
    return render_template("error.html", code=404, title="Page Not Found",
                           message="The page or record you are looking for does not exist."), 404


@app.errorhandler(405)
def bad_method(_):
    return render_template("error.html", code=405, title="Not Allowed",
                           message="That action is not allowed here."), 405


@app.errorhandler(500)
def server_error(_):
    return render_template("error.html", code=500, title="Something Went Wrong",
                           message="An unexpected system error occurred. Please try again."), 500


if __name__ == "__main__":
    app.run(debug=True)
