

import uuid
from database import execute_query, fetch_all, fetch_one
from modules.payment import process_payment

CATEGORIES = ('Meals', 'Breakfast', 'Snacks', 'Beverages', 'Dessert')
ORDER_STATUSES = ('PLACED', 'PREPARING', 'OUT_FOR_DELIVERY', 'DELIVERED', 'CANCELLED')


def generate_food_order_id() -> str:
    """Generate a unique food order reference ID."""
    return f"FOD-{uuid.uuid4().hex[:6].upper()}"


# =====================================================================
# MENU MANAGEMENT
# =====================================================================

def get_food_menu(category: str = None, only_available: bool = True) -> list:
    """Retrieve food items from the pantry catalog."""
    query = "SELECT * FROM food_menu WHERE 1=1"
    params = []
    if only_available:
        query += " AND is_available = 1"
    if category and category in CATEGORIES:
        query += " AND category = ?"
        params.append(category)

    query += " ORDER BY category, price ASC"
    return fetch_all(query, tuple(params))


def get_menu_item_by_id(item_id: int) -> dict:
    """Get single menu item by ID."""
    return fetch_one("SELECT * FROM food_menu WHERE id = ?", (item_id,))


def add_menu_item(item_name: str, category: str, price: float, is_available: int = 1) -> tuple:
    """Admin tool: Add a new dish or drink to the pantry catalog."""
    name = item_name.strip()
    cat = category.strip()

    if not name:
        return False, "Item name is required."
    if cat not in CATEGORIES:
        return False, f"Invalid category. Must be one of: {', '.join(CATEGORIES)}"
    if price <= 0:
        return False, "Price must be greater than zero."

    try:
        item_id = execute_query(
            "INSERT INTO food_menu (item_name, category, price, is_available) VALUES (?, ?, ?, ?)",
            (name, cat, round(price, 2), 1 if is_available else 0)
        )
        return True, f"Item '{name}' added to menu (ID: {item_id})."
    except Exception as e:
        return False, f"Failed to add menu item: {str(e)}"


def toggle_menu_availability(item_id: int, is_available: bool) -> tuple:
    """Staff/Admin: Toggle availability of an item."""
    try:
        execute_query(
            "UPDATE food_menu SET is_available = ? WHERE id = ?",
            (1 if is_available else 0, item_id)
        )
        state = "Available" if is_available else "Out of Stock"
        return True, f"Item status updated to: {state}."
    except Exception as e:
        return False, f"Failed to update menu item: {str(e)}"


# =====================================================================
# ORDERING SYSTEM
# =====================================================================

def place_food_order(pnr: str, user_id: int, items_ordered: list,
                     delivery_station: str, seat_info: str,
                     payment_method: str = 'UPI') -> tuple:
    """
    Order food to seat linked to a verified confirmed PNR.
    items_ordered format: [{'item_id': int, 'quantity': int}, ...]
    Returns (success: bool, message: str, order_data: dict or None).
    """
    clean_pnr = pnr.strip()

    # Validate PNR exists and is CONFIRMED
    booking = fetch_one("SELECT * FROM bookings WHERE pnr = ?", (clean_pnr,))
    if not booking:
        return False, f"PNR '{clean_pnr}' not found. Please enter a valid booking PNR.", None

    if booking['booking_status'] != 'CONFIRMED':
        return False, f"Cannot order food. Booking status for PNR {clean_pnr} is {booking['booking_status']}.", None

    if not items_ordered or len(items_ordered) == 0:
        return False, "Order must contain at least one item.", None

    # Calculate total and validate availability
    validated_items = []
    total_amount = 0.0

    for item in items_ordered:
        item_id = item['item_id']
        qty = int(item['quantity'])
        if qty <= 0:
            continue

        db_item = get_menu_item_by_id(item_id)
        if not db_item:
            return False, f"Item ID {item_id} not found in menu.", None
        if not db_item['is_available']:
            return False, f"Item '{db_item['item_name']}' is currently out of stock.", None

        line_total = db_item['price'] * qty
        total_amount += line_total
        validated_items.append({
            'item_id': db_item['id'],
            'item_name': db_item['item_name'],
            'unit_price': db_item['price'],
            'quantity': qty,
            'line_total': line_total
        })

    if not validated_items:
        return False, "No valid items selected for order.", None

    # Process simulated payment
    order_id = generate_food_order_id()
    pay_ok, pay_msg, txn_id = process_payment(
        user_id=user_id,
        amount=total_amount,
        payment_method=payment_method,
        payment_type='FOOD_ORDER',
        food_order_id=order_id
    )

    if not pay_ok:
        return False, f"Food payment failed: {pay_msg}", None

    try:
        execute_query(
            """
            INSERT INTO food_orders (order_id, pnr, user_id, delivery_station, seat_info, total_amount, order_status, payment_status)
            VALUES (?, ?, ?, ?, ?, ?, 'PLACED', 'PAID')
            """,
            (order_id, clean_pnr, user_id, delivery_station.strip().upper(), seat_info.strip(), round(total_amount, 2))
        )

        for item in validated_items:
            execute_query(
                """
                INSERT INTO food_order_items (order_id, item_id, item_name, quantity, unit_price)
                VALUES (?, ?, ?, ?, ?)
                """,
                (order_id, item['item_id'], item['item_name'], item['quantity'], item['unit_price'])
            )

        order_data = {
            'order_id': order_id,
            'pnr': clean_pnr,
            'delivery_station': delivery_station.strip().upper(),
            'seat_info': seat_info.strip(),
            'items': validated_items,
            'total_amount': total_amount,
            'status': 'PLACED',
            'txn_id': txn_id
        }
        return True, f"Food order placed successfully! Order ID: {order_id}", order_data

    except Exception as e:
        return False, f"Failed to record food order: {str(e)}", None


