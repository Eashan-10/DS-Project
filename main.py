from flask import Flask, request, jsonify
import cv2
import numpy as np
import networkx as nx
from datetime import datetime, timedelta, timezone
from flask_cors import CORS

# ✅ THIS LINKS YOUR PERFECTED PIPELINE TO THE BACKEND
from OCR import extract_ticket_data 

# ==========================================
# INIT
# ==========================================
app = Flask(__name__)
CORS(app)  # ✅ CORS is now active and will not be overwritten

IST = timezone(timedelta(hours=5, minutes=30))

# ==========================================
# GRAPH (ROUTE VALIDATION)
# ==========================================
G = nx.Graph()

RAILWAY_LINES = {
    "WESTERN": ["CHURCHGATE","MARINE LINES","CHARNI ROAD","GRANT ROAD","MUMBAI CENTRAL","MAHALAXMI","LOWER PAREL","PRABHADEVI","DADAR","MATUNGA ROAD","MAHIM","BANDRA","KHAR ROAD","SANTACRUZ","VILE PARLE","ANDHERI","BORIVALI","DAHISAR","VIRAR"],
    "CENTRAL": ["CSMT","MASJID","SANDHURST ROAD","BYCULLA","CHINCHPOKLI","CURREY ROAD","PAREL","DADAR","MATUNGA","SION","KURLA","VIDYAVIHAR","GHATKOPAR","THANE","DOMBIVLI","KALYAN"],
    "HARBOUR": ["CSMT","MASJID","SANDHURST ROAD","VADALA ROAD","KURLA","CHEMBUR","VASHI","NERUL","BELAPUR","PANVEL"],
    "TRANS_HARBOUR": ["THANE","VASHI","PANVEL"]
}

for line in RAILWAY_LINES.values():
    for i in range(len(line)-1):
        G.add_edge(line[i], line[i+1])

# ==========================================
# VALIDATION LOGIC
# ==========================================
def parse_dt(dt_str):
    """Tries multiple common date formats for both printed and digital tickets"""
    formats = [
        "%d/%m/%Y %H:%M",   # 28/04/2026 14:30
        "%d-%m-%Y %H:%M",   # 28-04-2026 14:30
        "%d/%m/%Y %I:%M %p",# 28/04/2026 02:30 PM
        "%d-%m-%Y %I:%M %p",# 28-04-2026 02:30 PM
        "%Y-%m-%d %H:%M:%S" # Database format
    ]
    for f in formats:
        try:
            return datetime.strptime(dt_str, f).replace(tzinfo=IST)
        except ValueError:
            continue
    return None

def parse_pass_date(d_str):
    """Tries multiple common date formats for Season Passes"""
    formats = [
        "%d-%m-%Y",   # 28-04-2026
        "%d/%m/%Y",   # 28/04/2026
        "%Y-%m-%d",   # 2026-04-28
        "%d.%m.%Y"    # 28.04.2026 (Sometimes OCR reads a dot instead of a dash)
    ]
    for f in formats:
        try:
            return datetime.strptime(d_str, f).date()
        except ValueError:
            continue
    return None

def validate_ticket(data):
    now = datetime.now(IST)

    src = str(data.get("Source Station", "")).upper().strip()
    dest = str(data.get("Destination Station", "")).upper().strip()
    cat = data.get("Ticket Category","")

    # ------------------------------------------
    # 1. CONDITIONAL DATE VALIDATION
    # ------------------------------------------
    if "Season Pass" in cat:
        valid_from_str = data.get("Valid From Date", "")
        valid_to_str = data.get("Valid To Date", "")
        
        # Guard against the OCR outputting 'Not Applicable' or missing data
        if valid_from_str == "Not Applicable" or valid_to_str == "Not Applicable":
            return False, "Season Pass dates not found"

        valid_from = parse_pass_date(valid_from_str)
        valid_to = parse_pass_date(valid_to_str)
        
        if not valid_from or not valid_to:
            return False, "Invalid Season Pass date format"
            
        if not (valid_from <= now.date() <= valid_to):
            return False, "Season Pass expired or not yet active"
            
    elif "Journey" in cat or "Return" in cat:
        dt = data.get("Booking Date & Time", "")
        
        if dt == "Not Applicable":
            return False, "Booking Date & Time not found"

        ticket_dt = parse_dt(dt)
        if not ticket_dt:
            return False, "Invalid Booking Date/Time format"
            
        if ticket_dt.date() != now.date():
            return False, "Ticket not valid for today"
            
        if "Journey" in cat:
            if now > ticket_dt + timedelta(hours=1):
                return False, "Journey Ticket expired (over 1 hour)"
    else:
        return False, "Unknown Ticket Category"

   # ------------------------------------------
    # 2. ROUTE VALIDATION
    # ------------------------------------------
    if not src or not dest:
        return False, "Station names missing from OCR"

    try:
        # Just verify that a valid path exists between the two stations
        path = nx.shortest_path(G, src, dest)
        
    except nx.NodeNotFound as e:
        # This will tell you exactly which station spelled wrong
        return False, f"Station not on map: {e}" 
    except Exception:
        return False, "Invalid or disconnected route"

    # Returns the dynamic category name to the frontend (e.g., "Valid Season Pass")
    return True, f"Valid {cat}"

# ==========================================
# API ROUTE (THIS LINKS FRONTEND TO YOUR OCR.py)
# ==========================================
@app.route("/scan-and-verify", methods=["POST"])
def scan_and_verify():
    try:
        if "image" not in request.files:
            return jsonify({
                "status": "invalid",
                "message": "No image provided",
                "extracted": {}
            })

        file = request.files["image"]

        npimg = np.frombuffer(file.read(), np.uint8)
        frame = cv2.imdecode(npimg, cv2.IMREAD_COLOR)

        # ✅ THIS NOW CALLS YOUR OCR.py FILE
        data = extract_ticket_data(frame)

        if not data:
            return jsonify({
                "status": "invalid",
                "message": "OCR failed",
                "extracted": {}
            })

        valid, msg = validate_ticket(data)

        return jsonify({
            "status": "valid" if valid else "invalid",
            "message": msg,
            "extracted": data
        })

    except Exception as e:
        print("🔥 SERVER ERROR:", e)

        return jsonify({
            "status": "invalid",
            "message": "Internal server error",
            "extracted": {}
        })

# ==========================================
# RUN SERVER
# ==========================================
if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0') # host='0.0.0.0' allows mobile connection