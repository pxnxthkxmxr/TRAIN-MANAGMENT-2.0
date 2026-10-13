
import os
import sys
from datetime import datetime

from database import init_db
from modules.auth import change_password, login_user, register_user
from modules.booking import (
    CLASS_CAPACITY,
    book_ticket,
    cancel_booking,
    check_seat_availability,
    get_all_bookings,
    get_booking_by_pnr,
    get_user_bookings,
)
from modules.complaints import (
    CATEGORIES as COMP_CATEGORIES,
    file_complaint,
    get_all_complaints,
    get_complaint_by_ticket,
    get_user_complaints,
    resolve_complaint,
)
from modules.employees import (
    DEPARTMENTS,
    SHIFTS,
    add_employee,
    get_all_employees,
    get_employee_by_user_id,
    update_employee,
)
from modules.food import (
    CATEGORIES as FOOD_CATEGORIES,
    add_menu_item,
    get_all_food_orders,
    get_food_menu,
    get_food_order_details,
    get_food_orders_by_pnr,
    get_user_food_orders,
    place_food_order,
    toggle_menu_availability,
    update_food_order_status,
)
from modules.payment import get_all_transactions, get_user_transactions
from modules.reports import (
    get_popular_routes,
    get_staff_department_breakdown,
    get_system_overview_stats,
    get_top_performing_trains,
)
from modules.schedule import (
    get_live_train_tracking,
    get_station_live_board,
    update_train_live_status,
)
from modules.trains import (
    CLASS_NAMES,
    add_route_stop,
    add_station,
    add_train,
    calculate_fare,
    get_all_stations,
    get_all_trains,
    get_train_by_id,
    get_train_by_number,
    get_train_route,
    search_trains_between_stations,
)
from seed_data import seed_all

# Configure stdout encoding on Windows
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def clear_screen():
    
    os.system("cls" if os.name == "nt" else "clear")


def print_banner(title: str):
    
    width = 72
    print("\n" + "=" * width)
    print(f" {title.center(width - 2)} ")
    print("=" * width)


def prompt(label: str, default: str = None) -> str:
    """Prompt user for input with optional default value."""
    if default:
        val = input(f"{label} [{default}]: ").strip()
        return val if val else default
    return input(f"{label}: ").strip()


def pause():
    """Pause until user presses Enter."""
    input("\nPress Enter to continue...")


# =====================================================================
# PUBLIC / GUEST ACTIONS
# =====================================================================

def public_search_trains():
    print_banner("SEARCH TRAINS")
    src = prompt("Enter Source Station Code (e.g. NDLS)").upper()
    dest = prompt("Enter Destination Station Code (e.g. BPL, AGC, CSMT)").upper()

    results = search_trains_between_stations(src, dest)
    if not results:
        print(f"\nNo direct trains found running from {src} to {dest}.")
        pause()
        return

    print(f"\nFound {len(results)} train(s) running from {src} to {dest}:")
    print("-" * 75)
    print(f"{'Train No':<10} {'Train Name':<26} {'Departs':<10} {'Arrives':<10} {'Dist (km)':<10}")
    print("-" * 75)
    for t in results:
        print(f"{t['train_number']:<10} {t['train_name'][:25]:<26} {t['departure_time']:<10} {t['arrival_time']:<10} {t['journey_distance_km']:<10}")
    print("-" * 75)
    pause()


def public_view_route():
    print_banner("VIEW TRAIN ROUTE & TIMETABLE")
    num = prompt("Enter Train Number (e.g. 12002, 12952, 22436)")
    train = get_train_by_number(num)
    if not train:
        print("Train not found.")
        pause()
        return

    route = get_train_route(train['id'])
    print(f"\nTimetable for: {train['train_number']} - {train['train_name']} ({train['train_type']})")
    print("-" * 75)
    print(f"{'Seq':<5} {'Station':<8} {'Station Name':<28} {'Arr':<8} {'Dep':<8} {'Platform':<8} {'Dist':<6}")
    print("-" * 75)
    for r in route:
        print(f"{r['stop_sequence']:<5} {r['station_code']:<8} {r['station_name'][:26]:<28} {r['scheduled_arrival']:<8} {r['scheduled_departure']:<8} {r['platform_number']:<8} {r['distance_km']}km")
    print("-" * 75)
    pause()


def public_check_pnr():
    print_banner("PNR STATUS ENQUIRY")
    pnr = prompt("Enter 10-Digit PNR Number")
    booking = get_booking_by_pnr(pnr)
    if not booking:
        print(f"\nPNR '{pnr}' not found. Please verify the number.")
        pause()
        return

    print("\n" + "-" * 60)
    print(f" PNR NUMBER       : {booking['pnr']}")
    print(f" TRAIN            : {booking['train_number']} - {booking['train_name']} ({booking['train_type']})")
    print(f" ROUTE            : {booking['source_name']} ({booking['source_code']}) -> {booking['dest_name']} ({booking['dest_code']})")
    print(f" JOURNEY DATE     : {booking['journey_date']}")
    print(f" CLASS            : {CLASS_NAMES.get(booking['coach_class'], booking['coach_class'])}")
    print(f" STATUS           : {booking['booking_status']}")
    print(f" TOTAL FARE       : Rs. {booking['total_fare']:.2f}")
    print("-" * 60)
    print("PASSENGERS:")
    for idx, p in enumerate(booking['passengers'], 1):
        print(f"  {idx}. {p['name']} ({p['age']}y, {p['gender']}) | Seat: {p['seat_number']}")
    print("-" * 60)
    pause()


