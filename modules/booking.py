"""
modules/booking.py - Ticket Reservation, PNR Generation, Seat Assignment & Cancellation
"""

import random
from database import execute_query, fetch_all, fetch_one
from modules.payment import process_payment, process_refund
from modules.trains import calculate_fare, get_train_by_id

# Standard coach capacity per class
CLASS_CAPACITY = {
    '1A': 24,
    '2A': 48,
    '3A': 64,
    'CC': 72,
    'SL': 72,
}

COACH_PREFIX = {
    '1A': 'H1',
    '2A': 'A1',
    '3A': 'B1',
    'CC': 'C1',
    'SL': 'S1',
}

BERTH_TYPES = ['Lower Berth', 'Middle Berth', 'Upper Berth', 'Side Lower', 'Side Upper', 'Window Seat']


def generate_pnr() -> str:
    """Generate a unique 10-digit Indian Railways-style PNR number."""
    while True:
        pnr = str(random.randint(2000000000, 9999999999))
        existing = fetch_one("SELECT id FROM bookings WHERE pnr = ?", (pnr,))
        if not existing:
            return pnr


def check_seat_availability(train_id: int, journey_date: str, coach_class: str) -> dict:
    """
    Check total capacity, booked seats, and remaining seats for a train on a date.
    """
    capacity = CLASS_CAPACITY.get(coach_class, 60)

    # Count confirmed passenger seats on this train, date, and class
    sql = """
    SELECT COUNT(p.id) as booked_count
    FROM passengers p
    JOIN bookings b ON p.booking_id = b.id
    WHERE b.train_id = ?
      AND b.journey_date = ?
      AND b.coach_class = ?
      AND b.booking_status = 'CONFIRMED'
    """
    result = fetch_one(sql, (train_id, journey_date, coach_class))
    booked_count = result['booked_count'] if result else 0
    available = max(0, capacity - booked_count)

    return {
        'coach_class': coach_class,
        'capacity': capacity,
        'booked': booked_count,
        'available': available,
        'status': 'AVAILABLE' if available > 0 else 'REGRET / FULL'
    }


def allocate_seats(train_id: int, journey_date: str, coach_class: str, num_passengers: int) -> list:
    """
    Generate sequential seat numbers for passengers in the designated coach.
    Example: ['B1-14 (Lower Berth)', 'B1-15 (Middle Berth)']
    """
    prefix = COACH_PREFIX.get(coach_class, 'S1')

    # Get highest currently allocated seat index
    sql = """
    SELECT COUNT(p.id) as current_occupied
    FROM passengers p
    JOIN bookings b ON p.booking_id = b.id
    WHERE b.train_id = ? AND b.journey_date = ? AND b.coach_class = ? AND b.booking_status = 'CONFIRMED'
    """
    res = fetch_one(sql, (train_id, journey_date, coach_class))
    start_index = (res['current_occupied'] if res else 0) + 1

    allocated = []
    for i in range(num_passengers):
        seat_num = start_index + i
        berth = BERTH_TYPES[(seat_num - 1) % len(BERTH_TYPES)]
        allocated.append(f"{prefix}-{seat_num} ({berth})")
    return allocated


