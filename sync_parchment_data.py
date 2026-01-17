#!/usr/bin/env python3
"""
Codicum Google Drive Sync & QR Detection Tool
Pivoted from Google Photos to Google Drive to handle 300k+ images and bypass API locks.
Includes ZIP deduplication (deleting duplicates from ZIP and re-uploading).
"""

import os
import io
import json
import logging
import time
import zipfile
from datetime import datetime

import cv2
import numpy as np
from pyzbar.pyzbar import decode
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

# =================CONFIGURATION=================
# SCOPES required (Full Drive + Sheets)
SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/spreadsheets'
]

# Target Folder IDs
TARGET_FOLDERS = [
    '1o_AEq5-7WAvtRjOpHObBW7ivfMDfOOzP'  # User Provided Test Folder
]

# Google Sheet ID for Archive Tracking (Create a new Sheet and paste ID here)
GSHEET_ID = '1J2nTTW6bVoWGoirOfcDh923CTGtxvh5XOOpgS6yyUP0' 

# Folder ID for storing thumbnails on Drive (Create a folder and paste its ID)
THUMBS_FOLDER_ID = None 

# Local Paths
ASSETS_DIR = os.path.join(os.getcwd(), 'assets')
IMAGES_DIR = os.path.join(ASSETS_DIR, 'images')
THUMBS_DIR = os.path.join(ASSETS_DIR, 'thumbnails')
MAPPING_FILE = os.path.join(ASSETS_DIR, 'photo_mapping.json')
CREDENTIALS_FILE = os.path.join(os.getcwd(), 'credentials.json')
TOKEN_FILE = os.path.join(os.getcwd(), 'token.json')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_services():
    """Authenticates and returns both Drive and Sheets services."""
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logging.info("Refreshing Access Token...")
            try:
                creds.refresh(Request())
            except Exception:
                creds = None
        
        if not creds:
            logging.info("Initiating OAuth Flow (Drive + Sheets)...")
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
    
    drive = build('drive', 'v3', credentials=creds)
    sheets = build('sheets', 'v4', credentials=creds)
    return drive, sheets

def update_oauth():
    """Instructions for the user to update OAuth if permissions changed."""
    logging.info("♻️  If you encounter 403 Errors (insufficient permissions):")
    logging.info("   1. Delete your local 'token.json' file.")
    logging.info("   2. Run the script again to authorize the 'drive' (Write) scope.")

def log_to_gsheet(service, sheet_id, mapping):
    """Smartly updates the Google Sheet: updates existing rows or appends new ones."""
    if not sheet_id or 'PASTE' in sheet_id:
        logging.warning("Skipping GSheet log: Placeholder or empty ID.")
        return

    logging.info("📊 Performing Smart Sync to Google Sheets...")
    try:
        # 1. Get existing data
        range_name = "Sheet1!A:Z"
        result = service.spreadsheets().values().get(spreadsheetId=sheet_id, range=range_name).execute()
        rows = result.get('values', [])

        headers = ["Parchment ID", "Original Filename", "Captured Date", "Sync Date", "Creator", "Camera", "Location", "Image Preview", "QR Preview"]
        if not rows:
            # Initialize with headers
            rows = [headers]
            service.spreadsheets().values().update(
                spreadsheetId=sheet_id, range="Sheet1!A1",
                valueInputOption="USER_ENTERED", body={'values': rows}).execute()
        else:
            # Ensure headers match our expectation or use existing ones
            current_headers = rows[0]
            for h in headers:
                if h not in current_headers:
                    current_headers.append(h)
            rows[0] = current_headers

        # 2. Map columns
        col_map = {name: i for i, name in enumerate(rows[0])}
        id_col = col_map.get("Parchment ID", 0)

        # 3. Process mapping
        existing_ids = {row[id_col]: i for i, row in enumerate(rows) if len(row) > id_col}
        
        for qid in sorted(mapping.keys()):
            item = mapping[qid]
            img_formula = f'=IMAGE("https://drive.google.com/uc?id={item.get("drive_thumb_id")}")' if item.get('drive_thumb_id') else ""
            qr_formula = f'=IMAGE("https://drive.google.com/uc?id={item.get("drive_qr_id")}")' if item.get('drive_qr_id') else ""
            
            row_data = {
                "Parchment ID": qid,
                "Original Filename": item.get('filename', 'Unknown'),
                "Captured Date": item.get('timestamp', 'Unknown'),
                "Sync Date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "Creator": item.get('creator', 'Unknown'),
                "Camera": item.get('camera', 'Unknown'),
                "Location": item.get('location', 'Unknown'),
                "Image Preview": img_formula,
                "QR Preview": qr_formula
            }

            if qid in existing_ids:
                # Update existing row (only our columns)
                row_idx = existing_ids[qid]
                for col_name, val in row_data.items():
                    if col_name in col_map:
                        target_col = col_map[col_name]
                        while len(rows[row_idx]) <= target_col:
                            rows[row_idx].append("")
                        rows[row_idx][target_col] = val
            else:
                # Prepare new row
                new_row = [""] * len(rows[0])
                for col_name, val in row_data.items():
                    if col_name in col_map:
                        target_col = col_map[col_name]
                        new_row[target_col] = val
                rows.append(new_row)

        # 4. Overwrite with updated set (Batch update is faster but this is safe)
        # We sort the rows (excluding header) by ID for tidiness
        header = rows[0]
        data_rows = sorted(rows[1:], key=lambda x: x[id_col])
        final_rows = [header] + data_rows

        body = {'values': final_rows}
        service.spreadsheets().values().update(
            spreadsheetId=sheet_id, range="Sheet1!A1",
            valueInputOption="USER_ENTERED", body=body).execute()
        
        logging.info(f"✅ GSheet smart-synced ({len(mapping)} items).")
    except Exception as e:
        logging.error(f"Failed to smart-update GSheet: {e}")

