import cv2
import json
import os
import base64
from dotenv import load_dotenv
from groq import Groq

# ==========================================
# 1. INITIALIZE GROQ AI SECURELY
# ==========================================
load_dotenv(override=True) # Forces Python to read the fresh key
api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    print("❌ Error: GROQ_API_KEY not found. Please check your .env file.")
    exit()

# Initialize the Groq client
client = Groq(api_key=api_key) 

# ==========================================
# 2. VALIDATION DATABASE
# ==========================================
WESTERN_LINE = ["CHURCHGATE", "MARINE LINES", "CHARNI ROAD", "GRANT ROAD", "MUMBAI CENTRAL", "MAHALAXMI", "LOWER PAREL", "PRABHADEVI", "DADAR", "MATUNGA ROAD", "MAHIM", "BANDRA", "KHAR ROAD", "SANTACRUZ", "VILE PARLE", "ANDHERI", "JOGESHWARI", "RAM MANDIR", "GOREGAON", "MALAD", "KANDIVALI", "BORIVALI", "DAHISAR", "MIRA ROAD", "BHAYANDAR", "NAIGAON", "VASAI ROAD", "NALASOPARA", "VIRAR"]
CENTRAL_LINE = ["CSMT", "MASJID", "SANDHURST ROAD", "BYCULLA", "CHINCHPOKLI", "CURREY ROAD", "PAREL", "DADAR", "MATUNGA", "SION", "KURLA", "GHATKOPAR", "THANE", "DOMBIVLI", "KALYAN", "ULHASNAGAR", "AMBERNATH"]
HARBOUR_LINE = ["MAHIM", "BANDRA", "KHAR ROAD", "SANTACRUZ", "VILE PARLE", "ANDHERI", "JOGESHWARI", "RAM MANDIR", "GOREGAON","KINGS CIRCLE", "VADALA ROAD", "SEWRI","COTTON GREEN" ,"REARY ROAD" ,"DOCKYARD ROAD" ,"SANDHURST ROAD", "CHEMBUR", "VASHI", "NERUL", "BELAPUR", "PANVEL", "CSMT"]
# Combine them into one string for the AI
ALL_STATIONS = ", ".join(set(CENTRAL_LINE + HARBOUR_LINE + WESTERN_LINE))


