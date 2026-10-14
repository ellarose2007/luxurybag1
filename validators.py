"""Input validation helpers. Each returns (cleaned_value, error_message)."""
import re

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{4,20}$")


def required(value, label, max_len=80):
    value = (value or "").strip()
    if not value:
        return value, f"{label} is required."
    if len(value) > max_len:
        return value, f"{label} must be at most {max_len} characters."
    return value, None


def parse_price(raw):
    try:
        price = float(raw)
    except (TypeError, ValueError):
        return None, "Price must be a valid number."
    if price <= 0:
        return None, "Price must be greater than zero."
    if price > 100_000_000:
        return None, "Price is unrealistically high."
    return round(price, 2), None


def parse_int(raw, label, minimum=0, maximum=10_000):
    try:
        number = int(raw)
    except (TypeError, ValueError):
        return None, f"{label} must be a whole number."
    if number < minimum:
        return None, f"{label} must be at least {minimum}."
    if number > maximum:
        return None, f"{label} must be at most {maximum}."
    return number, None


def validate_username(username):
    username = (username or "").strip()
    if not USERNAME_RE.match(username):
        return username, "Username must be 4-20 letters, numbers or underscores."
    return username, None


def validate_password(password):
    if not password or len(password) < 6:
        return password, "Password must be at least 6 characters."
    return password, None


def validate_email(email):
    email = (email or "").strip()
    if email and not EMAIL_RE.match(email):
        return email, "Email address is not valid."
    return email, None
