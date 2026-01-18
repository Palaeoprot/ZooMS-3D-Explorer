import os.path
import json
import logging
import requests
import cv2
import numpy as np
from datetime import datetime, timedelta
from dateutil import parser
from pyzbar.pyzbar import decode
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# =================CONFIGURATION=================
# SCOPES required for reading library and albums
# CRITICAL: Must use full 'photoslibrary' scope to access existing albums.
# The '.readonly' scope ONLY shows app-uploaded photos, not your library!
SCOPES = [
    'https://www.googleapis.com/auth/photoslibrary',  # Full read access to library
]

# Target Album Titles to Auto-Discover
TARGET_TITLES = ["CODICUM MPO", "CODICUM FA"]

# OPTIONAL: If auto-discovery fails with 403, paste your Album IDs here.
# Note: These MUST be API IDs (not the long string in the Browser URL).
MANUAL_ALBUM_IDS = {
    # "CODICUM MPO": "AF1QipNuhutkyPUSZAgSK0jhcDJmFSU4Wn_PiKH4PZ8JbXS7t8MSnhc0UYYmadGa3dUR5g", 
    # "CODICUM FA": "AF1QipPa1jD4Szy00OG6ywTqgwcp83Zlq88rI0uk1t4IqsJN3vQN8lE-LXxhLl50ESV0ow"
}

# Paths
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_FILE = os.path.join(ROOT_DIR, 'credentials.json')
TOKEN_FILE = os.path.join(ROOT_DIR, 'token.json')
ASSETS_DIR = os.path.join(ROOT_DIR, 'assets')
IMAGES_DIR = os.path.join(ASSETS_DIR, 'images')
MAPPING_FILE = os.path.join(ASSETS_DIR, 'photo_mapping.json')
BATCH_REPORT_FILE = os.path.join(ASSETS_DIR, 'batch_report.json')
FAILED_LOG = os.path.join(ROOT_DIR, 'failed_scans.txt')

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def setup_directories():
    """Ensure assets and images directories exist."""
    if not os.path.exists(ASSETS_DIR):
        os.makedirs(ASSETS_DIR)
    if not os.path.exists(IMAGES_DIR):
        os.makedirs(IMAGES_DIR)

def check_token_info(creds):
    """Diagnose what scopes the token REALLY has by asking Google's tokeninfo endpoint."""
    try:
        url = f"https://oauth2.googleapis.com/tokeninfo?access_token={creds.token}"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            granted_scopes = data.get('scope', '').split(' ')
            logging.info(f"Verified Granular Scopes: {granted_scopes}")
            
            # Check if our critical scopes are missing
            for s in SCOPES:
                if s not in granted_scopes:
                    logging.error(f"CRITICAL MISSING SCOPE: {s}")
                    logging.error("This means your Google Workspace is stripping this permission.")
        else:
            logging.warning(f"Could not verify token info: {response.text}")
    except Exception as e:
        logging.warning(f"Diagnostic failed: {e}")

def get_service():
    """Authenticates and returns the Photos Library API service."""
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logging.info("Refreshing Access Token...")
            try:
                creds.refresh(Request())
            except Exception as e:
                logging.error(f"Failed to refresh token: {e}. Clearing token and starting fresh flow.")
                creds = None
        
        if not creds:
            logging.info("Initiating OAuth Flow...")
            if not os.path.exists(CREDENTIALS_FILE):
                raise FileNotFoundError(f"Could not find {CREDENTIALS_FILE}. Please place it in the root directory.")
            
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
    
    # Run Diagnostic
    check_token_info(creds)

    # Use explicit discovery URL for Photos Library API (more robust)
    DISCOVERY_URL = 'https://photoslibrary.googleapis.com/$discovery/rest?version=v1'
    return build('photoslibrary', 'v1', credentials=creds, discoveryServiceUrl=DISCOVERY_URL, static_discovery=False)

