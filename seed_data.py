"""
seed_data.py - Sample Data Ingestion Script
Populates the SQLite database with realistic railway stations, trains, routes,
food menus, staff members, pre-set bookings, and user accounts.
"""

from database import execute_query, fetch_one, init_db
from modules.auth import register_user
from modules.booking import book_ticket
from modules.complaints import file_complaint
from modules.employees import add_employee
from modules.food import add_menu_item, place_food_order
from modules.schedule import update_train_live_status
from modules.trains import add_route_stop, add_station, add_train


def seed_all(force: bool = False):
    """Seed sample data into database."""
    if force:
        from database import execute_script
        execute_script("""
            PRAGMA foreign_keys = OFF;
            DROP TABLE IF EXISTS complaints;
            DROP TABLE IF EXISTS food_order_items;
            DROP TABLE IF EXISTS food_orders;
            DROP TABLE IF EXISTS food_menu;
            DROP TABLE IF EXISTS payments;
            DROP TABLE IF EXISTS passengers;
            DROP TABLE IF EXISTS bookings;
            DROP TABLE IF EXISTS train_live_status;
            DROP TABLE IF EXISTS routes;
            DROP TABLE IF EXISTS trains;
            DROP TABLE IF EXISTS stations;
            DROP TABLE IF EXISTS employees;
            DROP TABLE IF EXISTS users;
            PRAGMA foreign_keys = ON;
        """)
        init_db()
    else:
        init_db()
        existing_user = fetch_one("SELECT id FROM users WHERE username = 'admin'")
        if existing_user:
            print("Database already contains seed data. Run with force=True to re-seed.")
            return

    print(">>> Seeding database with realistic railway data...")

    # 1. Seed Users
    print("Seeding users (Admin, Staff, Passengers)...")
    _, _, admin_id = register_user("admin", "admin123", "System Administrator", "admin@trainsystem.org", "9876543210", "admin")
    _, _, staff1_id = register_user("staff1", "staff123", "Ramesh Kumar (Ops)", "ramesh@trainsystem.org", "9876543211", "staff")
    _, _, staff2_id = register_user("staff2", "staff123", "Sunita Rao (Pantry)", "sunita@trainsystem.org", "9876543212", "staff")
    _, _, pass1_id = register_user("passenger1", "pass123", "Rahul Sharma", "rahul.sharma@example.com", "9123456780", "passenger")
    _, _, pass2_id = register_user("priya_p", "pass123", "Priya Patel", "priya.patel@example.com", "9123456781", "passenger")

    # 2. Seed Stations
    print("Seeding railway stations...")
    stations_data = [
        ("NDLS", "New Delhi Railway Station", "New Delhi", "Delhi", 16),
        ("CSMT", "Chhatrapati Shivaji Maharaj Terminus", "Mumbai", "Maharashtra", 18),
        ("SBC", "KSR Bengaluru City Junction", "Bengaluru", "Karnataka", 10),
        ("MAS", "Chennai Central", "Chennai", "Tamil Nadu", 12),
        ("HWH", "Howrah Junction", "Kolkata", "West Bengal", 23),
        ("AGC", "Agra Cantt", "Agra", "Uttar Pradesh", 6),
        ("GWL", "Gwalior Junction", "Gwalior", "Madhya Pradesh", 4),
        ("VGLJ", "VGL Jhansi Junction", "Jhansi", "Uttar Pradesh", 8),
        ("BPL", "Bhopal Junction", "Bhopal", "Madhya Pradesh", 6),
        ("KOTA", "Kota Junction", "Kota", "Rajasthan", 5),
        ("RTM", "Ratlam Junction", "Ratlam", "Madhya Pradesh", 7),
        ("BRC", "Vadodara Junction", "Vadodara", "Gujarat", 7),
        ("ST", "Surat Railway Station", "Surat", "Gujarat", 4),
    ]
    for code, name, city, state, plats in stations_data:
        add_station(code, name, city, state, plats)

    # 3. Seed Trains
    print("Seeding express and high-speed trains...")
    trains_data = [
        ("12002", "Bhopal Shatabdi Express", "Shatabdi", "NDLS", "BPL", 16, 1.4),
        ("12952", "Mumbai Rajdhani Express", "Rajdhani", "NDLS", "CSMT", 20, 1.6),
        ("22436", "Vande Bharat Express", "Vande Bharat", "NDLS", "VGLJ", 16, 1.8),
        ("12628", "Karnataka Express", "Superfast", "NDLS", "SBC", 22, 1.1),
        ("12007", "Mysuru Shatabdi Express", "Shatabdi", "MAS", "SBC", 14, 1.3),
    ]
    train_ids = {}
    for num, name, t_type, src, dest, coaches, fare in trains_data:
        ok, _ = add_train(num, name, t_type, src, dest, coaches, fare)
        # Fetch train id
        t_row = fetch_one("SELECT id FROM trains WHERE train_number = ?", (num,))
        train_ids[num] = t_row['id']

    # 4. Seed Route Stops & Schedules
    print("Configuring train timetables and intermediate stops...")
    # Train 12002: NDLS -> AGC -> GWL -> VGLJ -> BPL
    t1 = train_ids["12002"]
    add_route_stop(t1, "NDLS", 1, 0, "--", "06:00", 1)
    add_route_stop(t1, "AGC", 2, 188, "07:50", "07:55", 2)
    add_route_stop(t1, "GWL", 3, 306, "09:23", "09:28", 1)
    add_route_stop(t1, "VGLJ", 4, 403, "10:45", "10:53", 4)
    add_route_stop(t1, "BPL", 5, 707, "14:40", "--", 1)

    # Train 12952: NDLS -> KOTA -> RTM -> BRC -> ST -> CSMT
    t2 = train_ids["12952"]
    add_route_stop(t2, "NDLS", 1, 0, "--", "16:55", 3)
    add_route_stop(t2, "KOTA", 2, 465, "21:30", "21:40", 1)
    add_route_stop(t2, "RTM", 3, 730, "00:45", "00:50", 4)
    add_route_stop(t2, "BRC", 4, 992, "03:50", "04:00", 2)
    add_route_stop(t2, "ST", 5, 1122, "05:15", "05:20", 1)
    add_route_stop(t2, "CSMT", 6, 1384, "08:35", "--", 18)

    # Train 22436: NDLS -> AGC -> GWL -> VGLJ
    t3 = train_ids["22436"]
    add_route_stop(t3, "NDLS", 1, 0, "--", "06:00", 16)
    add_route_stop(t3, "AGC", 2, 188, "07:30", "07:35", 3)
    add_route_stop(t3, "GWL", 3, 306, "08:45", "08:48", 2)
    add_route_stop(t3, "VGLJ", 4, 403, "09:55", "--", 3)

    # Train 12628: NDLS -> AGC -> BPL -> SBC
    t4 = train_ids["12628"]
    add_route_stop(t4, "NDLS", 1, 0, "--", "20:20", 5)
    add_route_stop(t4, "AGC", 2, 188, "22:48", "22:50", 1)
    add_route_stop(t4, "BPL", 3, 707, "06:25", "06:30", 3)
    add_route_stop(t4, "SBC", 4, 2400, "12:00", "--", 4)

    # Train 12007: MAS -> SBC
    t5 = train_ids["12007"]
    add_route_stop(t5, "MAS", 1, 0, "--", "06:00", 2)
    add_route_stop(t5, "SBC", 2, 362, "10:45", "--", 1)

    # 5. Live Tracking Initial Status
    print("Setting live train status & simulated delays...")
    update_train_live_status(t1, "AGC", "GWL", delay_minutes=12, current_status="DELAYED")
    update_train_live_status(t2, "KOTA", "RTM", delay_minutes=0, current_status="ON_TIME")
    update_train_live_status(t3, "GWL", "VGLJ", delay_minutes=5, current_status="ON_TIME")
    update_train_live_status(t4, "AGC", "BPL", delay_minutes=25, current_status="DELAYED")
    update_train_live_status(t5, "MAS", "SBC", delay_minutes=0, current_status="ON_TIME")

    # 6. Seed Staff & Employees
    print("Onboarding staff members with roles and departments...")
    add_employee("Ramesh Kumar", "Station Master", "Operations", "9876543211", 65000.0, "Morning (06:00 - 14:00)", "NDLS Junction")
    add_employee("Sunita Rao", "Pantry & Catering Supervisor", "Catering", "9876543212", 45000.0, "Morning (06:00 - 14:00)", "Shatabdi Pantry Car")
    add_employee("Vikram Singh", "Senior Ticket Examiner (TTE)", "Ticketing", "9876543213", 52000.0, "Evening (14:00 - 22:00)", "Train 12952 Rajdhani")
    add_employee("Anil Verma", "Track & Rolling Stock Inspector", "Maintenance", "9876543214", 48000.0, "Night (22:00 - 06:00)", "Northern Railway Depot")
    add_employee("Pooja Nair", "Chief Operations Manager", "Management", "9876543215", 85000.0, "General / Flexible", "Rail Bhawan HQ")

    # 7. Seed Pantry Food Menu
    print("Populating pantry food menu...")
    menu_items = [
        # Meals
        ("Royal North Indian Thali", "Meals", 180.0),
        ("South Indian Special Thali", "Meals", 160.0),
        ("Hyderabadi Chicken Biryani Box", "Meals", 220.0),
        ("Paneer Butter Masala with Parathas", "Meals", 190.0),
        # Breakfast
        ("Puri Bhaji (4 pcs)", "Breakfast", 80.0),
        ("Masala Dosa with Sambar & Chutney", "Breakfast", 90.0),
        ("Bread Omelette (2 eggs)", "Breakfast", 70.0),
        ("Steamed Idli Vada Combo", "Breakfast", 75.0),
        # Snacks
        ("Vegetable Cutlets (2 pcs)", "Snacks", 50.0),
        ("Crispy Samosa (2 pcs) with Chutney", "Snacks", 40.0),
        ("Grilled Veg Cheese Sandwich", "Snacks", 90.0),
        ("Salted Roasted Cashews", "Snacks", 60.0),
        # Beverages
        ("Special Masala Chai", "Beverages", 20.0),
        ("South Indian Filter Coffee", "Beverages", 25.0),
        ("Packaged Rail Neer (1 Litre)", "Beverages", 15.0),
        ("Cold Fresh Lemon Soda", "Beverages", 35.0),
        # Dessert
        ("Hot Gulab Jamun (2 pcs)", "Dessert", 50.0),
        ("Vanilla Ice Cream Cup", "Dessert", 40.0),
    ]
    for name, cat, price in menu_items:
        add_menu_item(name, cat, price)

    # 8. Seed Pre-booked Tickets
    print("Generating sample passenger bookings...")
    sample_passengers_1 = [
        {'name': 'Rahul Sharma', 'age': 29, 'gender': 'Male', 'berth_pref': 'Lower Berth'},
        {'name': 'Ananya Sharma', 'age': 27, 'gender': 'Female', 'berth_pref': 'Middle Berth'}
    ]
    ok_b1, msg_b1, b1_data = book_ticket(
        user_id=pass1_id,
        train_id=t1,
        journey_date="2026-09-25",
        source_code="NDLS",
        dest_code="BPL",
        coach_class="3A",
        passenger_list=sample_passengers_1,
        payment_method="UPI"
    )

    sample_passengers_2 = [
        {'name': 'Priya Patel', 'age': 32, 'gender': 'Female', 'berth_pref': 'Window Seat'}
    ]
    ok_b2, msg_b2, b2_data = book_ticket(
        user_id=pass2_id,
        train_id=t3,
        journey_date="2026-09-26",
        source_code="NDLS",
        dest_code="AGC",
        coach_class="CC",
        passenger_list=sample_passengers_2,
        payment_method="CARD"
    )

    # 9. Seed Sample Food Order for booking 1
    if ok_b1 and b1_data:
        print("Generating sample in-train food order...")
        food_items = [
            {'item_id': 1, 'quantity': 2},  # 2x Royal North Indian Thali
            {'item_id': 13, 'quantity': 2}, # 2x Special Masala Chai
        ]
        place_food_order(
            pnr=b1_data['pnr'],
            user_id=pass1_id,
            items_ordered=food_items,
            delivery_station="AGC",
            seat_info=b1_data['seats'][0],
            payment_method="UPI"
        )

    # 10. Seed Sample Complaint
    print("Registering sample passenger grievance...")
    file_complaint(
        user_id=pass1_id,
        category="Cleanliness",
        description="Coach B1 washroom requires immediate sanitization and water replenishment.",
        pnr=b1_data['pnr'] if (ok_b1 and b1_data) else None
    )

    print(">>> Seed data populated successfully!")
    print(f"Default Admin: username='admin', password='admin123'")
    print(f"Default Staff: username='staff1', password='staff123'")
    print(f"Default Passenger: username='passenger1', password='pass123'")


if __name__ == "__main__":
    seed_all(force=True)