def run_gap_analysis(mapping):
    """Identifies missing IDs in numerical sequences (if applicable)."""
    logging.info("🔍 Running Gap Analysis...")
    ids = sorted(mapping.keys())
    # Assuming IDs look like 'XXX-001', 'XXX-002'
    # This is a simple generic gap finder
    try:
        import re
        prefixes = {}
        for qid in ids:
            match = re.search(r'([A-Za-z-]+)(\d+)', qid)
            if match:
                pref, num = match.groups()
                if pref not in prefixes: prefixes[pref] = []
                prefixes[pref].append(int(num))
        
        for pref, nums in prefixes.items():
            full_range = set(range(min(nums), max(nums) + 1))
            missing = sorted(list(full_range - set(nums)))
            if missing:
                logging.warning(f"⚠️ GAPS DETECTED in {pref}: {missing[:10]}...")
            else:
                logging.info(f"✅ No gaps detected in {pref} sequence.")
    except Exception:
        logging.info("Gap analysis skipped: IDs do not follow a standard numerical pattern.")

def detect_qr(image_data):
    """Scans the entire image for QR codes and returns (data, rect)."""
    try:
        nparr = np.frombuffer(image_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None: return None, None
        
        qrs = decode(img)
        if qrs:
            return qrs[0].data.decode('utf-8'), qrs[0].rect
        return None, None
    except Exception:
        return None, None

def get_decimal_from_dms(dms, ref):
    """Converts Degrees, Minutes, Seconds to decimal format."""
    try:
        def to_float(val):
            if hasattr(val, 'numerator'): return float(val.numerator) / float(val.denominator)
            return float(val)
        
        d = to_float(dms[0])
        m = to_float(dms[1]) / 60.0
        s = to_float(dms[2]) / 3600.0
        if ref in ['S', 'W']:
            return - (d + m + s)
        return d + m + s
    except Exception:
        return 0.0

def extract_exif(image_data):
    """Extracts camera model and GPS coordinates from image data."""
    try:
        img = Image.open(io.BytesIO(image_data))
        exif = img._getexif()
        if not exif:
            return "Unknown", "Unknown"

        details = {TAGS.get(tag, tag): value for tag, value in exif.items()}
        
        # Camera Detail
        make = details.get('Make', '')
        model = details.get('Model', '')
        camera = f"{make} {model}".strip() or "Unknown"

        # Location Detail
        location = "Unknown"
        if 'GPSInfo' in details:
            gps_info = {}
            for t in details['GPSInfo']:
                sub_tag = GPSTAGS.get(t, t)
                gps_info[sub_tag] = details['GPSInfo'][t]

            lat = gps_info.get('GPSLatitude')
            lat_ref = gps_info.get('GPSLatitudeRef')
            lon = gps_info.get('GPSLongitude')
            lon_ref = gps_info.get('GPSLongitudeRef')

            if lat and lat_ref and lon and lon_ref:
                decimal_lat = get_decimal_from_dms(lat, lat_ref)
                decimal_lon = get_decimal_from_dms(lon, lon_ref)
                location = f"{decimal_lat:.5f}, {decimal_lon:.5f}"

        return camera, location
    except Exception as e:
        logging.debug(f"EXIF error: {e}")
        return "Unknown", "Unknown"

def generate_thumbnails(qr_id, image_data, rect):
    """Generates a small image thumbnail and a cropped QR thumbnail."""
    try:
        nparr = np.frombuffer(image_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None: return
        
        os.makedirs(THUMBS_DIR, exist_ok=True)
        
        # 1. Image Thumbnail (resize to 300px width)
        h, w = img.shape[:2]
        ratio = 300.0 / w
        dim = (300, int(h * ratio))
        thumb = cv2.resize(img, dim, interpolation=cv2.INTER_AREA)
        thumb_path = os.path.join(THUMBS_DIR, f"{qr_id}_thumb.jpg")
        cv2.imwrite(thumb_path, thumb)
        
        # 2. QR/Barcode Thumbnail (if rect provided)
        if rect:
            l, t, w, h = rect.left, rect.top, rect.width, rect.height
            # Add some padding (20%)
            pad_w = int(w * 0.2)
            pad_h = int(h * 0.2)
            img_h, img_w = img.shape[:2]
            
            y1 = max(0, t - pad_h)
            y2 = min(img_h, t + h + pad_h)
            x1 = max(0, l - pad_w)
            x2 = min(img_w, l + w + pad_w)
            
            qr_crop = img[y1:y2, x1:x2]
            qr_path = os.path.join(THUMBS_DIR, f"{qr_id}_qr.jpg")
            cv2.imwrite(qr_path, qr_crop)
            return thumb_path, qr_path
            
    except Exception as e:
        logging.error(f"Thumbnail error: {e}")
    return None, None

def upload_thumbnail(service, local_path, qr_id, thumb_type):
    """Uploads a thumbnail to Google Drive and rotates it if needed (not implemented here)."""
    if not THUMBS_FOLDER_ID:
        return None
    
    try:
        file_metadata = {
            'name': f"{qr_id}_{thumb_type}.jpg",
            'parents': [THUMBS_FOLDER_ID]
        }
        media = MediaIoBaseUpload(io.FileIO(local_path, 'rb'), mimetype='image/jpeg', resumable=True)
        file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        # Set shared permissions so =IMAGE can see it
        # Actually, if it's within a shared folder, it's fine, but let's be explicit
        service.permissions().create(fileId=file.get('id'), body={'type': 'anyone', 'role': 'reader'}).execute()
        return file.get('id')
    except Exception as e:
        logging.error(f"Failed to upload {thumb_type} for {qr_id}: {e}")
    return None

def process_zip(service, file_id, file_name, mapping, creator="Unknown"):
    """Downloads a ZIP, extracts NEW images, and re-uploads a CLEANED zip without duplicates."""
    logging.info(f"📦 Processing & Cleaning ZIP archive: {file_name} (Uploaded by: {creator})")
    try:
        request = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        
        cleaned_fh = io.BytesIO()
        new_matches = 0
        duplicates_removed = False
        
        with zipfile.ZipFile(fh) as z_old:
            with zipfile.ZipFile(cleaned_fh, 'w') as z_new:
                image_exts = ('.jpg', '.jpeg', '.png', '.tiff', '.webp')
                
                for z_item in z_old.infolist():
                    img_name = z_item.filename
                    if z_item.is_dir():
                        z_new.writestr(z_item, b'')
                        continue

                    is_image = img_name.lower().endswith(image_exts)
                    
                    if is_image:
                        # Check mapping (using filename as proxy for identification)
                        already_captured = any(m.get('filename') == os.path.basename(img_name) for m in mapping.values())
                        
                        if not already_captured:
                            with z_old.open(img_name) as f:
                                img_data = f.read()
                                qr_id, rect = detect_qr(img_data)
                                
                                if qr_id:
                                    logging.info(f"✨ NEW MATCH IN ZIP: {qr_id}")
                                    local_path = os.path.join(IMAGES_DIR, f"{qr_id}.jpg")
                                    with open(local_path, 'wb') as lf:
                                        lf.write(img_data)
                                    
                                    # Generate Thumbnails
                                    t_path, q_path = generate_thumbnails(qr_id, img_data, rect)
                                    # Extract EXIF
                                    cam, loc = extract_exif(img_data)

                                    mapping[qr_id] = {
                                        "filename": os.path.basename(img_name),
                                        "source_zip": file_name,
                                        "timestamp": datetime.now().isoformat(),
                                        "local_path": local_path,
                                        "thumb_path": t_path,
                                        "qr_path": q_path,
                                        "creator": creator,
                                        "camera": cam,
                                        "location": loc
                                    }
                                    new_matches += 1
                                    duplicates_removed = True 
                                    # We don't write it to z_new, so it's "deleted" from the archive
                                else:
                                    # Not a match, keep it in the archive
                                    z_new.writestr(z_item, img_data)
                        else:
                            logging.info(f"🗑️ Removing duplicate from ZIP: {img_name}")
                            duplicates_removed = True
                    else:
                        z_new.writestr(z_item, z_old.read(img_name))

        if duplicates_removed:
            logging.info(f"📤 Re-uploading cleaned ZIP ({file_name})...")
            cleaned_fh.seek(0)
            media = MediaIoBaseUpload(cleaned_fh, mimetype='application/zip', resumable=True)
            service.files().update(fileId=file_id, media_body=media).execute()
            logging.info("✅ ZIP cleaned and shrunk on Drive.")
            
        return new_matches
    except Exception as e:
        logging.error(f"ZIP error: {e}")
        return 0

def process_folder(service, folder_id, mapping):
    """Iterates through images and zips in a Drive folder."""
    fields = "nextPageToken, files(id, name, mimeType, createdTime, owners(displayName))"
    query = f"'{folder_id}' in parents and (mimeType contains 'image/' or mimeType contains 'zip') and trashed = false"
    match_count = 0
    
    page_token = None
    while True:
        results = service.files().list(q=query, pageSize=100, fields=fields, pageToken=page_token).execute()
        items = results.get('files', [])
        if not items: break

        for item in items:
            file_id, file_name, mime_type = item['id'], item['name'], item['mimeType']
            owners = item.get('owners', [])
            creator = owners[0].get('displayName', 'Unknown') if owners else 'Unknown'
            
            if 'zip' in mime_type:
                match_count += process_zip(service, file_id, file_name, mapping, creator=creator)
                continue

            if any(m.get('drive_id') == file_id for m in mapping.values()):
                continue
            
            logging.info(f"Processing Image: {file_name} (Owner: {creator})")
            try:
                request = service.files().get_media(fileId=file_id)
                fh = io.BytesIO()
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while not done:
                    _, done = downloader.next_chunk()
                
                img_data = fh.getvalue()
                qr_id, rect = detect_qr(img_data)
                if qr_id:
                    logging.info(f"✨ MATCH FOUND: {qr_id}")
                    local_path = os.path.join(IMAGES_DIR, f"{qr_id}.jpg")
                    with open(local_path, 'wb') as f:
                        f.write(img_data)
                    
                    # Generate Thumbnails
                    t_path, q_path = generate_thumbnails(qr_id, img_data, rect)
                    # Extract EXIF
                    cam, loc = extract_exif(img_data)

                    mapping[qr_id] = {
                        "filename": file_name, 
                        "drive_id": file_id, 
                        "timestamp": item.get('createdTime'), 
                        "local_path": local_path,
                        "thumb_path": t_path,
                        "qr_path": q_path,
                        "creator": creator,
                        "camera": cam,
                        "location": loc
                    }
                    match_count += 1
            except Exception as e:
                logging.error(f"Error: {e}")

        page_token = results.get('nextPageToken')
        if not page_token: break
    return match_count

def main():
    print("\n--- Codicum Google Drive Sync & Clean Tool ---")
    update_oauth()
    os.makedirs(IMAGES_DIR, exist_ok=True)
    os.makedirs(THUMBS_DIR, exist_ok=True)
    
    mapping = {}
    if os.path.exists(MAPPING_FILE):
        try:
            with open(MAPPING_FILE, 'r') as f: 
                mapping = json.load(f)
        except Exception as e:
            logging.error(f"Error loading mapping file: {e}")

    try:
        drive_service, sheets_service = get_services()
    except Exception as e:
        logging.error(f"Authentication Failed: {e}")
        return

    start_time = time.time()
    total_matches = 0
    
    # 1. Ensure Thumbnail Folder exists on Drive
    global THUMBS_FOLDER_ID
    if not THUMBS_FOLDER_ID:
        try:
            logging.info("📁 Looking for 'Codicum_Thumbnails' folder on Drive...")
            q = "name = 'Codicum_Thumbnails' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
            res = drive_service.files().list(q=q, fields="files(id)").execute()
            files = res.get('files', [])
            if files:
                THUMBS_FOLDER_ID = files[0]['id']
                logging.info(f"📂 Found existing thumbnail folder: {THUMBS_FOLDER_ID}")
            else:
                logging.info("🆕 Creating new 'Codicum_Thumbnails' folder on Drive...")
                folder_metadata = {'name': 'Codicum_Thumbnails', 'mimeType': 'application/vnd.google-apps.folder'}
                folder = drive_service.files().create(body=folder_metadata, fields='id').execute()
                THUMBS_FOLDER_ID = folder.get('id')
                # Share the whole folder so cells can see images
                drive_service.permissions().create(fileId=THUMBS_FOLDER_ID, body={'type': 'anyone', 'role': 'reader'}).execute()
        except Exception as e:
            logging.error(f"Failed to setup thumbnail folder: {e}")

    # 2. Sync folders
    for folder_id in TARGET_FOLDERS:
        logging.info(f"🚀 Scanning Folder: {folder_id}")
        total_matches += process_folder(drive_service, folder_id, mapping)

    # 3. Heal Mapping (Backfill thumbnails, creators, and metadata)
    logging.info("🩹 Healing mapping (backfilling missing meta/thumbs)...")
    healed = 0
    # Pre-cache zip owners to avoid redundant API calls
    zip_owners = {}

    for qid, item in mapping.items():
        needs_heal = False
        img_data = None
        
        # 3a. Read imaging data if needed for multiple checks
        local_img = item.get('local_path', '')
        if os.path.exists(local_img):
            # 3b. Heal Thumbnails or EXIF
            if not item.get('thumb_path') or not item.get('camera'):
                try:
                    with open(local_img, 'rb') as f:
                        img_data = f.read()
                    
                    if not item.get('thumb_path'):
                        _, rect = detect_qr(img_data)
                        t_path, q_path = generate_thumbnails(qid, img_data, rect)
                        item['thumb_path'] = t_path
                        item['qr_path'] = q_path
                        needs_heal = True
                    
                    if not item.get('camera') or item.get('camera') == 'Unknown':
                        cam, loc = extract_exif(img_data)
                        item['camera'] = cam
                        item['location'] = loc
                        needs_heal = True
                except Exception as e:
                    logging.error(f"Data heal failed for {qid}: {e}")

        # 3c. Heal Creator (Fetch from Drive)
        if not item.get('creator') or item.get('creator') == 'Unknown':
            try:
                creator = "Unknown"
                if item.get('drive_id'):
                    f_meta = drive_service.files().get(fileId=item['drive_id'], fields="owners(displayName)").execute()
                    owners = f_meta.get('owners', [])
                    creator = owners[0].get('displayName', 'Unknown') if owners else 'Unknown'
                elif item.get('source_zip'):
                    z_name = item['source_zip']
                    if z_name not in zip_owners:
                        q = f"name = '{z_name}' and trashed = false"
                        res = drive_service.files().list(q=q, fields="files(owners(displayName))").execute()
                        files = res.get('files', [])
                        zip_owners[z_name] = files[0].get('owners', [{}])[0].get('displayName', 'Unknown') if files else 'Unknown'
                    creator = zip_owners[z_name]
                
                if creator != "Unknown":
                    item['creator'] = creator
                    needs_heal = True
            except Exception as e:
                logging.error(f"Creator heal failed for {qid}: {e}")

        if needs_heal: healed += 1
    
    if healed: logging.info(f"✨ Healed {healed} items with missing metadata.")

    # 4. Proactively upload ANY missing thumbnails in the mapping
    logging.info("📤 Checking for missing thumbnail uploads to Drive...")
    for qid, item in mapping.items():
        if item.get('thumb_path') and not item.get('drive_thumb_id'):
            item['drive_thumb_id'] = upload_thumbnail(drive_service, item['thumb_path'], qid, 'thumb')
        if item.get('qr_path') and not item.get('drive_qr_id'):
            item['drive_qr_id'] = upload_thumbnail(drive_service, item['qr_path'], qid, 'qr')

    # 5. Save local mapping
    try:
        with open(MAPPING_FILE, 'w') as f: 
            json.dump(mapping, f, indent=2)
        logging.info(f"✅ Saved local mapping to {MAPPING_FILE}")
    except Exception as e:
        logging.error(f"Failed to save mapping: {e}")

    # 5. Log to Google Sheets
    log_to_gsheet(sheets_service, GSHEET_ID, mapping)

    # 6. Run Gap Analysis
    run_gap_analysis(mapping)

    logging.info(f"🎉 Complete! Found {total_matches} new matches in {time.time()-start_time:.1f}s")

if __name__ == "__main__":
    main()