def public_live_tracking():
    print_banner("LIVE TRAIN TRACKING")
    num = prompt("Enter Train Number (e.g. 12002, 12952, 22436, 12628)")
    tracking = get_live_train_tracking(num)
    if not tracking:
        print(f"Train '{num}' not found.")
        pause()
        return

    t = tracking['train']
    print(f"\nTRAIN: {t['train_number']} - {t['train_name']}")
    print(f"CURRENT LOCATION : Station {tracking['current_station']}")
    print(f"NEXT STATION     : Station {tracking['next_station']}")
    print(f"LIVE DELAY       : {tracking['delay_minutes']} Minute(s)")
    print(f"STATUS           : {tracking['current_status']}")
    print(f"DISTANCE COVERED : {tracking['distance_covered_km']} km / {tracking['total_distance_km']} km ({tracking['progress_percentage']}%)")
    print(f"LAST UPDATED     : {tracking['last_updated']}")

    print("\nVISUAL JOURNEY PROGRESSION:")
    print("-" * 75)
    print(tracking['journey_map'])
    print("-" * 75)

    print("\nDETAILED STATION-BY-STATION TIMELINE:")
    print(f"{'State':<12} {'Station':<8} {'Station Name':<24} {'Sched Arr/Dep':<16} {'Estimated':<12} {'Plat':<5}")
    print("-" * 80)
    for stop in tracking['timeline']:
        sched = f"{stop['scheduled_arrival']}/{stop['scheduled_departure']}"
        est = f"{stop['estimated_arrival']}/{stop['estimated_departure']}"
        print(f"{stop['icon'] + ' ' + stop['state']:<12} {stop['station_code']:<8} {stop['station_name'][:22]:<24} {sched:<16} {est:<12} P#{stop['platform']}")
    print("-" * 80)
    pause()


def public_station_board():
    print_banner("LIVE STATION BOARD (ARRIVALS & DEPARTURES)")
    code = prompt("Enter Station Code (e.g. NDLS, AGC, BPL, CSMT)").upper()
    board = get_station_live_board(code)
    if not board:
        print(f"\nNo active trains scheduled at station {code}.")
        pause()
        return

    print(f"\nLive Departures & Arrivals at {code}:")
    print("-" * 80)
    print(f"{'Train':<8} {'Train Name':<24} {'Arr (Sch/Est)':<16} {'Dep (Sch/Est)':<16} {'Plat':<6} {'Delay':<8}")
    print("-" * 80)
    for item in board:
        arr_str = f"{item['scheduled_arrival']}/{item['expected_arrival']}"
        dep_str = f"{item['scheduled_departure']}/{item['expected_departure']}"
        delay_str = f"+{item['delay_minutes']}m" if item['delay_minutes'] > 0 else "On Time"
        print(f"{item['train_number']:<8} {item['train_name'][:22]:<24} {arr_str:<16} {dep_str:<16} P#{item['platform_number']:<4} {delay_str:<8}")
    print("-" * 80)
    pause()


def public_browse_food_menu():
    print_banner("IN-TRAIN PANTRY FOOD MENU")
    menu = get_food_menu()
    current_cat = None
    for item in menu:
        if item['category'] != current_cat:
            current_cat = item['category']
            print(f"\n--- {current_cat.upper()} ---")
        avail = "In Stock" if item['is_available'] else "Out of Stock"
        print(f"  [{item['id']:02d}] {item['item_name']:<35} : Rs. {item['price']:.2f} ({avail})")
    pause()


# =====================================================================
# PASSENGER PORTAL
# =====================================================================

