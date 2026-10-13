"""
modules/trains.py - Train, Station & Route Management
Handles station queries, train creation, multi-stop route discovery, and fare calculations.
"""

from database import execute_query, fetch_all, fetch_one

# Fare multipliers for different coach classes
CLASS_MULTIPLIERS = {
    '1A': 3.2,   # AC First Class
    '2A': 2.2,   # AC 2 Tier
    '3A': 1.5,   # AC 3 Tier
    'CC': 1.2,   # AC Chair Car
    'SL': 0.6,   # Sleeper Class
}

CLASS_NAMES = {
    '1A': 'AC First Class (1A)',
    '2A': 'AC 2 Tier (2A)',
    '3A': 'AC 3 Tier (3A)',
    'CC': 'AC Chair Car (CC)',
    'SL': 'Sleeper Class (SL)',
}

TRAIN_TYPE_MULTIPLIERS = {
    'Vande Bharat': 1.5,
    'Rajdhani': 1.4,
    'Shatabdi': 1.3,
    'Superfast': 1.1,
    'Express': 1.0,
}


# =====================================================================
# STATION MANAGEMENT
# =====================================================================

def add_station(station_code: str, station_name: str, city: str, state: str, platforms_count: int = 2) -> tuple:
    """Add a new railway station."""
    code = station_code.strip().upper()
    name = station_name.strip()
    city = city.strip()
    state = state.strip()

    if not code or len(code) < 2 or len(code) > 6:
        return False, "Station code must be between 2 and 6 characters."

    existing = fetch_one("SELECT id FROM stations WHERE station_code = ?", (code,))
    if existing:
        return False, f"Station code '{code}' already exists."

    try:
        execute_query(
            """
            INSERT INTO stations (station_code, station_name, city, state, platforms_count)
            VALUES (?, ?, ?, ?, ?)
            """,
            (code, name, city, state, max(1, platforms_count))
        )
        return True, f"Station {name} ({code}) added successfully."
    except Exception as e:
        return False, f"Failed to add station: {str(e)}"


def get_all_stations() -> list:
    """Retrieve all stations ordered by code."""
    return fetch_all("SELECT * FROM stations ORDER BY station_code ASC")


def get_station_by_code(code: str) -> dict:
    """Get station record by its 2-6 letter code."""
    return fetch_one("SELECT * FROM stations WHERE station_code = ?", (code.strip().upper(),))


def search_stations(query: str) -> list:
    """Search stations by code, name, or city."""
    term = f"%{query.strip()}%"
    return fetch_all(
        """
        SELECT * FROM stations
        WHERE station_code LIKE ? OR station_name LIKE ? OR city LIKE ?
        ORDER BY station_code ASC
        """,
        (term, term, term)
    )


# =====================================================================
# TRAIN MANAGEMENT
# =====================================================================

