import json
import os

TOKEN_FILE = 'token.json'

if os.path.exists(TOKEN_FILE):
    with open(TOKEN_FILE, 'r') as f:
        data = json.load(f)
        token = data.get('token')
        print(f"\n--- RAW API TEST (CURL) ---")
        print(f"Run this command to see the raw error from Google:")
        print(f'curl -H "Authorization: Bearer {token}" "https://photoslibrary.googleapis.com/v1/albums?pageSize=1"')
        print(f"---------------------------\n")
else:
    print("token.json not found. Please run the script first.")
