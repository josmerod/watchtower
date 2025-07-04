#!/bin/bash

# Simple validation test
echo "Testing basic validation..."

# Test 1: Script syntax
echo "Test 1: Script syntax"
if bash -n deploy.sh; then
    echo "✅ Deploy script syntax OK"
else
    echo "❌ Deploy script syntax failed"
fi

# Test 2: Required files
echo "Test 2: Required files"
missing_files=()
for file in deploy.sh requirements.txt src/web/fullstreamlit/app.py run_all_etl.sh; do
    if [[ ! -f "$file" ]]; then
        missing_files+=("$file")
    fi
done

if [[ ${#missing_files[@]} -eq 0 ]]; then
    echo "✅ All required files present"
else
    echo "❌ Missing files: ${missing_files[*]}"
fi

# Test 3: Python
echo "Test 3: Python"
if python3 -c "print('Hello')" >/dev/null 2>&1; then
    echo "✅ Python works"
else
    echo "❌ Python failed"
fi

echo "Basic validation complete!"