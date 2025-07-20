# Windows Installation Guide (No WSL Required)

This guide helps you install and run the AI Image Analyzer on Windows without requiring WSL (Windows Subsystem for Linux).

## Quick Start (5 minutes)

### Option 1: Cloud-Only Mode (Easiest)
If you just want to use Google Gemini (cloud-based), you only need Python:

1. **Install Python 3.12**
   - Download from: https://www.python.org/downloads/
   - ✅ Check "Add Python to PATH" during installation

2. **Install the AI Image Analyzer**
   ```cmd
   git clone https://github.com/yourusername/ai-image-analyzer.git
   cd ai-image-analyzer
   pip install -r requirements.txt
   ```

3. **Set your API key**
   ```cmd
   set GOOGLE_API_KEY=your_api_key_here
   ```

4. **Run the analyzer**
   ```cmd
   python scripts/enhanced_gemini_analyzer_v2.py
   ```

### Option 2: Local + Cloud Mode (Full Features)
For both local LLaVA models and cloud Gemini:

1. **Install Python 3.12** (same as above)

2. **Install Ollama** (for local models)
   - Download from: https://ollama.ai/download
   - Run the installer (simple click-through)

3. **Install the AI Image Analyzer**
   ```cmd
   git clone https://github.com/yourusername/ai-image-analyzer.git
   cd ai-image-analyzer
   pip install -r requirements.txt
   ```

4. **Download a local model** (optional)
   ```cmd
   ollama pull llava:13b
   ```

5. **Run the web interface**
   ```cmd
   python web/app.py
   ```
   Then open: http://localhost:5000

## Detailed Installation Options

### A. Standalone Scripts (No Web Interface)

#### Google Gemini Script
```cmd
# Set API key
set GOOGLE_API_KEY=your_google_api_key

# Run analysis
python scripts/enhanced_gemini_analyzer_v2.py
```

#### Local LLaVA Script
```cmd
# Make sure Ollama is running, then:
python scripts/enhanced_llava_analyzer_v2.py "C:\Your\Photos\Directory"
```

### B. Web Interface (Recommended)

1. **Start the web server:**
   ```cmd
   python web/app.py
   ```

2. **Open your browser to:** `http://localhost:5000`

3. **Use the interface to:**
   - Select your photo directory
   - Choose between local (LLaVA) or cloud (Gemini) models
   - Download local models if needed
   - Monitor progress in real-time

## System Requirements

### Minimum Requirements
- **OS:** Windows 10 or 11
- **RAM:** 8GB (for cloud mode)
- **Storage:** 2GB free space
- **Python:** 3.12 or newer

### Recommended for Local Models
- **RAM:** 16GB+ (for LLaVA models)
- **Storage:** 10GB+ (models can be large)
- **CPU:** Modern multi-core processor

## Installing Local Models

The web interface includes a "Download Model" feature, but you can also do it manually:

### Available Models
```cmd
# Lightweight models (faster, less accurate)
ollama pull llava:7b

# Balanced models (recommended)
ollama pull llava:13b
ollama pull llava:34b

# Large models (slower, more accurate)
ollama pull llava:70b
```

### Check Available Models
```cmd
ollama list
```

### Remove Models (to save space)
```cmd
ollama rm llava:34b
```

## Configuration Options

### Environment Variables
Create a `.env` file in the project directory:
```
GOOGLE_API_KEY=your_google_api_key
OLLAMA_URL=http://localhost:11434
```

### Config File
Create `config.py` for advanced settings:
```python
class Config:
    # Processing settings
    MAX_WORKERS = 4  # Adjust based on your CPU
    MAX_DIMENSION = 1024  # Resize images to this size
    
    # Paths
    SOURCE_DIRECTORY = r"C:\Users\YourName\Pictures"
    OUTPUT_DIRECTORY = r"C:\Results"
    
    # Model settings
    PREFERRED_MODEL = "llava:13b"
    OLLAMA_URL = "http://localhost:11434"
```

## Troubleshooting

### Common Issues

#### "Python not found"
- Reinstall Python and check "Add to PATH"
- Or use full path: `C:\Python312\python.exe`

#### "Module not found" errors
```cmd
pip install --upgrade pip
pip install -r requirements.txt
```

#### "Connection refused" for local models
- Check if Ollama is running: `ollama serve`
- Verify URL: http://localhost:11434

#### High memory usage
- Close other applications
- Use smaller models (llava:7b instead of llava:13b)
- Reduce MAX_WORKERS in config

#### Slow processing
- Use cloud models (Gemini) for speed
- Enable image optimization
- Use SSD storage for models

### Getting Help

1. **Check the logs:**
   ```cmd
   type ai_analyzer.log
   type llava_analyzer.log
   ```

2. **Test your setup:**
   ```cmd
   python -c "import requests, PIL; print('✅ Basic requirements OK')"
   python -c "import google.genai; print('✅ Google AI OK')"
   ```

3. **Check model availability:**
   - Web interface: http://localhost:5000
   - Or manually: `curl http://localhost:11434/api/tags`

## Advanced Usage

### Batch Processing
```cmd
# Process specific directory with custom prompt
python scripts/enhanced_llava_analyzer_v2.py ^
  "C:\Photos" ^
  --prompt "Rate this photo from 1-10 and explain why" ^
  --workers 2 ^
  --output "my_results.csv"
```

### Integration with Lightroom
1. Install the Lightroom plugin from `lightroom-plugin/`
2. The system will automatically detect Lightroom and reduce resource usage
3. Export photos from Lightroom, then run analysis

### Automated Scheduling
Create a batch file for regular processing:
```batch
@echo off
set GOOGLE_API_KEY=your_key_here
cd /d "C:\path\to\ai-image-analyzer"
python scripts/enhanced_gemini_analyzer_v2.py
pause
```

## Performance Tips

1. **Close unnecessary applications** when processing
2. **Use an SSD** for better model loading speed
3. **Start with small batches** to test your system
4. **Monitor system resources** - the tool will auto-throttle if needed
5. **Use cloud models** for speed, local models for privacy

## No WSL Needed! 🎉

This entire setup runs on native Windows with no Linux subsystem required. Everything runs through:
- Standard Windows Python installation
- Native Windows Ollama application
- Regular Windows command prompt or PowerShell

Perfect for users who want to keep their system simple and avoid WSL complexity.
