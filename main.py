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
    "WESTERN": ["CHURCHGATE","MARINE LINES","CHARNI ROAD","GRANT ROAD","MUMBAI CENTRAL","MAHALAXMI","LOWER PAREL","PRABHADEVI","DADAR","MATUNGA ROAD","MAHIM","BANDRA","KHAR ROAD","SANTACRUZ","VILE PARLE","ANDHERI","BORIVALI","VIRAR"],
    "CENTRAL": ["CSMT","MASJID","SANDHURST ROAD","BYCULLA","CHINCHPOKLI","CURREY ROAD","PAREL","DADAR","MATUNGA","SION","KURLA","VIDYAVIHAR","GHATKOPAR","THANE","DOMBIVLI","KALYAN"],
    "HARBOUR": ["CSMT","MASJID","SANDHURST ROAD","WADALA ROAD","KURLA","CHEMBUR","VASHI","NERUL","BELAPUR","PANVEL"],
    "TRANS_HARBOUR": ["THANE","VASHI","PANVEL"]
}

for line in RAILWAY_LINES.values():
    for i in range(len(line)-1):
        G.add_edge(line[i], line[i+1])

# ==========================================
# VALIDATION LOGIC
# ==========================================
def parse_dt(dt):
    try:
        return datetime.strptime(dt, "%d/%m/%Y %H:%M").replace(tzinfo=IST)
    except:
        return None

def validate_ticket(data):
    now = datetime.now(IST)

    src = data.get("Source Station","").upper()
    dest = data.get("Destination Station","").upper()
    cat = data.get("Ticket Category","")
    dt = data.get("Booking Date & Time","")

    ticket_dt = parse_dt(dt)
    if not ticket_dt:
        return False, "Invalid date/time"

    if ticket_dt.date() != now.date():
        return False, "Ticket not for today"

    if "Journey" in cat:
        if now > ticket_dt + timedelta(hours=1):
            return False, "Ticket expired"

    try:
        path = nx.shortest_path(G, src, dest)
        # 🔴 You can later pass checker station dynamically
        checker = "DADAR"
        if checker not in path:
            return False, "Wrong route"
    except:
        return False, "Invalid route"

    return True, "Valid ticket"

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