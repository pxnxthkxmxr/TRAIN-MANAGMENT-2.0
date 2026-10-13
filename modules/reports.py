"""
modules/reports.py - System Analytics, Occupancy & Financial Reporting Dashboard
Computes aggregate revenue, booking trends, route occupancy, and operational statistics.
"""

from database import fetch_all, fetch_one


def get_system_overview_stats() -> dict:
    """Aggregate high-level key performance metrics for the admin dashboard."""
    users_count = fetch_one("SELECT COUNT(*) as c FROM users")['c']
    trains_count = fetch_one("SELECT COUNT(*) as c FROM trains WHERE status = 'ACTIVE'")['c']
    stations_count = fetch_one("SELECT COUNT(*) as c FROM stations")['c']
    staff_count = fetch_one("SELECT COUNT(*) as c FROM employees WHERE status = 'ACTIVE'")['c']

    total_bookings = fetch_one("SELECT COUNT(*) as c FROM bookings")['c']
    confirmed_bookings = fetch_one("SELECT COUNT(*) as c FROM bookings WHERE booking_status = 'CONFIRMED'")['c']
    cancelled_bookings = fetch_one("SELECT COUNT(*) as c FROM bookings WHERE booking_status = 'CANCELLED'")['c']
    passengers_booked = fetch_one("SELECT COUNT(*) as c FROM passengers")['c']

    # Financial breakdown
    ticket_rev_res = fetch_one("SELECT SUM(total_fare) as s FROM bookings WHERE booking_status = 'CONFIRMED'")
    ticket_revenue = ticket_rev_res['s'] if ticket_rev_res['s'] else 0.0

    food_rev_res = fetch_one("SELECT SUM(total_amount) as s FROM food_orders WHERE payment_status = 'PAID'")
    food_revenue = food_rev_res['s'] if food_rev_res['s'] else 0.0

    refunds_res = fetch_one("SELECT SUM(amount) as s FROM payments WHERE payment_type = 'REFUND'")
    total_refunds = refunds_res['s'] if refunds_res['s'] else 0.0

    # Net revenue
    net_revenue = ticket_revenue + food_revenue - total_refunds

    # Grievances
    complaints_total = fetch_one("SELECT COUNT(*) as c FROM complaints")['c']
    complaints_resolved = fetch_one("SELECT COUNT(*) as c FROM complaints WHERE status IN ('RESOLVED', 'CLOSED')")['c']
    complaints_open = fetch_one("SELECT COUNT(*) as c FROM complaints WHERE status = 'OPEN'")['c']

    return {
        'total_users': users_count,
        'active_trains': trains_count,
        'stations': stations_count,
        'active_staff': staff_count,
        'total_bookings': total_bookings,
        'confirmed_bookings': confirmed_bookings,
        'cancelled_bookings': cancelled_bookings,
        'passengers_travelled': passengers_booked,
        'gross_ticket_revenue': round(ticket_revenue, 2),
        'food_order_revenue': round(food_revenue, 2),
        'total_refunds': round(total_refunds, 2),
        'net_revenue': round(net_revenue, 2),
        'complaints_total': complaints_total,
        'complaints_open': complaints_open,
        'complaints_resolved': complaints_resolved,
        'complaint_resolution_rate': round((complaints_resolved / complaints_total * 100), 1) if complaints_total > 0 else 100.0
    }


def get_top_performing_trains(limit: int = 5) -> list:
    """Retrieve trains generating highest booking revenue and passenger volume."""
    sql = """
    SELECT
        t.train_number,
        t.train_name,
        t.train_type,
        COUNT(b.id) as bookings_count,
        COALESCE(SUM(b.total_fare), 0.0) as total_revenue
    FROM trains t
    LEFT JOIN bookings b ON t.id = b.train_id AND b.booking_status = 'CONFIRMED'
    GROUP BY t.id
    ORDER BY total_revenue DESC, bookings_count DESC
    LIMIT ?
    """
    return fetch_all(sql, (limit,))


def get_popular_routes(limit: int = 5) -> list:
    """Retrieve most frequent travel origin-destination pairs."""
    sql = """
    SELECT
        b.source_code,
        s1.city as source_city,
        b.dest_code,
        s2.city as dest_city,
        COUNT(b.id) as journey_count,
        SUM(b.total_fare) as route_revenue
    FROM bookings b
    JOIN stations s1 ON b.source_code = s1.station_code
    JOIN stations s2 ON b.dest_code = s2.station_code
    WHERE b.booking_status = 'CONFIRMED'
    GROUP BY b.source_code, b.dest_code
    ORDER BY journey_count DESC
    LIMIT ?
    """
    return fetch_all(sql, (limit,))


def get_staff_department_breakdown() -> list:
    """Retrieve staff headcount and payroll aggregate by department."""
    sql = """
    SELECT
        department,
        COUNT(id) as staff_count,
        SUM(salary) as monthly_payroll
    FROM employees
    WHERE status = 'ACTIVE'
    GROUP BY department
    ORDER BY staff_count DESC
    """
    return fetch_all(sql)
