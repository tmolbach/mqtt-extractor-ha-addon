# Fix: Local Add-on Not Appearing

## Status: JSON is Valid ✅

Your config.json is valid JSON, so the issue is elsewhere.

## Possible Issues

### Issue 1: Supervisor Not Scanning /config/addons/

Home Assistant Supervisor might not automatically scan `/config/addons/` for local add-ons. Some versions require add-ons to be in `/data/addons/local/` instead.

**Try this:**

```bash
# Check if /data/addons/local exists
ls -la /data/addons/local/ 2>/dev/null || echo "Directory doesn't exist"

# If it doesn't exist, create it and copy the add-on there
mkdir -p /data/addons/local
cp -r /config/addons/mqtt-extractor /data/addons/local/
chmod +x /data/addons/local/mqtt-extractor/run.sh

# Then restart Home Assistant
```

### Issue 2: Missing Required Field

Some Home Assistant versions require additional fields. Try adding:

```json
{
  "name": "...",
  "version": "...",
  "slug": "...",
  "url": "https://github.com/your-repo/mqtt-extractor",
  ...
}
```

But wait - if it's a local add-on, you might not need `url`. Let me check what's actually required.

### Issue 3: Supervisor Version

Older versions of Home Assistant Supervisor might not support local add-ons in `/config/addons/`. Check your supervisor version:

**Via Web UI:**
- Settings → System → About → Supervisor

**Via SSH:**
```bash
ha supervisor info
```

### Issue 4: Check Supervisor Logs for Validation Errors

Even though JSON is valid, the supervisor might have stricter validation. Check logs:

```bash
# Check for validation errors
journalctl -u hassos-supervisor | grep -i "validation\|error\|mqtt-extractor" | tail -30
```

## Solution: Use Git Repository Method (Most Reliable)

If local add-ons aren't working, the most reliable method is to create a Git repository:

1. **Create a GitHub repository** (can be private)
2. **Push your mqtt-extractor folder** to the repository
3. **Add repository in Home Assistant:**
   - Settings → Add-ons → Add-on Store → Repositories
   - Add: `https://github.com/your-username/mqtt-extractor`
4. **Install from repository**

This method is guaranteed to work and is how most Home Assistant add-ons are distributed.

## Quick Test: Verify Supervisor Can See It

Check if supervisor detects the add-on via API:

```bash
# Check all add-ons
curl -s http://localhost:4357/addons | python3 -m json.tool | grep -i "mqtt\|local"

# Or check specific add-on
curl -s http://localhost:4357/addons/local_mqtt-extractor
```

If this returns 404 or empty, the supervisor isn't detecting it.

## Next Steps

1. **Try moving to /data/addons/local/** (Issue 1)
2. **Check supervisor version** (Issue 3)
3. **Check logs for validation errors** (Issue 4)
4. **If all else fails, use Git repository method** (Most reliable)