def passenger_book_ticket(user: dict):
    print_banner("BOOK TRAIN TICKET")
    src = prompt("Source Station Code (e.g. NDLS)").upper()
    dest = prompt("Destination Station Code (e.g. AGC, BPL)").upper()

    trains = search_trains_between_stations(src, dest)
    if not trains:
        print(f"\nNo trains running between {src} and {dest}.")
        pause()
        return

    print(f"\nAvailable Trains between {src} and {dest}:")
    for idx, t in enumerate(trains, 1):
        print(f"  [{idx}] Train {t['train_number']} - {t['train_name']} ({t['train_type']}) | Dep: {t['departure_time']} -> Arr: {t['arrival_time']} | {t['journey_distance_km']} km")

    choice = prompt("\nSelect Train [1-{}]".format(len(trains)))
    if not choice.isdigit() or int(choice) < 1 or int(choice) > len(trains):
        print("Invalid selection.")
        pause()
        return

    selected_train = trains[int(choice) - 1]
    train_id = selected_train['train_id']

    date_str = prompt("Enter Journey Date (YYYY-MM-DD)", default=datetime.now().strftime("%Y-%m-%d"))

    print("\nSelect Travel Class:")
    classes = list(CLASS_NAMES.keys())
    for idx, c in enumerate(classes, 1):
        avail = check_seat_availability(train_id, date_str, c)
        fare_sample = calculate_fare(selected_train['train_type'], selected_train['base_fare_per_km'], selected_train['journey_distance_km'], c, 1)
        print(f"  [{idx}] {CLASS_NAMES[c]:<25} | Seats Avail: {avail['available']:<3} | Fare/person: Rs. {fare_sample:.2f}")

    c_choice = prompt("Choose Class [1-{}]".format(len(classes)))
    if not c_choice.isdigit() or int(c_choice) < 1 or int(c_choice) > len(classes):
        print("Invalid class selection.")
        pause()
        return

    chosen_class = classes[int(c_choice) - 1]

    # Passenger Details
    num_p_str = prompt("Enter Number of Passengers (1-6)", default="1")
    num_p = int(num_p_str) if num_p_str.isdigit() and 1 <= int(num_p_str) <= 6 else 1

    passengers_list = []
    print("\nEnter Passenger Details:")
    for i in range(1, num_p + 1):
        print(f"\nPassenger #{i}:")
        name = prompt("  Full Name")
        age = prompt("  Age", default="30")
        gender = prompt("  Gender (Male/Female/Other)", default="Male")
        berth = prompt("  Berth Preference (Lower Berth/Middle Berth/Upper Berth/Window Seat/No Preference)", default="No Preference")
        passengers_list.append({
            'name': name if name else f"Passenger {i}",
            'age': int(age) if age.isdigit() else 30,
            'gender': gender,
            'berth_pref': berth
        })

    # Payment method
    print("\nSelect Payment Gateway Method:")
    print("  [1] UPI (Google Pay, PhonePe, Paytm)")
    print("  [2] Credit / Debit Card")
    print("  [3] Net Banking")
    print("  [4] IRCTC Railway Wallet")
    p_opt = prompt("Choose Payment Method [1-4]", default="1")
    method_map = {'1': 'UPI', '2': 'CARD', '3': 'NETBANKING', '4': 'WALLET'}
    pay_method = method_map.get(p_opt, 'UPI')

    print("\nProcessing Reservation & Secure Payment...")
    ok, msg, b_data = book_ticket(
        user_id=user['id'],
        train_id=train_id,
        journey_date=date_str,
        source_code=src,
        dest_code=dest,
        coach_class=chosen_class,
        passenger_list=passengers_list,
        payment_method=pay_method
    )

    if not ok:
        print(f"\n[BOOKING FAILED]: {msg}")
    else:
        print("\n" + "=" * 65)
        print(" TICKET BOOKING CONFIRMED!")
        print("=" * 65)
        print(f" PNR NUMBER        : {b_data['pnr']}")
        print(f" TRAIN             : {b_data['train_number']} - {b_data['train_name']}")
        print(f" JOURNEY           : {src} -> {dest} on {date_str}")
        print(f" CLASS             : {CLASS_NAMES.get(chosen_class, chosen_class)}")
        print(f" ALLOCATED SEATS   : {', '.join(b_data['seats'])}")
        print(f" TOTAL FARE PAID   : Rs. {b_data['total_fare']:.2f} via {pay_method}")
        print(f" TRANSACTION ID    : {b_data['txn_id']}")
        print("=" * 65)

    pause()


def passenger_my_bookings(user: dict):
    print_banner("MY BOOKING HISTORY")
    bookings = get_user_bookings(user['id'])
    if not bookings:
        print("You have no past or active bookings.")
        pause()
        return

    print(f"{'PNR':<12} {'Train':<24} {'Route':<14} {'Date':<12} {'Fare':<10} {'Status':<10}")
    print("-" * 80)
    for b in bookings:
        route_str = f"{b['source_code']} -> {b['dest_code']}"
        print(f"{b['pnr']:<12} {b['train_number'] + ' ' + b['train_name'][:14]:<24} {route_str:<14} {b['journey_date']:<12} Rs.{b['total_fare']:<7.2f} {b['booking_status']:<10}")
    print("-" * 80)

    pnr_inspect = prompt("\nEnter PNR to view full details (or press Enter to return)")
    if pnr_inspect:
        b_det = get_booking_by_pnr(pnr_inspect)
        if b_det and b_det['user_id'] == user['id']:
            print("\n" + "-" * 60)
            print(f"PNR: {b_det['pnr']} | Status: {b_det['booking_status']}")
            print(f"Train: {b_det['train_number']} - {b_det['train_name']}")
            print(f"Route: {b_det['source_name']} -> {b_det['dest_name']}")
            print(f"Date: {b_det['journey_date']} | Class: {b_det['coach_class']}")
            print("Passengers:")
            for p in b_det['passengers']:
                print(f"  - {p['name']} ({p['age']}y, {p['gender']}) | Assigned Seat: {p['seat_number']}")
            print("-" * 60)
        else:
            print("Booking not found or not owned by you.")
    pause()


def passenger_cancel_ticket(user: dict):
    print_banner("CANCEL TICKET & CLAIM REFUND")
    pnr = prompt("Enter 10-Digit PNR to cancel")
    confirm = prompt(f"Are you sure you want to cancel ticket with PNR {pnr}? (y/n)", default="n").lower()
    if confirm != 'y':
        print("Cancellation aborted.")
        pause()
        return

    ok, msg = cancel_booking(pnr, user_id=user['id'])
    print(f"\n{msg}")
    pause()


