# AI Photo Analyzer and XMP culling with HTML GUI and Adobe LIGHTROOM plugin 

A comprehensive image analysis system using AI models to automatically tag, categorize, assess and critique photographs helping organize, enormous libraries, or portfolios. This project includes standalone scripts, a web GUI, and a Lightroom plugin.

This was created by a professional photographer 20 years of photo archives 

## Features

- **Three AI Model Options**: 
  - **BakLLaVA** (Local): Mistral-based multimodal model with excellent image understanding
  - **LLaVA via Ollama** (Local): Fast local processing with good quality
  - **Google Gemini** (Cloud): High-quality cloud-based analysis
- **Goal-Based Processing**: Optimized workflows for different use cases
  - Archive Culling: Fast keep/delete decisions for large collections
  - Gallery Selection: Detailed artistic analysis for curation
  - Catalog Organization: Comprehensive tagging and categorization
  - Model Comparison: A/B testing between different AI models
- **EXIF Integration**: Automatically writes analysis results to image metadata
- **XMP Sidecar Files**: Non-destructive Lightroom-compatible metadata
- **Web Interface**: Real-time processing with WebSocket updates and 3-model support
- **Lightroom Plugin**: Full-featured integration with Adobe Lightroom (complete feature parity with web GUI)
- **Batch Processing**: Process entire directories of images efficiently
- **Smart Rating System**: Preserves existing high ratings while adding AI-generated scores
- **Test Mode**: Validate analysis on first 20 images before full processing

## Project Structure

```
ai-image-analyzer/
├── scripts/                              # Standalone analysis scripts
│   ├── enhanced_unified_analyzer_v3.py  # ⭐ MAIN SCRIPT - 3 models, goal-based
│   ├── gemini_analyzer.py              # Google Gemini-based analyzer
│   ├── llava_analyzer.py               # Ollama LLaVA-based analyzer
│   ├── bakllava_simple.py              # BakLLaVA placeholder analyzer
│   └── bakllava_analyzer.py            # BakLLaVA PyLLMCore integration
├── models/
│   └── download_bakllava.py             # BakLLaVA model downloader
├── web/                                 # Flask web application
│   ├── app.py                          # Main Flask application
│   ├── templates/                      # HTML templates
│   └── static/                         # CSS, JS, and images
├── ai-image-analyzer.lrplugin/          # Adobe Lightroom plugin files (.lrplugin folder)
├── docs/                               # Documentation
├── config/                             # Configuration files
└── tests/                              # Test files
```

## Installation

### Using Conda (Recommended)

1. Clone this repository
2. Create the conda environment:
   ```bash
   conda env create -f environment.yml
   conda activate ai-image-analyzer
   ```

### Using pip

1. Clone this repository
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

## Configuration

### For Google Gemini API
Set your API key as an environment variable:
```bash
export GOOGLE_API_KEY=your_api_key_here
```

### For Local LLaVA Model (Ollama)
1. Install Ollama: https://ollama.ai/
2. Pull the LLaVA model:
   ```bash
   ollama pull llava:13b
   ```

### For BakLLaVA Model (Local)
1. Download the BakLLaVA model:
   ```bash
   python models/download_bakllava.py
   ```
   This downloads ~5GB of model files to your models directory.

