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
load_dotenv() # Loads the hidden variables from the .env file
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("❌ Error: API key not found. Please check your .env file.")
    exit()

client = genai.Client(api_key=api_key) 

def extract_ticket_data(image_frame):
    print("\n" + "="*40)
    print("🧠 SENDING TICKET TO GEMINI 2.5 FLASH...")
    print("="*40)
    
    rgb_frame = cv2.cvtColor(image_frame, cv2.COLOR_BGR2RGB)
    pil_image = Image.fromarray(rgb_frame)

    prompt = """
    You are an expert at reading Mumbai Local train tickets. You must be able to read BOTH physically printed dot-matrix tickets and digital 'Railone' app tickets.
    
    First, analyze the image to determine the Ticket Category: "Journey Ticket", "Return Ticket", or "Season Pass".
    Use context to fix blurry or faded text on physical tickets.

    Extract the following data strictly in JSON format:
    
    COMMON FIELDS (Must always be extracted):
    - "Ticket ID / UTS No.": The 10-character alphanumeric ID.
    - "Source Station": The starting station.
    - "Destination Station": The ending station.
    - "Ticket Class": Must be exactly "First Class", "Second Class", or "AC EMU".
    - "Ticket Category": Must be "Journey Ticket", "Return Ticket", or "Season Pass".

    CONDITIONAL DATE FIELDS (Follow these rules strictly based on the Ticket Category):
    - If "Journey Ticket" or "Return Ticket": 
        Extract "Booking Date & Time" (Format DD/MM/YYYY HH:MM). 
        Set "Valid From Date" and "Valid To Date" to "Not Applicable".
    - If "Season Pass": 
        Extract "Valid From Date" and "Valid To Date" (Format DD-MM-YYYY). 
        Set "Booking Date & Time" to "Not Applicable".

    If any required field is completely unreadable due to glare or damage, output the value as "Not Found".
    """

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[pil_image, prompt],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )

        data = json.loads(response.text)

        print("\n✨ TICKET DATA SUCCESSFULLY EXTRACTED")
        print("-" * 40)
        for key, value in data.items():
            print(f"{key.ljust(22)}: {value}")
        print("-" * 40 + "\n")

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

if __name__ == "__main__":
    start_live_scanner()