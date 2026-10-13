

import os
import sqlite3
from contextlib import contextmanager

# Ensure data directory exists
DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(DB_DIR, exist_ok=True)
DB_PATH = os.path.join(DB_DIR, "train_system.db")


@contextmanager
def get_db():
    """Context manager for SQLite database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Access columns by name
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def execute_query(sql, params=()):
    """Execute a query that modifies data (INSERT, UPDATE, DELETE)."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        return cursor.lastrowid


def execute_script(sql_script):
    """Execute a multi-statement SQL script."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.executescript(sql_script)


def fetch_one(sql, params=()):
    """Fetch a single row as a dictionary."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        row = cursor.fetchone()
        return dict(row) if row else None


def fetch_all(sql, params=()):
    """Fetch all rows as a list of dictionaries."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        return [dict(r) for r in rows]


def init_db():
    """Create all required tables, views, and indexes if they do not exist."""
    schema_sql = """
    -- Users Table (Role-based access: admin, staff, passenger)
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        salt TEXT NOT NULL,
        full_name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        phone TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('admin', 'staff', 'passenger')),
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    -- Employees Table (Staff records managed by admin)
    CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE,
        employee_code TEXT UNIQUE NOT NULL,
        full_name TEXT NOT NULL,
        role_title TEXT NOT NULL,
        department TEXT NOT NULL CHECK(department IN ('Operations', 'Ticketing', 'Catering', 'Maintenance', 'Management')),
        contact TEXT NOT NULL,
        salary REAL NOT NULL DEFAULT 0.0,
        shift TEXT NOT NULL DEFAULT 'Morning (06:00 - 14:00)',
        status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK(status IN ('ACTIVE', 'ON_LEAVE', 'INACTIVE')),
        assigned_to TEXT DEFAULT 'HQ / General',
        joining_date DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
    );

    -- Stations Table
    CREATE TABLE IF NOT EXISTS stations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        station_code TEXT UNIQUE NOT NULL,
        station_name TEXT NOT NULL,
        city TEXT NOT NULL,
        state TEXT NOT NULL,
        platforms_count INTEGER NOT NULL DEFAULT 2
    );

    -- Trains Table
    CREATE TABLE IF NOT EXISTS trains (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        train_number TEXT UNIQUE NOT NULL,
        train_name TEXT NOT NULL,
        train_type TEXT NOT NULL CHECK(train_type IN ('Rajdhani', 'Shatabdi', 'Vande Bharat', 'Superfast', 'Express')),
        total_coaches INTEGER NOT NULL DEFAULT 16,
        source_code TEXT NOT NULL,
        dest_code TEXT NOT NULL,
        base_fare_per_km REAL NOT NULL DEFAULT 1.2,
        status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK(status IN ('ACTIVE', 'CANCELLED')),
        FOREIGN KEY (source_code) REFERENCES stations(station_code),
        FOREIGN KEY (dest_code) REFERENCES stations(station_code)
    );

    -- Train Routes Table (Intermediate stops, schedule, distances, platforms)
    CREATE TABLE IF NOT EXISTS routes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        train_id INTEGER NOT NULL,
        station_code TEXT NOT NULL,
        stop_sequence INTEGER NOT NULL,
        distance_km INTEGER NOT NULL DEFAULT 0,
        scheduled_arrival TEXT NOT NULL,
        scheduled_departure TEXT NOT NULL,
        platform_number INTEGER NOT NULL DEFAULT 1,
        FOREIGN KEY (train_id) REFERENCES trains(id) ON DELETE CASCADE,
        FOREIGN KEY (station_code) REFERENCES stations(station_code),
        UNIQUE(train_id, stop_sequence),
        UNIQUE(train_id, station_code)
    );

    -- Live Train Status Table (Tracking and delays)
    CREATE TABLE IF NOT EXISTS train_live_status (
        train_id INTEGER PRIMARY KEY,
        current_station_code TEXT NOT NULL,
        next_station_code TEXT,
        delay_minutes INTEGER NOT NULL DEFAULT 0,
        current_status TEXT NOT NULL DEFAULT 'ON_TIME' CHECK(current_status IN ('ON_TIME', 'DELAYED', 'ARRIVED', 'DEPARTED')),
        last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (train_id) REFERENCES trains(id) ON DELETE CASCADE
    );

    -- Bookings Table (PNR and reservation details)
    CREATE TABLE IF NOT EXISTS bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pnr TEXT UNIQUE NOT NULL,
        user_id INTEGER NOT NULL,
        train_id INTEGER NOT NULL,
        journey_date TEXT NOT NULL,
        source_code TEXT NOT NULL,
        dest_code TEXT NOT NULL,
        coach_class TEXT NOT NULL CHECK(coach_class IN ('1A', '2A', '3A', 'SL', 'CC')),
        seat_numbers TEXT NOT NULL,
        total_fare REAL NOT NULL,
        booking_status TEXT NOT NULL DEFAULT 'CONFIRMED' CHECK(booking_status IN ('CONFIRMED', 'CANCELLED')),
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (train_id) REFERENCES trains(id)
    );

    -- Passengers Table (Individual passengers in a booking)
    CREATE TABLE IF NOT EXISTS passengers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        booking_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        age INTEGER NOT NULL,
        gender TEXT NOT NULL CHECK(gender IN ('Male', 'Female', 'Other')),
        berth_pref TEXT NOT NULL DEFAULT 'No Preference',
        seat_number TEXT NOT NULL,
        FOREIGN KEY (booking_id) REFERENCES bookings(id) ON DELETE CASCADE
    );

    -- Payments Table (Transactions & refunds)
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        transaction_id TEXT UNIQUE NOT NULL,
        user_id INTEGER NOT NULL,
        booking_id INTEGER,
        food_order_id TEXT,
        amount REAL NOT NULL,
        payment_method TEXT NOT NULL CHECK(payment_method IN ('UPI', 'CARD', 'NETBANKING', 'WALLET', 'CASH')),
        payment_type TEXT NOT NULL CHECK(payment_type IN ('TICKET_BOOKING', 'FOOD_ORDER', 'REFUND')),
        status TEXT NOT NULL DEFAULT 'SUCCESS' CHECK(status IN ('SUCCESS', 'REFUNDED', 'FAILED')),
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    );

    -- Food Menu Table (Pantry items)
    CREATE TABLE IF NOT EXISTS food_menu (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_name TEXT NOT NULL,
        category TEXT NOT NULL CHECK(category IN ('Meals', 'Breakfast', 'Snacks', 'Beverages', 'Dessert')),
        price REAL NOT NULL,
        is_available INTEGER NOT NULL DEFAULT 1
    );

    -- Food Orders Table
    CREATE TABLE IF NOT EXISTS food_orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id TEXT UNIQUE NOT NULL,
        pnr TEXT NOT NULL,
        user_id INTEGER NOT NULL,
        delivery_station TEXT NOT NULL,
        seat_info TEXT NOT NULL,
        total_amount REAL NOT NULL,
        order_status TEXT NOT NULL DEFAULT 'PLACED' CHECK(order_status IN ('PLACED', 'PREPARING', 'OUT_FOR_DELIVERY', 'DELIVERED', 'CANCELLED')),
        payment_status TEXT NOT NULL DEFAULT 'PAID' CHECK(payment_status IN ('PAID', 'PENDING', 'REFUNDED')),
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (pnr) REFERENCES bookings(pnr),
        FOREIGN KEY (user_id) REFERENCES users(id)
    );

    -- Food Order Items Table
    CREATE TABLE IF NOT EXISTS food_order_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id TEXT NOT NULL,
        item_id INTEGER NOT NULL,
        item_name TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        unit_price REAL NOT NULL,
        FOREIGN KEY (order_id) REFERENCES food_orders(order_id) ON DELETE CASCADE,
        FOREIGN KEY (item_id) REFERENCES food_menu(id)
    );

    -- Complaints / Grievances Table
    CREATE TABLE IF NOT EXISTS complaints (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticket_number TEXT UNIQUE NOT NULL,
        user_id INTEGER NOT NULL,
        pnr TEXT,
        category TEXT NOT NULL CHECK(category IN ('Cleanliness', 'Food Quality', 'Punctuality', 'Staff Behavior', 'Ticketing', 'Other')),
        description TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'OPEN' CHECK(status IN ('OPEN', 'IN_PROGRESS', 'RESOLVED', 'CLOSED')),
        resolution_note TEXT,
        assigned_staff_id INTEGER,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        resolved_at DATETIME,
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (assigned_staff_id) REFERENCES employees(id)
    );

    -- Indexes for performance
    CREATE INDEX IF NOT EXISTS idx_routes_train ON routes(train_id, stop_sequence);
    CREATE INDEX IF NOT EXISTS idx_bookings_pnr ON bookings(pnr);
    CREATE INDEX IF NOT EXISTS idx_bookings_user ON bookings(user_id);
    CREATE INDEX IF NOT EXISTS idx_food_orders_pnr ON food_orders(pnr);
    CREATE INDEX IF NOT EXISTS idx_complaints_user ON complaints(user_id);
    CREATE INDEX IF NOT EXISTS idx_complaints_status ON complaints(status);
    """
    execute_script(schema_sql)


if __name__ == "__main__":
    init_db()
    print(f"Database initialized successfully at: {DB_PATH}")
