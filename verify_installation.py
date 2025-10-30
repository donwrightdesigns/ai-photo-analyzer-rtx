#!/usr/bin/env python3
"""
Installation Verification Script for AI Image Analyzer
Checks all dependencies and system requirements
"""

import sys
import subprocess
import importlib
from pathlib import Path

def check_python_version():
    """Check Python version compatibility"""
    print("🐍 Checking Python version...")
    version = sys.version_info
    print(f"   Python {version.major}.{version.minor}.{version.micro}")
    
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("   ❌ Python 3.8+ required")
        return False
    else:
        print("   ✅ Python version OK")
        return True

def check_package(package_name, import_name=None, optional=False):
    """Check if a Python package is available"""
    if import_name is None:
        import_name = package_name
        
    try:
        importlib.import_module(import_name)
        print(f"   ✅ {package_name}")
        return True
    except ImportError:
        if optional:
            print(f"   ⚠️  {package_name} (optional)")
            return True
        else:
            print(f"   ❌ {package_name} - Missing")
            return False

def check_ollama_connection():
    """Check Ollama installation and connection"""
    print("🦙 Checking Ollama...")
    
    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        
        if response.status_code == 200:
            models = response.json().get('models', [])
            model_names = [m['name'] for m in models]
            
            print("   ✅ Ollama is running")
            print(f"   📦 Available models: {', '.join(model_names) if model_names else 'None'}")
            
            # Check for recommended models
            recommended_models = ['llava:13b', 'llava:7b', 'llava']
            found_model = False
            
            for model in recommended_models:
                if any(model in name for name in model_names):
                    print(f"   ✅ Found recommended model: {model}")
                    found_model = True
                    break
            
            if not found_model:
                print("   ⚠️  No LLaVA models found. Run: ollama pull llava:13b")
            
            return True
        else:
            print(f"   ❌ Ollama responded with HTTP {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("   ❌ Ollama not running or not installed")
        print("   💡 Install Ollama from https://ollama.com")
        return False
    except Exception as e:
        print(f"   ❌ Error connecting to Ollama: {e}")
        return False

def check_gpu_support():
    """Check GPU availability"""
    print("🎮 Checking GPU support...")
    
    try:
        import torch
        if torch.cuda.is_available():
            gpu_count = torch.cuda.device_count()
            gpu_name = torch.cuda.get_device_name(0) if gpu_count > 0 else "Unknown"
            gpu_memory = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            
            print(f"   ✅ CUDA GPU available: {gpu_name}")
            print(f"   💾 GPU Memory: {gpu_memory:.1f} GB")
            
            if gpu_memory >= 8:
                print("   🚀 Excellent GPU for LLaVA 13B")
            elif gpu_memory >= 4:
                print("   ⚡ Good GPU for LLaVA 7B")
            else:
                print("   ⚠️  Limited GPU memory - consider CPU processing")
                
            return True
        else:
            print("   ⚠️  No CUDA GPU detected - will use CPU")
            return True
            
    except ImportError:
        print("   ❌ PyTorch not installed")
        return False
    except Exception as e:
        print(f"   ❌ Error checking GPU: {e}")
        return False

def main():
    """Run all verification checks"""
    print("🔍 AI Image Analyzer - Installation Verification")
    print("=" * 50)
    
    all_good = True
    
    # Core Python version check
    if not check_python_version():
        all_good = False
    
    print("\n📦 Checking Python packages...")
    
    # Required packages
    required_packages = [
        ("Pillow", "PIL"),
        ("requests", "requests"),
        ("google-generativeai", "google.generativeai"),
        ("PyTorch", "torch"),
        ("torchvision", "torchvision"),
        ("PyIQA", "pyiqa"),
        ("piexif", "piexif"),
        ("PyExifTool", "exiftool"),
        ("psutil", "psutil"),
    ]
    
    for package_name, import_name in required_packages:
        if not check_package(package_name, import_name):
            all_good = False
    
    # Built-in packages (should always be available)
    print("\n🏗️ Checking built-in packages...")
    builtin_packages = [
        ("tkinter", "tkinter"),
        ("json", "json"),
        ("threading", "threading"),
        ("pathlib", "pathlib"),
    ]
    
    for package_name, import_name in builtin_packages:
        check_package(package_name, import_name)
    
    print()
    
    # Ollama check
    if not check_ollama_connection():
        print("   💡 Ollama is recommended for local processing")
    
    print()
    
    # GPU check
    check_gpu_support()
    
    print("\n" + "=" * 50)
    
    if all_good:
        print("🎉 Installation verification completed successfully!")
        print("🚀 You can now run: python main.py")
    else:
        print("❌ Some issues found. Please install missing packages:")
        print("   pip install -r requirements.txt")
        
    return all_good

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)