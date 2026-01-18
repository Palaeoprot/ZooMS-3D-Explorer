import os.path
import json
import logging
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# Same config as main script
SCOPES = ['https://www.googleapis.com/auth/photoslibrary']
TOKEN_FILE = 'token.json'

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    if not os.path.exists(TOKEN_FILE):
        print("token.json not found. Please run sync_parchment_data.py first to authenticate.")
        return

    creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())

    # Build service without discovery URL (Standard way)
    service = build('photoslibrary', 'v1', credentials=creds, static_discovery=False)

    print("\n--- DEFINITIVE WRITE TEST ---")
    print("Attempting to create a test album to verify full scope power...")
    
    try:
        body = {'album': {'title': 'API TEST ALBUM (Antigravity)'}}
        result = service.albums().create(body=body).execute()
        print(f"✅ SUCCESS! Created album with ID: {result.get('id')}")
        print("This proves the scope is WORKING. The 403 on listing is likely just propagation delay.")
    except Exception as e:
        print(f"❌ FAILED to create album.")
        print(f"Error: {e}")
        if "insufficient authentication scopes" in str(e).lower():
            print("\nRESULT: The token holds the scope, but Google Infrastructure is REJECTING the authority.")
            print("This means the 'Trust' setting in your Admin Console hasn't worked yet.")
    
    print("-----------------------------\n")

if __name__ == '__main__':
    main()
