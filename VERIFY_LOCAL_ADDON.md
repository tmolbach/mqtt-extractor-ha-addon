# Verifying Local Add-on Detection

## The Issue

Home Assistant Supervisor logs show it's loading add-ons from Git repositories but **not scanning `/config/addons/`** for local add-ons. This suggests the supervisor might not be detecting local add-ons automatically.

## Solution 1: Check Supervisor API Directly

Test if the add-on is detected via the Supervisor API:

**Via Browser (from your Windows PC):**
```
http://10.30.1.254:4357/addons
```

Or check specifically for local add-ons:
```
http://10.30.1.254:4357/addons/local_mqtt-extractor
```

**Via SSH/Terminal:**
```bash
# Check all add-ons
curl -s http://localhost:4357/addons | python3 -m json.tool | grep -i mqtt

# Check local add-ons specifically
curl -s http://localhost:4357/addons | python3 -m json.tool | grep -A 10 "local_"
```

## Solution 2: Verify the Correct Path

In some Home Assistant versions, local add-ons might need to be in a different location. Check:

```bash
# Check if supervisor looks in /data/addons/local/
ls -la /data/addons/local/ 2>/dev/null || echo "Directory doesn't exist"

# Check current location
ls -la /config/addons/mqtt-extractor/
```

## Solution 3: Check if Repository Field is Needed

I've added `"repository": "local"` to config.json. Try:

1. **Update the config.json** on your Home Assistant system
2. **Restart Home Assistant** again
3. **Check if add-on appears**

## Solution 4: Manual Registration (If Needed)

If the supervisor still doesn't detect it, you might need to manually register it. However, this is unusual - local add-ons should be auto-detected.

## Solution 5: Check Home Assistant Version

Some older versions of Home Assistant might not support local add-ons in `/config/addons/`. Check your version:

**Via Web UI:**
- Settings → System → About
- Note the Supervisor version

**Via SSH:**
```bash
ha supervisor info
```

## What the Logs Tell Us

The supervisor logs show:
- ✅ Loading add-ons from Git repositories: `/data/addons/git/...`
- ✅ Loading core add-ons: `/data/addons/core`
- ❌ **NO mention of scanning `/config/addons/`**

This suggests either:
1. The supervisor doesn't scan `/config/addons/` automatically
2. There's a configuration needed to enable local add-on scanning
3. Local add-ons need to be in a different location

## Next Steps

1. **Check Supervisor API** (Solution 1) - This will tell us if the add-on is detected but just not showing in UI
2. **Verify file location** - Make sure files are in the right place
3. **Check Home Assistant version** - Ensure it supports local add-ons
4. **Try the updated config.json** with `"repository": "local"` field

## Alternative: Use Git Repository Method

If local add-ons don't work, you can create a Git repository:

1. **Create a GitHub repository** with your add-on
2. **Add it as a repository** in Home Assistant:
   - Settings → Add-ons → Add-on Store → Repositories
   - Add your GitHub repository URL
3. **Install from the repository**

This is more reliable but requires a Git repository.

