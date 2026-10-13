# Indian Railways - Train Management System (TMS)

A complete, production-grade, modular CLI-based **Train Management System** built with Python and SQLite. The system implements role-based portals for **Passengers**, **Railway Staff**, and **System Administrators**, alongside a **Public/Guest** enquiry desk.

---

## 📁 Project Structure

```text
d:/train management system/
├── main.py                 # CLI entry point with interactive role-based menus
├── database.py             # SQLite schema, connection manager & foreign key enforcement
├── seed_data.py            # Sample data loader (stations, trains, routes, staff, food menu, users)
├── test_system.py          # Automated verification test suite covering all modules
├── README.md               # Complete project documentation and user manual
├── data/
│   └── train_system.db     # Auto-created SQLite database
└── modules/
    ├── __init__.py         # Package initializer
    ├── auth.py             # User registration, authentication, PBKDF2-SHA256 password hashing
    ├── trains.py           # Stations, trains, coach classes, multi-station route search & fares
    ├── booking.py          # Seat availability, ticket booking, PNR allocation, cancellation & refunds
    ├── payment.py          # Payment gateway simulation, transaction logging, receipts, refunds
    ├── schedule.py         # Live train tracking, station-by-station progress bar, delays, station boards
    ├── employees.py        # Staff management: Admin CRUD for staff, roles, departments, shift schedules
    ├── food.py             # Pantry & food delivery: menu browsing, order by PNR/seat, kitchen delivery status
    ├── complaints.py       # Grievance handling: lodge complaint, track status, staff/admin resolution
    └── reports.py          # Analytics dashboard: revenue, occupancy rates, popular routes, system stats
```

---

## 🔑 Pre-Seeded Accounts

| Role | Username | Password | Notes |
| :--- | :--- | :--- | :--- |
| **Admin** | `admin` | `admin123` | Full access to trains, stations, staff onboarding, analytics |
| **Staff (Operations)** | `staff1` | `staff123` | Station master / delays / grievance redressal desk |
| **Staff (Pantry)** | `staff2` | `staff123` | Pantry supervisor / food order fulfillment desk |
| **Passenger** | `passenger1` | `pass123` | Booking tickets, tracking, food ordering, complaints |
| **Passenger** | `priya_p` | `pass123` | Pre-booked passenger account |

---

## 🚀 Quick Start

### 1. Run the Interactive CLI Application
```powershell
python main.py
```

### 2. Run the Automated Test Suite
```powershell
python test_system.py
```

### 3. Re-seed or Reset Database
```powershell
python seed_data.py
```

---

## 🌟 Key Features

### 1. Role-Based Portals & Authentication
- **PBKDF2-HMAC-SHA256 Cryptographic Hashing**: Secure password storage with unique per-user salts.
- **Passenger Registration & Login**: Validated email, 10-digit mobile, and username uniqueness.
- **Role Permissions**: Seamless routing to Passenger, Staff, or Admin dashboards upon login.

### 2. Proper Real-Time Train Tracking (`modules/schedule.py`)
- **Station-by-Station Visual Progress Bar**:
  ```text
  [PASS NDLS] ---> [PASS AGC] ---> [NEXT GWL] ---> [NEXT VGLJ] ---> [NEXT BPL]
  ```
- **Live Delays & Platforms**: Live delay calculations (in minutes), platform assignments, and estimated arrival/departure times.
- **Station Live Board**: View all trains arriving or departing at any station (e.g. `NDLS`, `CSMT`, `AGC`).
- **Staff Control**: Staff and Station Masters can update live location and report delays directly.

### 3. Seat Reservation & PNR Allocation (`modules/booking.py`)
- **Dynamic Fare Engine**: Calculates fares based on train type (`Vande Bharat`, `Rajdhani`, `Shatabdi`, `Superfast`, `Express`), distance, and coach class (`1A`, `2A`, `3A`, `SL`, `CC`).
- **10-Digit Unique PNR Generation**: Generates official Indian Railways-style 10-digit PNR.
- **Automatic Seat Allocation**: Assigns Coach and Berth preferences (e.g., `B1-14 (Lower Berth)`).
- **Cancellation & Refunds**: Calculates cancellation deductions (20%) and issues immediate automated refunds (80%) linked to transaction history.

### 4. In-Train Pantry & Food Delivery System (`modules/food.py`)
- **Seat-Side Delivery**: Passengers order meals, snacks, and beverages linked to their confirmed PNR.
- **Pantry Menu**: Features categorized items (Meals, Breakfast, Snacks, Beverages, Dessert).
- **Kitchen Order Lifecycle**:
  `PLACED` &rarr; `PREPARING` &rarr; `OUT_FOR_DELIVERY` &rarr; `DELIVERED`.
- **Catering Dispatch Desk**: Railway staff update preparation status and delivery to passengers.

### 5. Staff & Employee Management (`modules/employees.py`)
- **Admin Onboarding**: Admin can hire/onboard new employees with auto-generated Employee IDs (`EMP-XXXX`).
- **Department & Shift Allocation**: Supports Operations, Ticketing, Catering, Maintenance, and Management.
- **Staff Login Generation**: Automatically creates linked staff credentials during employee onboarding.
- **Staff Self-Service**: Staff can view their shift timings, duties, and assigned train/station.

### 6. Passenger Grievance Redressal (`modules/complaints.py`)
- Lodge complaints across categories: Cleanliness, Food Quality, Punctuality, Staff Behavior, Ticketing, and Other.
- Generates unique tracking ticket numbers (`CMP-2026-XXXX`).
- Staff/Admin workspace to investigate and record resolution responses.

### 7. Executive Analytics & Reports Dashboard (`modules/reports.py`)
- **Financial Breakdown**: Gross Ticket Sales, Pantry Revenue, Refunds Issued, and Net Operating Revenue.
- **Occupancy & Volume**: Active trains, stations, total passengers travelled, and bookings.
- **Top Trains & Routes**: Identifies highest revenue routes and most popular origin-destination pairs.
- **Workforce Metrics**: Staff headcount and monthly payroll by department.
