import random
from datetime import datetime
from typing import Optional, List, Dict, Any
import psycopg2
from psycopg2.extras import RealDictCursor
from langchain_core.tools import tool
from src.database import DB_URL

def _get_connection():
    # RealDictCursor ensures queries return dictionaries instead of raw tuples, just like sqlite3.Row
    return psycopg2.connect(DB_URL, cursor_factory=RealDictCursor)

def _utcnow_str() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

def _find_free_seat(cur, flight_number: str) -> str:
    cur.execute("SELECT seat_number FROM bookings WHERE flight_number = %s", (flight_number,))
    used = {r["seat_number"] for r in cur.fetchall()}
    for _ in range(200):
        seat = f"{random.randint(1,50)}{random.choice('ABCDEF')}"
        if seat not in used: return seat
    return f"{random.randint(1,50)}{random.choice('ABCDEF')}"

@tool
def query_flights_by_city(from_city: str, to_city: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Query flights between two cities."""
    conn = _get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM flights WHERE departure_city = %s AND arrival_city = %s ORDER BY departure_time LIMIT %s",
                (from_city.strip().title(), to_city.strip().title(), limit)
            )
            return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()

@tool
def seats_remaining(flight_number: str) -> Optional[Dict[str, Any]]:
    """Check how many seats are remaining on a specific flight."""
    conn = _get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT capacity FROM flights f JOIN aircraft ac ON f.aircraft_id = ac.aircraft_id WHERE f.flight_number = %s", (flight_number,))
            row = cur.fetchone()
            if not row: return None
            
            cap = int(row["capacity"])
            econ_cap, biz_cap = int(round(cap * 0.85)), cap - int(round(cap * 0.85))
            
            cur.execute("SELECT travel_class, COUNT(*) AS sold FROM bookings WHERE flight_number = %s AND status != 'Cancelled' GROUP BY travel_class", (flight_number,))
            sold = cur.fetchall()
            sold_map = {r["travel_class"]: int(r["sold"]) for r in sold}
            
            return {"economy_remaining": max(econ_cap - sold_map.get("Economy", 0), 0), "business_remaining": max(biz_cap - sold_map.get("Business", 0), 0)}
    finally:
        conn.close()

@tool
def get_customer(email: Optional[str] = None, phone: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Resolve a customer by email or phone number to get their customer_id."""
    conn = _get_connection()
    try:
        with conn.cursor() as cur:
            if email:
                cur.execute("SELECT * FROM customers WHERE LOWER(email) = LOWER(%s)", (email.strip(),))
                row = cur.fetchone()
                if row: return dict(row)
            if phone:
                cur.execute("SELECT * FROM customers WHERE phone = %s", (phone.strip(),))
                row = cur.fetchone()
                if row: return dict(row)
            return None
    finally:
        conn.close()

@tool
def get_booking(booking_id: Optional[int] = None, customer_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """Fetch booking details using a booking_id or customer_id."""
    conn = _get_connection()
    try:
        with conn.cursor() as cur:
            if booking_id:
                cur.execute("SELECT * FROM bookings WHERE booking_id = %s", (int(booking_id),))
                row = cur.fetchone()
                return dict(row) if row else None
            if customer_id:
                cur.execute("SELECT * FROM bookings WHERE customer_id = %s ORDER BY booking_date DESC LIMIT 1", (int(customer_id),))
                row = cur.fetchone()
                return dict(row) if row else None
            return None
    finally:
        conn.close()

@tool
def list_airports(limit: int = 10) -> List[Dict[str, Any]]:
    """Get a list of supported airports and cities."""
    conn = _get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT airport_code, airport_name, city, country FROM airports LIMIT %s", (limit,))
            return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()

@tool
def create_booking_basic(customer_id: int, flight_number: str, travel_class: str, special_requests: Optional[str] = None) -> Dict[str, Any]:
    """Create a minimal booking record for a user. MUST provide customer_id, flight_number, and travel_class ('Economy' or 'Business')."""
    conn = _get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT economy_price, business_price FROM flights WHERE flight_number = %s", (flight_number,))
            row = cur.fetchone()
            unit_price = float(row["economy_price"] if travel_class.capitalize() == "Economy" else row["business_price"])
            seat = _find_free_seat(cur, flight_number)
            ts = _utcnow_str()
            
            # RETURNING id is standard in Postgres to get the inserted ID
            cur.execute(
                "INSERT INTO bookings (customer_id, flight_number, booking_date, seat_number, travel_class, price_paid, status, special_requests) VALUES (%s, %s, %s, %s, %s, %s, 'Confirmed', %s) RETURNING booking_id", 
                (int(customer_id), flight_number, ts, seat, travel_class.capitalize(), unit_price, special_requests)
            )
            booking_id = cur.fetchone()["booking_id"]
            conn.commit()
            
            return {"created": True, "booking_id": booking_id, "seat_number": seat, "status": "Confirmed"}
    finally:
        conn.close()

@tool
def cancel_booking_basic(booking_id: int) -> Dict[str, Any]:
    """Cancel a booking by changing its status to 'Cancelled'."""
    conn = _get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE bookings SET status = 'Cancelled' WHERE booking_id = %s", (int(booking_id),))
            conn.commit()
            return {"updated": True, "new_status": "Cancelled"}
    finally:
        conn.close()

@tool
def create_ticket_basic(customer_id: int, problem: str, booking_id: Optional[int] = None) -> Dict[str, Any]:
    """Create a support/complaint ticket for a customer."""
    conn = _get_connection()
    try:
        with conn.cursor() as cur:
            ts = _utcnow_str()
            cur.execute(
                "INSERT INTO tickets (customer_id, booking_id, problem, status, created_date, last_update) VALUES (%s, %s, %s, 'Open', %s, %s) RETURNING ticket_id", 
                (int(customer_id), booking_id, problem, ts, ts)
            )
            ticket_id = cur.fetchone()["ticket_id"]
            conn.commit()
            return {"created": True, "ticket_id": ticket_id, "status": "Open"}
    finally:
        conn.close()

db_tools_list = [
    query_flights_by_city, seats_remaining, get_customer, 
    get_booking, list_airports, create_booking_basic, 
    cancel_booking_basic, create_ticket_basic
]