def get_food_order_details(order_id: str) -> dict:
    """Retrieve food order details including line items."""
    order = fetch_one(
        """
        SELECT fo.*, u.full_name as customer_name, u.phone as customer_phone
        FROM food_orders fo
        JOIN users u ON fo.user_id = u.id
        WHERE fo.order_id = ?
        """,
        (order_id.strip(),)
    )
    if not order:
        return None

    items = fetch_all("SELECT * FROM food_order_items WHERE order_id = ?", (order['order_id'],))
    order['items'] = items
    return order


def get_food_orders_by_pnr(pnr: str) -> list:
    """Fetch all food orders linked to a specific PNR."""
    orders = fetch_all(
        "SELECT * FROM food_orders WHERE pnr = ? ORDER BY created_at DESC",
        (pnr.strip(),)
    )
    for o in orders:
        o['items'] = fetch_all("SELECT * FROM food_order_items WHERE order_id = ?", (o['order_id'],))
    return orders


def get_user_food_orders(user_id: int) -> list:
    """Fetch food order history for a logged in passenger."""
    orders = fetch_all(
        "SELECT * FROM food_orders WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,)
    )
    for o in orders:
        o['items'] = fetch_all("SELECT * FROM food_order_items WHERE order_id = ?", (o['order_id'],))
    return orders


def get_all_food_orders(status_filter: str = None) -> list:
    """Staff Pantry Dashboard: View active or filtered food orders."""
    query = """
    SELECT fo.*, u.full_name as customer_name, u.phone as customer_phone
    FROM food_orders fo
    JOIN users u ON fo.user_id = u.id
    WHERE 1=1
    """
    params = []
    if status_filter:
        query += " AND fo.order_status = ?"
        params.append(status_filter)

    query += " ORDER BY fo.created_at DESC"
    orders = fetch_all(query, tuple(params))
    for o in orders:
        o['items'] = fetch_all("SELECT * FROM food_order_items WHERE order_id = ?", (o['order_id'],))
    return orders


def update_food_order_status(order_id: str, new_status: str) -> tuple:
    """Staff / Pantry tool: Advance order status."""
    status = new_status.strip().upper()
    if status not in ORDER_STATUSES:
        return False, f"Invalid status. Must be one of: {', '.join(ORDER_STATUSES)}"

    try:
        execute_query(
            "UPDATE food_orders SET order_status = ? WHERE order_id = ?",
            (status, order_id.strip())
        )
        return True, f"Order {order_id} status updated to '{status}'."
    except Exception as e:
        return False, f"Failed to update food order status: {str(e)}"
