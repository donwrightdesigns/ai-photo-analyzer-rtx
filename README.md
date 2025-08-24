# AI Image Analyzer v4.0 - Streamlined Desktop & Lightroom Workflow

![AI Image Analyzer](logo-ai-analyzer.jpg)

**A powerful, local-first, AI-powered image analysis tool for professional and enthusiast photographers, now with a completely rebuilt, simplified, and reliable Adobe Lightroom Classic integration.**

This major update abandons the previous complex web-based plugin in favor of a robust, practical, and familiar "send-to-app" workflow, inspired by industry-standard tools like Topaz Photo AI.

---

## 🎯 Key Features

- **Standalone Desktop GUI**: A clean, modern interface for analyzing folders of images.
- **New Lightroom Plugin**: A simple, reliable plugin to send images directly to the desktop app.
- **Two Processing Modes**:
    - **Archive Mode**: Comprehensive analysis of all images for a fully searchable archive.
    - **Curated Mode**: Fast, quality-focused analysis of only the best images.
- **Local-First Processing**: Your images are processed on your machine, ensuring privacy and security.
- **Powerful AI Models**: Supports local models like BakLLaVA for speed and Gemini for quality.
- **RTX Acceleration**: Optimized for NVIDIA RTX GPUs for blazing-fast performance.
- **XMP Sidecar Metadata**: Non-destructive metadata that works with Lightroom, Bridge, and Capture One.

---

## 🚀 New Simplified Workflow

The new architecture is designed for simplicity and reliability:

1.  **Select in Lightroom**: Choose images in the Library module.
2.  **Send to Desktop App**: Use the `Plug-in Extras` menu to send images to the AI Image Analyzer desktop app.
3.  **Analyze**: Use the full power of the desktop app to analyze your images in either Archive or Curated mode.
4.  **Refresh in Lightroom**: Once finished, use the `Refresh Metadata` command in Lightroom to instantly see your new ratings, keywords, and descriptions.

This workflow is faster, more reliable, and more powerful than the previous web-based plugin.

---

## 🛠️ Installation

### 1. Install the Desktop App

- **Windows**: Download the latest release from the Releases page and run the installer.
- **macOS/Linux**: Clone the repository and run the app from source (see below).

### 2. Install the Lightroom Plugin

1.  Open Lightroom Classic.
2.  Go to `File` > `Plug-in Manager`.
3.  Click `Add` and navigate to the `ai-image-analyzer-v2.lrplugin` folder in this repository.
4.  The plugin is now installed and will appear in the `Plug-in Extras` menu.

---

## 💻 Running from Source

If you prefer to run the desktop app from source:

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/your-username/ai-image-analyzer.git
    cd ai-image-analyzer
    ```

2.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Run the main application**:
    ```bash
    python main.py
    ```

---

## 🤖 Supported AI Models

- **BakLLaVA (Local, Recommended)**: Incredibly fast on NVIDIA RTX GPUs, ideal for large batches.
- **Gemini (Cloud)**: High-quality analysis using Google's API, great for single images or small batches.
- **Ollama (Local)**: Supports a wide variety of local models, good for privacy-focused users.

---

## 📈 Project Cleanup & Refactoring

This release represents a major cleanup and refactoring of the project. The following have been **removed**:

-   **Old Lightroom Plugin**: The entire `ai-image-analyzer.lrplugin` has been deleted and replaced with the much simpler `ai-image-analyzer-v2.lrplugin`.
-   **Web Interface**: The Flask-based web GUI has been removed to focus on a single, high-quality desktop application.
-   **Obsolete Scripts**: Numerous old and experimental scripts have been deleted to clean up the codebase.
-   **Outdated Documentation**: All documentation related to the old plugin and web interface has been removed.

This leaves a clean, focused, and maintainable codebase centered around the desktop application and its new, streamlined Lightroom integration.
