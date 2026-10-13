"""
modules/payment.py - Payment Gateway & Transaction Processing
Handles simulated payments (UPI, Cards, NetBanking), refunds, and transaction ledgers.
"""

import uuid
from database import execute_query, fetch_all, fetch_one


def generate_transaction_id() -> str:
    """Generate a unique 12-character transaction ID."""
    return f"TXN-{uuid.uuid4().hex[:8].upper()}"


def process_payment(user_id: int, amount: float, payment_method: str,
                    payment_type: str, booking_id: int = None,
                    food_order_id: str = None) -> tuple:
    """
    Process a simulated payment transaction.
    Returns (success: bool, message: str, transaction_id: str or None).
    """
    if amount <= 0:
        return False, "Invalid payment amount.", None

    method = payment_method.strip().upper()
    valid_methods = ('UPI', 'CARD', 'NETBANKING', 'WALLET', 'CASH')
    if method not in valid_methods:
        return False, f"Invalid payment method. Choose from: {', '.join(valid_methods)}", None

    p_type = payment_type.strip().upper()
    if p_type not in ('TICKET_BOOKING', 'FOOD_ORDER', 'REFUND'):
        return False, "Invalid payment type.", None

    txn_id = generate_transaction_id()

    try:
        execute_query(
            """
            INSERT INTO payments (transaction_id, user_id, booking_id, food_order_id, amount, payment_method, payment_type, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'SUCCESS')
            """,
            (txn_id, user_id, booking_id, food_order_id, round(amount, 2), method, p_type)
        )
        return True, f"Payment of Rs. {amount:.2f} successful via {method}. Txn ID: {txn_id}", txn_id
    except Exception as e:
        return False, f"Payment processing failed: {str(e)}", None


def process_refund(user_id: int, original_booking_id: int,
                   refund_amount: float, payment_method: str = 'UPI') -> tuple:
    """
    Issue a refund for a cancelled ticket or failed order.
    Returns (success: bool, message: str, refund_txn_id: str or None).
    """
    if refund_amount <= 0:
        return False, "Refund amount must be positive.", None

    refund_txn = f"REF-{uuid.uuid4().hex[:8].upper()}"

    try:
        execute_query(
            """
            INSERT INTO payments (transaction_id, user_id, booking_id, amount, payment_method, payment_type, status)
            VALUES (?, ?, ?, ?, ?, 'REFUND', 'REFUNDED')
            """,
            (refund_txn, user_id, original_booking_id, round(refund_amount, 2), payment_method)
        )
        return True, f"Refund of Rs. {refund_amount:.2f} processed. Refund Ref: {refund_txn}", refund_txn
    except Exception as e:
        return False, f"Refund processing failed: {str(e)}", None


def get_user_transactions(user_id: int) -> list:
    """Retrieve all payment records for a specific user."""
    return fetch_all(
        "SELECT * FROM payments WHERE user_id = ? ORDER BY timestamp DESC",
        (user_id,)
    )


def get_all_transactions(limit: int = 50) -> list:
    """Retrieve recent payment records across all users (Admin view)."""
    return fetch_all(
        """
        SELECT p.*, u.username, u.full_name
        FROM payments p
        JOIN users u ON p.user_id = u.id
        ORDER BY p.timestamp DESC
        LIMIT ?
        """,
        (limit,)
    )


def get_transaction_by_id(txn_id: str) -> dict:
    """Fetch single transaction record by ID."""
    return fetch_one("SELECT * FROM payments WHERE transaction_id = ?", (txn_id.strip(),))
