#!/bin/sh
# Quick diagnostic script for mqtt-extractor add-on

cd /config/addons/mqtt-extractor || exit 1

echo "=== File Check ==="
ls -la

echo -e "\n=== JSON Validation ==="
if python3 -m json.tool config.json > /dev/null 2>&1; then
    echo "✅ JSON is valid"
else
    echo "❌ JSON is INVALID - check syntax"
    python3 -m json.tool config.json 2>&1 | head -5
fi

echo -e "\n=== Permissions ==="
if [ -x run.sh ]; then
    echo "✅ run.sh is executable"
else
    echo "❌ run.sh is NOT executable - run: chmod +x run.sh"
fi

echo -e "\n=== Required Files ==="
[ -f config.json ] && echo "✅ config.json" || echo "❌ config.json MISSING"
[ -f Dockerfile ] && echo "✅ Dockerfile" || echo "❌ Dockerfile MISSING"
[ -f run.sh ] && echo "✅ run.sh" || echo "❌ run.sh MISSING"
[ -f requirements.txt ] && echo "✅ requirements.txt" || echo "❌ requirements.txt MISSING"
[ -d mqtt_extractor ] && echo "✅ mqtt_extractor/" || echo "❌ mqtt_extractor/ MISSING"

echo -e "\n=== Config.json Contents Check ==="
python3 <<EOF
import json
try:
    with open('config.json') as f:
        data = json.load(f)
        print(f"Name: {data.get('name', 'MISSING')}")
        print(f"Slug: {data.get('slug', 'MISSING')}")
        print(f"Version: {data.get('version', 'MISSING')}")
        print(f"Arch: {data.get('arch', 'MISSING')}")
        print(f"Startup: {data.get('startup', 'MISSING')}")
        print(f"Boot: {data.get('boot', 'MISSING')}")
        print(f"Image: {data.get('image', 'MISSING')}")
        
        # Check slug matches folder name
        import os
        folder_name = os.path.basename(os.getcwd())
        if data.get('slug') == folder_name:
            print(f"✅ Slug matches folder name: {folder_name}")
        else:
            print(f"❌ Slug mismatch! Folder: {folder_name}, Slug: {data.get('slug')}")
except Exception as e:
    print(f"❌ Error reading config.json: {e}")
EOF

echo -e "\n=== Next Steps ==="
echo "1. If all checks pass, restart Home Assistant"
echo "2. Check logs: journalctl -u hassos-supervisor | grep -i addon"
echo "3. Look for add-on in: Settings → Add-ons → Add-on Store"

