#!/usr/bin/env python3
"""
AI Image Analyzer Configuration Selector

This script helps users select and apply the appropriate configuration
for their system and preferences.
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List

def load_config(config_path: Path) -> Dict:
    """Load configuration from JSON file"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading config {config_path}: {e}")
        return {}

def list_available_configs() -> List[Dict]:
    """List all available configurations"""
    configs_dir = Path(__file__).parent / "configs"
    if not configs_dir.exists():
        print(f"Configs directory not found: {configs_dir}")
        return []
    
    configs = []
    for config_file in configs_dir.glob("*.json"):
        config_data = load_config(config_file)
        if config_data:
            config_data['file_path'] = str(config_file)
            configs.append(config_data)
    
    return configs

def display_config_options(configs: List[Dict]):
    """Display available configuration options"""
    print("Available Configurations:")
    print("=" * 50)
    
    for i, config in enumerate(configs, 1):
        env = config.get('environment', {})
        model = config.get('model_settings', {})
        perf = config.get('performance', {})
        
        print(f"{i}. {config.get('config_name', 'Unknown')}")
        print(f"   Description: {config.get('description', 'N/A')}")
        print(f"   Platform: {env.get('platform', 'N/A')}")
        print(f"   Model: {model.get('model_type', 'N/A')}")
        print(f"   GPU Required: {'Yes' if env.get('requires_gpu') else 'No'}")
        print(f"   WSL Required: {'Yes' if env.get('requires_wsl') else 'No'}")
        print(f"   Internet Required: {'Yes' if perf.get('internet_required') else 'No'}")
        print(f"   Expected Speed: {perf.get('expected_speed', 'N/A')}")
        print()

def display_setup_instructions(config: Dict):
    """Display setup instructions for selected configuration"""
    installation = config.get('installation', {})
    
    print(f"Setup Instructions for: {config.get('config_name')}")
    print("=" * 60)
    print(f"Description: {config.get('description')}")
    print()
    
    print(f"Python Version Required: {installation.get('python_version', 'N/A')}")
    print()
    
    print("Required Packages:")
    for package in installation.get('required_packages', []):
        print(f"  - {package}")
    
    optional_packages = installation.get('optional_packages', [])
    if optional_packages:
        print("\\nOptional Packages:")
        for package in optional_packages:
            print(f"  - {package}")
    
    print("\\nSetup Steps:")
    for step in installation.get('setup_instructions', []):
        print(f"  {step}")
    
    # Display features
    features = config.get('features', {})
    print("\\nSupported Features:")
    for feature, supported in features.items():
        status = "✓" if supported else "✗"
        print(f"  {status} {feature.replace('_', ' ').title()}")
    
    # Display performance info
    perf = config.get('performance', {})
    print("\\nPerformance Information:")
    for key, value in perf.items():
        print(f"  {key.replace('_', ' ').title()}: {value}")

def create_environment_script(config: Dict, output_dir: Path):
    """Create environment-specific setup script"""
    env = config.get('environment', {})
    installation = config.get('installation', {})
    model_settings = config.get('model_settings', {})
    
    if env.get('platform') == 'windows':
        script_name = f"setup_{config.get('config_name', 'config').lower().replace(' ', '_').replace('+', '').replace('(', '').replace(')', '')}.bat"
        script_path = output_dir / script_name
        
        # Create batch script for Windows
        script_content = f"""@echo off
echo Setting up AI Image Analyzer - {config.get('config_name')}
echo.

REM Create virtual environment
echo Creating virtual environment...
python -m venv venv
if errorlevel 1 goto error

REM Activate virtual environment
echo Activating virtual environment...
call venv\\Scripts\\activate.bat
if errorlevel 1 goto error

REM Install requirements
echo Installing requirements...
"""
        
        # Determine which requirements file to use
        if model_settings.get('model_type') == 'gemini':
            script_content += "pip install -r requirements_gemini.txt\n"
        else:
            script_content += "pip install -r requirements_ollama.txt\n"
        
        script_content += """
if errorlevel 1 goto error

echo.
echo Setup complete!
"""
        
        # Add API key setup for Gemini
        if model_settings.get('api_key_required'):
            api_key_var = model_settings.get('api_key_env_var', 'GOOGLE_API_KEY')
            script_content += f"""
echo.
echo Don't forget to set your API key:
echo set {api_key_var}=your_api_key_here
echo.
"""
        
        script_content += """
echo To run the analyzer:
echo python scripts/unified_analyzer.py --model """ + model_settings.get('model_type', 'llava') + """ [directory_path]
echo.
goto end

:error
echo An error occurred during setup.
pause
exit /b 1

:end
pause
"""
        
    else:  # WSL2/Linux
        script_name = f"setup_{config.get('config_name', 'config').lower().replace(' ', '_').replace('+', '').replace('(', '').replace(')', '')}.sh"
        script_path = output_dir / script_name
        
        script_content = f"""#!/bin/bash
echo "Setting up AI Image Analyzer - {config.get('config_name')}"
echo

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv
if [ $? -ne 0 ]; then
    echo "Error creating virtual environment"
    exit 1
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install requirements
echo "Installing requirements..."
"""
        
        # Determine which requirements file to use
        if model_settings.get('model_type') == 'gemini':
            script_content += "pip install -r requirements_gemini.txt\n"
        else:
            script_content += "pip install -r requirements_ollama.txt\n"
        
        script_content += """
if [ $? -ne 0 ]; then
    echo "Error installing requirements"
    exit 1
fi

echo
echo "Setup complete!"
"""
        
        # Add API key setup for Gemini
        if model_settings.get('api_key_required'):
            api_key_var = model_settings.get('api_key_env_var', 'GOOGLE_API_KEY')
            script_content += f"""
echo
echo "Don't forget to set your API key:"
echo "export {api_key_var}=your_api_key_here"
echo
"""
        
        script_content += """
echo "To run the analyzer:"
echo "python scripts/unified_analyzer.py --model """ + model_settings.get('model_type', 'llava') + """ [directory_path]"
echo
"""
    
    # Write script file
    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(script_content)
    
    # Make executable on Unix-like systems
    if not env.get('platform') == 'windows':
        os.chmod(script_path, 0o755)
    
    print(f"Setup script created: {script_path}")

def main():
    """Main function"""
    print("AI Image Analyzer Configuration Selector")
    print("=" * 50)
    
    configs = list_available_configs()
    if not configs:
        print("No configurations found!")
        sys.exit(1)
    
    while True:
        display_config_options(configs)
        
        try:
            choice = input("Select a configuration (number), 'q' to quit: ").strip()
            
            if choice.lower() == 'q':
                break
            
            choice_num = int(choice)
            if 1 <= choice_num <= len(configs):
                selected_config = configs[choice_num - 1]
                
                print("\\n" + "=" * 60)
                display_setup_instructions(selected_config)
                print("\\n" + "=" * 60)
                
                create_script = input("\\nCreate setup script? (y/n): ").strip().lower()
                if create_script == 'y':
                    output_dir = Path(__file__).parent
                    create_environment_script(selected_config, output_dir)
                
                another = input("\\nSelect another configuration? (y/n): ").strip().lower()
                if another != 'y':
                    break
            else:
                print("Invalid selection. Please try again.")
        
        except ValueError:
            print("Invalid input. Please enter a number or 'q' to quit.")
        except KeyboardInterrupt:
            print("\\nExiting...")
            break

if __name__ == "__main__":
    main()