def find_target_albums(service):
    """
    Searches for albums matching TARGET_TITLES in both owned and shared albums.
    Returns a dictionary {Title: ID}.
    """
    found = {}
    
    # Try Owned Albums
    try:
        logging.info("Listing Owned Albums...")
        results = service.albums().list(pageSize=50).execute()
        albums = results.get('albums', [])
        if not albums:
            logging.info(" - No owned albums found.")
        for alb in albums:
            title = alb.get('title')
            logging.info(f" - Found Owned Album: {title} (ID: {alb.get('id')})")
            if title in TARGET_TITLES:
                found[title] = alb.get('id')
    except Exception as e:
        logging.warning(f"Could not list owned albums: {e}")

    # Try Shared Albums (Joined)
    try:
        logging.info("Listing Shared Albums (Joined)...")
        results = service.sharedAlbums().list(pageSize=50).execute()
        shared_albums = results.get('sharedAlbums', [])
        if not shared_albums:
            logging.info(" - No shared albums found.")
        for alb in shared_albums:
            title = alb.get('title')
            logging.info(f" - Found Shared Album: {title} (ID: {alb.get('id')})")
            if title in TARGET_TITLES:
                found[title] = alb.get('id')
    except Exception as e:
        logging.warning(f"Could not list shared albums: {e}")

    return found

def load_json(filepath):
    """Loads JSON file."""
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            return json.load(f)
    return {}

def save_json(filepath, data):
    """Saves JSON file."""
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=4)

def download_image(url, save_path=None):
    """Downloads image from URL."""
    try:
        response = requests.get(url)
        if response.status_code == 200:
            if save_path:
                with open(save_path, 'wb') as f:
                    f.write(response.content)
                return True
            return response.content
    except Exception as e:
        logging.error(f"Download error: {e}")
    return None

def detect_qr(image_bytes):
    """
    Detects QR code.
    Optimized: Crops to top-left 30% first.
    """
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if img is None:
        return None

    height, width, _ = img.shape
    # Crop top-left 30% (with margin)
    crop_h = int(height * 0.45) 
    crop_w = int(width * 0.45)
    crop = img[0:crop_h, 0:crop_w]

    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    decoded_objects = decode(gray)
    
    if decoded_objects:
        return decoded_objects[0].data.decode('utf-8')
    return None

def update_batch_report(item, batch_data):
    """
    Groups items into 1-minute batches based on creationTime.
    batch_data structure: {"YYYY-MM-DD HH:MM": [item_list]}
    """
    creation_time_str = item.get('mediaMetadata', {}).get('creationTime')
    if not creation_time_str:
        return

    try:
        dt = parser.parse(creation_time_str)
        # Round down to minute
        batch_key = dt.strftime("%Y-%m-%d %H:%M")
        
        if batch_key not in batch_data:
            batch_data[batch_key] = []
        
        # Add basic info to batch
        batch_data[batch_key].append({
            "filename": item.get('filename'),
            "id": item.get('id'),
            "creationTime": creation_time_str,
            "camera": item.get('mediaMetadata', {}).get('photo', {}).get('cameraModel', 'Unknown'),
            "aperture": item.get('mediaMetadata', {}).get('photo', {}).get('apertureFNumber', 'Unknown')
        })
    except Exception as e:
        logging.warning(f"Error parsing date for batching: {e}")