def passenger_order_food(user: dict):
    print_banner("ORDER FOOD TO SEAT")
    pnr = prompt("Enter Confirmed Booking PNR")
    booking = get_booking_by_pnr(pnr)
    if not booking:
        print("Booking not found.")
        pause()
        return

    if booking['booking_status'] != 'CONFIRMED':
        print(f"Cannot order food for a {booking['booking_status']} booking.")
        pause()
        return

    print(f"\nBooking verified: Train {booking['train_number']} ({booking['source_code']} -> {booking['dest_code']})")
    print(f"Booked Seats: {booking['seat_numbers']}")

    delivery_stn = prompt("Delivery Station Code (e.g. AGC, GWL, BPL)", default=booking['dest_code']).upper()
    seat_info = prompt("Coach and Seat Number", default=booking['seat_numbers'].split(',')[0].strip())

    # Display Menu
    menu = get_food_menu(only_available=True)
    print("\nAvailable Pantry Menu Items:")
    for item in menu:
        print(f"  [{item['id']:02d}] {item['item_name']:<35} : Rs. {item['price']:.2f} [{item['category']}]")

    orders = []
    print("\nEnter items to order (enter item ID and quantity. Enter 0 to finish):")
    while True:
        i_id_str = prompt("Item ID (0 to checkout)")
        if not i_id_str.isdigit() or int(i_id_str) == 0:
            break
        i_qty_str = prompt("Quantity", default="1")
        qty = int(i_qty_str) if i_qty_str.isdigit() and int(i_qty_str) > 0 else 1
        orders.append({'item_id': int(i_id_str), 'quantity': qty})

    if not orders:
        print("No items ordered.")
        pause()
        return

    # Payment method
    pay_method = prompt("Payment Method (UPI/CARD/WALLET)", default="UPI").upper()

    ok, msg, o_data = place_food_order(
        pnr=pnr,
        user_id=user['id'],
        items_ordered=orders,
        delivery_station=delivery_stn,
        seat_info=seat_info,
        payment_method=pay_method
    )

    if not ok:
        print(f"\n[ORDER FAILED]: {msg}")
    else:
        print("\n" + "=" * 60)
        print(" FOOD ORDER CONFIRMED & SENT TO PANTRY!")
        print("=" * 60)
        print(f" Order ID        : {o_data['order_id']}")
        print(f" Delivery Station: {o_data['delivery_station']}")
        print(f" Seat            : {o_data['seat_info']}")
        print(f" Total Bill      : Rs. {o_data['total_amount']:.2f}")
        print(" Items:")
        for it in o_data['items']:
            print(f"   - {it['item_name']} x{it['quantity']} (Rs. {it['line_total']:.2f})")
        print("=" * 60)

    pause()


def passenger_my_food_orders(user: dict):
    print_banner("MY IN-TRAIN FOOD ORDERS")
    orders = get_user_food_orders(user['id'])
    if not orders:
        print("No food orders found.")
        pause()
        return

    for o in orders:
        print("-" * 65)
        print(f"Order ID: {o['order_id']} | PNR: {o['pnr']} | Status: {o['order_status']}")
        print(f"Delivery: Station {o['delivery_station']} | Seat: {o['seat_info']} | Total: Rs. {o['total_amount']:.2f}")
        print("Dishes:")
        for it in o['items']:
            print(f"  * {it['item_name']} x{it['quantity']} (Rs. {it['unit_price']:.2f} each)")
    print("-" * 65)
    pause()


def passenger_file_complaint(user: dict):
    print_banner("FILE GRIEVANCE / COMPLAINT")
    print("Categories:")
    for idx, c in enumerate(COMP_CATEGORIES, 1):
        print(f"  [{idx}] {c}")

    cat_idx = prompt("Select Category [1-{}]".format(len(COMP_CATEGORIES)))
    cat = COMP_CATEGORIES[int(cat_idx) - 1] if cat_idx.isdigit() and 1 <= int(cat_idx) <= len(COMP_CATEGORIES) else "Other"

    pnr = prompt("PNR Number (Optional, press Enter to skip)")
    desc = prompt("Detailed description of the issue")

    ok, msg, ticket = file_complaint(user['id'], cat, desc, pnr if pnr else None)
    print(f"\n{msg}")
    pause()


def passenger_my_complaints(user: dict):
    print_banner("MY GRIEVANCES & RESOLUTION STATUS")
    complaints = get_user_complaints(user['id'])
    if not complaints:
        print("You have not lodged any complaints.")
        pause()
        return

    for c in complaints:
        print("-" * 65)
        print(f"Ticket: {c['ticket_number']} | Category: {c['category']} | Status: {c['status']}")
        print(f"Filed At: {c['created_at']} | PNR: {c['pnr'] if c['pnr'] else 'N/A'}")
        print(f"Issue   : {c['description']}")
        if c['resolution_note']:
            print(f"Resolution Response: {c['resolution_note']}")
            print(f"Resolved At        : {c['resolved_at']}")
    print("-" * 65)
    pause()


def passenger_profile(user: dict):
    print_banner("MY PROFILE & ACCOUNT SETTINGS")
    print(f" Full Name   : {user['full_name']}")
    print(f" Username    : {user['username']}")
    print(f" Email       : {user['email']}")
    print(f" Phone       : {user['phone']}")
    print(f" Role        : {user['role'].upper()}")
    print(f" Member Since: {user['created_at']}")

    print("\nOptions:")
    print("  [1] Change Password")
    print("  [2] View Transaction History")
    print("  [3] Return to Dashboard")

    opt = prompt("Select Option", default="3")
    if opt == '1':
        old_pw = prompt("Enter Current Password")
        new_pw = prompt("Enter New Password (min 6 chars)")
        ok, msg = change_password(user['id'], old_pw, new_pw)
        print(f"\n{msg}")
        pause()
    elif opt == '2':
        txns = get_user_transactions(user['id'])
        print("\nPayment History:")
        for t in txns:
            print(f"  {t['timestamp']} | {t['transaction_id']} | Rs. {t['amount']:.2f} | {t['payment_type']} | {t['payment_method']} | {t['status']}")
        pause()


# =====================================================================
# STAFF PORTAL
# =====================================================================

