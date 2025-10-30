#!/bin/bash

# Background scanner for remaining drives
LOG_FILE="/home/don/large_image_search_continued_$(date +%Y%m%d_%H%M%S).log"
PROGRESS_FILE="/tmp/image_scan_progress.txt"

log_message() {
    echo -e "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

echo "Starting background scan for F and J drives..."
echo "Progress will be logged to: $LOG_FILE"
echo "You can monitor with: tail -f $LOG_FILE"

# Start the scan in background
nohup bash -c '
LOG_FILE="/home/don/large_image_search_continued_$(date +%Y%m%d_%H%M%S).log"
DRIVES=("/mnt/f" "/mnt/j")
FILES_PROCESSED=0

log_message() {
    echo -e "$(date \"+%Y-%m-%d %H:%M:%S\") - $1" | tee -a "$LOG_FILE"
}

is_dropbox_path() {
    echo "$1" | grep -qi "dropbox"
}

get_image_info() {
    identify -ping -format "%w %h %B" "$1" 2>/dev/null || echo "0 0 0"
}

format_size() {
    local size=$1
    if [ $size -gt 1073741824 ]; then
        echo "$(echo "scale=2; $size/1073741824" | bc) GB"
    elif [ $size -gt 1048576 ]; then
        echo "$(echo "scale=2; $size/1048576" | bc) MB"
    else
        echo "$(echo "scale=2; $size/1024" | bc) KB"
    fi
}

log_message "=== CONTINUING IMAGE SEARCH ==="
log_message "Scanning remaining drives: F and J"

for drive in "${DRIVES[@]}"; do
    log_message "Starting $drive..."
    
    find "$drive" -type f \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" -o -iname "*.tif" \) 2>/dev/null | while read -r file; do
        FILES_PROCESSED=$((FILES_PROCESSED + 1))
        
        if [ $((FILES_PROCESSED % 500)) -eq 0 ]; then
            echo "Drive: $drive | Files: $FILES_PROCESSED" > /tmp/image_scan_progress.txt
        fi
        
        if is_dropbox_path "$file"; then
            continue
        fi
        
        basename=$(basename "$file")
        if echo "$basename" | grep -qi -E "(ortho|birdseye|giga)"; then
            info=$(get_image_info "$file")
            width=$(echo "$info" | awk "{print \$1}")
            height=$(echo "$info" | awk "{print \$2}")
            size=$(echo "$info" | awk "{print \$3}")
            
            if [ "$width" -gt 0 ] && [ "$height" -gt 0 ]; then
                formatted_size=$(format_size $size)
                log_message "FILENAME MATCH: $file ($width x $height, $formatted_size)"
            fi
        elif echo "$file" | grep -qi "\\.jpe\\?g$"; then
            info=$(get_image_info "$file")
            width=$(echo "$info" | awk "{print \$1}")
            height=$(echo "$info" | awk "{print \$2}")
            
            if [ "$width" -gt 25000 ] || [ "$height" -gt 25000 ]; then
                size=$(echo "$info" | awk "{print \$3}")
                formatted_size=$(format_size $size)
                log_message "SIZE MATCH: $file ($width x $height, $formatted_size)"
            fi
        fi
    done
    
    log_message "Completed $drive"
done

log_message "=== SCAN COMPLETE ==="
rm -f /tmp/image_scan_progress.txt
' > /tmp/image_scan_bg.out 2>&1 &

BG_PID=$!
echo "Background process started with PID: $BG_PID"
echo "Monitor progress: tail -f /tmp/image_scan_bg.out"
echo "Check if running: ps -p $BG_PID"