def extract_ticket_data(image_frame):
    print("\n" + "="*40)
    print("🧠 SENDING TICKET TO GROQ (LLAMA 3.2 VISION)...")
    print("="*40)
    
    # 1. Boost contrast and brightness to separate faded ink from dark borders
    alpha = 1.5  
    beta = 20    
    enhanced_frame = cv2.convertScaleAbs(image_frame, alpha=alpha, beta=beta)

    # 2. SHRINK THE PAYLOAD (Max 800px width for fast API transmission)
    height, width = enhanced_frame.shape[:2]
    new_width = 800
    new_height = int((new_width / width) * height)
    resized_frame = cv2.resize(enhanced_frame, (new_width, new_height))

    # 3. Convert OpenCV frame to a Base64 String for Groq
    # Groq API requires the image to be passed as a base64 encoded string
    _, buffer = cv2.imencode('.jpg', resized_frame)
    base64_image = base64.b64encode(buffer).decode('utf-8')

    prompt = f"""
    You are an expert at reading Mumbai Local train tickets. You must be able to read BOTH physically printed dot-matrix tickets and digital 'Railone' app tickets.
    
    First, analyze the image to determine the Ticket Category: "Journey Ticket", "Return Ticket", or "Season Pass".
    Use context to fix blurry or faded text on physical tickets.

    CRITICAL SPELLING RULE: 
    The Mumbai rail network only contains specific stations. The station names you extract MUST perfectly match a station from this allowed list: 
    [{ALL_STATIONS}]
    
    If the ticket text is blurry and looks like a typo (e.g., "BADAR", "BAJAR", or "DADR"), you MUST map it to the closest valid station from the list above (e.g., "DADAR"). Do not output invalid station names.

    Extract the following data strictly in JSON format. Do NOT include any markdown formatting, backticks, or extra text. Output ONLY the raw JSON object.
    
    COMMON FIELDS (Must always be extracted):
   - "Ticket ID / UTS No.": 
        For physical tickets, look explicitly for the text "UTS:" or "UTS No:" and extract the alphanumeric string immediately following it. 
        For digital app tickets, the "UTS" label is often missing. Instead, look for the standalone 10-character alphanumeric string (e.g., "X015EBI2F9") typically located on the right side, directly opposite the Ticket Category (e.g., across from "Journey Ticket"). 
        CRITICAL: Do NOT read the number next to the letter 'M' in the top corners. The ID is often attached directly to the colon with NO SPACE (e.g., if you see "UTS:B0IHEA1418", extract strictly "B0IHEA1418").
    - "Source Station": Extract ONLY the alphabetical station name. CRITICAL FOR SEASON PASSES: Stations are often printed on a single line like "SOURCE(dist) & DESTINATION" (e.g., "DAHISAR(27) & VADALA ROAD"). The source is the word BEFORE the bracketed distance number. You MUST strip out any distance numbers or brackets. MUST be from the allowed list.
    - "Destination Station": Extract ONLY the alphabetical station name. CRITICAL FOR SEASON PASSES: The destination is usually printed on the same line as the source, immediately AFTER an ampersand ("&") (e.g., in "& VADALA ROAD", extract strictly "VADALA ROAD"). MUST be from the allowed list.
    - "Ticket Class": Must be exactly "First Class", "Second Class", or "AC EMU".
    - "Ticket Category": Must be "Journey Ticket", "Return Ticket", or "Season Pass".

    CONDITIONAL DATE FIELDS (Follow these rules strictly based on the Ticket Category):
    - If "Journey Ticket" or "Return Ticket": 
        Extract "Booking Date & Time" (Format DD/MM/YYYY HH:MM). 
        CRITICAL HINT: On physical tickets, this is usually printed in faded dot-matrix ink near the very top or bottom edge. It heavily overlaps with the pre-printed borders. Look extremely closely at the border lines for hidden digits. If a number is cut in half by a line, use the visible half to infer the digit.
        Set "Valid From Date" and "Valid To Date" to "Not Applicable".
    - If "Season Pass": 
        Extract "Valid From Date" and "Valid To Date" (Format DD-MM-YYYY). 
        Set "Booking Date & Time" to "Not Applicable".

    If any required field is completely unreadable due to glare or damage, output the value as "Not Found".
    """

    try:
        # 4. Fire the Base64 image and prompt to Groq's Vision Model
        response = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}",
                            },
                        },
                    ],
                }
            ],
            temperature=0.1, # Low temperature forces stricter JSON formatting
        )

        # Extract response text and clean up any accidental markdown blocks 
        raw_response = response.choices[0].message.content
        clean_json = raw_response.replace("```json", "").replace("```", "").strip()
        data = json.loads(clean_json)

        print("\n✨ TICKET DATA SUCCESSFULLY EXTRACTED")
        print("-" * 40)
        for key, value in data.items():
            print(f"{key.ljust(22)}: {value}")
        print("-" * 40 + "\n")

    except json.JSONDecodeError:
        print("\n❌ Parsing Error: The AI did not return a valid JSON object.")
        print(f"Raw Output: {raw_response}\n")
    except Exception as e:
        print(f"\n❌ Network or API Error: Could not verify ticket.")
        print(f"Details: {e}")
        print("Please check your internet connection and try again.\n")


def start_live_scanner():
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("❌ Error: Could not access the webcam.")
        return

    print("\n" + "="*50)
    print("📷 GROQ VISION TICKET SCANNER ACTIVATED")
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
        
        if key == 32: # SPACE bar
            extract_ticket_data(frame)
            print("Shutting down scanner camera...")
            break # Ensures the loop terminates after a single successful scan
            
        elif key == ord('q'):
            print("\nClosing scanner. Goodbye!")
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    start_live_scanner()