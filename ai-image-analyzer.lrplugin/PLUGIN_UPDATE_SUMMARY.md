# AI Image Analyzer Lightroom Plugin - Update Summary

## Version 2.0.0 - January 2025

This update brings the Lightroom plugin up to date with all the latest features from the web GUI version.

## 🆕 **New Features Added**

### 1. **3-Model Support System**
- ✅ **Ollama (Local)** - Local LLaVA models via Ollama server
- ✅ **Google Gemini (Cloud)** - Google's cloud-based Gemini models  
- ✅ **BakLLaVA (Local)** - Local BakLLaVA quantized models

### 2. **Prompt Profile Selection**
The plugin now includes 6 different analysis perspectives:
- **Professional Art Critic** - Gallery curator perspective focusing on artistic merit
- **Family Memory Keeper** - Personal photo organizer focused on emotional value
- **Commercial Photographer** - Industry professional evaluating marketability
- **Social Media Expert** - Digital content creator focused on engagement
- **Documentary Journalist** - Photojournalist perspective emphasizing story
- **Travel Content Creator** - Travel photographer focused on destination appeal

### 3. **XMP Sidecar File Support**
- ✅ **XMP Sidecar Generation** - Creates `.xmp` files alongside images
- ✅ **Adobe-Compatible Format** - Works with Lightroom, Photoshop, Bridge
- ✅ **Non-Destructive** - Doesn't modify original image files
- ✅ **Full Metadata** - Includes ratings, categories, tags, and critiques

### 4. **Enhanced API Integration**
- ✅ **Updated Endpoints** - Compatible with latest Flask web service
- ✅ **Prompt Profile Sync** - Automatically syncs selected profile with server
- ✅ **Model-Agnostic Status** - Works with any available model type
- ✅ **Improved Error Handling** - Better fallback options and user messaging

## 🔧 **Technical Improvements**

### Settings Panel (`Settings.lua`)
- Added 3-model selection dropdown
- Added analysis perspective dropdown with 6 profile options  
- Updated default to Gemini model and XMP sidecar files
- Enhanced UI descriptions reflecting new capabilities

### API Module (`AIImageAnalyzerAPI.lua`) 
- Updated preference handling for new model types and prompt profiles
- Added `setPromptProfile()` function to sync with server
- Improved service status checking to work with all models
- Enhanced metadata handling for both EXIF and XMP workflows

### Plugin Info (`Info.lua`)
- Bumped version to 2.0.0 to reflect major feature additions
- Updated compatibility info

## 🎯 **How to Use New Features**

### Setting Up the Plugin
1. **Install the updated plugin** in Lightroom's Plugin Manager
2. **Configure settings** via `Library > Plug-in Extras > Plugin Settings`
3. **Choose your model**: Ollama, Gemini, or BakLLaVA
4. **Select analysis perspective** based on your workflow needs
5. **Enable XMP sidecars** for non-destructive metadata storage

### Using Different Analysis Perspectives
- **Art Galleries**: Use "Professional Art Critic" for exhibition-quality assessment
- **Family Photos**: Use "Family Memory Keeper" for sentimental value evaluation  
- **Commercial Work**: Use "Commercial Photographer" for client deliverability
- **Social Media**: Use "Social Media Expert" for engagement potential
- **Journalism**: Use "Documentary Journalist" for storytelling strength
- **Travel**: Use "Travel Content Creator" for wanderlust and destination appeal

### XMP Sidecar Benefits
- **Safe**: Original images remain untouched
- **Portable**: XMP files travel with images
- **Compatible**: Works across Adobe Creative Suite
- **Searchable**: Metadata is indexed by Lightroom
- **Backup-Friendly**: Text files are easy to backup and sync

## 🔄 **Compatibility**

- **Lightroom Classic**: Fully compatible
- **Web Service**: Requires Flask web service version 2.0+
- **Models**: Compatible with all supported AI models
- **File Formats**: All image formats supported by Lightroom

## 📋 **Migration Notes**

If upgrading from version 1.x:
1. **Settings will be preserved** but new options will use defaults
2. **Review model selection** - default changed from LLaVA to Gemini
3. **Check XMP setting** - now enabled by default
4. **Select prompt profile** - defaults to Professional Art Critic

## 🔗 **Integration**

The plugin now fully integrates with the updated Flask web service, providing:
- ✅ Consistent analysis results across web GUI and Lightroom
- ✅ Shared prompt profiles and model configurations
- ✅ Compatible metadata formats
- ✅ Synchronized feature sets

This update ensures the Lightroom plugin provides feature parity with the web interface while maintaining the familiar Lightroom workflow.
