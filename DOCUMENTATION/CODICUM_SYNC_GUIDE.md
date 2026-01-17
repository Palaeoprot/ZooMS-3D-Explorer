# Codicum: Archival Sync Guide

Welcome to the Codicum image synchronisation tool. This system automates the archiving of archaeological parchment photos while keeping our cloud storage clean and organised.

---

## **How it Works (The "Big Picture")**

A digital archivist that processes your parchment photos, identifies them by their QR codes, and keeps everything organised in Google Drive.

---

## **The New Workflow (Post-March 2025)**

> **Important:** Google deprecated the Photos Library API in March 2025. We now use a manual download step to bridge Google Photos and our processing pipeline.

### **Phase 1: Capture & Upload to Google Photos**

**Why Google Photos?**
- Unlimited storage for photos
- Automatic cloud backup
- Easy mobile upload from the field
- Organisation by date/event

**Steps:**
1. Take photos of parchments with QR codes visible
2. Upload to Google Photos (via mobile app or web)
3. Create an album for each batch/week (e.g., "CODICUM Week 12", "MPO Batch Jan 2025")

### **Phase 2: Download Weekly Batches**

Once you've finished a batch (daily/weekly), download it:

**Option A: Download from Google Photos Album (Recommended)**

1. Go to https://photos.google.com
2. Navigate to your album (e.g., "CODICUM MPO Week 12")
3. Click the **three dots** (⋮) menu in top-right
4. Select **"Download all"**
5. Google creates a ZIP file containing all photos
6. Download the ZIP to your computer

**Option B: Google Takeout (For Large Batches)**

1. Go to https://takeout.google.com
2. Click "Deselect all"
3. Select **"Google Photos"** only
4. Click "All photo albums included" → Choose specific albums
5. Click "Next step" → "Create export"
6. Google emails you a download link (may take hours for large batches)
7. Download the ZIP file

**Naming Convention:**
Save your ZIP files with descriptive names:
- `CODICUM_MPO_2025-01-15.zip`
- `CODICUM_FA_Week12.zip`
- `Orval_Abbey_Batch03.zip`

### **Phase 3: Upload to Google Drive**

**Upload your downloaded ZIP to the designated Google Drive folder:**

1. Go to Google Drive: https://drive.google.com
2. Navigate to: **`CODICUM Project/Raw Parchment Batches/`**
3. Drag and drop your ZIP file
4. Wait for upload to complete

**Important:** Do NOT unzip the file! The script processes ZIP files directly.

### **Phase 4: Run the Sync Script**

Now the script can process your batch:

```bash
python3 sync_parchment_data.py
```

**What happens:**

1. **Downloads ZIP**: Script fetches the ZIP from Google Drive
2. **Scans QR Codes**: Identifies each parchment by its barcode
3. **Extracts Matched Photos**: Saves images with QR codes to local archive
4. **Creates Thumbnails**: Generates preview images for dashboard
5. **Updates Tracking**: Logs findings to Google Sheets
6. **Shrinks ZIP**: Re-uploads a cleaned version with only unmatched photos (saves storage)

---

## **Detailed Workflow Breakdown**

### **1. The "Clean and Shrink" Workflow**

We upload batches of photos as **ZIP files** to Google Drive. Over time, these can consume massive storage.

- **Step A**: Script downloads the ZIP file from Google Drive
- **Step B**: Looks inside for any new images not yet processed
- **Step C**: If it finds a "Matched" image (one with a QR code), saves a copy for the Explorer dashboard
- **Step D**: **Re-uploads a cleaned ZIP** to Google Drive, removing duplicates (keeps storage manageable)

### **2. QR Code Identification**

Every parchment has a unique QR code (e.g., `RA-A031`, `MPO-157`). The tool avoids human error by scanning the photo itself.

- **Full Image Scan**: Finds QR codes anywhere in the photo
- **Smart Cropping**: Focuses on top-left 30% where QR codes are usually placed (faster processing)
- **Thumbnails**: Creates preview images and close-ups of barcodes for quick verification

### **3. Automated Tracking (Google Sheets)**