def book_ticket(user_id: int, train_id: int, journey_date: str,
                source_code: str, dest_code: str, coach_class: str,
                passenger_list: list, payment_method: str = 'UPI') -> tuple:
    """
    Reserve train tickets, allocate seats, charge fare, and generate PNR.
    Returns (success: bool, message: str, booking_data: dict or None).
    """
    if not passenger_list or len(passenger_list) == 0:
        return False, "At least one passenger must be provided.", None

    if len(passenger_list) > 6:
        return False, "Maximum 6 passengers allowed per booking.", None

    train = get_train_by_id(train_id)
    if not train:
        return False, "Selected train does not exist.", None

    if train['status'] != 'ACTIVE':
        return False, f"Train {train['train_number']} is currently suspended or cancelled.", None

    src = source_code.strip().upper()
    dest = dest_code.strip().upper()

    # Verify route stops and calculate distance
    stop_src = fetch_one(
        "SELECT distance_km, stop_sequence FROM routes WHERE train_id = ? AND station_code = ?",
        (train_id, src)
    )
    stop_dest = fetch_one(
        "SELECT distance_km, stop_sequence FROM routes WHERE train_id = ? AND station_code = ?",
        (train_id, dest)
    )

    if not stop_src or not stop_dest or stop_src['stop_sequence'] >= stop_dest['stop_sequence']:
        return False, f"Invalid route from {src} to {dest} on Train {train['train_number']}.", None

    distance_km = stop_dest['distance_km'] - stop_src['distance_km']

    # Check seat availability
    avail = check_seat_availability(train_id, journey_date, coach_class)
    if avail['available'] < len(passenger_list):
        return False, f"Only {avail['available']} seats available in {coach_class}. Requested {len(passenger_list)}.", None

    # Calculate total fare
    total_fare = calculate_fare(
        train_type=train['train_type'],
        base_fare_per_km=train['base_fare_per_km'],
        distance_km=distance_km,
        coach_class=coach_class,
        num_passengers=len(passenger_list)
    )

    # Process simulated payment
    pay_ok, pay_msg, txn_id = process_payment(
        user_id=user_id,
        amount=total_fare,
        payment_method=payment_method,
        payment_type='TICKET_BOOKING'
    )
    if not pay_ok:
        return False, f"Payment failed: {pay_msg}", None

    # Generate PNR and Seat Allocations
    pnr = generate_pnr()
    seat_allocations = allocate_seats(train_id, journey_date, coach_class, len(passenger_list))
    seat_summary_str = ", ".join([s.split(" ")[0] for s in seat_allocations])

    try:
        booking_id = execute_query(
            """
            INSERT INTO bookings (pnr, user_id, train_id, journey_date, source_code, dest_code,
                                  coach_class, seat_numbers, total_fare, booking_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'CONFIRMED')
            """,
            (pnr, user_id, train_id, journey_date, src, dest, coach_class, seat_summary_str, total_fare)
        )

        # Insert individual passengers
        for idx, p in enumerate(passenger_list):
            execute_query(
                """
                INSERT INTO passengers (booking_id, name, age, gender, berth_pref, seat_number)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    booking_id,
                    p.get('name', 'Passenger').strip(),
                    int(p.get('age', 25)),
                    p.get('gender', 'Male'),
                    p.get('berth_pref', 'No Preference'),
                    seat_allocations[idx]
                )
            )

        booking_data = {
            'booking_id': booking_id,
            'pnr': pnr,
            'train_number': train['train_number'],
            'train_name': train['train_name'],
            'from_station': src,
            'to_station': dest,
            'journey_date': journey_date,
            'coach_class': coach_class,
            'seats': seat_allocations,
            'total_fare': total_fare,
            'txn_id': txn_id,
            'passengers_count': len(passenger_list)
        }
        return True, f"Ticket booked successfully! PNR: {pnr}", booking_data

    except Exception as e:
        return False, f"Failed to record booking: {str(e)}", None


def get_booking_by_pnr(pnr: str) -> dict:
    """Retrieve full booking details including train, route, passengers, and payment info."""
    clean_pnr = pnr.strip()
    booking = fetch_one(
        """
        SELECT b.*, t.train_number, t.train_name, t.train_type,
               s1.station_name as source_name, s2.station_name as dest_name,
               u.full_name as booked_by, u.email as user_email, u.phone as user_phone
        FROM bookings b
        JOIN trains t ON b.train_id = t.id
        JOIN stations s1 ON b.source_code = s1.station_code
        JOIN stations s2 ON b.dest_code = s2.station_code
        JOIN users u ON b.user_id = u.id
        WHERE b.pnr = ?
        """,
        (clean_pnr,)
    )

    if not booking:
        return None

    # Fetch passengers
    passengers = fetch_all(
        "SELECT name, age, gender, berth_pref, seat_number FROM passengers WHERE booking_id = ?",
        (booking['id'],)
    )
    booking['passengers'] = passengers

    # Fetch associated food orders
    food_orders = fetch_all("SELECT * FROM food_orders WHERE pnr = ?", (clean_pnr,))
    booking['food_orders'] = food_orders

    return booking


def cancel_booking(pnr: str, user_id: int, is_admin: bool = False) -> tuple:
    """
    Cancel a confirmed ticket, calculate deduction fee, and issue refund.
    """
    booking = get_booking_by_pnr(pnr)
    if not booking:
        return False, f"No booking found for PNR '{pnr}'."

    if not is_admin and booking['user_id'] != user_id:
        return False, "Unauthorized. You can only cancel your own bookings."

    if booking['booking_status'] == 'CANCELLED':
        return False, f"Ticket with PNR {pnr} is already CANCELLED."

    # Calculation: 20% cancellation fee, 80% refund
    fare = booking['total_fare']
    cancellation_fee = round(fare * 0.20, 2)
    refund_amount = round(fare - cancellation_fee, 2)

    try:
        # Update booking status
        execute_query(
            "UPDATE bookings SET booking_status = 'CANCELLED' WHERE id = ?",
            (booking['id'],)
        )

        # Process refund
        ref_ok, ref_msg, ref_id = process_refund(
            user_id=booking['user_id'],
            original_booking_id=booking['id'],
            refund_amount=refund_amount
        )

        msg = (
            f"Ticket {pnr} cancelled successfully.\n"
            f"Fare Paid: Rs. {fare:.2f} | Cancellation Fee (20%): Rs. {cancellation_fee:.2f}\n"
            f"Refund Amount: Rs. {refund_amount:.2f} (Refund Ref: {ref_id})"
        )
        return True, msg
    except Exception as e:
        return False, f"Cancellation failed: {str(e)}"


def get_user_bookings(user_id: int) -> list:
    """Fetch all bookings made by a particular user."""
    return fetch_all(
        """
        SELECT b.*, t.train_number, t.train_name,
               s1.station_name as source_name, s2.station_name as dest_name
        FROM bookings b
        JOIN trains t ON b.train_id = t.id
        JOIN stations s1 ON b.source_code = s1.station_code
        JOIN stations s2 ON b.dest_code = s2.station_code
        WHERE b.user_id = ?
        ORDER BY b.created_at DESC
        """,
        (user_id,)
    )


def get_all_bookings(limit: int = 50) -> list:
    """Fetch recent system-wide bookings (Admin view)."""
    return fetch_all(
        """
        SELECT b.*, t.train_number, t.train_name, u.username, u.full_name as customer_name
        FROM bookings b
        JOIN trains t ON b.train_id = t.id
        JOIN users u ON b.user_id = u.id
        ORDER BY b.created_at DESC
        LIMIT ?
        """,
        (limit,)
    )
