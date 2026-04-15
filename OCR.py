import cv2
import json
import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
from PIL import Image

# ==========================================
# 1. INITIALIZE GEMINI AI SECURELY
# ==========================================
# Add override=True to force Python to read the new key
load_dotenv(override=True) 
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("❌ Error: API key not found. Please check your .env file.")
    exit()

client = genai.Client(api_key=api_key)

# ==========================================
# 2. VALIDATION DATABASE
# ==========================================
WESTERN_LINE = ["CHURCHGATE", "MARINE LINES", "CHARNI ROAD", "GRANT ROAD", "MUMBAI CENTRAL", "MAHALAXMI", "LOWER PAREL", "PRABHADEVI", "DADAR", "MATUNGA ROAD", "MAHIM", "BANDRA", "KHAR ROAD", "SANTACRUZ", "VILE PARLE", "ANDHERI", "JOGESHWARI", "RAM MANDIR", "GOREGAON", "MALAD", "KANDIVALI", "BORIVALI", "DAHISAR", "MIRA ROAD", "BHAYANDAR", "NAIGAON", "VASAI ROAD", "NALASOPARA", "VIRAR"]
CENTRAL_LINE = ["CSMT", "MASJID", "SANDHURST ROAD", "BYCULLA", "CHINCHPOKLI", "CURREY ROAD", "PAREL", "DADAR", "MATUNGA", "SION", "KURLA", "GHATKOPAR", "THANE", "DOMBIVLI", "KALYAN", "ULHASNAGAR", "AMBERNATH"]
HARBOUR_LINE = ["MAHIM", "BANDRA", "KHAR ROAD", "SANTACRUZ", "VILE PARLE", "ANDHERI", "JOGESHWARI", "RAM MANDIR", "GOREGAON", "KINGS CIRCLE", "VADALA ROAD", "SEWRI", "CHEMBUR", "VASHI", "NERUL", "BELAPUR", "PANVEL"]

# FIX: All three lines are now included
ALL_STATIONS = ", ".join(set(WESTERN_LINE + CENTRAL_LINE + HARBOUR_LINE))


def extract_ticket_data(image_frame):
    print("\n" + "="*40)
    print("SCANNING...")
    print("="*40)

    # Boost contrast and brightness to separate faded ink from dark borders
    alpha = 1.5
    beta = 20
    enhanced_frame = cv2.convertScaleAbs(image_frame, alpha=alpha, beta=beta)

    rgb_frame = cv2.cvtColor(enhanced_frame, cv2.COLOR_BGR2RGB)
    pil_image = Image.fromarray(rgb_frame)

    prompt = f"""
    You are an expert at reading Mumbai Local train tickets. You can read THREE types of tickets:
    1. Physical dot-matrix UTS tickets (small, printed with faded ink and dark borders)
    2. Digital 'Railone' app tickets (clean digital format on a smartphone screen)
    3. Physical ATVM tickets (printed at station vending machines — white paper, bold black ink,
       "HAPPY JOURNEY / शुभ यात्रा" header in an orange/brown banner, Indian Railways logo,
       QR code in the top right, and a large AIA booking number at the top)

    First, identify which ticket type you are looking at, then extract all fields accordingly.

    CRITICAL SPELLING RULE:
    The Mumbai rail network only contains specific stations. The station names you extract MUST
    perfectly match a station from this allowed list:
    [{ALL_STATIONS}]

    If the ticket text is blurry or looks like a typo (e.g., "BADAR", "LOWR PAREL"), you MUST
    map it to the closest valid station from the allowed list. Do not output invalid station names.

    Extract the following fields strictly in JSON format:

    --- COMMON FIELDS (extract for ALL ticket types) ---

    - "Ticket Type": Must be exactly one of: "UTS App Ticket", "ATVM Ticket", or "Railone Ticket".

    - "Ticket ID / UTS No.":
        * For ATVM tickets: Look for the label "UTS NO :" and extract the alphanumeric code after it
          (e.g., "ZU82EDE061"). Do NOT use the large "AIA XXXXXXXX" number at the top.
        * For UTS App / Railone tickets: Look for "UTS:" or "UTS No:" label and extract the code after it.

    - "Booking ID":
        * For ATVM tickets: Extract the large alphanumeric code at the very top (e.g., "AIA 12070115").
          This is separate from the UTS No.
        * For other ticket types: Set to "Not Applicable".

    - "Source Station": Extract ONLY the station name. Strip out distance markers, brackets, km values
      (e.g., "CHARNI ROAD TO LOWER PAREL KM 6" -> Source is "CHARNI ROAD"). MUST be from the allowed list.

    - "Destination Station": Extract ONLY the station name. Strip any "&", "KM X", or distance markers
      (e.g., "LOWER PAREL KM 6" -> Destination is "LOWER PAREL"). MUST be from the allowed list.

    - "Ticket Class":
        * For ATVM tickets: "SECOND ORDINARY" maps to "Second Class", "FIRST CLASS" maps to "First Class".
          Must output exactly "First Class", "Second Class", or "AC EMU".
        * For other ticket types: Must be exactly "First Class", "Second Class", or "AC EMU".

    - "Ticket Category": Must be exactly "Journey Ticket", "Return Ticket", or "Season Pass".

    - "Number of Adults": Extract the number after "ADULT:" (e.g., 2). If not present, output 1.

    - "Number of Children": Extract the number after "CHILD:" (e.g., 0). If not present, output 0.

    - "Fare": Extract the ticket price (e.g., "Rs. 10/-" -> "Rs. 10"). If not found, output "Not Found".

    - "Payment Mode": Look for "MODE:" label (e.g., "MODE:PYTM" -> "Paytm").
      Common mappings: PYTM -> "Paytm", CASH -> "Cash", UPI -> "UPI".
      If not present, output "Not Applicable".

    --- CONDITIONAL DATE FIELDS ---

    - If "Journey Ticket" or "Return Ticket":
        Extract "Booking Date & Time" (Format DD/MM/YYYY HH:MM).
        * For ATVM tickets: Look at the bottom line of the ticket. It contains a date and time
          in the format DD/MM/YYYY HH:MM (e.g., "20/02/2026 20:02"). Extract this.
        * For UTS/dot-matrix tickets: Look near the top or bottom edge in faded ink. If a digit
          is cut in half by a border line, infer it from the visible portion.
        Set "Valid From Date" and "Valid To Date" to "Not Applicable".

    - If "Season Pass":
        Extract "Valid From Date" and "Valid To Date" (Format DD-MM-YYYY).
        Set "Booking Date & Time" to "Not Applicable".

    If any required field is completely unreadable, output its value as "Not Found".
    """

    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash-001',
            contents=[pil_image, prompt],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )

        data = json.loads(response.text)

        print("\n✨ TICKET DATA SUCCESSFULLY EXTRACTED")
        print("-" * 40)
        for key, value in data.items():
            print(f"{key.ljust(26)}: {value}")
        print("-" * 40 + "\n")

    except Exception as e:
        print(f"\n❌ Network or API Error: Could not verify ticket.")
        print(f"Details: {e}")
        print("Please check your internet connection and try again.\n")


