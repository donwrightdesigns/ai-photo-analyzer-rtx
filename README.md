# AI Photo Analyzer and XMP culling with HTML GUI and Adobe LIGHTROOM plugin 
<img src="http://www.donwrightdesigns.com/wp-content/uploads/2025/06/header-logo.jpg" width="50%">

A comprehensive image analysis system using AI models to automatically tag, categorize, assess and critique photographs helping organize, enormous libraries, or portfolios. This project includes standalone scripts, a web GUI, and a Lightroom plugin.

This was created by a professional photographer 20 years of photo archives 

## Features

- **Multiple AI Models**: Support for both local (LLaVA via Ollama) and cloud-based (Google Gemini) models
- **EXIF Integration**: Automatically writes analysis results to image metadata
- **Web Interface**: Real-time processing with WebSocket updates
- **Lightroom Plugin**: Direct integration with Adobe Lightroom
- **Batch Processing**: Process entire directories of images
- **Smart Rating System**: Preserves existing high ratings while adding AI-generated scores
- **Gallery Tagging**: Automatically tags 5-star images for gallery use

## Project Structure

```
ai-image-analyzer/
├── scripts/                    # Standalone analysis scripts
│   ├── gemini_analyzer.py     # Google Gemini-based analyzer
│   └── llava_analyzer.py      # Local LLaVA-based analyzer
├── web/                       # Flask web application
│   ├── app.py                # Main Flask application
│   ├── templates/            # HTML templates
│   └── static/               # CSS, JS, and images
├── lightroom-plugin/         # Adobe Lightroom plugin files
├── docs/                     # Documentation
├── config/                   # Configuration files
└── tests/                    # Test files
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

### For Local LLaVA Model
1. Install Ollama: https://ollama.ai/
2. Pull the LLaVA model:
   ```bash
   ollama pull llava:13b
   ```

## Usage

### Standalone Scripts

#### Gemini Analyzer
```bash
python scripts/gemini_analyzer.py
```
Edit the script to set your source directory and API key.

#### LLaVA Analyzer
```bash
python scripts/llava_analyzer.py
```
Requires Ollama running locally with LLaVA model.

### Web Interface

1. Start the Flask application:
   ```bash
   python web/app.py
   ```
2. Open your browser to `http://localhost:5000`
3. Select your image directory and processing options
4. Monitor progress in real-time

### Lightroom Plugin

1. Copy the `lightroom-plugin` folder to your Lightroom plugins directory
2. Enable the plugin in Lightroom's Plugin Manager
3. Access the plugin from the Library module

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

### v1.0.0 (2025-07-20)
- Initial release with Gemini and LLaVA support
- Web interface with real-time processing
- Lightroom plugin integration
- EXIF metadata writing
- Batch processing capabilities




