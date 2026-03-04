import os
import sqlite3
import random
import time
from datetime import date, datetime, timedelta, timezone
from typing import Optional, List, Dict, Any, Tuple
from faker import Faker

fake = Faker()

AIRPORTS = [
    ("DXB", "Dubai International Airport", "Dubai", "UAE", "Asia/Dubai"),
    ("AUH", "Abu Dhabi International Airport", "Abu Dhabi", "UAE", "Asia/Dubai"),
    ("JFK", "John F. Kennedy International Airport", "New York", "USA", "America/New_York"),
    ("LHR", "Heathrow Airport", "London", "UK", "Europe/London"),
    ("CDG", "Charles de Gaulle Airport", "Paris", "France", "Europe/Paris"),
    ("HND", "Haneda Airport", "Tokyo", "Japan", "Asia/Tokyo"),
    ("SYD", "Sydney Airport", "Sydney", "Australia", "Australia/Sydney"),
    ("SIN", "Changi Airport", "Singapore", "Singapore", "Asia/Singapore"),
]

AIRCRAFT_MODELS = [
    ("A6-ELA", "A380-800", "Airbus", 519, "2015-03-15", "2023-05-20", "Active"),
    ("A6-EBA", "787-9 Dreamliner", "Boeing", 290, "2018-07-22", "2023-06-10", "Active"),
    ("A6-ECB", "A350-900", "Airbus", 315, "2019-11-05", "2023-04-15", "Active"),
    ("A6-EDD", "777-300ER", "Boeing", 360, "2017-09-18", "2023-06-01", "Active"),
    ("A6-EEF", "A320neo", "Airbus", 174, "2020-02-10", "2023-05-28", "Active"),
    ("A6-EGA", "787-10 Dreamliner", "Boeing", 330, "2021-08-12", "2023-06-05", "Active"),
    ("A6-EHA", "A380-800", "Airbus", 519, "2016-05-30", "2023-04-30", "Maintenance"),
]

ROUTES = [
    ("DXB", "JFK"), ("JFK", "DXB"),
    ("DXB", "LHR"), ("LHR", "DXB"),
    ("DXB", "CDG"), ("CDG", "DXB"),
    ("DXB", "HND"), ("HND", "DXB"),
    ("DXB", "SYD"), ("SYD", "DXB"),
    ("DXB", "SIN"), ("SIN", "DXB"),
    ("AUH", "LHR"), ("LHR", "AUH"),
    ("AUH", "JFK"), ("JFK", "AUH"),
]

FLIGHT_STATUSES = ["Scheduled", "Boarding", "In Flight", "Landed", "Cancelled", "Delayed"]
BOOKING_STATUSES = ["Confirmed", "Cancelled", "Checked-In", "Boarded"]
TICKET_STATUSES = ["Open", "In Progress", "Resolved", "Closed"]
TRAVEL_CLASSES = ["Economy", "Business"] 

