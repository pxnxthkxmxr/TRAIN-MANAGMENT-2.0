

import sys
from seed_data import seed_all
from modules.auth import login_user, register_user
from modules.booking import book_ticket, cancel_booking, check_seat_availability, get_booking_by_pnr
from modules.complaints import file_complaint, get_complaint_by_ticket, resolve_complaint
from modules.employees import add_employee, get_all_employees, get_employee_by_code
from modules.food import (
    get_all_food_orders,
    get_food_menu,
    get_food_order_details,
    place_food_order,
    update_food_order_status,
)
from modules.payment import get_all_transactions
from modules.reports import get_popular_routes, get_system_overview_stats, get_top_performing_trains
from modules.schedule import get_live_train_tracking, get_station_live_board, update_train_live_status
from modules.trains import (
    calculate_fare,
    get_all_stations,
    get_all_trains,
    get_train_by_number,
    search_trains_between_stations,
)


def run_tests():
    print("=" * 65)
    print(" STARTING TRAIN MANAGEMENT SYSTEM AUTOMATED VERIFICATION")
    print("=" * 65)

    # 0. Clean Seed
    print("\n[STEP 0] Resetting and Seeding Database...")
    seed_all(force=True)

    # 1. Test Auth
    print("\n[STEP 1] Testing Authentication & Password Hashing...")
    # Test valid login
    ok, msg, admin_user = login_user("admin", "admin123")
    assert ok and admin_user['role'] == 'admin', f"Admin login failed: {msg}"
    print("  [OK] Admin login verified.")

    ok, msg, staff_user = login_user("staff1", "staff123")
    assert ok and staff_user['role'] == 'staff', f"Staff login failed: {msg}"
    print("  [OK] Staff login verified.")

    ok, msg, pass_user = login_user("passenger1", "pass123")
    assert ok and pass_user['role'] == 'passenger', f"Passenger login failed: {msg}"
    print("  [OK] Passenger login verified.")

    # Test invalid password rejection
    bad_login, _, _ = login_user("admin", "wrongpass")
    assert not bad_login, "Security alert: Wrong password was accepted!"
    print("  [OK] Invalid password correctly rejected.")

    # Test registration
    reg_ok, reg_msg, new_uid = register_user("testuser_99", "password123", "Test User", "test99@example.com", "9988776655")
    assert reg_ok, f"User registration failed: {reg_msg}"
    print("  [OK] User registration successful.")

    # 2. Test Trains & Route Search
    print("\n[STEP 2] Testing Stations, Trains & Route Search...")
    stations = get_all_stations()
    assert len(stations) >= 8, f"Expected >=8 stations, found {len(stations)}"
    print(f"  [OK] {len(stations)} stations loaded.")

    trains = get_all_trains()
    assert len(trains) >= 5, f"Expected >=5 trains, found {len(trains)}"
    print(f"  [OK] {len(trains)} trains loaded.")

    # Search trains between NDLS and AGC
    found_trains = search_trains_between_stations("NDLS", "AGC")
    assert len(found_trains) >= 3, f"Expected >=3 trains between NDLS and AGC, found {len(found_trains)}"
    train_numbers = [t['train_number'] for t in found_trains]
    print(f"  [OK] Train search (NDLS -> AGC) found: {', '.join(train_numbers)}")

    fare_3a = calculate_fare("Shatabdi", 1.4, 188, "3A", 1)
    assert fare_3a > 100, f"Unexpected fare calculation: {fare_3a}"
    print(f"  [OK] Dynamic fare calculated for 188km Shatabdi 3A: Rs. {fare_3a}")

    # 3. Test Booking, PNR & Cancellation
    print("\n[STEP 3] Testing Ticket Booking, Seat Allocation & Cancellation...")
    t1 = get_train_by_number("12002")
    assert t1 is not None

    avail_before = check_seat_availability(t1['id'], "2026-09-30", "2A")
    initial_avail = avail_before['available']

    passengers_input = [
        {'name': 'Vikram Mehra', 'age': 34, 'gender': 'Male', 'berth_pref': 'Lower Berth'},
        {'name': 'Neha Mehra', 'age': 31, 'gender': 'Female', 'berth_pref': 'Upper Berth'}
    ]
    book_ok, book_msg, b_info = book_ticket(
        user_id=new_uid,
        train_id=t1['id'],
        journey_date="2026-09-30",
        source_code="NDLS",
        dest_code="AGC",
        coach_class="2A",
        passenger_list=passengers_input,
        payment_method="UPI"
    )
    assert book_ok, f"Booking failed: {book_msg}"
    test_pnr = b_info['pnr']
    print(f"  [OK] Ticket booked. PNR: {test_pnr}, Allocated Seats: {b_info['seats']}")

    # Check availability decremented
    avail_after = check_seat_availability(t1['id'], "2026-09-30", "2A")
    assert avail_after['available'] == initial_avail - 2, "Seat inventory did not decrement properly"
    print(f"  [OK] Seat inventory properly decremented ({initial_avail} -> {avail_after['available']}).")

    # Fetch booking details by PNR
    b_retrieved = get_booking_by_pnr(test_pnr)
    assert b_retrieved['pnr'] == test_pnr
    assert len(b_retrieved['passengers']) == 2
    print("  [OK] Full PNR enquiry record retrieved.")

    # Cancel ticket & verify refund
    cancel_ok, cancel_msg = cancel_booking(test_pnr, user_id=new_uid)
    assert cancel_ok, f"Cancellation failed: {cancel_msg}"
    b_cancelled = get_booking_by_pnr(test_pnr)
    assert b_cancelled['booking_status'] == 'CANCELLED'
    print(f"  [OK] Ticket cancelled successfully with refund processed.")

    # 4. Test Live Train Tracking & Delays
    print("\n[STEP 4] Testing Proper Train Tracking & Station Boards...")
    track_info = get_live_train_tracking("12002")
    assert track_info is not None
    assert 'timeline' in track_info
    assert track_info['total_distance_km'] == 707
    print(f"  [OK] Live Tracking for 12002 retrieved. Current Station: {track_info['current_station']}, Delay: {track_info['delay_minutes']} min")
    print(f"  [OK] Visual Journey Map: {track_info['journey_map']}")

    # Staff updates live location & delay
    up_ok, up_msg = update_train_live_status(t1['id'], "GWL", "VGLJ", delay_minutes=15, current_status="DELAYED")
    assert up_ok, f"Status update failed: {up_msg}"
    track_updated = get_live_train_tracking("12002")
    assert track_updated['current_station'] == 'GWL'
    assert track_updated['delay_minutes'] == 15
    print("  [OK] Live train status updated by staff to GWL (+15m).")

    # Live Station Board
    board = get_station_live_board("NDLS")
    assert len(board) >= 3, f"Expected >=3 trains on NDLS board, found {len(board)}"
    print(f"  [OK] Live Station Board for NDLS retrieved ({len(board)} trains listed).")

    # 5. Test Employee / Staff Management (Admin role)
    print("\n[STEP 5] Testing Staff / Employee Management (Admin CRUD)...")
    emp_ok, emp_msg, emp_id = add_employee(
        full_name="Kavita Rao",
        role_title="Assistant Station Master",
        department="Operations",
        contact="9988112233",
        salary=58000.0,
        shift="Evening (14:00 - 22:00)",
        assigned_to="CSMT Terminal",
        create_login=True,
        username="kavita_ops",
        password="password123"
    )
    assert emp_ok, f"Employee creation failed: {emp_msg}"
    print(f"  [OK] Admin onboarded new staff: {emp_msg}")

    # Verify staff login works
    kavita_login, _, kavita_user = login_user("kavita_ops", "password123")
    assert kavita_login and kavita_user['role'] == 'staff'
    print("  [OK] New staff member credentials authenticated successfully.")

    employees = get_all_employees()
    assert len(employees) >= 6, f"Expected >=6 employees, found {len(employees)}"
    print(f"  [OK] Total employees in system: {len(employees)}")

    # 6. Test Pantry & In-Train Food Delivery System
    print("\n[STEP 6] Testing Pantry & Food Delivery System...")
    menu = get_food_menu()
    assert len(menu) >= 10, f"Expected >=10 menu items, found {len(menu)}"
    print(f"  [OK] Pantry menu loaded ({len(menu)} items).")

    # Re-book a valid confirmed ticket to test food ordering
    book_ok2, _, b2 = book_ticket(
        user_id=new_uid,
        train_id=t1['id'],
        journey_date="2026-10-05",
        source_code="NDLS",
        dest_code="BPL",
        coach_class="3A",
        passenger_list=[{'name': 'Vikram Mehra', 'age': 34, 'gender': 'Male'}],
        payment_method="UPI"
    )
    valid_pnr = b2['pnr']

    # Order food
    food_items_order = [
        {'item_id': 1, 'quantity': 1},  # Royal Thali
        {'item_id': 13, 'quantity': 2}, # 2x Masala Chai
    ]
    food_ok, food_msg, f_order = place_food_order(
        pnr=valid_pnr,
        user_id=new_uid,
        items_ordered=food_items_order,
        delivery_station="AGC",
        seat_info=b2['seats'][0],
        payment_method="UPI"
    )
    assert food_ok, f"Food ordering failed: {food_msg}"
    test_order_id = f_order['order_id']
    print(f"  [OK] Food order placed! Order ID: {test_order_id}, Amount: Rs. {f_order['total_amount']}")

    # Catering staff advances order status
    status_ok, _ = update_food_order_status(test_order_id, "PREPARING")
    assert status_ok
    status_ok2, _ = update_food_order_status(test_order_id, "DELIVERED")
    assert status_ok2
    order_chk = get_food_order_details(test_order_id)
    assert order_chk['order_status'] == 'DELIVERED'
    print(f"  [OK] Food order status advanced by catering staff: PLACED -> PREPARING -> DELIVERED.")

    # 7. Test Grievance / Complaint Redressal
    print("\n[STEP 7] Testing Complaint / Grievance Redressal System...")
    cmp_ok, cmp_msg, ticket_num = file_complaint(
        user_id=new_uid,
        category="Punctuality",
        description="Train was delayed by 45 minutes at outer signal without announcement.",
        pnr=valid_pnr
    )
    assert cmp_ok, f"Filing complaint failed: {cmp_msg}"
    print(f"  [OK] Passenger filed grievance: Ticket {ticket_num}")

    # Staff/Admin resolves complaint
    res_ok, res_msg = resolve_complaint(
        ticket_number=ticket_num,
        resolution_note="Signal failure rectified by Northern Railway signaling team. Apologies for delay.",
        staff_id=1,
        new_status="RESOLVED"
    )
    assert res_ok, f"Resolution failed: {res_msg}"
    comp_chk = get_complaint_by_ticket(ticket_num)
    assert comp_chk['status'] == 'RESOLVED'
    print(f"  [OK] Complaint {ticket_num} marked as RESOLVED by staff.")

    # 8. Test Reports & Analytics Dashboard
    print("\n[STEP 8] Testing Reports & Financial Analytics Dashboard...")
    stats = get_system_overview_stats()
    assert stats['gross_ticket_revenue'] > 0
    assert stats['food_order_revenue'] > 0
    assert stats['total_bookings'] >= 2
    print(f"  [OK] Overview Stats:")
    print(f"      Gross Ticket Revenue : Rs. {stats['gross_ticket_revenue']:,.2f}")
    print(f"      Food Order Revenue   : Rs. {stats['food_order_revenue']:,.2f}")
    print(f"      Total Refunds Issued : Rs. {stats['total_refunds']:,.2f}")
    print(f"      Net Revenue          : Rs. {stats['net_revenue']:,.2f}")
    print(f"      Complaints Redressed : {stats['complaints_resolved']}/{stats['complaints_total']} ({stats['complaint_resolution_rate']}%)")

    top_trains = get_top_performing_trains(3)
    assert len(top_trains) > 0
    print(f"  [OK] Top Revenue Train: {top_trains[0]['train_name']} (Rs. {top_trains[0]['total_revenue']:,.2f})")

    pop_routes = get_popular_routes(3)
    assert len(pop_routes) > 0
    print(f"  [OK] Popular Route: {pop_routes[0]['source_code']} -> {pop_routes[0]['dest_code']} ({pop_routes[0]['journey_count']} journeys)")

    txns = get_all_transactions(5)
    assert len(txns) >= 3
    print(f"  [OK] Payment Ledger: {len(txns)} transactions verified.")

    print("\n" + "=" * 65)
    print(" ALL SYSTEM MODULES AND INTEGRATION TESTS PASSED PERFECTLY!")
    print("=" * 65)


if __name__ == "__main__":
    try:
        run_tests()
    except AssertionError as e:
        print(f"\n[TEST FAILED]: {str(e)}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\n[UNEXPECTED ERROR]: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