2. The model files will be saved to your local models folder (e.g., `J:\models\BakLLaVA\`)

## Usage

### ⭐ Enhanced Unified Analyzer (Recommended)

The main script that combines all three AI models with goal-based processing:

```bash
python scripts/enhanced_unified_analyzer_v3.py
```

This script provides:
- Interactive menu for goal and model selection
- Automatic model detection (Gemini, Ollama, BakLLaVA)
- Test mode for validating on first 20 images
- Goal-optimized processing workflows
- Comprehensive output (CSV + XMP sidecar files)

#### Processing Goals:

1. **Archive Culling**: Fast keep/delete decisions for large photo collections
   - Optimized for speed (60s timeout per image)
   - Essential tags only
   - Score-based decisions (1-3=DELETE, 7-10=KEEP)

2. **Gallery Selection**: Detailed artistic analysis for photo curation
   - Comprehensive analysis (120s timeout)
   - Detailed artistic critique
   - Quality assessment and mood analysis

3. **Catalog Organization**: Complete tagging and categorization
   - Full metadata extraction
   - Comprehensive tag assignment
   - Category and sub-category classification

4. **Model Comparison**: A/B test different AI models on same images
   - Process images with multiple models
   - Compare analysis quality and consistency
   - Export comparison data for analysis

### Individual Model Scripts

#### Gemini Analyzer
```bash
python scripts/gemini_analyzer.py
```
Edit the script to set your source directory and API key.

#### LLaVA Analyzer (Ollama)
```bash
python scripts/llava_analyzer.py
```
Requires Ollama running locally with LLaVA model.

#### BakLLaVA Analyzer
```bash
python scripts/bakllava_simple.py path/to/image.jpg --goal archive_culling
```
Local Mistral-based multimodal analysis.

### Web Interface

1. Start the Flask application:
   ```bash
   python web/app.py
   ```
2. Open your browser to `http://localhost:5001`
3. Select your image directory and processing options
4. Monitor progress in real-time

### Lightroom Plugin

The Lightroom plugin provides complete feature parity with the web GUI, including:
- **3 AI Model Support**: Ollama, Google Gemini, and BakLLaVA
- **6 Analysis Perspectives**: Professional art critic, family archivist, commercial photographer, social media curator, documentary journalist, travel blogger
- **XMP Sidecar File Support**: Non-destructive metadata alongside EXIF writing
- **Direct API Integration**: Real-time communication with Flask service
- **Advanced Settings**: Model selection, timeout configuration, critique thresholds
- **Export Capabilities**: Analysis reports and batch processing

#### Installation:
1. **Rename the plugin folder**: The folder must be named `ai-image-analyzer.lrplugin` (with `.lrplugin` extension)
2. **Add to Lightroom**: File > Plug-in Manager > Add > Select the `.lrplugin` folder
3. **Configure Settings**: Library > Plugin Settings to set model type, API key, and preferences
4. **Start Flask Service**: Ensure `python web/app.py` is running on port 5001

#### Available Menu Items:
- **Analyze Selected Images**: Process selected photos with AI analysis
- **Batch Analyze Folder**: Process entire directories of images
- **View AI Analysis**: Display existing analysis results
- **Export Analysis Report**: Generate CSV/JSON reports
- **Download Local Models**: Manage Ollama/BakLLaVA model downloads
- **System Status**: Check model availability and service connectivity
- **Plugin Settings**: Configure model types, API keys, and analysis preferences

## Analysis Schema

### Categories
- People
- Place  
- Thing

### Sub-Categories
- Candid, Posed
- Automotive, Real Estate, Landscape
- Events, Animal, Product, Food

### Tags
- Lighting: Strobist, Available Light, Natural Light
- Quality: Beautiful, Timeless, Low Quality, Out of Focus
- Mood: Evocative, Calm, Busy, Sentimental
- Events: Wedding, Bride, Groom, Family
- Style: Black & White, Minimalist, Action

### Scoring
- 1-10 scale (poor to masterpiece)
- Automatically converts to 1-5 star rating
- Preserves existing 4-5 star ratings
- Adds "GALLERY" tag for 5-star images

## Deployment

### Synology NAS Deployment

1. Enable SSH and Web Station on your Synology
2. Install Python and pip packages
3. Copy the project files to your web directory
4. Configure reverse proxy if needed
5. Set up environment variables for API keys

### Docker Deployment

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["python", "web/app.py"]
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

MIT License - see LICENSE file for details

## Author

Don Wright - Created with AI assistance

## Changelog

### v2.0.1 (2025-01-13) - Web GUI & Lightroom Plugin Feature Parity
- **NEW**: Web GUI completely redesigned with 3-model support and modern UI
- **NEW**: 6 Analysis Perspective profiles (Art Critic, Family Archivist, Commercial Photographer, etc.)
- **NEW**: Real-time WebSocket communication for progress updates
- **NEW**: Dynamic model selection with API key management
- **NEW**: XMP sidecar file generation option ("Write to XMP sidecar files")
- **NEW**: Export functionality (JSON/CSV) with analysis reports
- **NEW**: Model management interface (download Ollama/BakLLaVA models)
- **ENHANCED**: Lightroom plugin updated to match web GUI feature set exactly
- **ENHANCED**: Plugin now supports all 3 models (Ollama, Gemini, BakLLaVA)
- **ENHANCED**: Plugin includes all 6 analysis perspectives from web GUI
- **ENHANCED**: Plugin provides same XMP sidecar and export capabilities
- **ENHANCED**: Plugin renamed to `.lrplugin` folder structure for proper Lightroom recognition
- **FIXED**: JSON.lua syntax errors that prevented plugin loading
- **FIXED**: Flask web service port updated to 5001 for consistency
- **ACHIEVEMENT**: Complete feature parity between web GUI and Lightroom plugin

### v2.0.0 (2025-01-11) - BakLLaVA Integration
- **NEW**: BakLLaVA integration - Mistral-based multimodal model
- **NEW**: Enhanced Unified Analyzer v3.1 with 3-model support
- **NEW**: Goal-based processing workflows (Archive Culling, Gallery Selection, etc.)
- **NEW**: Interactive setup menu with model auto-detection
- **NEW**: Test mode - validate on first 20 images before full processing
- **NEW**: Model comparison system for A/B testing
- **NEW**: XMP sidecar file generation for Lightroom compatibility
- **NEW**: CPU-only mode for GPU resource management
- **ENHANCED**: Improved error handling and progress tracking
- **ENHANCED**: Optimized processing workflows for different use cases
- **ENHANCED**: Better model file detection and management

### v1.0.0 (2025-07-20)
- Initial release with Gemini and LLaVA support
- Web interface with real-time processing
- Lightroom plugin integration
- EXIF metadata writing
- Batch processing capabilities

