# Setting Up Git Repository for Home Assistant Add-on

## Issue: Repository Authentication Error

The error indicates Home Assistant can't access your GitHub repository. This usually means:
1. **Repository is private** - Home Assistant can't access private repos without authentication
2. **Repository doesn't exist** - Check the URL
3. **URL format is wrong** - Must be exact GitHub URL

## Solution 1: Make Repository Public (Easiest)

1. **Go to your GitHub repository**
2. **Click Settings** → Scroll down to **"Danger Zone"**
3. **Click "Change visibility"** → **"Make public"**
4. **Confirm** the change

Then try adding the repository again in Home Assistant.

## Solution 2: Use Public GitHub Repository URL Format

Make sure you're using the correct format:

**Correct:**
```
https://github.com/tmolbach/mqtt-extractor-ha-addon
```

**Wrong:**
```
https://github.com/tmolbach/mqtt-extractor-ha-addon.git
git@github.com:tmolbach/mqtt-extractor-ha-addon.git
```

## Solution 3: Verify Repository Structure

Your GitHub repository should have this structure:

```
mqtt-extractor-ha-addon/
└── mqtt-extractor/
    ├── config.json
    ├── Dockerfile
    ├── run.sh
    ├── requirements.txt
    ├── extractor.py
    └── mqtt_extractor/
        └── ...
```

**Important:** The add-on folder (`mqtt-extractor`) must be inside the repository root, not the repository itself.

## Solution 4: Check Repository Exists

Verify your repository is accessible:
- Open: `https://github.com/tmolbach/mqtt-extractor-ha-addon` in your browser
- You should see the files
- If you get 404, the repository doesn't exist or is private

## Solution 5: Alternative - Use GitHub Releases

If you want to keep the repository private, you can:
1. Create a **public release** with the add-on files
2. Use the release URL (but this is more complex)

## Quick Fix Steps

1. **Make repository public** (if it's private)
2. **Verify the URL** in Home Assistant is exactly: `https://github.com/tmolbach/mqtt-extractor-ha-addon`
3. **Check repository structure** - ensure `mqtt-extractor/` folder is in the root
4. **Try adding repository again** in Home Assistant

## Verify Repository Structure

Your repository should look like this when viewed on GitHub:

```
Repository: mqtt-extractor-ha-addon
├── mqtt-extractor/
│   ├── config.json
│   ├── Dockerfile
│   ├── run.sh
│   ├── requirements.txt
│   ├── extractor.py
│   └── mqtt_extractor/
│       └── ...
```

If your files are directly in the root (not in a `mqtt-extractor/` subfolder), that's the problem!

## Correct Repository Structure

The repository should have the add-on in a subfolder matching the slug:

```
mqtt-extractor-ha-addon/          ← Repository root
└── mqtt-extractor/               ← Add-on folder (matches slug)
    ├── config.json
    ├── Dockerfile
    └── ...
```

This is how Home Assistant expects add-on repositories to be structured.

