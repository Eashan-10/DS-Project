First setup your OCR:
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

Steps to implement the project: (You will need 3 terminals)
Step 1. Enter this in terminal: 
	pip install flask flask-cors networkx numpy opencv-python groq python-dotenv

Step 2. To start implementation, first connect your mobile device and laptop on the same network (e.g., a mobile hotspot).

	1. Connect your laptop to your phone's Wi-Fi hotspot or both should be on same WiFi.

	2. Find your laptop's local IPv4 address:

		Open a seperate VS Code terminal (terminal 3) and type ipconfig.
		Look under the Wireless LAN adapter Wi-Fi section and copy your IPv4 Address (e.g., 192.168.0.224).

	3. Open frontend/index.html.

		Scroll down to the endpoint variable (around line 1019) and update it with your exact IPv4 address like this: const endpoint = 'http://IPv4addrs:5000/scan-and-verify'

		Save the file.

Step 3. You will need 3 terminals to run this on mobile
	1. Start the backend while keeping your virtual environment active.
	Enter this in main terminal 1:
	python main.py

	2.Start the Web Frontend
	Open a new terminal, and start the Python HTTP server:

	Enter this in terminal 2:
	python -m http.server 5500 --bind 0.0.0.0

	3. Now on your mobile:
	First set permission for the browser:
	Open chrome and enter chrome://flags
	Search for: Insecure origins treated as secure
	Enter the exact frontend URL into the text box:
	http://YOUR_IPV4_ADDRESS:5500 --> (You need to enter this same link in your browser to open frontend on mobile)

	Change the dropdown to Enabled and tap the Relaunch button.
	Once Chrome restarts, navigate to your frontend URL. Tap "Open Camera", grant permissions, and scan a ticket!	