def _utc_str(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def _enable_foreign_keys(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA foreign_keys = ON;")

def init_air_db(db_path: str, reset: bool = True, preview: bool = False) -> None:
    parent_dir = os.path.dirname(db_path)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)

    if reset and os.path.exists(db_path):
        os.remove(db_path)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    _enable_foreign_keys(conn)

    try:
        print("Creating Light Airlines database...")
        for t in ["tickets", "bookings", "flights", "customers", "crew", "aircraft", "airports", "loyalty_program"]:
            cur.execute(f"DROP TABLE IF EXISTS {t}")

        cur.execute("""
        CREATE TABLE airports (
            airport_code TEXT PRIMARY KEY, airport_name TEXT NOT NULL, city TEXT NOT NULL,
            country TEXT NOT NULL, timezone TEXT NOT NULL)""")

        cur.execute("""
        CREATE TABLE aircraft (
            aircraft_id TEXT PRIMARY KEY, model TEXT NOT NULL, manufacturer TEXT NOT NULL,
            capacity INTEGER NOT NULL CHECK (capacity > 0), first_flight_date DATE NOT NULL,
            last_maintenance DATE NOT NULL, status TEXT CHECK (status IN ('Active', 'Maintenance', 'Retired')))""")

        cur.execute("""
        CREATE TABLE crew (
            crew_id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, position TEXT NOT NULL,
            nationality TEXT NOT NULL, hire_date DATE NOT NULL, base_airport TEXT NOT NULL,
            FOREIGN KEY (base_airport) REFERENCES airports(airport_code))""")

        cur.execute("""
        CREATE TABLE customers (
            customer_id INTEGER PRIMARY KEY AUTOINCREMENT, first_name TEXT NOT NULL, last_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL, phone TEXT NOT NULL, passport_number TEXT UNIQUE,
            nationality TEXT NOT NULL, date_of_birth DATE NOT NULL,
            loyalty_tier TEXT CHECK (loyalty_tier IN ('Basic', 'Silver', 'Gold', 'Platinum')))""")

        cur.execute("""
        CREATE TABLE loyalty_program (
            loyalty_id INTEGER PRIMARY KEY AUTOINCREMENT, customer_id INTEGER NOT NULL, points_balance INTEGER NOT NULL DEFAULT 0,
            join_date DATE NOT NULL, last_activity DATE NOT NULL, FOREIGN KEY (customer_id) REFERENCES customers(customer_id))""")

        cur.execute("""
        CREATE TABLE flights (
            flight_number TEXT PRIMARY KEY, departure_airport TEXT NOT NULL, arrival_airport TEXT NOT NULL,
            departure_city TEXT NOT NULL, arrival_city TEXT NOT NULL, departure_time DATETIME NOT NULL,
            arrival_time DATETIME NOT NULL, aircraft_id TEXT NOT NULL, captain_id INTEGER NOT NULL,
            first_officer_id INTEGER NOT NULL, flight_attendant_id INTEGER NOT NULL,
            status TEXT CHECK (status IN ('Scheduled', 'Boarding', 'In Flight', 'Landed', 'Cancelled', 'Delayed')),
            economy_price REAL NOT NULL CHECK (economy_price >= 0), business_price REAL NOT NULL CHECK (business_price >= 0),
            FOREIGN KEY (departure_airport) REFERENCES airports(airport_code), FOREIGN KEY (arrival_airport) REFERENCES airports(airport_code),
            FOREIGN KEY (aircraft_id) REFERENCES aircraft(aircraft_id), FOREIGN KEY (captain_id) REFERENCES crew(crew_id),
            FOREIGN KEY (first_officer_id) REFERENCES crew(crew_id), FOREIGN KEY (flight_attendant_id) REFERENCES crew(crew_id))""")

        cur.execute("""
        CREATE TABLE bookings (
            booking_id INTEGER PRIMARY KEY AUTOINCREMENT, customer_id INTEGER NOT NULL, flight_number TEXT NOT NULL,
            booking_date DATETIME NOT NULL, seat_number TEXT NOT NULL, travel_class TEXT CHECK (travel_class IN ('Economy', 'Business', 'First')),
            price_paid REAL NOT NULL CHECK (price_paid >= 0), status TEXT CHECK (status IN ('Confirmed', 'Cancelled', 'Checked-In', 'Boarded')),
            special_requests TEXT, FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
            FOREIGN KEY (flight_number) REFERENCES flights(flight_number), UNIQUE (flight_number, seat_number))""")

        cur.execute("""
        CREATE TABLE tickets (
            ticket_id INTEGER PRIMARY KEY AUTOINCREMENT, customer_id INTEGER NOT NULL, booking_id INTEGER,
            problem TEXT NOT NULL, status TEXT CHECK (status IN ('Open', 'In Progress', 'Resolved', 'Closed')) NOT NULL,
            created_date DATETIME NOT NULL, last_update DATETIME NOT NULL, FOREIGN KEY (customer_id) REFERENCES customers(customer_id))""")

        cur.execute("CREATE INDEX IF NOT EXISTS idx_flights_no ON flights(flight_number)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_flights_route_time ON flights(departure_airport, arrival_airport, departure_time)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_bookings_cust ON bookings(customer_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_bookings_flight ON bookings(flight_number)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_tickets_cust ON tickets(customer_id)")

        cur.executemany("INSERT INTO airports VALUES (?, ?, ?, ?, ?)", AIRPORTS)
        cur.executemany("INSERT INTO aircraft VALUES (?, ?, ?, ?, ?, ?, ?)", AIRCRAFT_MODELS)

        crew_members = []
        bases = [a[0] for a in AIRPORTS if a[0] in ("DXB", "AUH", "JFK", "LHR")]
        for _ in range(30):
            crew_members.append((fake.name(), random.choice(["Captain", "First Officer", "Flight Attendant", "Senior Flight Attendant"]), fake.country(), fake.date_between(start_date='-10y', end_date='-1y').strftime("%Y-%m-%d"), random.choice(bases)))
        cur.executemany("INSERT INTO crew (name, position, nationality, hire_date, base_airport) VALUES (?, ?, ?, ?, ?)", crew_members)

        customers = []
        for _ in range(200):
            customers.append((fake.first_name(), fake.last_name(), fake.unique.email(), fake.phone_number(), fake.unique.passport_number(), fake.country(), fake.date_of_birth(minimum_age=18, maximum_age=80).strftime("%Y-%m-%d"), random.choice(["Basic", "Silver", "Gold", "Platinum"])))
        cur.executemany("INSERT INTO customers (first_name, last_name, email, phone, passport_number, nationality, date_of_birth, loyalty_tier) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", customers)

        cust_ids = [row[0] for row in cur.execute("SELECT customer_id FROM customers").fetchall()]
        loyalty_rows = []
        for cid in cust_ids:
            jd = fake.date_between(start_date='-5y', end_date=date.today())
            loyalty_rows.append((cid, random.randint(0, 50000), jd.strftime("%Y-%m-%d"), fake.date_between(start_date=jd, end_date=date.today()).strftime("%Y-%m-%d")))
        cur.executemany("INSERT INTO loyalty_program (customer_id, points_balance, join_date, last_activity) VALUES (?, ?, ?, ?)", loyalty_rows)

        flight_numbers = [f"LA{i:03d}" for i in range(1, 101)]
        captains = [row[0] for row in cur.execute("SELECT crew_id FROM crew WHERE position = 'Captain'").fetchall()]
        first_officers = [row[0] for row in cur.execute("SELECT crew_id FROM crew WHERE position = 'First Officer'").fetchall()]
        attendants = [row[0] for row in cur.execute("SELECT crew_id FROM crew WHERE position IN ('Flight Attendant','Senior Flight Attendant')").fetchall()]
        code_to_city = {code: city for (code, _name, city, _country, _tz) in AIRPORTS}

        flights = []
        for fn in flight_numbers:
            dep, arr = random.choice(ROUTES)
            dep_time = fake.date_time_between(start_date='-30d', end_date='now', tzinfo=timezone.utc)
            duration = timedelta(hours=14) if "JFK" in (dep, arr) else timedelta(hours=10) if "HND" in (dep, arr) else timedelta(hours=13) if "SYD" in (dep, arr) else timedelta(hours=random.randint(4, 8))
            arr_time = dep_time + duration
            econ_price = random.randint(300, 1500)
            flights.append((fn, dep, arr, code_to_city.get(dep, dep), code_to_city.get(arr, arr), _utc_str(dep_time), _utc_str(arr_time), random.choice(AIRCRAFT_MODELS)[0], random.choice(captains), random.choice(first_officers), random.choice(attendants), random.choices(FLIGHT_STATUSES, weights=[70, 5, 5, 15, 2, 3])[0], float(econ_price), float(econ_price * random.uniform(2.5, 4.0))))
        cur.executemany("INSERT INTO flights (flight_number, departure_airport, arrival_airport, departure_city, arrival_city, departure_time, arrival_time, aircraft_id, captain_id, first_officer_id, flight_attendant_id, status, economy_price, business_price) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", flights)

        used_seats = {fn: set() for fn in flight_numbers}
        bookings = []
        for _ in range(500):
            fn = random.choice(flight_numbers)
            seat = f"{random.randint(1, 50)}{random.choice('ABCDEF')}"
            while seat in used_seats[fn]: seat = f"{random.randint(1, 50)}{random.choice('ABCDEF')}"
            used_seats[fn].add(seat)
            
            econ, biz = cur.execute("SELECT economy_price, business_price FROM flights WHERE flight_number = ?", (fn,)).fetchone()
            tclass = random.choices(TRAVEL_CLASSES, weights=[80, 20])[0]
            price = float(econ if tclass == "Economy" else biz) * (random.uniform(0.7, 0.9) if random.random() < 0.2 else 1)
            special = random.choice(["Vegetarian meal", "Wheelchair assistance", "Extra legroom requested", "Baby bassinet", "Kosher meal"]) if random.random() < 0.15 else None
            bookings.append((random.choice(cust_ids), fn, _utc_str(fake.date_time_between(start_date='-60d', end_date='now', tzinfo=timezone.utc)), seat, tclass, round(price, 2), random.choices(BOOKING_STATUSES, weights=[70, 10, 15, 5])[0], special))
        cur.executemany("INSERT INTO bookings (customer_id, flight_number, booking_date, seat_number, travel_class, price_paid, status, special_requests) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", bookings)

        problems = ["My flight was delayed", "I need to change my booking dates", "My luggage was lost", "I was charged twice", "Refund requested"]
        some_custs = random.sample(cust_ids, min(5, len(cust_ids)))
        some_bids = [row[0] for row in cur.execute("SELECT booking_id FROM bookings LIMIT 5").fetchall()]
        for i in range(len(some_custs)):
            created = fake.date_time_between(start_date='-30d', end_date='now', tzinfo=timezone.utc)
            cur.execute("INSERT INTO tickets (customer_id, booking_id, problem, status, created_date, last_update) VALUES (?, ?, ?, ?, ?, ?)", (some_custs[i], some_bids[i] if i < len(some_bids) else None, problems[i], random.choices(TICKET_STATUSES, weights=[20, 30, 40, 10])[0], _utc_str(created), _utc_str(fake.date_time_between(start_date=created, end_date='now', tzinfo=timezone.utc))))
        
        conn.commit()
    finally:
        conn.close()
        time.sleep(0.5)

# Export the dynamic path for the rest of the application
DB_PATH = os.path.join(os.getcwd(), "data", "airline.db")