# ==========================================
# 3. SCAN FROM IMAGE FILE
# ==========================================
def scan_from_image():
    print("\n" + "="*50)
    print("🖼️  IMAGE FILE TICKET SCANNER")
    print("="*50)
    print("Supported formats: JPG, JPEG, PNG, BMP, WEBP")
    print("Tip: You can drag and drop the image into the")
    print("     terminal to auto-fill the path.\n")

    image_path = input("📂 Enter the full path to your ticket image: ").strip()
    image_path = image_path.strip('"').strip("'")

    if not os.path.exists(image_path):
        print(f"\n❌ Error: File not found at '{image_path}'")
        print("Please double-check the path and try again.\n")
        return

    supported_formats = (".jpg", ".jpeg", ".png", ".bmp", ".webp")
    if not image_path.lower().endswith(supported_formats):
        print(f"\n❌ Error: Unsupported file format.")
        print(f"Please use one of: {', '.join(supported_formats)}\n")
        return

    image_frame = cv2.imread(image_path)

    if image_frame is None:
        print(f"\n❌ Error: Could not read the image. The file may be corrupted.\n")
        return

    print(f"\n✅ Image loaded successfully: {os.path.basename(image_path)}")
    print(f"   Resolution: {image_frame.shape[1]}x{image_frame.shape[0]} px")

    extract_ticket_data(image_frame)


# ==========================================
# 4. CAMERA SCANNER
# ==========================================
def start_live_scanner():
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("❌ Error: Could not access the webcam.")
        return

    print("\n" + "="*50)
    print("📷 CLOUD AI TICKET SCANNER ACTIVATED")
    print("-> Hold the ticket up to your camera.")
    print("-> Press the 'SPACE' bar to snap a photo.")
    print("-> The scanner will process the image and close automatically.")
    print("="*50 + "\n")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab camera frame.")
            break

        cv2.imshow("Mumbai Local Ticket Scanner", frame)

        key = cv2.waitKey(1) & 0xFF

        if key == 32:
            extract_ticket_data(frame)
            print("Shutting down scanner camera...")
            break

        elif key == ord('q'):
            print("\nClosing scanner. Goodbye!")
            break

    cap.release()
    cv2.destroyAllWindows()


# ==========================================
# 5. MAIN MENU
# ==========================================
if __name__ == "__main__":
    print("\n" + "="*50)
    print("   🚆 MUMBAI LOCAL TICKET SCANNER")
    print("="*50)
    print("How would you like to scan your ticket?\n")
    print("  [1] 📷 Live Camera")
    print("  [2] 🖼️  Upload an Image File")
    print("  [Q] ❌ Quit")
    print("="*50)

    choice = input("\nEnter your choice (1 / 2 / Q): ").strip().upper()

    if choice == "1":
        start_live_scanner()
    elif choice == "2":
        scan_from_image()
    elif choice == "Q":
        print("\nGoodbye! 👋\n")
    else:
        print("\n❌ Invalid choice. Please run the script again and enter 1, 2, or Q.\n")