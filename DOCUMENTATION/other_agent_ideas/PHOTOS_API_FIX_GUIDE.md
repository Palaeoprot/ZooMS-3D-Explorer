# CODICUM Photos Sync - CORRECT Fix Guide
## Root Cause Analysis & Solution

---

## 🔴 THE REAL PROBLEM

Your script has **THE WRONG SCOPE** on line 19:

```python
# WRONG - This only shows app-uploaded photos!
SCOPES = ['https://www.googleapis.com/auth/photoslibrary.readonly']

# CORRECT - This shows your existing library
SCOPES = ['https://www.googleapis.com/auth/photoslibrary']
```

**What `.readonly` actually does:**
- ✅ Shows photos that YOUR APP uploaded
- ❌ Does NOT show your existing library
- ❌ Does NOT show your albums
- ❌ Does NOT show photos you uploaded manually

This is why you're getting 403 errors - the API is correctly blocking you from accessing albums that don't contain app-uploaded photos!

---

## ✅ STEP-BY-STEP FIX (5 minutes)

### Step 1: Update OAuth Consent Screen Scopes

1. Go to: https://console.cloud.google.com/apis/credentials/consent
2. **Verify you're in the correct project** (top dropdown)
3. Click **"EDIT APP"**
4. Navigate to **"Scopes"** section
5. Click **"ADD OR REMOVE SCOPES"**
6. **Remove** any `.readonly` scopes
7. **Add** this scope:
   ```
   https://www.googleapis.com/auth/photoslibrary
   ```
8. Click **"UPDATE"** then **"SAVE AND CONTINUE"**

### Step 2: Verify Photos API is Enabled

1. Go to: https://console.cloud.google.com/apis/library/photoslibrary.googleapis.com
2. **Verify project is selected** (top dropdown)
3. If button says **"ENABLE"** → Click it
4. If button says **"MANAGE"** → Already enabled ✅

### Step 3: Clean Old Authentication

```bash
# Delete the old token (it has wrong scopes)
rm token.json

# Optional: Backup old credentials
cp credentials.json credentials.json.backup
```

### Step 4: Use the Fixed Script

Replace your `sync_parchment_data.py` with the fixed version:

```python
# UPDATED CONFIGURATION
SCOPES = [
    'https://www.googleapis.com/auth/photoslibrary',  # Full library access
]
```

### Step 5: Re-authenticate

```bash
python3 sync_parchment_data_FIXED.py
```

**What should happen:**
1. Browser opens automatically
2. You see Google consent screen
3. **CRITICAL:** You should see a checkbox for "See and download all your Google Photos"
4. Click the checkbox ✅
5. Click "Continue"

**If you DON'T see checkboxes:**
- Your Workspace admin has blocked this scope
- See "Workspace Admin Fix" below

### Step 6: Verify Success

After authentication, the script will:
1. Print: `Verified Granular Scopes: ['https://www.googleapis.com/auth/photoslibrary']`
2. List your albums: `Found Owned Album: CODICUM MPO (ID: ABC123...)`
3. Start syncing photos

---

## 🏢 IF STILL BLOCKED: Workspace Admin Fix

If the consent screen doesn't show checkboxes, your Workspace is blocking the scope.

### Option A: Trust the App (Recommended)

1. Go to Admin Console: https://admin.google.com/ac/owl/list?tab=apps
2. Click **"Add app"** → **"OAuth App Name Or Client ID"**
3. Enter your **OAuth Client ID** (from credentials.json):
   ```
   Find this in credentials.json under "installed" → "client_id"
   ```
4. Click **"Search"**
5. Select your app
6. Click **"Trusted"**
7. Set access to **"Limited"** or **"Trusted"**
8. Click **"CONFIGURE"**
9. Select the scope: `https://www.googleapis.com/auth/photoslibrary`
10. Click **"FINISH"**

Wait 5 minutes for changes to propagate, then try again.

### Option B: Make App Internal (Alternative)

If your app is currently "External", you can make it "Internal":

1. Go to: https://console.cloud.google.com/apis/credentials/consent
2. Under **"User Type"**, check if it says "External"
3. If yes, you can only change this by creating a NEW project:
   - The project MUST be created with `@palaeome.org` account
   - The Organization must be set to `palaeome.org`
   - Then you can select "Internal" user type

