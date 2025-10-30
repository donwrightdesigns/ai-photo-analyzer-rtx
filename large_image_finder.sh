#!/bin/bash

# Large Image Finder Script
LOG_FILE="/home/don/large_image_search_$(date +%Y%m%d_%H%M%S).log"
TEMP_FILE="/tmp/image_search_temp.txt"
DRIVES=("/mnt/e" "/mnt/f" "/mnt/j")

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_message() {
    echo -e "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

is_dropbox_path() {
    local path="$1"
    if echo "$path" | grep -qi "dropbox"; then
        return 0
    else
        return 1
    fi
}

get_image_info() {
    local file_path="$1"
    local temp_info
    temp_info=$(identify -ping -format "%w %h %B" "$file_path" 2>/dev/null)
    if [ $? -eq 0 ] && [ -n "$temp_info" ]; then
        echo "$temp_info"
    else
        echo "0 0 0"
    fi
}

format_size() {
    local size=$1
    if [ $size -gt 1073741824 ]; then
        echo "$(echo "scale=2; $size/1073741824" | bc) GB"
    elif [ $size -gt 1048576 ]; then
        echo "$(echo "scale=2; $size/1048576" | bc) MB"
    elif [ $size -gt 1024 ]; then
        echo "$(echo "scale=2; $size/1024" | bc) KB"
    else
        echo "${size} B"
    fi
}

matches_filename_criteria() {
    local filename="$1"
    local basename=$(basename "$filename")
    if echo "$basename" | grep -qi -E "(ortho|birdseye|giga)"; then
        return 0
    else
        return 1
    fi
}

process_image() {
    local file_path="$1"
    local file_size="$2"
    
    if is_dropbox_path "$file_path"; then
        return 0
    fi
    
    local image_info=$(get_image_info "$file_path")
    local width=$(echo "$image_info" | awk '{print $1}')
    local height=$(echo "$image_info" | awk '{print $2}')
    local byte_size=$(echo "$image_info" | awk '{print $3}')
    
    if [ "$width" -eq 0 ] && [ "$height" -eq 0 ]; then
        return 0
    fi
    
    local basename=$(basename "$file_path")
    local extension="${basename##*.}"
    local matches_criteria=false
    local reason=""
    
    if matches_filename_criteria "$file_path"; then
        matches_criteria=true
        reason="Filename contains ortho/birdseye/giga"
    fi
    
    if echo "$extension" | grep -qi -E "(jpg|jpeg)"; then
        if [ "$width" -gt 25000 ] || [ "$height" -gt 25000 ]; then
            matches_criteria=true
            if [ -n "$reason" ]; then
                reason="$reason + Large JPEG (${width}x${height})"
            else
                reason="Large JPEG (${width}x${height}px)"
            fi
        fi
    fi
    
    if [ "$matches_criteria" = true ]; then
        local formatted_size=$(format_size $byte_size)
        
        local output="MATCH: $file_path
  Name: $basename
  Resolution: ${width}x${height}px
  File Size: $formatted_size
  Reason: $reason
  ----------------------------------------"
        
        echo -e "${GREEN}$output${NC}"
        echo "$output" >> "$LOG_FILE"
        echo "$file_path" >> "$TEMP_FILE"
    fi
}

search_drive() {
    local drive_path="$1"
    
    if [ ! -d "$drive_path" ]; then
        log_message "${RED}Drive $drive_path not found or not accessible${NC}"
        return 1
    fi
    
    log_message "${BLUE}Starting search on drive: $drive_path${NC}"
    
    find "$drive_path" -type f \( \
        -iname "*.jpg" -o \
        -iname "*.jpeg" -o \
        -iname "*.png" -o \
        -iname "*.tiff" -o \
        -iname "*.tif" -o \
        -iname "*.bmp" -o \
        -iname "*.gif" -o \
        -iname "*.raw" -o \
        -iname "*.cr2" -o \
        -iname "*.nef" -o \
        -iname "*.arw" -o \
        -iname "*.dng" -o \
        -iname "*.heic" -o \
        -iname "*.webp" \
    \) 2>/dev/null | while read -r file; do
        local file_size=$(stat -c%s "$file" 2>/dev/null || echo "0")
        process_image "$file" "$file_size"
    done
    
    log_message "${BLUE}Completed search on drive: $drive_path${NC}"
}

main() {
    log_message "${YELLOW}========================================${NC}"
    log_message "${YELLOW}Starting Large Image Search${NC}"
    log_message "${YELLOW}Criteria:${NC}"
    log_message "${YELLOW}1. Filenames containing 'ortho', 'birdseye', or 'giga'${NC}"
    log_message "${YELLOW}2. JPEG files larger than 25000px width or height${NC}"
    log_message "${YELLOW}3. Excluding Dropbox folders${NC}"
    log_message "${YELLOW}========================================${NC}"
    
    > "$TEMP_FILE"
    
    for drive in "${DRIVES[@]}"; do
        search_drive "$drive"
    done
    
    local total_matches=0
    if [ -f "$TEMP_FILE" ]; then
        total_matches=$(wc -l < "$TEMP_FILE")
    fi
    
    log_message "${YELLOW}========================================${NC}"
    log_message "${GREEN}Search completed!${NC}"
    log_message "${GREEN}Total matches found: $total_matches${NC}"
    log_message "${GREEN}Results logged to: $LOG_FILE${NC}"
    log_message "${YELLOW}========================================${NC}"
    
    rm -f "$TEMP_FILE"
}

if ! command -v identify >/dev/null 2>&1; then
    echo "Error: ImageMagick 'identify' command not found."
    exit 1
fi

if ! command -v bc >/dev/null 2>&1; then
    echo "Installing bc for calculations..."
    sudo apt install -y bc
fi

main
