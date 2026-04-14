# DS-Project
Used Gemini 2.5 Flash for ocr for more accuracy.
Generated an API key and made it secure by using .env file.

Steps to implement OCR:
1. Download files from GitHub.

2. Enable venv.
	 type: 
	1) python -m venv venv
	2) .\venv\Scripts\activate

3. Install this library:
	pip install google-genai opencv-python pillow python-dotenv networkx

4. Get Your API Key
	Go to Google AI Studio. (https://aistudio.google.com/app/api-keys?project=gen-lang-client-0177722062)
	Log in with your Google account and click Create API key.
	Copy the generated key.

5. Setup the Security File (.env)
	Inside the project folder, create a brand new file and name it exactly .env (no initial before .)
	Paste your API key into this file using this exact format (no spaces, no quotes):
		GEMINI_API_KEY=AIzaSyYourGeneratedKeyHere

6. Run the Scanner:
	python OCR.py
	press the SPACE bar to capture. Press Q to quit.