**BUT**: Since you said the project IS in @palaeome.org, you should be able to set it to Internal:
1. Click **"EDIT APP"**
2. Change **"User Type"** from "External" to **"Internal"**
3. Save changes

Internal apps automatically bypass the consent screen for all users in your domain.

---

## 🔍 DIAGNOSTIC CHECKLIST

Before running the fixed script, verify:

- [ ] Project is in @palaeome.org organization
- [ ] OAuth consent screen has `photoslibrary` scope (NOT `.readonly`)
- [ ] Photos Library API is enabled
- [ ] Old token.json is deleted
- [ ] Script uses the corrected SCOPES line

Run this to verify scopes in your token:

```bash
python3 -c "
import json
with open('token.json') as f:
    data = json.load(f)
    print('Current scopes:', data.get('scopes'))
"
```

Should print:
```
Current scopes: ['https://www.googleapis.com/auth/photoslibrary']
```

NOT:
```
Current scopes: ['https://www.googleapis.com/auth/photoslibrary.readonly', ...]
```

---

## 🎯 WHY THIS FIXES THE PROBLEM

### The `.readonly` Paradox

Google designed scopes with this logic:

| Scope | Purpose | What You Can Access |
|-------|---------|-------------------|
| `photoslibrary.readonly` | Read-only for app-uploaded photos | Photos YOUR APP uploaded |
| `photoslibrary` | Full library access | ALL photos in library, including manually uploaded |

**Your use case:** Sync photos from albums you created manually
**Required scope:** `photoslibrary` (full access)

The error message "403 Insufficient Scopes" doesn't mean you lack permissions - it means the token literally doesn't have the scope needed to see non-app-uploaded photos!

### Why Auto-Discovery Failed

Your `find_target_albums()` function correctly searches for albums, but:
1. It gets a list of album metadata (titles, IDs)
2. This WORKS with `.readonly` scope
3. But when you try to `mediaItems().search(albumId=...)`:
   - API checks: "Does this album contain app-uploaded photos?"
   - Answer: No (you uploaded them manually)
   - API returns: 403 Forbidden

With the full `photoslibrary` scope:
1. `find_target_albums()` works the same
2. But `mediaItems().search()` succeeds because:
   - API checks: "Does token have library access?"
   - Answer: Yes
   - API returns: Your photos ✅

---

## 📞 STILL STUCK?

If after following all steps you still get errors:

1. **Check token scopes:**
   ```bash
   python3 -c "import json; print(json.load(open('token.json'))['scopes'])"
   ```

2. **Verify API is enabled:**
   ```bash
   gcloud services list --enabled --project=YOUR_PROJECT_ID | grep photo
   ```

3. **Test with minimal script:**
   ```python
   from google.oauth2.credentials import Credentials
   from googleapiclient.discovery import build
   
   SCOPES = ['https://www.googleapis.com/auth/photoslibrary']
   creds = Credentials.from_authorized_user_file('token.json', SCOPES)
   service = build('photoslibrary', 'v1', credentials=creds)
   
   result = service.albums().list(pageSize=10).execute()
   print(f"Found {len(result.get('albums', []))} albums")
   ```

4. **Check Workspace restrictions:**
   - Admin Console → Apps → Google Workspace → Google Photos
   - Ensure service is "ON for everyone"

---

## 🚀 EXPECTED OUTCOME

After fixing, you should see:

```
--- Codicum Parchment Sync & Batch Tool ---
INFO - Refreshing Access Token...
INFO - Verified Granular Scopes: ['https://www.googleapis.com/auth/photoslibrary']
INFO - Searching for Target Albums (Owned & Shared)...
INFO - Listing Owned Albums...
INFO -  - Found Owned Album: CODICUM MPO (ID: AbCdEfG123)
INFO -  - Found Owned Album: CODICUM FA (ID: XyZ789...)
INFO - Syncing Album: CODICUM MPO
INFO - MATCH: MPO001 in IMG_1234.jpg
INFO - MATCH: MPO002 in IMG_1235.jpg
...
```

Not this:
```
ERROR - Error searching album CODICUM MPO: <HttpError 403 "Insufficient authentication scopes">
```

---

**VERSION:** 1.0 - Correct Diagnosis  
**DATE:** 2025-01-17  
**STATUS:** Production Fix Ready