Every run updates our shared **Google Sheets tracking log**.

**Logged Information:**
- **Parchment ID**: ID scanned from QR code
- **Source Batch**: Which ZIP file it came from
- **Upload Date**: When the photo was processed
- **Creator**: Person who uploaded the original batch
- **Camera & Location**: Technical metadata extracted from the photo
- **Preview Thumbnails**: Live image links for verification
- **Gap Analysis**: Checks for missing items in numerical sequences

---

## **Step-by-Step: Weekly Archive Routine**

### **Monday-Friday: Field Work**

- Take photos with phone/camera
- Upload to Google Photos throughout the week
- Add to album: "CODICUM Week [##]"

### **Friday Evening: Batch Download**

1. Open Google Photos
2. Go to your week's album
3. Click ⋮ → "Download all"
4. Save ZIP as: `CODICUM_[Archive]_[Date].zip`

### **Friday Evening: Upload to Drive**

1. Open Google Drive
2. Navigate to `CODICUM Project/Raw Parchment Batches/`
3. Upload your ZIP file
4. ☕ Wait for upload (5-10 min for ~500 photos)

### **Saturday: Run Sync Script**

```bash
cd ~/codicum-sync
python3 sync_parchment_data.py
```

**Watch for:**
- ✅ "MATCH: RA-A031 in IMG_1234.jpg" ← Good!
- ⚠️ "No QR in IMG_5678.jpg" ← Photo without barcode (review manually)

### **Saturday: Verify Results**

1. Check Google Sheets tracking log
2. Look for gaps in sequence (e.g., RA-A031, RA-A033 missing A032)
3. Review "No Match" photos in failed_scans.txt

---

## **Folder Structure**

```
Google Drive/
└── CODICUM Project/
    ├── Raw Parchment Batches/          ← Upload your ZIPs here
    │   ├── CODICUM_MPO_2025-01-15.zip
    │   ├── CODICUM_FA_Week12.zip
    │   └── Processing_Archive/          ← Script moves processed ZIPs here
    │
    └── Processed Images/                ← Script outputs
        ├── Matched/                     ← Images with QR codes
        │   ├── RA-A031.jpg
        │   ├── RA-A032.jpg
        │   └── ...
        ├── Thumbnails/                  ← Preview images
        └── Unmatched/                   ← Photos without QR codes (manual review)

Local Computer/
└── codicum-sync/
    ├── sync_parchment_data.py
    ├── credentials.json              ← Google Drive API credentials
    ├── token.json                    ← Auto-generated auth token
    ├── assets/
    │   ├── photo_mapping.json        ← Tracks processed images
    │   └── batch_report.json         ← Processing statistics
    └── failed_scans.txt              ← List of photos without QR codes
```

---

## **Troubleshooting**

### **"403 Forbidden" or "Insufficient Permissions"**

**Cause:** Script needs permission to access Google Drive

**Fix:**
```bash
rm token.json
python3 sync_parchment_data.py
```

Browser opens → Log in with your @palaeome.org account → Click "Allow"

### **"No ZIP files found"**

**Cause:** Script can't find ZIP files in the expected Drive folder

**Fix:**
1. Verify ZIP is in `CODICUM Project/Raw Parchment Batches/`
2. Check that file name ends with `.zip`
3. Ensure Drive sync is complete (check web interface)

### **"Download failed: File too large"**

**Cause:** ZIP file exceeds Google Drive API limits

**Fix:**
1. Split photos into smaller batches (~500 photos per ZIP)
2. Re-download from Google Photos in smaller chunks
3. Upload separate ZIPs to Drive

### **"No QR code found" for Most Photos**

**Possible Causes:**
- QR codes not visible (too far, angled, obscured)
- Photos taken without parchment in frame
- Wrong camera settings (too dark, blurry)

**Fix:**
1. Review `failed_scans.txt` for list of problem files
2. Check original photos in Google Photos
3. Re-photograph samples with clear QR codes
4. Ensure QR codes are in top-left 30% of frame (optimal)

### **Script is Very Slow**

