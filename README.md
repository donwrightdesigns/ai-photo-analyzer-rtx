# AI Image Analyzer v2.0 - Local AI-Powered Image Analysis

![AI Image Analyzer](https://repository-images.githubusercontent.com/1023260823/4a6294b7-6431-4fbe-9a7d-8d6e89724cb1)

**A powerful, local-first, AI-powered image analysis tool that automatically tags, rates, and describes your images using advanced AI models running locally on your machine.**

✨ **NEW in v2.0**: GPU Load Profile settings for optimized performance, enhanced Ollama integration, and streamlined desktop interface.

---

## 🎯 Key Features

- **🖥️ Clean Desktop GUI**: Modern, user-friendly interface for analyzing folders of images
- **🤖 Local AI Models**: Primary support for Ollama (LLaVA, Gemma) with Gemini cloud fallback
- **⚡ GPU Load Profiles**: Choose between Maximum Speed, Balanced, or Background Safe processing
- **🎯 Smart Quality Filtering**: Only analyze your best images using advanced quality assessment
- **📝 Rich Metadata**: Automatic tagging, rating, and curatorial descriptions
- **💾 EXIF/IPTC Embedding**: Industry-standard metadata embedded directly in image files
- **🔒 Privacy-First**: Your images never leave your machine with local processing
- **🚀 RTX Optimized**: Blazing-fast performance on NVIDIA RTX GPUs

---

## 🚀 Quick Start

1. **Install Ollama** (recommended for local processing)
2. **Clone and run** the AI Image Analyzer
3. **Select your image folder** in the GUI
4. **Choose your settings** (GPU load profile, quality threshold, etc.)
5. **Start analysis** and let AI tag and rate your images!

Your images will be automatically tagged with categories, keywords, quality ratings, and optional curatorial descriptions.

---

## 🛠️ Installation

### Prerequisites

- **Python 3.8+** (3.9+ recommended)
- **NVIDIA GPU** (optional but recommended for best performance)
- **Ollama** (for local AI models)

### Step 1: Install Ollama

**Ollama provides the local AI models and is the recommended approach:**

1. **Download Ollama**: Go to [ollama.com](https://ollama.com) and download for your platform
2. **Install and start** Ollama (it runs as a service)
3. **Pull a vision model**:
   ```bash
   ollama pull llava:13b    # Recommended - higher quality
   # OR
   ollama pull llava:7b     # Faster, lower VRAM usage
   ```

**Verify Ollama is running:**
```bash
ollama list    # Should show your downloaded models
```

### Step 2: Install AI Image Analyzer

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/ai-image-analyzer.git
   cd ai-image-analyzer
   ```

2. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Verify installation** (recommended):
   ```bash
   python verify_installation.py
   ```

4. **Run the application**:
   ```bash
   python main.py
   # OR directly:
   python ai_image_analyzer_gui.py
   ```

### Step 3: Configuration (Optional)

- **For cloud fallback**: Add your Google Gemini API key in Settings
- **For optimal performance**: Adjust the GPU Load Profile in Settings
- **Quality filtering**: Set your preferred quality threshold

---

## 🤖 Supported AI Models

### Local Models (via Ollama) - **Recommended**
- **LLaVA 13B**: Higher quality analysis, ~7GB VRAM, slower but excellent results
- **LLaVA 7B**: Faster analysis, ~4GB VRAM, good quality
- **Gemma 2B/12B**: Alternative local models with different strengths

### Cloud Models (Fallback)
- **Gemini 2.0 Flash**: High-quality cloud analysis when local models aren't available

---

## ⚡ GPU Load Profiles

**NEW in v2.0** - Choose the optimal performance setting for your needs:

### 🔥 Hurt My GPU (Maximum Speed)
- **When to use**: You want the fastest possible analysis
- **System impact**: High GPU usage, may impact other applications
- **Settings**: Shortest timeouts (15s min), 50ms between requests
- **Best for**: Dedicated analysis sessions, powerful GPUs

### ⚡ Normal Demand (Balanced) - **Default**
- **When to use**: Good balance of speed and system stability
- **System impact**: Moderate GPU usage, shouldn't impact normal usage
- **Settings**: Standard timeouts (30s), 100ms between requests
- **Best for**: Most users, everyday analysis

### 🌿 Light Demand (Background Safe)
- **When to use**: Running analysis in background while using other apps
- **System impact**: Low GPU usage, minimal impact on other applications
- **Settings**: Extended timeouts (60s), 1000ms between requests
- **Best for**: Background processing, shared systems, older GPUs

---

---

## 📚 Usage

### Basic Workflow

1. **Launch** the application: `python ai_image_analyzer_gui.py`
2. **Configure settings**: Click the Settings button to configure your preferences
3. **Select folder**: Browse to your image folder
4. **Choose options**: 
   - Include subfolders (recommended)
   - Set GPU load profile based on your needs
5. **Start Analysis**: Click "Start Analysis" and watch the progress

### What Gets Analyzed

- **Quality Assessment**: Images are scored using advanced quality metrics
- **AI Analysis**: Only high-quality images get full AI analysis (configurable threshold)
- **Metadata Generation**: Categories, tags, ratings, and optional descriptions
- **File Embedding**: Metadata is written directly into image EXIF/IPTC data

### Generated Metadata

- **Category**: Main subject category (Person, Animal, Landscape, etc.)
- **Subcategory**: More specific classification
- **Keywords/Tags**: Relevant descriptive tags
- **Quality Rating**: 1-5 star rating based on technical and artistic merit
- **Curatorial Description**: Optional AI-generated artistic critique (when enabled)

---

## 🔧 Troubleshooting

### Ollama Issues

**Ollama not connecting:**
```bash
# Check if Ollama is running
ollama list

# Restart Ollama if needed
# Windows: Restart the Ollama service
# macOS/Linux: killall ollama && ollama serve
```

**Model not found:**
```bash
# Pull the required model
ollama pull llava:13b
```

### Performance Issues

- **Slow processing**: Try the 🔥 "Hurt My GPU" load profile
- **System laggy**: Switch to 🌿 "Light Demand" load profile
- **Out of VRAM**: Use LLaVA 7B instead of 13B model
- **Connection timeouts**: Increase timeout in advanced settings

### General Issues

- **No images found**: Check that image folder contains supported formats (JPG, PNG, TIFF, etc.)
- **Metadata not visible**: Some applications need to refresh metadata view
- **Permission errors**: Ensure write access to image files

---

## 🔍 System Requirements

### Minimum Requirements
- **OS**: Windows 10+, macOS 10.14+, or Linux
- **Python**: 3.8+
- **RAM**: 8GB (16GB recommended)
- **Storage**: 2GB free space

### Recommended for Best Performance
- **GPU**: NVIDIA RTX 3060 or better with 8GB+ VRAM
- **RAM**: 16GB+
- **CPU**: Modern multi-core processor
- **Storage**: SSD for faster image loading

### Supported Image Formats
- **Primary**: JPG, JPEG, PNG, TIFF, TIF
- **RAW**: CR2, NEF, ARW, DNG (converted for analysis)
- **Other**: WEBP, BMP

---

## 📝 License

This project is licensed under the MIT License. See LICENSE file for details.

---

## 🚀 What's New in v2.0

- **⚡ GPU Load Profiles**: Choose optimal performance settings for your workflow
- **🤖 Enhanced Ollama Integration**: Seamless local AI model support with automatic configuration
- **🖥️ Streamlined GUI**: Clean, modern desktop interface with real-time status display
- **🔧 Smart Installation**: Verification script ensures all dependencies are correctly installed
- **💾 Improved Metadata**: Better EXIF/IPTC embedding with curatorial descriptions
- **🎯 Quality Filtering**: Advanced image quality assessment with multiple algorithms

---

## 🚀 Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for bugs and feature requests.

---

## 📞 Support

- **Issues**: Report bugs or request features via GitHub Issues
- **Discussions**: Join the community discussions for tips and troubleshooting
- **Documentation**: Check the README for the latest setup instructions

