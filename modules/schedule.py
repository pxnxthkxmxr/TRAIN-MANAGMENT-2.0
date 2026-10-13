"""
modules/schedule.py - Real-Time Train Tracking, Live Station Boards & Delay Management
Provides station-by-station journey progression, visual route timelines, and platform updates.
"""

from datetime import datetime, timedelta
from database import execute_query, fetch_all, fetch_one
from modules.trains import get_train_by_id, get_train_by_number, get_train_route


def add_minutes_to_time(time_str: str, minutes: int) -> str:
    """Helper to add delay minutes to 'HH:MM' time string."""
    try:
        t = datetime.strptime(time_str.strip(), "%H:%M")
        t_delayed = t + timedelta(minutes=minutes)
        return t_delayed.strftime("%H:%M")
    except Exception:
        return time_str


def get_live_train_tracking(train_identifier: str) -> dict:
    """
    Get comprehensive live tracking data for a train by number or ID.
    Includes current position, delay, platform number, next halt, and station timeline.
    """
    if str(train_identifier).isdigit() and len(str(train_identifier)) <= 4:
        train = get_train_by_id(int(train_identifier))
    else:
        train = get_train_by_number(str(train_identifier))

    if not train:
        return None

    train_id = train['id']
    route_stops = get_train_route(train_id)
    if not route_stops:
        return {'train': train, 'stops': [], 'status_info': None}

    # Fetch live status record
    status = fetch_one("SELECT * FROM train_live_status WHERE train_id = ?", (train_id,))
    if not status:
        # Default initialization
        status = {
            'current_station_code': route_stops[0]['station_code'],
            'next_station_code': route_stops[1]['station_code'] if len(route_stops) > 1 else route_stops[0]['station_code'],
            'delay_minutes': 0,
            'current_status': 'ON_TIME',
            'last_updated': 'Just now'
        }

    curr_code = status['current_station_code']
    delay = status['delay_minutes']

    # Find sequence index of current station
    curr_seq = 1
    for stop in route_stops:
        if stop['station_code'] == curr_code:
            curr_seq = stop['stop_sequence']
            break

    # Build timeline progression
    timeline = []
    total_dist = route_stops[-1]['distance_km'] if route_stops else 0
    covered_dist = 0

    for stop in route_stops:
        seq = stop['stop_sequence']
        scheduled_arr = stop['scheduled_arrival']
        scheduled_dep = stop['scheduled_departure']
        estimated_arr = add_minutes_to_time(scheduled_arr, delay) if scheduled_arr != '--' else '--'
        estimated_dep = add_minutes_to_time(scheduled_dep, delay) if scheduled_dep != '--' else '--'

        if seq < curr_seq:
            state = 'DEPARTED'
            icon = '[DONE]'
        elif seq == curr_seq:
            state = 'AT_STATION' if status['current_status'] in ('ARRIVED', 'ON_TIME') else 'DEPARTED'
            icon = '[NOW]'
            covered_dist = stop['distance_km']
        else:
            state = 'UPCOMING'
            icon = '[WAIT]'

        timeline.append({
            'sequence': seq,
            'station_code': stop['station_code'],
            'station_name': stop['station_name'],
            'city': stop['city'],
            'distance_km': stop['distance_km'],
            'scheduled_arrival': scheduled_arr,
            'scheduled_departure': scheduled_dep,
            'estimated_arrival': estimated_arr,
            'estimated_departure': estimated_dep,
            'platform': stop['platform_number'],
            'state': state,
            'icon': icon
        })

    # Render ASCII visual journey map
    # e.g.: [DONE: NDLS] ---> [*CURRENT: GZB (+15m)*] ---> [WAIT: ALJN] ---> [WAIT: CNB]
    journey_bar_elements = []
    for item in timeline:
        code = item['station_code']
        if item['state'] == 'DEPARTED':
            journey_bar_elements.append(f"[PASS {code}]")
        elif item['state'] == 'AT_STATION':
            if delay > 0:
                journey_bar_elements.append(f"[*CURRENT: {code} (+{delay}m)*]")
            else:
                journey_bar_elements.append(f"[*CURRENT: {code} (On Time)*]")
        else:
            journey_bar_elements.append(f"[NEXT {code}]")

    journey_map = " ---> ".join(journey_bar_elements)

    return {
        'train': train,
        'current_status': status['current_status'],
        'delay_minutes': delay,
        'current_station': curr_code,
        'next_station': status['next_station_code'],
        'last_updated': status['last_updated'],
        'total_distance_km': total_dist,
        'distance_covered_km': covered_dist,
        'progress_percentage': round((covered_dist / total_dist * 100), 1) if total_dist > 0 else 0,
        'timeline': timeline,
        'journey_map': journey_map
    }


def update_train_live_status(train_id: int, current_station_code: str,
                             next_station_code: str = None, delay_minutes: int = 0,
                             current_status: str = 'ON_TIME') -> tuple:
    """
    Staff / Admin tool: Update train live location, next station, delay, and operational status.
    """
    curr = current_station_code.strip().upper()
    route = get_train_route(train_id)
    if not route:
        return False, "Train route not configured."

    # Validate that current station is on route
    valid_codes = [r['station_code'] for r in route]
    if curr not in valid_codes:
        return False, f"Station '{curr}' is not on the route for this train."

    # Determine next station automatically if omitted
    if not next_station_code:
        idx = valid_codes.index(curr)
        next_station_code = valid_codes[idx + 1] if idx + 1 < len(valid_codes) else curr

    next_code = next_station_code.strip().upper()

    try:
        execute_query(
            """
            INSERT INTO train_live_status (train_id, current_station_code, next_station_code,
                                           delay_minutes, current_status, last_updated)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(train_id) DO UPDATE SET
                current_station_code = excluded.current_station_code,
                next_station_code = excluded.next_station_code,
                delay_minutes = excluded.delay_minutes,
                current_status = excluded.current_status,
                last_updated = CURRENT_TIMESTAMP
            """,
            (train_id, curr, next_code, int(delay_minutes), current_status)
        )
        return True, f"Live status updated: Train at {curr}, Delay: {delay_minutes} min ({current_status})."
    except Exception as e:
        return False, f"Failed to update status: {str(e)}"


def get_station_live_board(station_code: str) -> list:
    """
    Live Station Enquiry: Show all trains arriving or departing at a specific station.
    Includes scheduled time, platform, live delay, and current status.
    """
    code = station_code.strip().upper()
    sql = """
    SELECT
        t.train_number,
        t.train_name,
        t.train_type,
        r.stop_sequence,
        r.scheduled_arrival,
        r.scheduled_departure,
        r.platform_number,
        COALESCE(tls.delay_minutes, 0) as delay_minutes,
        COALESCE(tls.current_status, 'ON_TIME') as current_status,
        COALESCE(tls.current_station_code, 'N/A') as current_location
    FROM routes r
    JOIN trains t ON r.train_id = t.id
    LEFT JOIN train_live_status tls ON t.id = tls.train_id
    WHERE r.station_code = ?
      AND t.status = 'ACTIVE'
    ORDER BY r.scheduled_departure ASC
    """
    board = fetch_all(sql, (code,))
    for item in board:
        delay = item['delay_minutes']
        item['expected_arrival'] = add_minutes_to_time(item['scheduled_arrival'], delay) if item['scheduled_arrival'] != '--' else '--'
        item['expected_departure'] = add_minutes_to_time(item['scheduled_departure'], delay) if item['scheduled_departure'] != '--' else '--'
    return board
