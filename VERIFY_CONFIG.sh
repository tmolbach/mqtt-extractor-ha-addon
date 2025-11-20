#!/bin/sh
# Script to verify add-on configuration on Home Assistant

cd /config/addons/mqtt-extractor || exit 1

echo "=== Checking Add-on Configuration ==="
echo ""

echo "1. File Structure:"
ls -la
echo ""

echo "2. JSON Validation:"
if python3 -m json.tool config.json > /dev/null 2>&1; then
    echo "✅ config.json is valid JSON"
else
    echo "❌ config.json has JSON syntax errors:"
    python3 -m json.tool config.json 2>&1 | head -10
    exit 1
fi
echo ""

echo "3. Required Fields Check:"
python3 <<EOF
import json
import sys

required_fields = ['name', 'version', 'slug', 'description', 'arch', 'startup', 'boot', 'image']
required_sections = ['options', 'schema']

try:
    with open('config.json') as f:
        data = json.load(f)
        
    print("Checking required top-level fields...")
    missing = []
    for field in required_fields:
        if field not in data:
            missing.append(field)
        else:
            print(f"  ✅ {field}: {data[field]}")
    
    if missing:
        print(f"  ❌ Missing fields: {missing}")
        sys.exit(1)
    
    print("\nChecking required sections...")
    for section in required_sections:
        if section not in data:
            print(f"  ❌ Missing section: {section}")
            sys.exit(1)
        else:
            print(f"  ✅ {section}: present")
    
    # Check slug matches folder name
    import os
    folder_name = os.path.basename(os.getcwd())
    if data.get('slug') != folder_name:
        print(f"\n⚠️  WARNING: Slug '{data.get('slug')}' doesn't match folder name '{folder_name}'")
    else:
        print(f"\n✅ Slug matches folder name: {folder_name}")
    
    print("\n✅ All required fields present!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
EOF

echo ""
echo "4. File Permissions:"
if [ -x run.sh ]; then
    echo "✅ run.sh is executable"
else
    echo "❌ run.sh is NOT executable - run: chmod +x run.sh"
fi

echo ""
echo "5. Required Files:"
[ -f config.json ] && echo "✅ config.json" || echo "❌ config.json MISSING"
[ -f Dockerfile ] && echo "✅ Dockerfile" || echo "❌ Dockerfile MISSING"
[ -f run.sh ] && echo "✅ run.sh" || echo "❌ run.sh MISSING"
[ -f requirements.txt ] && echo "✅ requirements.txt" || echo "❌ requirements.txt MISSING"
[ -d mqtt_extractor ] && echo "✅ mqtt_extractor/" || echo "❌ mqtt_extractor/ MISSING"

echo ""
echo "=== Summary ==="
echo "If all checks pass, the add-on should be detected."
echo "If it's still not appearing, check supervisor logs for validation errors."

