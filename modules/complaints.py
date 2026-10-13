
from datetime import datetime
import uuid
from database import execute_query, fetch_all, fetch_one

CATEGORIES = ('Cleanliness', 'Food Quality', 'Punctuality', 'Staff Behavior', 'Ticketing', 'Other')
STATUSES = ('OPEN', 'IN_PROGRESS', 'RESOLVED', 'CLOSED')


def generate_ticket_number() -> str:
    """Generate unique grievance tracking number e.g. CMP-2026-4B9A."""
    year = datetime.now().year
    code = uuid.uuid4().hex[:4].upper()
    return f"CMP-{year}-{code}"


def file_complaint(user_id: int, category: str, description: str, pnr: str = None) -> tuple:
    """
    Lodge a new grievance ticket.
    Returns (success: bool, message: str, ticket_number: str or None).
    """
    cat = category.strip()
    desc = description.strip()

    if cat not in CATEGORIES:
        return False, f"Invalid category. Must be one of: {', '.join(CATEGORIES)}", None

    if len(desc) < 10:
        return False, "Complaint description must be at least 10 characters long.", None

    clean_pnr = pnr.strip() if pnr else None
    if clean_pnr:
        # Verify if PNR exists
        booking = fetch_one("SELECT id FROM bookings WHERE pnr = ?", (clean_pnr,))
        if not booking:
            return False, f"Booking with PNR '{clean_pnr}' does not exist.", None

    ticket_number = generate_ticket_number()

    try:
        execute_query(
            """
            INSERT INTO complaints (ticket_number, user_id, pnr, category, description, status)
            VALUES (?, ?, ?, ?, ?, 'OPEN')
            """,
            (ticket_number, user_id, clean_pnr, cat, desc)
        )
        return True, f"Complaint registered successfully! Tracking Ticket: {ticket_number}", ticket_number
    except Exception as e:
        return False, f"Failed to register complaint: {str(e)}", None


def get_complaint_by_ticket(ticket_number: str) -> dict:
    """Fetch complaint details by ticket code."""
    return fetch_one(
        """
        SELECT c.*, u.full_name as passenger_name, u.phone as passenger_phone,
               e.full_name as assigned_staff_name
        FROM complaints c
        JOIN users u ON c.user_id = u.id
        LEFT JOIN employees e ON c.assigned_staff_id = e.id
        WHERE c.ticket_number = ?
        """,
        (ticket_number.strip().upper(),)
    )


def get_user_complaints(user_id: int) -> list:
    """Fetch all complaints filed by a passenger."""
    return fetch_all(
        "SELECT * FROM complaints WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,)
    )


def get_all_complaints(status: str = None, category: str = None) -> list:
    """Retrieve complaints with optional filters (Admin/Staff desk)."""
    query = """
    SELECT c.*, u.full_name as passenger_name, u.phone as passenger_phone,
           e.full_name as assigned_staff_name
    FROM complaints c
    JOIN users u ON c.user_id = u.id
    LEFT JOIN employees e ON c.assigned_staff_id = e.id
    WHERE 1=1
    """
    params = []
    if status and status in STATUSES:
        query += " AND c.status = ?"
        params.append(status)
    if category and category in CATEGORIES:
        query += " AND c.category = ?"
        params.append(category)

    query += " ORDER BY c.created_at DESC"
    return fetch_all(query, tuple(params))


def resolve_complaint(ticket_number: str, resolution_note: str,
                      staff_id: int = None, new_status: str = 'RESOLVED') -> tuple:
    """Resolve or update status of an open grievance ticket."""
    clean_ticket = ticket_number.strip().upper()
    comp = get_complaint_by_ticket(clean_ticket)
    if not comp:
        return False, f"Ticket {clean_ticket} not found."

    note = resolution_note.strip()
    status = new_status.strip().upper()
    if status not in STATUSES:
        return False, f"Invalid status: {status}"

    try:
        execute_query(
            """
            UPDATE complaints
            SET status = ?, resolution_note = ?, assigned_staff_id = ?, resolved_at = CURRENT_TIMESTAMP
            WHERE ticket_number = ?
            """,
            (status, note, staff_id, clean_ticket)
        )
        return True, f"Complaint {clean_ticket} marked as {status}."
    except Exception as e:
        return False, f"Failed to update complaint: {str(e)}"