def add_train(train_number: str, train_name: str, train_type: str,
              source_code: str, dest_code: str, total_coaches: int = 16,
              base_fare_per_km: float = 1.2) -> tuple:
    """Register a new train in the system."""
    number = train_number.strip()
    name = train_name.strip()
    t_type = train_type.strip()
    src = source_code.strip().upper()
    dest = dest_code.strip().upper()

    if not get_station_by_code(src):
        return False, f"Source station '{src}' does not exist."
    if not get_station_by_code(dest):
        return False, f"Destination station '{dest}' does not exist."
    if src == dest:
        return False, "Source and destination stations cannot be the same."

    existing = fetch_one("SELECT id FROM trains WHERE train_number = ?", (number,))
    if existing:
        return False, f"Train number '{number}' already exists."

    try:
        train_id = execute_query(
            """
            INSERT INTO trains (train_number, train_name, train_type, total_coaches, source_code, dest_code, base_fare_per_km)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (number, name, t_type, total_coaches, src, dest, max(0.5, float(base_fare_per_km)))
        )
        # Initialize train live status
        execute_query(
            """
            INSERT INTO train_live_status (train_id, current_station_code, next_station_code, delay_minutes, current_status)
            VALUES (?, ?, ?, 0, 'ON_TIME')
            """,
            (train_id, src, src)
        )
        return True, f"Train '{name}' ({number}) registered successfully. ID: {train_id}"
    except Exception as e:
        return False, f"Failed to register train: {str(e)}"


def get_all_trains() -> list:
    """Retrieve all trains with source and destination details."""
    return fetch_all(
        """
        SELECT t.*, s1.station_name as source_name, s2.station_name as dest_name
        FROM trains t
        JOIN stations s1 ON t.source_code = s1.station_code
        JOIN stations s2 ON t.dest_code = s2.station_code
        ORDER BY t.train_number ASC
        """
    )


def get_train_by_id(train_id: int) -> dict:
    """Get train details by primary key ID."""
    return fetch_one(
        """
        SELECT t.*, s1.station_name as source_name, s2.station_name as dest_name
        FROM trains t
        JOIN stations s1 ON t.source_code = s1.station_code
        JOIN stations s2 ON t.dest_code = s2.station_code
        WHERE t.id = ?
        """,
        (train_id,)
    )


def get_train_by_number(train_number: str) -> dict:
    """Get train details by train number."""
    return fetch_one(
        """
        SELECT t.*, s1.station_name as source_name, s2.station_name as dest_name
        FROM trains t
        JOIN stations s1 ON t.source_code = s1.station_code
        JOIN stations s2 ON t.dest_code = s2.station_code
        WHERE t.train_number = ?
        """,
        (train_number.strip(),)
    )


# =====================================================================
# ROUTE & SCHEDULE MANAGEMENT
# =====================================================================

def add_route_stop(train_id: int, station_code: str, stop_sequence: int,
                   distance_km: int, scheduled_arrival: str, scheduled_departure: str,
                   platform_number: int = 1) -> tuple:
    """Add or update an intermediate stop along a train's route."""
    code = station_code.strip().upper()
    if not get_station_by_code(code):
        return False, f"Station '{code}' does not exist."

    train = get_train_by_id(train_id)
    if not train:
        return False, "Train not found."

    try:
        execute_query(
            """
            INSERT INTO routes (train_id, station_code, stop_sequence, distance_km,
                                scheduled_arrival, scheduled_departure, platform_number)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(train_id, stop_sequence) DO UPDATE SET
                station_code = excluded.station_code,
                distance_km = excluded.distance_km,
                scheduled_arrival = excluded.scheduled_arrival,
                scheduled_departure = excluded.scheduled_departure,
                platform_number = excluded.platform_number
            """,
            (train_id, code, stop_sequence, distance_km, scheduled_arrival, scheduled_departure, platform_number)
        )
        return True, f"Stop sequence {stop_sequence} ({code}) added for Train ID {train_id}."
    except Exception as e:
        return False, f"Failed to add route stop: {str(e)}"


def get_train_route(train_id: int) -> list:
    """Retrieve all stops in order along a train's route."""
    return fetch_all(
        """
        SELECT r.*, s.station_name, s.city
        FROM routes r
        JOIN stations s ON r.station_code = s.station_code
        WHERE r.train_id = ?
        ORDER BY r.stop_sequence ASC
        """,
        (train_id,)
    )


def search_trains_between_stations(source_code: str, dest_code: str) -> list:
    """
    Find all trains running between source and destination stations.
    Validates that source stop sequence < destination stop sequence.
    """
    src = source_code.strip().upper()
    dest = dest_code.strip().upper()

    sql = """
    SELECT
        t.id as train_id,
        t.train_number,
        t.train_name,
        t.train_type,
        t.base_fare_per_km,
        t.status,
        r1.station_code as src_code,
        s1.station_name as src_name,
        r1.scheduled_departure as departure_time,
        r1.platform_number as src_platform,
        r1.distance_km as src_dist,
        r2.station_code as dest_code,
        s2.station_name as dest_name,
        r2.scheduled_arrival as arrival_time,
        r2.platform_number as dest_platform,
        r2.distance_km as dest_dist,
        (r2.distance_km - r1.distance_km) as journey_distance_km
    FROM routes r1
    JOIN routes r2 ON r1.train_id = r2.train_id
    JOIN trains t ON t.id = r1.train_id
    JOIN stations s1 ON r1.station_code = s1.station_code
    JOIN stations s2 ON r2.station_code = s2.station_code
    WHERE r1.station_code = ?
      AND r2.station_code = ?
      AND r1.stop_sequence < r2.stop_sequence
      AND t.status = 'ACTIVE'
    ORDER BY r1.scheduled_departure ASC
    """
    return fetch_all(sql, (src, dest))


def calculate_fare(train_type: str, base_fare_per_km: float,
                   distance_km: int, coach_class: str, num_passengers: int = 1) -> float:
    """Calculate passenger fare based on class, train type, distance, and headcount."""
    dist = max(10, int(distance_km))
    class_mult = CLASS_MULTIPLIERS.get(coach_class, 1.0)
    type_mult = TRAIN_TYPE_MULTIPLIERS.get(train_type, 1.0)

    single_fare = dist * base_fare_per_km * class_mult * type_mult
    # Round to reasonable railway fare (minimum 50 INR)
    single_fare = max(50.0, round(single_fare, 2))
    return round(single_fare * num_passengers, 2)
