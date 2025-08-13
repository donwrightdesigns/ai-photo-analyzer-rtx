@echo off
REM AI Image Analyzer - Windows Installation Script
REM No WSL required - runs on native Windows

echo ==========================================
echo AI Image Analyzer - Windows Installer
echo ==========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python is not installed or not in PATH
    echo.
    echo Please install Python 3.12 from: https://www.python.org/downloads/
    echo ✅ Make sure to check "Add Python to PATH" during installation
    echo.
    pause
    exit /b 1
)

echo ✅ Python found:
python --version

REM Check if git is available (optional)
git --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ⚠️ Git not found - you'll need to download the project manually
) else (
    echo ✅ Git found
)

echo.
echo Installing Python dependencies...
pip install --upgrade pip
pip install -r requirements.txt

if %errorlevel% neq 0 (
    echo ❌ Failed to install Python dependencies
    pause
    exit /b 1
)

echo ✅ Python dependencies installed

REM Check if Ollama should be installed
echo.
set /p install_ollama="Do you want to use local AI models? (requires Ollama) [y/N]: "
if /i "%install_ollama%"=="y" (
    echo.
    echo 📦 Please install Ollama for local models:
    echo 1. Go to: https://ollama.ai/download
    echo 2. Download and run the Windows installer
    echo 3. After installation, run: ollama pull llava:13b
    echo.
    echo Press any key after installing Ollama...
    pause >nul
    
    REM Test Ollama installation
    echo Testing Ollama installation...
    curl -s http://localhost:11434/api/tags >nul 2>&1
    if %errorlevel% equ 0 (
        echo ✅ Ollama is running
    ) else (
        echo ⚠️ Ollama not detected - you may need to start it manually
        echo   Run: ollama serve
    )
)

REM Setup environment
echo.
echo Setting up environment...

REM Create .env file if it doesn't exist
if not exist .env (
    echo Creating .env configuration file...
    echo # AI Image Analyzer Configuration > .env
    echo GOOGLE_API_KEY=your_google_api_key_here >> .env
    echo OLLAMA_URL=http://localhost:11434 >> .env
    echo.
    echo ⚠️ Don't forget to add your Google API key to .env file
)

REM Create desktop shortcuts
echo.
set /p create_shortcuts="Create desktop shortcuts? [y/N]: "
if /i "%create_shortcuts%"=="y" (
    echo Creating shortcuts...
    
    REM Web Interface shortcut
    set "shortcut_path=%USERPROFILE%\Desktop\AI Image Analyzer.bat"
    echo @echo off > "%shortcut_path%"
    echo cd /d "%CD%" >> "%shortcut_path%"
    echo python web/app.py >> "%shortcut_path%"
    echo pause >> "%shortcut_path%"
    
    echo ✅ Desktop shortcut created: AI Image Analyzer.bat
)

echo.
echo ==========================================
echo 🎉 Installation Complete!
echo ==========================================
echo.
echo Running first-time setup wizard...
echo.
python setup_wizard.py
echo.
echo ==========================================
echo 🚀 Ready to Use!
echo ==========================================
echo.
echo Quick Start Options:
echo.
echo 1. WEB INTERFACE (Recommended):
echo    python web/app.py
echo    Then open: http://localhost:5001
echo.
echo 2. COMMAND LINE - Google Gemini:
echo    set GOOGLE_API_KEY=your_key
echo    python scripts/enhanced_gemini_analyzer_v2.py
echo.
echo 3. COMMAND LINE - Local LLaVA:
echo    python scripts/enhanced_llava_analyzer_v2.py "C:\Your\Photos"
echo.
echo ==========================================
echo Configuration:
echo ==========================================
echo.
echo • Edit .env file to set your Google API key
echo • Logs will be saved to: ai_analyzer.log
echo • Results will be saved as CSV files
echo • System resources will be monitored automatically
echo.
if /i "%install_ollama%"=="y" (
    echo Local Models:
    echo • Download models: ollama pull llava:13b
    echo • List models: ollama list
    echo • Remove models: ollama rm model_name
    echo.
)
echo Documentation:
echo • Windows Guide: WINDOWS_INSTALL.md
echo • Migration Guide: MIGRATION_GUIDE.md
echo • Full README: README.md
echo.
echo ==========================================
echo Ready to use! 🚀
echo ==========================================
pause
