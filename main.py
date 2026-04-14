import cv2
import json
import os
import networkx as nx
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from google import genai
from google.genai import types
from PIL import Image

# ==========================================
# 1. NETWORK & TIMEZONE SETUP
# ==========================================
# Manual IST setup to avoid Windows 'tzdata' errors
IST = timezone(timedelta(hours=5, minutes=30))

G = nx.Graph()
RAILWAY_LINES = {
    "WESTERN": ["CHURCHGATE", "MARINE LINES", "CHARNI ROAD", "GRANT ROAD", "MUMBAI CENTRAL", "MAHALAXMI", "LOWER PAREL", "PRABHADEVI", "DADAR", "MATUNGA ROAD", "MAHIM", "BANDRA", "KHAR ROAD", "SANTACRUZ", "VILE PARLE", "ANDHERI", "BORIVALI", "VIRAR"],
    "CENTRAL": ["CSMT", "MASJID", "SANDHURST ROAD", "BYCULLA", "CHINCHPOKLI", "CURREY ROAD", "PAREL", "DADAR", "MATUNGA", "SION", "KURLA", "VIDYAVIHAR", "GHATKOPAR", "THANE", "DOMBIVLI", "KALYAN"],
    "HARBOUR": ["CSMT", "MASJID", "SANDHURST ROAD", "WADALA ROAD", "KURLA", "CHEMBUR", "VASHI", "NERUL", "BELAPUR", "PANVEL"],
    "TRANS_HARBOUR": ["THANE", "VASHI", "PANVEL"]
}

for line in RAILWAY_LINES.values():
    for i in range(len(line)-1):
        G.add_edge(line[i], line[i+1])

ALL_STATIONS = [s for line in RAILWAY_LINES.values() for s in line]

# ==========================================
# 2. FAIL-FAST VALIDATION LOGIC
# ==========================================
def parse_strict_dt(dt_str):
    """Parses DD/MM/YYYY HH:MM and returns an IST-aware datetime object."""
    try:
        # Tries standard format first
        dt = datetime.strptime(dt_str.strip(), "%d/%m/%Y %H:%M")
        return dt.replace(tzinfo=IST)
    except ValueError:
        return None

def validate_ticket(data, checker_loc):
    now_ist = datetime.now(IST)
    
    src = data.get("Source Station", "").upper()
    dest = data.get("Destination Station", "").upper()
    cat = data.get("Ticket Category", "")
    dt_str = data.get("Booking Date & Time", "")

    # Clean OCR noise
    if src == "BADAR": src = "DADAR"
    if dest == "BADAR": dest = "DADAR"

    # --- STEP 1: DATE & TIME CHECK ---
    ticket_dt = parse_strict_dt(dt_str)
    if not ticket_dt:
        return False, f"❌ OCR ERROR: Unreadable date/time string '{dt_str}'"

    # A. Date Check: Must be today
    if ticket_dt.date() != now_ist.date():
        return False, f"❌ INVALID DATE: Ticket is for {ticket_dt.strftime('%d/%m/%Y')}. Today is {now_ist.strftime('%d/%m/%Y')}."

    # B. 1-Hour Rule: Must be within 60 minutes (Journey Tickets only)
    if "Journey" in cat:
        expiry_time = ticket_dt + timedelta(hours=1)
        if now_ist > expiry_time:
            return False, f"❌ EXPIRED: Ticket valid until {expiry_time.strftime('%H:%M')} IST."
        
        # Future-date guard
        if now_ist < ticket_dt - timedelta(minutes=2):
            return False, "❌ ERROR: Ticket is from the future. Check system clock."

    # --- STEP 2: LOCATION CHECK ---
    try:
        path = nx.shortest_path(G, src, dest)
        if checker_loc not in path:
            return False, f"❌ WRONG ROUTE: {checker_loc} is not on the way from {src} to {dest}."
    except Exception:
        return False, f"❌ ROUTE ERROR: Stations {src} or {dest} not found in database."

    return True, f"✅ VALID: {cat} ({src} -> {dest}). Booked at {ticket_dt.strftime('%H:%M')} IST."

# ==========================================
# 3. AI & MAIN EXECUTION
# ==========================================
def process_scan(frame, checker_loc):
    # ... previous code ...

    # 1. Shrink further to 480p - enough for OCR but uses 40% fewer tokens
    small_frame = cv2.resize(frame, (480, 360))
    
    # 2. Convert to Grayscale to reduce data complexity
    gray = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)
    
    # 3. Increase contrast so the AI can still read the gray image
    enhanced = cv2.convertScaleAbs(gray, alpha=1.8, beta=10)
    
    pil_img = Image.fromarray(enhanced) # PIL handles grayscale fine

    # ... rest of your code ...

def main():
    print("="*40)
    print("MUMBAI LOCAL AI VALIDATOR - TC VERSION")
    print("="*40)
    
    checker_station = input("Enter your Current Station (e.g., MATUNGA): ").strip().upper()
    if checker_station not in ALL_STATIONS:
        print("Invalid station. Please use full names.")
        return

    cap = cv2.VideoCapture(0)
    print(f"\nSystem active at {checker_station}. Press SPACE to scan, 'q' to quit.")
    
    while True:
        ret, frame = cap.read()
        if not ret: break
        
        # Display info on screen
        cv2.putText(frame, f"TC AT: {checker_station}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.imshow("TC Handheld Scanner", frame)
        
        key = cv2.waitKey(1)
        if key == 32: # Space
            process_scan(frame, checker_station)
        elif key == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()