def staff_update_tracking():
    print_banner("STAFF DESK: UPDATE TRAIN LIVE LOCATION & DELAYS")
    num = prompt("Enter Train Number to Update (e.g. 12002)")
    train = get_train_by_number(num)
    if not train:
        print("Train not found.")
        pause()
        return

    route = get_train_route(train['id'])
    print(f"\nRoute Stations for Train {train['train_number']}:")
    valid_codes = []
    for r in route:
        valid_codes.append(r['station_code'])
        print(f"  Stop #{r['stop_sequence']}: {r['station_code']} ({r['station_name']})")

    curr = prompt("Enter Current Station Code").upper()
    if curr not in valid_codes:
        print(f"Station '{curr}' is not along this train's route.")
        pause()
        return

    delay = prompt("Enter Delay in Minutes (0 for On Time)", default="0")
    status = prompt("Train Status (ON_TIME/DELAYED/ARRIVED/DEPARTED)", default="ON_TIME").upper()

    ok, msg = update_train_live_status(train['id'], curr, delay_minutes=int(delay) if delay.isdigit() else 0, current_status=status)
    print(f"\n{msg}")
    pause()


def staff_pantry_orders():
    print_banner("PANTRY DISPATCH: IN-TRAIN FOOD ORDERS")
    orders = get_all_food_orders()
    if not orders:
        print("No food orders in queue.")
        pause()
        return

    print(f"{'Order ID':<12} {'PNR':<12} {'Delivery Stn':<14} {'Seat':<12} {'Total':<10} {'Status':<16}")
    print("-" * 80)
    for o in orders:
        print(f"{o['order_id']:<12} {o['pnr']:<12} {o['delivery_station']:<14} {o['seat_info']:<12} Rs.{o['total_amount']:<7.2f} {o['order_status']:<16}")
    print("-" * 80)

    oid = prompt("\nEnter Order ID to update status (or press Enter to return)")
    if oid:
        print("\nStatuses: [1] PREPARING  [2] OUT_FOR_DELIVERY  [3] DELIVERED  [4] CANCELLED")
        st_opt = prompt("Choose Status [1-4]")
        st_map = {'1': 'PREPARING', '2': 'OUT_FOR_DELIVERY', '3': 'DELIVERED', '4': 'CANCELLED'}
        if st_opt in st_map:
            ok, msg = update_food_order_status(oid, st_map[st_opt])
            print(f"\n{msg}")
        else:
            print("Invalid status option.")
    pause()


def staff_complaints_desk(user: dict):
    print_banner("GRIEVANCE REDRESSAL DESK")
    complaints = get_all_complaints()
    if not complaints:
        print("No grievances reported.")
        pause()
        return

    print(f"{'Ticket No':<16} {'Category':<16} {'Passenger':<18} {'Status':<14}")
    print("-" * 65)
    for c in complaints:
        print(f"{c['ticket_number']:<16} {c['category']:<16} {c['passenger_name'][:16]:<18} {c['status']:<14}")
    print("-" * 65)

    ticket = prompt("\nEnter Ticket Number to inspect & resolve (or press Enter to return)")
    if ticket:
        comp = get_complaint_by_ticket(ticket)
        if comp:
            print("\n" + "-" * 60)
            print(f"Ticket: {comp['ticket_number']} | Passenger: {comp['passenger_name']} ({comp['passenger_phone']})")
            print(f"Category: {comp['category']} | Status: {comp['status']}")
            print(f"Description: {comp['description']}")
            print("-" * 60)

            note = prompt("Enter Investigation & Resolution Note")
            new_st = prompt("Set Status (IN_PROGRESS/RESOLVED/CLOSED)", default="RESOLVED").upper()
            ok, msg = resolve_complaint(ticket, note, staff_id=None, new_status=new_st)
            print(f"\n{msg}")
        else:
            print("Ticket not found.")
    pause()


def staff_view_profile(user: dict):
    print_banner("STAFF PROFILE & ASSIGNED DUTIES")
    emp = get_employee_by_user_id(user['id'])
    if not emp:
        print("No linked employee record found for this user.")
        pause()
        return

    print(f" Employee Code    : {emp['employee_code']}")
    print(f" Full Name        : {emp['full_name']}")
    print(f" Designation      : {emp['role_title']}")
    print(f" Department       : {emp['department']}")
    print(f" Assigned Station : {emp['assigned_to']}")
    print(f" Shift Schedule   : {emp['shift']}")
    print(f" Contact          : {emp['contact']}")
    print(f" Employment Status: {emp['status']}")
    pause()


# =====================================================================
# ADMIN CONTROL CENTER
# =====================================================================

def admin_system_analytics():
    print_banner("EXECUTIVE ANALYTICS & REVENUE DASHBOARD")
    stats = get_system_overview_stats()

    print("\n--- REVENUE & FINANCIAL PERFORMANCE ---")
    print(f"  Gross Ticket Sales Revenue : Rs. {stats['gross_ticket_revenue']:,.2f}")
    print(f"  Food & Pantry Revenue      : Rs. {stats['food_order_revenue']:,.2f}")
    print(f"  Refunds Issued on Cancels  : Rs. {stats['total_refunds']:,.2f}")
    print(f"  NET OPERATING REVENUE      : Rs. {stats['net_revenue']:,.2f}")

    print("\n--- OPERATIONAL CAPACITY & VOLUME ---")
    print(f"  Active Trains Running      : {stats['active_trains']}")
    print(f"  Total Stations Managed     : {stats['stations']}")
    print(f"  Total Confirmed Bookings   : {stats['confirmed_bookings']}")
    print(f"  Total Passengers Served    : {stats['passengers_travelled']}")
    print(f"  Cancelled Bookings         : {stats['cancelled_bookings']}")
    print(f"  Active Workforce / Staff   : {stats['active_staff']}")

    print("\n--- CUSTOMER SATISFACTION & GRIEVANCES ---")
    print(f"  Total Grievances Logged    : {stats['complaints_total']}")
    print(f"  Open Grievances Pending    : {stats['complaints_open']}")
    print(f"  Grievance Resolution Rate  : {stats['complaint_resolution_rate']}%")

    print("\n--- TOP REVENUE GENERATING TRAINS ---")
    top_trains = get_top_performing_trains(5)
    for idx, t in enumerate(top_trains, 1):
        print(f"  {idx}. {t['train_name']} ({t['train_number']}) | Bookings: {t['bookings_count']} | Revenue: Rs. {t['total_revenue']:,.2f}")

    print("\n--- MOST POPULAR PASSENGER ROUTES ---")
    pop_routes = get_popular_routes(5)
    for idx, r in enumerate(pop_routes, 1):
        print(f"  {idx}. {r['source_code']} ({r['source_city']}) -> {r['dest_code']} ({r['dest_city']}) | Trips: {r['journey_count']} | Revenue: Rs. {r['route_revenue']:,.2f}")

    print("\n--- STAFF DISTRIBUTION BY DEPARTMENT ---")
    depts = get_staff_department_breakdown()
    for d in depts:
        print(f"  * {d['department']:<16} : {d['staff_count']} Staff | Monthly Payroll: Rs. {d['monthly_payroll']:,.2f}")

    pause()


