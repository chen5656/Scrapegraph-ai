import os
from dotenv import load_dotenv
load_dotenv()

try:
    from google import genai
    print("google-genai SDK imported successfully.")
    
    # Try to initialize client
    # Note: Ensure GOOGLE_API_KEY is set in environment or passed to Client()
    api_key = os.environ.get("GOOGLE_API_KEY")
    if api_key:
        # In some intranet environments, SSL verification might fail.
        # This is a temporary workaround for testing.
        import ssl
        ssl._create_default_https_context = ssl._create_unverified_context
        
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-2.5-flash", 
            contents="Explain how AI works in a few words",
        )
        print(f"Gemini Response: {response.text}")
    else:
        print("GOOGLE_API_KEY not found. Skipping live test.")
except ImportError:
    print("google-genai SDK not found. Installing...")
    import subprocess
    import sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "google-genai"])
    print("Installed. Please run again.")
except Exception as e:
    print(f"Error testing Gemini: {e}")
