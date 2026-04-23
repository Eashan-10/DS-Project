# DS-Project
Used Llama 4 Scout for ocr model (Replacement of Gemini flash ocr).
Llama 4 runs on Groq's servers.
Generated an API key and made it secure by using .env file.

Steps to implement OCR:
1. Download files from GitHub.

2. Enable venv.
	 type: 
	1) python -m venv venv
	2) .\venv\Scripts\activate

3. Install this library:
	pip install google-genai opencv-python pillow python-dotenv

4. Get Your API Key
	Go to Groq cloud website. (https://console.groq.com/keys)
	Log in with your Google account and click on API keys then Create API key.
	Copy the generated key.

5. Setup the Security File (.env)
	Inside the project folder, create a brand new file and name it exactly .env (no initial before .)
	Paste your API key into this file using this exact format (no spaces, no quotes):
		GROQ_API_KEY=YourGeneratedKeyHere

6. Run the Scanner:
	python OCR.py
	press the SPACE bar to capture. Press Q to quit.