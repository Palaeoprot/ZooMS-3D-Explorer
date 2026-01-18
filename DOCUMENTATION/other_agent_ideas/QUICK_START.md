# CODICUM Photos API - Quick Fix Summary

## 🎯 The Problem (1 sentence)

Your script uses the **wrong scope** (`.readonly`) which only shows app-uploaded photos, not your existing library.

---

## ✅ The Solution (3 steps)

### 1. Fix Your Script (30 seconds)

Replace line 19 in `sync_parchment_data.py`:

**BEFORE:**
```python
SCOPES = [
    'https://www.googleapis.com/auth/photoslibrary.readonly',
    'https://www.googleapis.com/auth/photoslibrary.sharing'
]
```

**AFTER:**
```python
SCOPES = [
    'https://www.googleapis.com/auth/photoslibrary',
]
```

Or use the fixed version: `sync_parchment_data_FIXED.py`

### 2. Update Google Cloud Console (2 minutes)

1. Go to: https://console.cloud.google.com/apis/credentials/consent
2. Click **"EDIT APP"**
3. Go to **"Scopes"** section
4. Click **"ADD OR REMOVE SCOPES"**
5. **Remove** any `.readonly` scopes
6. **Add** scope: `https://www.googleapis.com/auth/photoslibrary`
7. Click **"UPDATE"** then **"SAVE"**

### 3. Re-authenticate (1 minute)

```bash
rm token.json  # Delete old token with wrong scopes
python3 sync_parchment_data_FIXED.py
```

Browser opens → Select @palaeome.org account → Check the box → Done!

---

## 📋 Files Included

1. **sync_parchment_data_FIXED.py** - Corrected script with proper scope
2. **PHOTOS_API_FIX_GUIDE.md** - Detailed troubleshooting (if needed)
3. **diagnose_photos.py** - Diagnostic tool to verify configuration

---

## 🔍 Quick Diagnostic

Run this first to check your setup:

```bash
python3 diagnose_photos.py
```

It will tell you exactly what's wrong and how to fix it.

---

## ❓ What Was Wrong?

| Scope | What It Does |
|-------|--------------|
| `.readonly` (WRONG) | Only shows photos YOUR APP uploaded |
| `photoslibrary` (CORRECT) | Shows your entire library + albums |

Since you manually uploaded photos to your albums, the API correctly blocked access because those photos weren't uploaded by your app. The full `photoslibrary` scope gives you access to everything.

---

## 🚨 Still Getting 403 After Fix?

If you still get errors after updating scopes and re-authenticating:

1. **Verify Photos API is enabled:**
   https://console.cloud.google.com/apis/library/photoslibrary.googleapis.com
   (Click ENABLE if needed)

2. **Check Workspace Admin restrictions:**
   - Admin Console → Apps → Google Workspace → Google Photos
   - Must be "ON for everyone"

3. **Trust the app (Workspace Admin):**
   - Admin Console → Security → API Controls → Manage Third-Party Apps
   - Add your OAuth Client ID
   - Set to "Trusted"

See **PHOTOS_API_FIX_GUIDE.md** for detailed Workspace admin instructions.

---

## ✅ Expected Success Output

After fixing, you should see:

```
INFO - Verified Granular Scopes: ['https://www.googleapis.com/auth/photoslibrary']
INFO - Listing Owned Albums...
INFO -  - Found Owned Album: CODICUM MPO (ID: ABC123...)
INFO -  - Found Owned Album: CODICUM FA (ID: XYZ789...)
INFO - Syncing Album: CODICUM MPO
INFO - MATCH: MPO001 in IMG_1234.jpg
```

Not this:
```
ERROR - 403 Insufficient authentication scopes
```

---

**That's it!** The fix is literally changing one line and re-authenticating.
