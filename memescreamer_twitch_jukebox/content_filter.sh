#!/bin/bash
# Content filter using Hotdog_NotHotdog CLIP-based NSFW detector
# https://github.com/CreativeMayhemLtd/memescreamer_Hotdog_NotHotdog
# 
# Input: $1 = path to media file
# Output: exit 0 = approved (SFW), exit 1 = rejected (NSFW)
#         stdout = rejection reason (optional)
#
# License: Dual-licensed (MIT for non-commercial, paid license for commercial use)
# See https://github.com/CreativeMayhemLtd/memescreamer_Hotdog_NotHotdog/blob/main/LICENSE

FILE="$1"

if [ ! -f "$FILE" ]; then
    echo "File not found"
    exit 1
fi

# Run the Hotdog_NotHotdog NSFW classifier
# Uses rules mode by default - for learned mode, train a classifier first
cd /app/hotdog_nothotdog

# Create temp output file
TEMP_CSV=$(mktemp /tmp/nsfw_check_XXXXXX.csv)

# Run the classifier on the single file
python Hotdog_NotHotDog.py "$(dirname "$FILE")" \
    --out "$TEMP_CSV" \
    --threshold 0.20 \
    --mode rules \
    2>/dev/null

# Check the result
if [ -f "$TEMP_CSV" ]; then
    # Get the decision for our specific file
    FILENAME=$(basename "$FILE")
    DECISION=$(grep "$FILENAME" "$TEMP_CSV" | cut -d',' -f13 2>/dev/null || echo "sfw")
    
    # Clean up
    rm -f "$TEMP_CSV"
    
    if [ "$DECISION" = "nsfw" ]; then
        echo "Content flagged as NSFW by Hotdog_NotHotdog classifier"
        exit 1
    fi
fi

# If we got here, content is SFW or couldn't be classified
exit 0