def admin_manage_staff():
    while True:
        print_banner("STAFF & EMPLOYEE MANAGEMENT (ADMIN)")
        print("  [1] Onboard New Staff Member (with Login Credentials)")
        print("  [2] View All Employees")
        print("  [3] Filter Employees by Department")
        print("  [4] Update Employee Details")
        print("  [0] Return to Admin Menu")

        opt = prompt("Select Option", default="0")
        if opt == '0':
            break

        if opt == '1':
            print("\n--- ONBOARD NEW STAFF MEMBER ---")
            name = prompt("Full Name")
            title = prompt("Role Title (e.g. Station Master, Conductor, Chef, Inspector)")
            print("Departments:")
            for i, d in enumerate(DEPARTMENTS, 1):
                print(f"  [{i}] {d}")
            dept_idx = prompt("Select Department [1-{}]".format(len(DEPARTMENTS)))
            dept = DEPARTMENTS[int(dept_idx) - 1] if dept_idx.isdigit() and 1 <= int(dept_idx) <= len(DEPARTMENTS) else DEPARTMENTS[0]

            contact = prompt("10-Digit Contact Phone")
            salary = prompt("Monthly Salary (Rs.)", default="45000")
            print("Shifts:")
            for i, s in enumerate(SHIFTS, 1):
                print(f"  [{i}] {s}")
            s_idx = prompt("Select Shift [1-{}]".format(len(SHIFTS)))
            shift = SHIFTS[int(s_idx) - 1] if s_idx.isdigit() and 1 <= int(s_idx) <= len(SHIFTS) else SHIFTS[0]
            assigned = prompt("Assigned Station or Train (e.g. NDLS, Shatabdi 12002)", default="HQ / General")

            create_login = prompt("Create login account for this staff? (y/n)", default="y").lower() == 'y'
            u_name, u_pass = None, None
            if create_login:
                u_name = prompt("Staff Username")
                u_pass = prompt("Staff Initial Password")

            ok, msg, emp_id = add_employee(
                full_name=name,
                role_title=title,
                department=dept,
                contact=contact,
                salary=float(salary) if salary.replace('.', '', 1).isdigit() else 45000.0,
                shift=shift,
                assigned_to=assigned,
                create_login=create_login,
                username=u_name,
                password=u_pass
            )
            print(f"\n{msg}")
            pause()

        elif opt == '2' or opt == '3':
            filter_dept = None
            if opt == '3':
                print("Departments: " + ", ".join(DEPARTMENTS))
                filter_dept = prompt("Enter Department Name")

            staff_list = get_all_employees(department=filter_dept)
            print(f"\nTotal Staff: {len(staff_list)}")
            print(f"{'Code':<10} {'Name':<20} {'Designation':<20} {'Dept':<14} {'Salary':<12} {'Status':<10}")
            print("-" * 90)
            for s in staff_list:
                print(f"{s['employee_code']:<10} {s['full_name'][:18]:<20} {s['role_title'][:18]:<20} {s['department']:<14} Rs.{s['salary']:<9.2f} {s['status']:<10}")
            print("-" * 90)
            pause()

        elif opt == '4':
            eid = prompt("Enter Employee ID to update")
            if not eid.isdigit():
                continue
            name = prompt("Updated Name")
            title = prompt("Updated Designation")
            dept = prompt("Department", default="Operations")
            contact = prompt("Contact")
            salary = prompt("Salary", default="50000")
            shift = prompt("Shift", default=SHIFTS[0])
            status = prompt("Status (ACTIVE/ON_LEAVE/INACTIVE)", default="ACTIVE").upper()
            assigned = prompt("Assigned Station/Train")

            ok, msg = update_employee(int(eid), name, title, dept, contact, float(salary), shift, status, assigned)
            print(f"\n{msg}")
            pause()


