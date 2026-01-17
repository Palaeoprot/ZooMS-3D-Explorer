# Codicum Parchment Sync Tool: Technical Overview

**Script Name:** `sync_parchment_data.py`
**Version:** 1.0.0
**Context:** Part of the ZooMS-3D-Explorer integration pipeline.

## 1. Executive Summary
This tool acts as a bridge between the **Google Photos** cloud storage (where archivists upload images) and the **ZooMS-3D-Explorer** (where researchers visualize them).

It automates the following workflow:
1.  **Discovers** specific Codicum albums in the cloud.
2.  **Scans** every new image for a QR Code (e.g., "RA-A031").
3.  **Mirrors** the original high-resolution image to the local server.
4.  **Catalogs** technical metadata (camera model, aperture, capture time) into batch reports.

## 2. Key Features

### A. Intelligent "Discovery" Mode
The script does not require hardcoded IDs. It automatically searches the user's Google Photos library for albums containing the keywords:
-   `"CODICUM MPO"`
-   `"CODICUM FA"`

> **Note for Teams:** If an album is empty (e.g., the team hasn't uploaded photos yet), the script simply logs that it found the album but found no items, and gracefully proceeds to the next one. It will check again the next time it runs.

### B. Bandwidth-Optimized Scanning
To ensure speed and low data usage, the script uses a two-step process:
1.  **Low-Res "Peek"**: It first downloads a lightweight, specific-width thumbnail (`w1000`) of the image.
2.  **Smart Caching**: It checks a local `photo_mapping.json` manifest. If an image ID has already been processed, it is skipped entirely.

### C. Computer Vision Pipeline (QR Detection)
Once the thumbnail is downloaded, the script applies **OpenCV** image processing:
-   **Cropping**: It assumes the archival tag is in the top-left corner. It automatically crops the image to the top-left 30% to remove noise and focus the detector.
-   **Grayscale Conversion**: Converts the crop to black-and-white to enhance contrast for the barcode reader.
-   **Decoding**: Uses `pyzbar` to extract the alphanumeric string (e.g., "RA-A031") from the QR code.

### D. Permanent Mirroring
When a QR code is successfully detected:
1.  The script requests the **Original** full-resolution image key from Google.
2.  It saves the file permanently to `assets/images/[QR_ID].jpg`.
3.  **Why?** Google Photos links expire after 60 minutes. This mirroring ensures the 3D Explorer typically loads textures instantly and never "breaks" due to expired links.

### E. Batch Reporting
The script generates a `batch_report.json` file.
-   **Logic**: It groups images into **1-minute time windows** based on their creation timestamp.
-   **Utility**: This allows the system to identify "batches" of photos taken in quick succession, which is critical for grouping multiple angles of the same parchment or identifying sessions.

## 3. Workflow Diagram

```mermaid
graph TD
    A[Start Script] --> B{Auth & Discover Albums}
    B -- Found "CODICUM MPO" --> C[List Media Items]
    C --> D{Already Scanned?}
    D -- Yes --> C
    D -- No --> E[Download w1000 Thumb]
    E --> F[Crop Top-Left 30%]
    F --> G{Detect QR Code}
    G -- No Match --> H[Log Failure & Continue]
    G -- Match Found (RA-A031) --> I[Download ORIGINAL Full-Res]
    I --> J[Save to assets/images/RA-A031.jpg]
    J --> K[Update photo_mapping.json]
    K --> L[Update batch_report.json]
```

## 4. Output Files

| File | Path | Purpose |
| :--- | :--- | :--- |
| **Photo Map** | `assets/photo_mapping.json` | The "Master Database" linking QR IDs to filenames and local paths. |
| **Images** | `assets/images/*.jpg` | The permanent local texture files for the 3D models. |
| **Batch Report** | `assets/batch_report.json` | Technical metadata grouping images by 1-minute capture windows. |
| **Fail Log** | `failed_scans.txt` | A list of images where no QR code could be detected. |

## 5. Instructions for the Team
1.  **Upload**: Upload photos to a Google Photos album named "CODICUM MPO" or "CODICUM FA".
2.  **Naming**: Filenames do not matter; the script reads the visual QR code.
3.  **Orientation**: Ensure the QR tag is roughly in the top-left quadrant of the photo.
4.  **Sync**: Run `python3 sync_parchment_data.py`.
