# CODICUM Photos Sync: Troubleshooting & Admin Report

## 1. The Core Problem: The Photos API Paradox
The primary reason we are hitting a `403 Permission Denied` error is a technical paradox in how Google designed the Photos Library API for unverified/third-party apps.

### The Paradox
*   **`.readonly` scope:** Rstricts access to app-uploaded photos only. Useful for apps that "create" data, but useless for "syncing" photos uploaded by humans.
*   **`photoslibrary` (full/restricted) scope:** Required to see your existing library, but Google Workspace blocks this for "Untrusted" apps.
*   **The Symptom (Missing Checkboxes):** If you log in with your `@palaeome.org` account and **don't see checkboxes**, it means your Workspace is silently stripping those scopes because the app is "Untrusted."

---

## 2. The Conflict: Cross-Org Permissions
The GCP project `codicum-photos` was created "outside" your current `@palaeome.org` organization. 
1.  **GCP Level:** The project lists `mc80york@gmail.com` (or similar) as the owner.
2.  **User Level:** You are trying to authorize it with `matthew@palaeome.org`.
3.  **The Result:** Google sees an "External" app trying to take "Sensitive" data from a "Workspace" user. For security, it hides the checkboxes entirely to prevent data theft.

---

## 3. The "Publish" Trap: Why NOT to Publish
> [!WARNING]
> **Do not click 'Publish App' yet.** 
> If you move the project from "Testing" to "Published" while requesting Photos scopes, Google will **lock the app** until it passes a manual security review (4-6 weeks). 

### The Solution: Staying in "Testing" + "Trusted"
The correct path for research is to keep the app in **Testing** mode and use your Admin authority to **"Trust"** it. 

---

## 4. The "Nuclear Option": Native Internal App
If the Admin Console "Save" button remains unclickable, it is because of the "Cross-Org" conflict (the project was created in a personal Gmail account). 

**The 100% Success Path:**
1.  **Switch Projects**: In the Google Cloud Console, ensure you are logged in as `matthew@palaeome.org`.
2.  **Create New Project**: Click the project dropdown > **New Project**. Ensure the "Location" is set to `palaeome.org`.
3.  **Set as Internal**: In the OAuth Consent Screen, you will now have the option to set User Type to **"Internal"**.
    - This allows all `@palaeome.org` users to access it without verification.
    - It bypasses the "Missing Checkbox" issue.
4.  **Download New Credentials**: You will get a new `credentials.json`. 
5.  **Run Sync**: Replace the old file and the script will work instantly.

---

## 5. The "Final Boss": Why a 403 persists for Internal Apps
If you have made the app **Internal** and clicked **Allow**, but the terminal still shows a `403 Insufficient Scopes`, there are only two possibilities left:

### A. The API is not Enabled in this Project
Even if your token is valid, the Google Photos server will reject the request if the **Library Service** is not switched "ON" for your specific project ID.
1.  **[Click here to check the Photos API Status](https://console.cloud.google.com/apis/library/photoslibrary.googleapis.com)**.
2.  Ensure you have the `codicum-photos` project selected in the top dropdown.
3.  If you see an **"ENABLE"** button, click it. (If it says "Manage," it's already active).

### B. Workspace Service Status is OFF
If the Google Photos *service itself* is disabled for your organization, the API will be blocked.
1.  Go to **Admin Console** > **Apps** > **Google Workspace**.
2.  Find **Google Photos** in the list.
3.  Ensure the status is **"ON for everyone."**

---

### C. The ID Mismatch (The "Smoking Gun")
The Google Photos Library API uses unique internal IDs. **The long string in your browser URL is NOT the API ID.** 
If you use a "Browser ID" in an API call, Google returns a `403 Insufficient Scopes` to secure the data.

**The Fix:**
1.  I have updated `sync_parchment_data.py` to aggressively search for your albums by title.
2.  I have **commented out** the `MANUAL_ALBUM_IDS` to force the script to find the correct IDs itself.
3.  **Run the script**: Look at the terminal output. It will now list EVERY album it finds. 

---

## 6. Current Script Status
The script `sync_parchment_data.py` is ready. 
Run the clean-out and sync:
```bash
rm token.json
python3 sync_parchment_data.py
```
If the script still fails to find the albums, **please look closely at the terminal output** and see if it lists any albums at all. If the list is empty, then the "Internal" trust is still propagating.
