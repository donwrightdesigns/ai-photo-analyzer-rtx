# AI Image Analyzer - Lightroom Plugin v2.0

A streamlined Lightroom plugin that follows the Topaz Photo AI workflow pattern - send selected images to the external desktop application for processing, then refresh metadata in Lightroom.

## Installation

1. **Install the Desktop App**: Ensure the AI Image Analyzer desktop application is installed and working
2. **Install Plugin**: Copy the `ai-image-analyzer-v2.lrplugin` folder to your Lightroom plugins directory
3. **Enable Plugin**: In Lightroom, go to File → Plug-in Manager → Add and select the plugin folder

## Usage

### Quick Start
1. Select one or more images in Lightroom Library module
2. Go to Library → Plug-in Extras → "Send to AI Image Analyzer"
3. The desktop app will launch automatically with your selected images
4. Process images in the desktop app
5. Return to Lightroom and use Library → Plug-in Extras → "Refresh Metadata from XMP"

### Processing Modes

#### General Processing
- **Send to AI Image Analyzer**: Launches desktop app with selected images in normal mode
- User can choose processing settings in the desktop GUI

#### Archive Mode
- **AI Image Analyzer - Archive Mode**: Launches in archive mode for comprehensive analysis
- Processes ALL selected images with full AI tagging and descriptions
- Creates searchable metadata for entire image archive
- Optimized for batch processing large collections

#### Curated Mode
- **AI Image Analyzer - Curated Mode**: Launches in curated mode for quality-focused workflow
- Applies quality filtering to select only the best images
- Faster processing focused on portfolio/delivery ready images
- Higher quality threshold for curation

### Metadata Refresh
- **Refresh Metadata from XMP**: Forces Lightroom to re-read XMP sidecar files
- Use this after desktop app processing is complete
- Updates keywords, ratings, descriptions, and other AI-generated metadata
- Shows progress dialog during refresh

## Features

- **Seamless Integration**: Works just like Topaz Photo AI or other external processors
- **No Complex UI**: Simple menu items - all processing done in full-featured desktop app
- **XMP Compatibility**: Uses XMP sidecar files for maximum Lightroom compatibility
- **Batch Processing**: Handle multiple images simultaneously
- **Mode Selection**: Archive mode for comprehensive tagging, Curated mode for quality filtering
- **Progress Tracking**: Clear feedback during processing and metadata refresh

## Technical Details

- **File Communication**: Uses temporary files to pass image lists to desktop app
- **Metadata Format**: XMP sidecar files ensure Lightroom compatibility
- **Auto-Discovery**: Automatically finds desktop app in standard installation locations
- **Error Handling**: Clear error messages for troubleshooting

## Requirements

- Adobe Lightroom Classic CC 2015.2.1 or later
- AI Image Analyzer desktop application installed
- Python 3.8+ (if running from source)

## Troubleshooting

### "AI Image Analyzer not found"
- Ensure the desktop app is installed in `C:\Program Files\AI Image Analyzer\`
- Or place `main.py` in the same directory as the plugin

### "No images selected"
- Select one or more images in the Library module before running
- Plugin works with any supported image format

### Metadata not updating
- Use "Refresh Metadata from XMP" after processing completes
- Check that XMP files were created next to your images
- Ensure Lightroom has write permissions to image directories

### Command line integration
The desktop app supports these command line arguments when launched from Lightroom:
- `--images path/to/image_list.txt` - Process specific images
- `--mode archive` - Force archive mode processing  
- `--mode curated` - Force curated mode processing
