# Codicum: Archival Sync Guide

Welcome to the Codicum image synchronization tool. This system is designed to automate the archival of archaeological parchment photos while keeping our cloud storage clean and organized.

## How it Works (The "Big Picture")

Think of this tool as a digital archivist that looks through your Google Drive, finds new photos, identifies them by their QR codes, and keeps everything tidy.

### 1. The "Clean and Shrink" Workflow
We upload batches of photos as **ZIP files** to Google Drive. Over time, these ZIP files can take up massive amounts of storage. 
-   **Step A**: The tool downloads the ZIP file.
-   **Step B**: It looks inside for any new images it hasn't seen before.
-   **Step C**: If it finds a "Matched" image (one with a QR code), it saves a copy for our Explorer dashboard.
-   **Step D**: It **re-uploads a new version of the ZIP** back to Google Drive with the duplicates removed. This keeps your cloud storage from filling up with files we've already processed.

### 2. QR Code Identification
Every parchment has a unique QR code (e.g., `RA-A031`). The tool avoids human error by scanning the photo itself to determine which sample it is. 
-   **Full Image Scan**: No matter where the QR code is in the photo, the tool will find it.
-   **Thumbnails**: For every match, the tool creates a small "reminder image" and a close-up of the barcode so you can quickly double-check samples in the 3D Explorer.

### 3. Automated Tracking (Google Sheets)
Every time the tool runs, it updates our shared **Google Sheets tracking log**.
-   **Parchment ID**: The ID scanned from the QR code.
-   **Creator**: The name of the person who uploaded the file/ZIP to Drive.
-   **Previews**: Live image thumbnails for quick verification.
-   **Gap Analysis**: It checks for missing items in numerical sequences.

---

## How to Run It

1.  **Upload photos**: Upload your weekly ZIP files or loose photos to the designated Google Drive folders.
2.  **Run the script**: 
    ```bash
    python3 sync_parchment_data.py
    ```
3.  **Check the Dashboard**: Once complete, the images will be available for the 3D ZooMS Explorer.

## Frequently Asked Questions

**Q: What if I get a "403 Forbidden" error?**
A: This mean the tool needs permission to access your Drive. Delete the `token.json` file in the folder and run the script again to re-authorize.

**Q: Do I need to delete photos manually?**
A: No. The tool automatically handles the "cleaning" of ZIP files on Drive. However, if you upload loose photos (not in a ZIP), you should move them to an "Archive" folder after the script confirms they are synced.

**Q: Where can I see the progress?**
A: Look at the shared Google Sheet. All findings are logged there automatically.
