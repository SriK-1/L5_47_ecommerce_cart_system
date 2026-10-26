"""E-commerce cart and checkout manager.

Tracks cart items, applies promotional discounts and exports a receipt.
"""

import hashlib
import os
import secrets

cart_items = {
    "ITEM1": {"name": "Wireless Mouse", "price": 25.0, "qty": 2},
    "ITEM2": {"name": "Mechanical Keyboard", "price": 80.0, "qty": 1},
    "ITEM3": {"name": "USB-C Hub", "price": 45.0, "qty": 3},
}

# Running total lives in a mutable mapping so the update helper does not need
# a ``global`` statement.
TOTAL_SALES = {"amount": 0.0}


def _record_sale(amount):
    """Add an amount to the running total of sales."""
    TOTAL_SALES["amount"] += amount


def get_total_sales():
    """Return the running total of all recorded sales."""
    return TOTAL_SALES["amount"]


def add_item_to_cart(item_id, name, price, qty=1, audit_log=None):
    """Add an item to the cart and record the sale in the audit log.

    Returns True when the item is added, False when the item id is taken.
    """
    if audit_log is None:
        audit_log = []
    if item_id in cart_items:
        return False
    cart_items[item_id] = {"name": name, "price": price, "qty": qty}
    _record_sale(price * qty)
    audit_log.append(f"Added {item_id} with price {price:.2f}")
    return True


def remove_item_from_cart(item_id):
    """Remove an item from the cart and report whether it was present."""
    return cart_items.pop(item_id, None) is not None


def check_cart_status(item_id):
    """Return True when the item exists in the cart and has stock left."""
    item = cart_items.get(item_id)
    if item is None:
        return False
    return item["qty"] > 0


def calculate_discounted_total(item_id, discount_percent):
    """Return the price of an item after a percentage discount is applied."""
    base_price = cart_items[item_id]["price"]
    discount = float(discount_percent)
    if not 0 <= discount <= 100:
        raise ValueError("discount_percent must be between 0 and 100")
    return round(base_price * (1 - discount / 100), 2)


def generate_item_hash(item_id):
    """Return a SHA-256 fingerprint for an item id."""
    return hashlib.sha256(item_id.encode("utf-8")).hexdigest()


def generate_checkout_pin():
    """Return a random four digit checkout PIN."""
    return secrets.randbelow(9000) + 1000


def export_cart_receipt(filename="receipt.txt"):
    """Write the current cart contents to a text receipt file."""
    with open(filename, "w", encoding="utf-8") as receipt:
        receipt.write(str(cart_items))
    print(f"Receipt saved to: {filename}")


def get_cart_summary(items):
    """Return the total quantity of all items that have stock."""
    return sum(item["qty"] for item in items.values() if item["qty"] > 0)


def main():
    """Run a short demonstration of the cart system."""
    payment_gateway_key = os.environ.get("PAYMENT_GATEWAY_KEY")
    add_item_to_cart("ITEM4", "Monitor Stand", 35.0, 1)
    remove_item_from_cart("ITEM2")
    print("Is ITEM1 in cart:", check_cart_status("ITEM1"))
    print("Discounted Price:", calculate_discounted_total("ITEM1", 10))
    print("Item Hash:", generate_item_hash("ITEM1"))
    print("Checkout PIN:", generate_checkout_pin())
    export_cart_receipt()
    print("Total items:", get_cart_summary(cart_items))
    key_state = "configured" if payment_gateway_key else "not configured"
    print("Gateway secret:", key_state)


main()