def sync_album(service, album_id, archive_name, mapping, batch_report):
    """Iterates through photos in an album and syncs them."""
    logging.info(f"Syncing Album: {archive_name}")
    
    # DIAGNOSTIC: Check if we can even 'get' the album.
    # If the ID starts with 'AF1Qip', it's a browser/sharing ID, not an API ID.
    try:
        service.albums().get(albumId=album_id).execute()
    except Exception as e:
        if "AF1Qip" in album_id:
            logging.warning(f"CAUTION: ID '{album_id}' appears to be a Browser ID, not an API ID.")
            logging.warning("The Photos API often returns 403 Forbidden for Browser IDs.")

    request_body = {'albumId': album_id, 'pageSize': 50}
    page_token = None
    
    while True:
        if page_token:
            request_body['pageToken'] = page_token
            
        try:
            results = service.mediaItems().search(body=request_body).execute()
        except Exception as e:
            if "insufficient authentication scopes" in str(e).lower():
                print("\n" + "!"*60)
                print("PERMISSION ERROR: The API is blocking the media search.")
                print("Since you have already set the app to 'Internal' and 'Trusted',")
                print("this 403 almost certainly means the Album ID is incorrect.")
                print("\nCrucial: The ID in your browser URL is NOT the API ID.")
                print("Please check if the 'find_target_albums' section listed any albums above.")
                print("!"*60 + "\n")
            logging.error(f"Error searching album {archive_name}: {e}")
            break

        items = results.get('mediaItems', [])
        if not items:
            break

        for item in items:
            filename = item.get('filename')
            base_url = item.get('baseUrl')
            google_id = item.get('id')
            
            # Update Batch Report
            update_batch_report(item, batch_report)

            # Check if scanned
            already_scanned = False
            for qr_data, meta in mapping.items():
                if meta.get('google_id') == google_id:
                     already_scanned = True
                     break
            
            if already_scanned:
                continue

            # 1. Download Thumbnail (w1000)
            scan_url = f"{base_url}=w1000"
            img_bytes = download_image(scan_url)
            
            if not img_bytes:
                logging.error(f"Failed to download {filename}")
                continue

            # 2. Detect via processing
            qr_code = detect_qr(img_bytes)
            
            if qr_code:
                logging.info(f"MATCH: {qr_code} in {filename}")
                
                # 3. Mirror Original
                original_url = f"{base_url}=d" 
                local_filename = f"{qr_code}.jpg"
                local_path_rel = os.path.join('assets', 'images', local_filename)
                local_path_abs = os.path.join(IMAGES_DIR, local_filename)
                
                if download_image(original_url, save_path=local_path_abs):
                    mapping[qr_code] = {
                        "filename": filename,
                        "google_url": base_url,
                        "google_id": google_id,
                        "timestamp": item.get('mediaMetadata', {}).get('creationTime'),
                        "archive": archive_name,
                        "local_path": local_path_rel
                    }
                    save_json(MAPPING_FILE, mapping)
            else:
                logging.warning(f"No QR in {filename}")
                with open(FAILED_LOG, 'a') as log:
                    log.write(f"{filename} | {archive_name} | {base_url}\n")

        page_token = results.get('nextPageToken')
        if not page_token:
            break

def main():
    setup_directories()
    print("--- Codicum Parchment Sync & Batch Tool ---")
    
    service = get_service()
    
    # 1. Clear manual IDs to force a fresh discovery attempt now that scopes are fixed
    target_albums = {}
    
    # 2. Try Auto-Discovery
    logging.info("Searching for Target Albums (Owned & Shared)...")
    try:
        target_albums = find_target_albums(service)
    except Exception as e:
        if "insufficient authentication scopes" in str(e).lower():
            print("\n" + "!"*60)
            print("CRITICAL: 403 PERMISSION ERROR")
            print("Your Google Cloud project is missing the required Scopes.")
            print("\nPlease check your GCP Console:")
            print("1. 'Data access' -> 'Add or remove scopes' -> Enable photoslibrary")
            print("2. 'Audience' -> Ensure your email is listed as a Test User.")
            print("!"*60 + "\n")
        else:
            logging.error(f"Discovery failed: {e}")
        return

    # 3. Fallback to manual IDs if discovery fails but we have them
    for title, aid in MANUAL_ALBUM_IDS.items():
        if title not in target_albums and aid:
            logging.info(f"Using Manual ID for {title}")
            target_albums[title] = aid

    if not target_albums:
        print(f"No albums found matching {TARGET_TITLES}.")
        print("Try creating a dummy album with one of these names to verify connectivity.")
        return

    mapping = load_json(MAPPING_FILE)
    batch_report = load_json(BATCH_REPORT_FILE)
    
    # Process found albums
    for title, alb_id in target_albums.items():
        print(f"\nProcessing Album: {title}")
        try:
            sync_album(service, alb_id, title, mapping, batch_report)
        except Exception as e:
             logging.error(f"Error syncing {title}: {e}")

    save_json(BATCH_REPORT_FILE, batch_report)
    print(f"\nSync Complete. Batch report saved to {BATCH_REPORT_FILE}")

if __name__ == '__main__':
    main()