def admin_manage_trains():
    while True:
        print_banner("TRAIN & ROUTE MANAGEMENT (ADMIN)")
        print("  [1] Add New Train")
        print("  [2] View All Trains")
        print("  [3] Add / Edit Route Stop for Train")
        print("  [4] View Train Timetable")
        print("  [0] Return to Admin Menu")

        opt = prompt("Select Option", default="0")
        if opt == '0':
            break

        if opt == '1':
            print("\n--- REGISTER NEW TRAIN ---")
            number = prompt("Train Number (e.g. 12050)")
            name = prompt("Train Name (e.g. Gatimaan Express)")
            print("Train Types: Rajdhani, Shatabdi, Vande Bharat, Superfast, Express")
            t_type = prompt("Train Type", default="Superfast")
            src = prompt("Source Station Code").upper()
            dest = prompt("Destination Station Code").upper()
            coaches = prompt("Total Coaches", default="16")
            base_fare = prompt("Base Fare per KM (Rs.)", default="1.3")

            ok, msg = add_train(number, name, t_type, src, dest, int(coaches) if coaches.isdigit() else 16, float(base_fare) if base_fare.replace('.', '', 1).isdigit() else 1.3)
            print(f"\n{msg}")
            pause()

        elif opt == '2':
            trains = get_all_trains()
            print(f"\n{'Train No':<10} {'Train Name':<26} {'Type':<14} {'Route':<18} {'Status':<8}")
            print("-" * 80)
            for t in trains:
                route_str = f"{t['source_code']} -> {t['dest_code']}"
                print(f"{t['train_number']:<10} {t['train_name'][:24]:<26} {t['train_type']:<14} {route_str:<18} {t['status']:<8}")
            print("-" * 80)
            pause()

        elif opt == '3':
            num = prompt("Enter Train Number")
            train = get_train_by_number(num)
            if not train:
                print("Train not found.")
                pause()
                continue
            stn = prompt("Station Code for Stop").upper()
            seq = prompt("Stop Sequence Number (e.g. 1, 2, 3)")
            dist = prompt("Distance from Source (KM)")
            arr = prompt("Scheduled Arrival Time (HH:MM or -- for origin)")
            dep = prompt("Scheduled Departure Time (HH:MM or -- for terminus)")
            plat = prompt("Platform Number", default="1")

            ok, msg = add_route_stop(train['id'], stn, int(seq), int(dist), arr, dep, int(plat))
            print(f"\n{msg}")
            pause()

        elif opt == '4':
            public_view_route()


def admin_manage_stations():
    while True:
        print_banner("STATION MANAGEMENT (ADMIN)")
        print("  [1] Add New Railway Station")
        print("  [2] View All Stations")
        print("  [0] Return to Admin Menu")

        opt = prompt("Select Option", default="0")
        if opt == '0':
            break

        if opt == '1':
            code = prompt("Station Code (e.g. PNBE)").upper()
            name = prompt("Station Name")
            city = prompt("City")
            state = prompt("State")
            plats = prompt("Number of Platforms", default="4")
            ok, msg = add_station(code, name, city, state, int(plats) if plats.isdigit() else 4)
            print(f"\n{msg}")
            pause()

        elif opt == '2':
            stns = get_all_stations()
            print(f"\n{'Code':<8} {'Station Name':<32} {'City':<18} {'Platforms':<10}")
            print("-" * 72)
            for s in stns:
                print(f"{s['station_code']:<8} {s['station_name'][:30]:<32} {s['city']:<18} {s['platforms_count']:<10}")
            print("-" * 72)
            pause()


def admin_manage_food():
    while True:
        print_banner("PANTRY & FOOD MENU MANAGEMENT (ADMIN)")
        print("  [1] Add New Dish / Drink to Menu")
        print("  [2] View Full Pantry Catalog")
        print("  [3] Toggle Item Availability (In Stock / Out of Stock)")
        print("  [0] Return to Admin Menu")

        opt = prompt("Select Option", default="0")
        if opt == '0':
            break

        if opt == '1':
            name = prompt("Dish / Beverage Name")
            print("Categories: " + ", ".join(FOOD_CATEGORIES))
            cat = prompt("Category", default="Meals")
            price = prompt("Price (Rs.)")
            ok, msg = add_menu_item(name, cat, float(price) if price.replace('.', '', 1).isdigit() else 100.0)
            print(f"\n{msg}")
            pause()

        elif opt == '2':
            public_browse_food_menu()

        elif opt == '3':
            iid = prompt("Enter Item ID to toggle")
            if iid.isdigit():
                state = prompt("Is available? (1 for Yes, 0 for No)", default="1") == "1"
                ok, msg = toggle_menu_availability(int(iid), state)
                print(f"\n{msg}")
                pause()


def admin_all_bookings():
    print_banner("ALL SYSTEM BOOKINGS & AUDIT LEDGER")
    bookings = get_all_bookings(50)
    print(f"{'PNR':<12} {'Passenger / User':<20} {'Train':<22} {'Date':<12} {'Fare':<10} {'Status':<10}")
    print("-" * 90)
    for b in bookings:
        user_info = f"{b['customer_name']} ({b['username']})"
        print(f"{b['pnr']:<12} {user_info[:18]:<20} {b['train_number'] + ' ' + b['train_name'][:12]:<22} {b['journey_date']:<12} Rs.{b['total_fare']:<7.2f} {b['booking_status']:<10}")
    print("-" * 90)
    pause()


# =====================================================================
# ROLE DASHBOARDS
# =====================================================================

