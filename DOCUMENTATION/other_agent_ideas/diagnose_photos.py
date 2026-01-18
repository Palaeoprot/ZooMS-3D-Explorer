#!/usr/bin/env python3
"""
Quick Google Photos API Configuration Checker
Verifies scopes, token, and API access
"""

import os
import json
import sys

def check_files():
    """Check if required files exist"""
    print("=" * 60)
    print("📁 FILE CHECK")
    print("=" * 60)
    
    files = {
        'credentials.json': 'OAuth credentials',
        'token.json': 'Access token (created after auth)',
    }
    
    all_good = True
    for filename, description in files.items():
        if os.path.exists(filename):
            print(f"✅ {filename} - {description}")
        else:
            print(f"❌ {filename} - {description} [MISSING]")
            if filename == 'credentials.json':
                all_good = False
    
    return all_good

def check_credentials():
    """Analyze credentials.json"""
    print("\n" + "=" * 60)
    print("🔑 CREDENTIALS ANALYSIS")
    print("=" * 60)
    
    if not os.path.exists('credentials.json'):
        print("❌ credentials.json not found")
        return False
    
    try:
        with open('credentials.json') as f:
            creds = json.load(f)
        
        if 'installed' in creds:
            client_info = creds['installed']
            app_type = "Desktop Application ✅"
        elif 'web' in creds:
            client_info = creds['web']
            app_type = "Web Application (Should be Desktop!)"
        else:
            print("❌ Unknown credential format")
            return False
        
        project_id = client_info.get('project_id', 'unknown')
        client_id = client_info.get('client_id', '')
        
        print(f"App Type: {app_type}")
        print(f"Project ID: {project_id}")
        print(f"Client ID: {client_id[:50]}...")
        
        # Check for org
        if 'palaeome' in project_id.lower() or 'palaeome' in client_id.lower():
            print("✅ Appears to be @palaeome.org project")
        else:
            print("⚠️  Cannot confirm project organization")
        
        return True
        
    except Exception as e:
        print(f"❌ Error reading credentials: {e}")
        return False

def check_token():
    """Analyze token.json and check scopes"""
    print("\n" + "=" * 60)
    print("🎫 TOKEN & SCOPE ANALYSIS")
    print("=" * 60)
    
    if not os.path.exists('token.json'):
        print("ℹ️  No token.json (not yet authenticated)")
        print("   This is normal for first run")
        return True
    
    try:
        with open('token.json') as f:
            token = json.load(f)
        
        scopes = token.get('scopes', [])
        print(f"Token contains {len(scopes)} scope(s):")
        
        has_correct_scope = False
        for scope in scopes:
            if scope == 'https://www.googleapis.com/auth/photoslibrary':
                print(f"  ✅ {scope} [CORRECT - Full library access]")
                has_correct_scope = True
            elif 'photoslibrary.readonly' in scope:
                print(f"  ❌ {scope} [WRONG - Only app-uploaded photos!]")
            elif 'photoslibrary' in scope:
                print(f"  ⚠️  {scope}")
            else:
                print(f"  ℹ️  {scope}")
        
        if not has_correct_scope and any('readonly' in s for s in scopes):
            print("\n" + "!" * 60)
            print("CRITICAL ISSUE: Token has .readonly scope!")
            print("This only shows app-uploaded photos, not your library.")
            print("\nFIX:")
            print("  1. Delete token.json")
            print("  2. Update SCOPES in script to:")
            print("     SCOPES = ['https://www.googleapis.com/auth/photoslibrary']")
            print("  3. Run script again")
            print("!" * 60)
            return False
        
        if has_correct_scope:
            print("\n✅ Token has correct scope!")
        
        return True
        
    except Exception as e:
        print(f"❌ Error reading token: {e}")
        return False

def check_script():
    """Check if script has correct scopes defined"""
    print("\n" + "=" * 60)
    print("📝 SCRIPT CONFIGURATION CHECK")
    print("=" * 60)
    
    if not os.path.exists('sync_parchment_data.py'):
        print("⚠️  sync_parchment_data.py not found in current directory")
        return True
    
    try:
        with open('sync_parchment_data.py') as f:
            content = f.read()
        
        # Check for scope definition
        if "photoslibrary.readonly" in content and "SCOPES = [" in content:
            print("❌ Script contains '.readonly' scope")
            print("   This is the WRONG scope!")
            print("\n   Change line ~19 from:")
            print("     SCOPES = ['https://www.googleapis.com/auth/photoslibrary.readonly']")
            print("   To:")
            print("     SCOPES = ['https://www.googleapis.com/auth/photoslibrary']")
            return False
        elif "https://www.googleapis.com/auth/photoslibrary" in content:
            print("✅ Script has correct scope configuration")
            return True
        else:
            print("⚠️  Could not verify scope configuration in script")
            return True
            
    except Exception as e:
        print(f"⚠️  Could not read script: {e}")
        return True

def provide_summary(checks):
    """Provide summary and next steps"""
    print("\n" + "=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    
    all_passed = all(checks.values())
    
    if all_passed:
        print("✅ All checks passed!")
        print("\nNext steps:")
        if not os.path.exists('token.json'):
            print("  1. Run: python3 sync_parchment_data.py")
            print("  2. Browser will open for authentication")
            print("  3. Select your @palaeome.org account")
            print("  4. Check the box: 'See and download all your Google Photos'")
            print("  5. Click Continue")
        else:
            print("  1. Run: python3 sync_parchment_data.py")
            print("  2. Script should find and sync your albums")
    else:
        print("❌ Issues detected (see above)")
        print("\nPriority fixes:")
        
        if not checks.get('files'):
            print("  1. Obtain credentials.json from Google Cloud Console")
            print("     https://console.cloud.google.com/apis/credentials")
        
        if not checks.get('script'):
            print("  2. Fix SCOPES in sync_parchment_data.py")
            print("     Use: SCOPES = ['https://www.googleapis.com/auth/photoslibrary']")
        
        if not checks.get('token'):
            print("  3. Delete token.json and re-authenticate:")
            print("     rm token.json")
            print("     python3 sync_parchment_data.py")

def main():
    print("\n" + "=" * 60)
    print("🔍 GOOGLE PHOTOS API DIAGNOSTIC")
    print("=" * 60)
    print()
    
    checks = {}
    checks['files'] = check_files()
    checks['credentials'] = check_credentials()
    checks['token'] = check_token()
    checks['script'] = check_script()
    
    provide_summary(checks)
    
    print("\n" + "=" * 60)
    print("For detailed fix instructions, see:")
    print("  PHOTOS_API_FIX_GUIDE.md")
    print("=" * 60 + "\n")

if __name__ == '__main__':
    main()