**Optimization Tips:**
- Process smaller batches (~200-500 photos)
- Run script on computer with good internet connection
- Close other applications during processing
- Consider running overnight for large batches (1000+ photos)

---

## **Best Practices**

### **Photography Tips**

✅ **DO:**
- Place QR code in top-left corner of photo
- Ensure barcode is flat, well-lit, in focus
- Take photo perpendicular to parchment (not angled)
- Include some context (parchment edges visible)
- Use consistent lighting

❌ **DON'T:**
- Cover QR code with fingers/equipment
- Take extreme close-ups (script needs context)
- Use flash that creates glare on QR code
- Mix different archives in same album

### **Naming Conventions**

**Google Photos Albums:**
- `CODICUM MPO 2025-01-15`
- `CODICUM FA Week 12`
- `Orval Abbey January Batch 3`

**ZIP Files:**
- `CODICUM_MPO_2025-01-15.zip`
- `CODICUM_FA_Week12.zip`
- `Orval_Abbey_2025-01_Batch03.zip`

**QR Code Format:**
- `[Archive]-[Number]` (e.g., `MPO-157`, `RA-A031`)
- Use leading zeros for consistent sorting
- Avoid spaces or special characters

### **Storage Management**

**Google Photos:**
- Keep organized by date/album
- Original photos stay in Google Photos indefinitely (free backup)
- Can delete after successful Drive processing if storage needed

**Google Drive:**
- ZIPs automatically cleaned after processing
- Matched images kept in `Processed Images/Matched/`
- Check `Processing_Archive/` quarterly, delete old ZIPs if needed

---

## **Frequently Asked Questions**

**Q: Why not process directly from Google Photos?**
A: Google deprecated their Photos API in March 2025. The manual download step is necessary until they provide a new API.

**Q: Do I need to keep photos in Google Photos after downloading?**
A: Your choice! Google Photos serves as your backup. Once processed to Drive + local archive, you can delete from Photos to save space.

**Q: What if I forget to download before next week?**
A: No problem! Download multiple weeks at once. Just create separate ZIPs for each batch and upload all to Drive. The script processes them sequentially.

**Q: Can I upload JPG files instead of ZIPs?**
A: The current script expects ZIP files. If you have loose JPGs, create a ZIP first:
```bash
zip my_batch.zip *.jpg
```

**Q: What happens to photos without QR codes?**
A: They're logged in `failed_scans.txt`. The script keeps them in the "cleaned" ZIP on Drive for manual review later.

**Q: Can multiple people run the script?**
A: Yes, but coordinate timing. The script locks ZIP files during processing. Use the Google Sheets log to see who processed what.

**Q: How long does processing take?**
A: Roughly 30-60 seconds per 100 photos, depending on:
- Internet speed (downloading ZIPs from Drive)
- Computer performance (QR detection)
- QR code clarity (retries for unclear codes)

**Q: Where can I see the progress?**
A: Look at the shared Google Sheet. All findings are logged automatically. Also check terminal output for real-time status.

---

## **Getting Help**

**Common Issues:** Check Troubleshooting section above

**Script Errors:** Check `failed_scans.txt` and terminal output

**Google Drive Access:** Verify you're logged in with @palaeome.org account

**Questions:** Contact the CODICUM project lead or check project documentation

---

## **Technical Notes**

**Dependencies:**
- Python 3.8+
- Google Drive API credentials
- Libraries: `opencv-python`, `pyzbar`, `google-auth`, `google-api-python-client`

**Authentication:**
- Uses OAuth 2.0 for Google Drive access
- Token stored locally in `token.json`
- Credentials from Google Cloud Console (`credentials.json`)

**Processing Pipeline:**
1. List ZIPs in Drive folder
2. Download ZIP to temp directory
3. Extract and scan each image
4. Detect QR codes using OpenCV + pyzbar
5. Copy matched images to local archive
6. Create cleaned ZIP (unmatched only)
7. Upload cleaned ZIP to Drive
8. Move original ZIP to Processing_Archive
9. Update tracking sheet

---

**Last Updated:** 2025-01-17  
**Version:** 2.0 (Post-API Deprecation)  
**Status:** Production - Google Drive Pipeline
