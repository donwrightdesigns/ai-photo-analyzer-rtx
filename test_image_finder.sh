#!/bin/bash

# Test version - search only current directory
LOG_FILE="/home/don/test_image_search_$(date +%Y%m%d_%H%M%S).log"
TEST_DIR="/mnt/j/TOOLS/ai-image-analyzer"

echo "Testing image finder on directory: $TEST_DIR"
echo "Testing image finder on directory: $TEST_DIR" > "$LOG_FILE"

find "$TEST_DIR" -maxdepth 1 -type f \( -iname "*.jpg" -o -iname "*.jpeg" \) | while read -r file; do
    echo "Testing file: $file"
    
    # Get image info
    image_info=$(identify -ping -format "%w %h %B" "$file" 2>/dev/null)
    if [ $? -eq 0 ] && [ -n "$image_info" ]; then
        width=$(echo "$image_info" | awk '{print $1}')
        height=$(echo "$image_info" | awk '{print $2}')
        byte_size=$(echo "$image_info" | awk '{print $3}')
        
        basename=$(basename "$file")
        
        echo "  File: $basename"
        echo "  Resolution: ${width}x${height}px"
        echo "  Size: $byte_size bytes"
        echo "  ---"
    else
        echo "  Could not get image info for $file"
    fi
done
