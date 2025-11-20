# Troubleshooting - Add-on Not Appearing

## Issue: Add-on Not Showing in Home Assistant

If your add-on doesn't appear in the Add-ons list after copying files, try these steps:

## Step 1: Verify File Structure

Check that all required files are present:

```bash
cd /config/addons/mqtt-extractor
ls -la
```

You should see:
- ✅ config.json
- ✅ Dockerfile
- ✅ run.sh (executable)
- ✅ requirements.txt
- ✅ extractor.py
- ✅ mqtt_extractor/ directory

## Step 2: Validate config.json

Check for JSON syntax errors:

```bash
cd /config/addons/mqtt-extractor
python3 -m json.tool config.json
```

If there are errors, fix them. Common issues:
- Missing commas
- Trailing commas
- Invalid characters

## Step 3: Check Home Assistant Logs

Home Assistant logs will show if there are validation errors:

1. **Via Web UI:**
   - Go to Settings → System → Logs
   - Look for errors related to "addon" or "mqtt-extractor"

2. **Via SSH:**
   ```bash
   # Check supervisor logs
   journalctl -u hassos-supervisor -f
   
   # Or check Home Assistant logs
   journalctl -u home-assistant@homeassistant.service -f
   ```

3. **Check add-on store logs:**
   - Look for messages about "local add-ons" or "mqtt-extractor"

## Step 4: Restart Home Assistant

Home Assistant needs to scan for new local add-ons:

1. **Full Restart:**
   - Go to Settings → System → Restart
   - Wait for complete restart (2-3 minutes)

2. **Or restart Supervisor:**
   ```bash
   # Via SSH
   systemctl restart hassos-supervisor
   ```

## Step 5: Check Add-on Store Location

Make sure you're looking in the right place:

1. **Settings → Add-ons → Add-on Store**
2. Look for a section called **"Local add-ons"** or check the bottom of the list
3. Some versions show local add-ons separately from the store

## Step 6: Verify Permissions

Ensure files have correct permissions:

```bash
cd /config/addons/mqtt-extractor
chmod +x run.sh
chmod 644 config.json Dockerfile requirements.txt extractor.py
chmod -R 755 mqtt_extractor
```

## Step 7: Check config.json Requirements

Verify these required fields are present:

- ✅ `name` - Add-on name
- ✅ `version` - Version number
- ✅ `slug` - Must match folder name (`mqtt-extractor`)
- ✅ `description` - Description text
- ✅ `arch` - Supported architectures
- ✅ `startup` - Startup type (`application`)
- ✅ `boot` - Boot behavior (`auto`)
- ✅ `image` - Image name pattern (`mqtt-extractor-{arch}`)

## Step 8: Validate JSON Schema

The schema section must match the options section. Check that:
- All options have corresponding schema entries
- Schema types are valid (`str`, `int`, `bool`, etc.)
- Optional fields use `?` suffix (e.g., `str?`)

## Step 9: Check for Common Issues

### Issue: Slug Mismatch
The `slug` in config.json must exactly match the folder name:
- Folder: `mqtt-extractor`
- Slug: `mqtt-extractor` ✅

### Issue: Invalid Architecture
Check your system architecture:
```bash
uname -m
```
Common values:
- `x86_64` → use `amd64` in config.json
- `aarch64` → use `aarch64` in config.json
- `armv7l` → use `armv7` in config.json

### Issue: Missing Required Files
All these files must exist:
- config.json
- Dockerfile
- run.sh
- requirements.txt (can be empty but must exist)

## Step 10: Manual Validation

Test the config.json manually:

```bash
cd /config/addons/mqtt-extractor

# Validate JSON syntax
python3 <<EOF
import json
with open('config.json') as f:
    data = json.load(f)
    print("✅ JSON is valid")
    print(f"Name: {data.get('name')}")
    print(f"Slug: {data.get('slug')}")
    print(f"Version: {data.get('version')}")
EOF
```

## Step 11: Check Supervisor API

You can check if the add-on is detected via the Supervisor API:

```bash
# Via SSH or curl
curl -s http://localhost:4357/addons | python3 -m json.tool | grep -A 5 mqtt-extractor
```

## Step 12: Force Refresh

Sometimes a hard refresh helps:

1. **Clear browser cache** and reload the page
2. **Try a different browser**
3. **Check if add-on appears after waiting 5-10 minutes**

## Step 13: Check Home Assistant Version

Local add-ons require Home Assistant OS (not Supervised or Container):
- ✅ Home Assistant OS
- ❌ Home Assistant Supervised (may not work)
- ❌ Home Assistant Container (won't work)

## Still Not Working?

If none of these steps work:

1. **Check the exact error in logs:**
   ```bash
   journalctl -u hassos-supervisor | grep -i "mqtt-extractor\|local.*addon" | tail -20
   ```

2. **Verify the folder structure matches exactly:**
   ```bash
   tree /config/addons/mqtt-extractor
   ```

3. **Try renaming and re-adding:**
   ```bash
   mv /config/addons/mqtt-extractor /config/addons/mqtt-extractor-backup
   # Wait 1 minute
   mv /config/addons/mqtt-extractor-backup /config/addons/mqtt-extractor
   # Restart Home Assistant
   ```

4. **Check if other local add-ons work** - if they don't, it's a system issue

## Quick Diagnostic Script

Run this to check everything:

```bash
#!/bin/bash
cd /config/addons/mqtt-extractor

echo "=== File Check ==="
ls -la

echo -e "\n=== JSON Validation ==="
python3 -m json.tool config.json > /dev/null && echo "✅ JSON valid" || echo "❌ JSON invalid"

echo -e "\n=== Permissions ==="
ls -l run.sh | grep -q "rwx" && echo "✅ run.sh executable" || echo "❌ run.sh not executable"

echo -e "\n=== Required Files ==="
[ -f config.json ] && echo "✅ config.json" || echo "❌ config.json missing"
[ -f Dockerfile ] && echo "✅ Dockerfile" || echo "❌ Dockerfile missing"
[ -f run.sh ] && echo "✅ run.sh" || echo "❌ run.sh missing"
[ -f requirements.txt ] && echo "✅ requirements.txt" || echo "❌ requirements.txt missing"
[ -d mqtt_extractor ] && echo "✅ mqtt_extractor/" || echo "❌ mqtt_extractor/ missing"

echo -e "\n=== Config Check ==="
python3 <<EOF
import json
with open('config.json') as f:
    data = json.load(f)
    print(f"Name: {data.get('name', 'MISSING')}")
    print(f"Slug: {data.get('slug', 'MISSING')}")
    print(f"Version: {data.get('version', 'MISSING')}")
    print(f"Arch: {data.get('arch', 'MISSING')}")
EOF
```

Save this as `check-addon.sh`, make it executable, and run it.