def passenger_dashboard(user: dict):
    while True:
        clear_screen()
        print_banner(f"PASSENGER PORTAL - Welcome, {user['full_name']}!")
        print("  [1] Search & Book Train Tickets")
        print("  [2] My Bookings & PNR Details")
        print("  [3] Cancel Ticket & Claim Refund")
        print("  [4] Live Train Tracking (Visual Route Map)")
        print("  [5] Order Food to Seat (Linked with PNR)")
        print("  [6] Track My Food Orders")
        print("  [7] File Grievance / Complaint")
        print("  [8] View My Complaints & Status")
        print("  [9] My Profile & Settings")
        print("  [0] Logout")

        choice = prompt("\nEnter your choice [0-9]", default="1")
        if choice == '0':
            print("Logging out...")
            break
        elif choice == '1':
            passenger_book_ticket(user)
        elif choice == '2':
            passenger_my_bookings(user)
        elif choice == '3':
            passenger_cancel_ticket(user)
        elif choice == '4':
            public_live_tracking()
        elif choice == '5':
            passenger_order_food(user)
        elif choice == '6':
            passenger_my_food_orders(user)
        elif choice == '7':
            passenger_file_complaint(user)
        elif choice == '8':
            passenger_my_complaints(user)
        elif choice == '9':
            passenger_profile(user)


def staff_dashboard(user: dict):
    while True:
        clear_screen()
        print_banner(f"STAFF DASHBOARD - Welcome, {user['full_name']}!")
        print("  [1] Update Train Live Location & Delays")
        print("  [2] Live Station Enquiry Board")
        print("  [3] In-Train Pantry & Food Orders Desk")
        print("  [4] Grievance & Passenger Complaints Desk")
        print("  [5] Live Train Tracking Map")
        print("  [6] My Staff Profile & Shift Timings")
        print("  [0] Logout")

        choice = prompt("\nEnter your choice [0-6]", default="1")
        if choice == '0':
            print("Logging out...")
            break
        elif choice == '1':
            staff_update_tracking()
        elif choice == '2':
            public_station_board()
        elif choice == '3':
            staff_pantry_orders()
        elif choice == '4':
            staff_complaints_desk(user)
        elif choice == '5':
            public_live_tracking()
        elif choice == '6':
            staff_view_profile(user)


def admin_dashboard(user: dict):
    while True:
        clear_screen()
        print_banner("ADMIN CONTROL CENTER - INDIAN RAILWAYS PORTAL")
        print("  [1] Executive Analytics & Revenue Dashboard")
        print("  [2] Staff & Employee Management (Add Staff, Assign Roles, Payroll)")
        print("  [3] Train & Route Timetable Management")
        print("  [4] Railway Station Management")
        print("  [5] Pantry & Food Menu Management")
        print("  [6] View All Bookings & Reservations")
        print("  [7] Grievance Redressal Desk")
        print("  [8] Reset & Re-Seed Database")
        print("  [0] Logout")

        choice = prompt("\nEnter your choice [0-8]", default="1")
        if choice == '0':
            print("Logging out...")
            break
        elif choice == '1':
            admin_system_analytics()
        elif choice == '2':
            admin_manage_staff()
        elif choice == '3':
            admin_manage_trains()
        elif choice == '4':
            admin_manage_stations()
        elif choice == '5':
            admin_manage_food()
        elif choice == '6':
            admin_all_bookings()
        elif choice == '7':
            staff_complaints_desk(user)
        elif choice == '8':
            confirm = prompt("Are you sure you want to reset all data and re-seed? (yes/no)").lower()
            if confirm == 'yes':
                seed_all(force=True)
                print("Database reset and re-seeded successfully.")
            pause()


# =====================================================================
# MAIN LOOP
# =====================================================================

def login_flow():
    print_banner("USER LOGIN")
    username = prompt("Username")
    password = prompt("Password")

    ok, msg, user_data = login_user(username, password)
    if not ok:
        print(f"\n[LOGIN FAILED]: {msg}")
        pause()
        return

    print(f"\n[SUCCESS]: {msg} (Role: {user_data['role'].upper()})")
    pause()

    # Route by role
    if user_data['role'] == 'admin':
        admin_dashboard(user_data)
    elif user_data['role'] == 'staff':
        staff_dashboard(user_data)
    else:
        passenger_dashboard(user_data)


def register_flow():
    print_banner("PASSENGER REGISTRATION")
    username = prompt("Desired Username (min 3 chars)")
    password = prompt("Password (min 6 chars)")
    name = prompt("Full Name")
    email = prompt("Email Address")
    phone = prompt("10-Digit Mobile Number")

    ok, msg, uid = register_user(username, password, name, email, phone, role='passenger')
    if ok:
        print(f"\n[REGISTRATION SUCCESSFUL]: {msg}")
        print("You can now log in with your new credentials.")
    else:
        print(f"\n[REGISTRATION FAILED]: {msg}")
    pause()



def main():
    init_db()

    while True:
        clear_screen()
        print_banner("TRAIN MANAGEMENT SYSTEM (TMS)")
        print("  [1] Search Trains Between Stations")
        print("  [2] View Train Route & Timetable")
        print("  [3] PNR Status Enquiry")
        print("  [4] Live Train Tracking (Visual Route Map & Delays)")
        print("  [5] Live Station Board (Departures & Arrivals)")
        print("  [6] In-Train Pantry Food Menu")
        print("  [7] Login (Passenger / Staff / Admin)")
        print("  [8] Register New Passenger Account")
        print("  [9] Exit System")

        choice = prompt("\nEnter option [1-9]", default="1")

        if choice == '1':
            public_search_trains()
        elif choice == '2':
            public_view_route()
        elif choice == '3':
            public_check_pnr()
        elif choice == '4':
            public_live_tracking()
        elif choice == '5':
            public_station_board()
        elif choice == '6':
            public_browse_food_menu()
        elif choice == '7':
            login_flow()
        elif choice == '8':
            register_flow()
        elif choice == '9':
            print("\nThank you for using the Train Management System. Have a safe journey!")
            sys.exit(0)
        else:
            print("Invalid choice, please select 1-9.")
            pause()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nOperation cancelled. Exiting.")
        sys.exit(0)
