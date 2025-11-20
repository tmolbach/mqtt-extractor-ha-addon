# How to Check Home Assistant Logs

## Method 1: Via Home Assistant Web UI (Easiest)

1. **Open Home Assistant** in your browser
2. **Go to Settings → System → Logs**
3. **Look for errors** related to:
   - "addon"
   - "mqtt-extractor"
   - "local add-on"
   - "validation"
   - "config.json"

4. **Filter logs:**
   - Use the search/filter box at the top
   - Search for: `addon` or `mqtt-extractor`

## Method 2: Via SSH (If Available)

If you have SSH access to Home Assistant OS:

```bash
# Check supervisor logs
journalctl -u hassos-supervisor -n 100 | grep -i "addon\|mqtt-extractor"

# Or view all recent supervisor logs
journalctl -u hassos-supervisor -n 200

# Check for errors specifically
journalctl -u hassos-supervisor -p err -n 50
```

## Method 3: Via Home Assistant Terminal Add-on

1. **Install "SSH & Web Terminal" add-on** if not already installed
2. **Open the terminal** from the add-on
3. **Run:**
   ```bash
   journalctl -u hassos-supervisor -n 100 | grep -i addon
   ```

## Method 4: Check Supervisor API

You can check if the add-on is detected via the Supervisor API:

**Via SSH or Terminal Add-on:**
```bash
# Check all add-ons
curl -s http://localhost:4357/addons | python3 -m json.tool | grep -i mqtt

# Or check specific add-on
curl -s http://localhost:4357/addons/local_mqtt-extractor
```

**Via Browser (from your Windows PC):**
```
http://homeassistant.local:4357/addons
```
(Replace `homeassistant.local` with your HA IP if needed)

## Method 5: Check Add-on Store Directly

Sometimes the add-on appears but isn't obvious:

1. **Go to Settings → Add-ons → Add-on Store**
2. **Look for:**
   - A section labeled "Local add-ons" or "Local"
   - Scroll to the very bottom of the store
   - Check if there's a filter/tab for "Local"
3. **Try refreshing** the page (Ctrl+F5 or Cmd+Shift+R)

## Method 6: Validate Files Manually

Run these checks via SSH or Terminal Add-on:

```bash
cd /config/addons/mqtt-extractor

# Check JSON validity
python3 -m json.tool config.json

# Check file structure
ls -la

# Check permissions
ls -l run.sh

# Verify slug matches folder
python3 <<EOF
import json
import os
with open('config.json') as f:
    data = json.load(f)
    folder = os.path.basename(os.getcwd())
    print(f"Folder: {folder}")
    print(f"Slug: {data.get('slug')}")
    print(f"Match: {folder == data.get('slug')}")
EOF
```

## What to Look For in Logs

Common error messages that prevent add-on detection:

1. **JSON Syntax Error:**
   ```
   Error parsing config.json: Expecting property name
   ```

2. **Missing Required Field:**
   ```
   Missing required field: 'slug'
   ```

3. **Slug Mismatch:**
   ```
   Slug 'mqtt-extractor' does not match folder name
   ```

4. **Architecture Mismatch:**
   ```
   Architecture 'amd64' not supported
   ```

5. **Invalid Schema:**
   ```
   Schema validation failed for mqtt-extractor
   ```

## Quick Check Commands

Run these one by one and note any errors:

```bash
# 1. Navigate to add-on directory
cd /config/addons/mqtt-extractor

# 2. Check JSON syntax
python3 -m json.tool config.json > /dev/null && echo "✅ JSON OK" || echo "❌ JSON ERROR"

# 3. Check required files exist
[ -f config.json ] && echo "✅ config.json" || echo "❌ Missing config.json"
[ -f Dockerfile ] && echo "✅ Dockerfile" || echo "❌ Missing Dockerfile"
[ -f run.sh ] && echo "✅ run.sh" || echo "❌ Missing run.sh"
[ -d mqtt_extractor ] && echo "✅ mqtt_extractor/" || echo "❌ Missing mqtt_extractor/"

# 4. Check run.sh is executable
[ -x run.sh ] && echo "✅ run.sh executable" || echo "❌ run.sh NOT executable"

# 5. Verify slug
python3 <<EOF
import json, os
with open('config.json') as f:
    data = json.load(f)
    folder = os.path.basename(os.getcwd())
    slug = data.get('slug', '')
    print(f"Folder: {folder}, Slug: {slug}, Match: {folder == slug}")
EOF
```

## Still Not Working?

If the add-on still doesn't appear after:
1. ✅ All files are present
2. ✅ JSON is valid
3. ✅ Permissions are correct
4. ✅ Home Assistant has been restarted
5. ✅ No errors in logs

Then try:
1. **Wait 5-10 minutes** - sometimes there's a delay
2. **Hard refresh** the browser (Ctrl+Shift+R)
3. **Try a different browser**
4. **Check Home Assistant version** - ensure you're on Home Assistant OS (not Supervised)
5. **Check if other local add-ons work** - if they don't, it's a system issue

