#!/usr/bin/env python3
# ----------------------------------------------------------------------
#  AI Image Analyzer - Setup Wizard
#  
#  Initial configuration wizard for setting up:
#  - Model directories
#  - API keys and tokens
#  - Model downloads
#  - Default preferences
# ----------------------------------------------------------------------

import os
import json
import requests
from pathlib import Path
from typing import Dict, Optional

class SetupWizard:
    """Initial setup wizard for AI Image Analyzer"""
    
    def __init__(self):
        self.config = {}
        self.config_file = Path("config/user_config.json")
        self.config_file.parent.mkdir(exist_ok=True)
    
    def run_setup(self):
        """Run the complete setup wizard"""
        print("" + "="*60)
        print("   AI IMAGE ANALYZER - FIRST TIME SETUP")
        print("="*63)
        print()
        print("Welcome! Let's configure your AI Image Analyzer for optimal performance.")
        print("This wizard will help you set up:")
        print("   Model storage directories")
        print("   API keys and tokens")
        print("   Automatic model downloads")
        print("   Default processing preferences")
        print()
        
        # Step 1: Model Directory
        self._setup_model_directory()
        
        # Step 2: API Keys/Tokens
        self._setup_api_credentials()
        
        # Step 3: Model Downloads
        self._setup_model_downloads()
        
        # Step 4: Default Preferences  
        self._setup_default_preferences()
        
        # Step 5: Save Configuration
        self._save_configuration()
        
        print("\n Setup Complete!")
        print(f" Configuration saved to: {self.config_file}")
        print("\nYou can now run the AI Image Analyzer with optimized settings!")
    
    def _setup_model_directory(self):
        """Configure model storage directory"""
        print("\n MODEL STORAGE DIRECTORY")
        print("-" * 30)
        
        # Auto-detect common model directories
        common_dirs = [
            Path("J:/models"),           # User's current setup
            Path.home() / "models",      # Home models
            Path.cwd() / "models",       # Local models
            Path("C:/models"),           # System models
            Path("D:/models"),           # Secondary drive
        ]
        
        existing_dirs = [d for d in common_dirs if d.exists()]
        
        if existing_dirs:
            print(" Found existing model directories:")
            for i, dir_path in enumerate(existing_dirs, 1):
                size = self._get_directory_size(dir_path)
                print(f"  {i}. {dir_path} ({size})")
            
            print(f"  {len(existing_dirs) + 1}. Enter custom path")
            print(f"  {len(existing_dirs) + 2}. Create new directory")
            
            while True:
                try:
                    choice = int(input(f"\nSelect directory (1-{len(existing_dirs) + 2}): "))
                    if 1 <= choice <= len(existing_dirs):
                        self.config['model_directory'] = str(existing_dirs[choice - 1])
                        break
                    elif choice == len(existing_dirs) + 1:
                        custom_path = input("Enter custom model directory path: ").strip().strip('"')
                        custom_dir = Path(custom_path)
                        if custom_dir.exists():
                            self.config['model_directory'] = str(custom_dir)
                            break
                        else:
                            print(" Directory doesn't exist!")
                    elif choice == len(existing_dirs) + 2:
                        new_path = input("Enter new directory path to create: ").strip().strip('"')
                        new_dir = Path(new_path)
                        try:
                            new_dir.mkdir(parents=True, exist_ok=True)
                            self.config['model_directory'] = str(new_dir)
                            print(f" Created: {new_dir}")
                            break
                        except Exception as e:
                            print(f" Failed to create directory: {e}")
                    else:
                        print("Invalid selection!")
                except ValueError:
                    print("Please enter a number!")
        else:
            # No existing directories found
            print("No existing model directories found.")
            default_dir = Path.home() / "models"
            create_default = input(f"Create default directory at {default_dir}? (Y/n): ").strip().lower()
            
            if create_default in ['', 'y', 'yes']:
                try:
                    default_dir.mkdir(parents=True, exist_ok=True)
                    self.config['model_directory'] = str(default_dir)
                    print(f" Created: {default_dir}")
                except Exception as e:
                    print(f" Failed to create directory: {e}")
            else:
                custom_path = input("Enter custom model directory path: ").strip().strip('"')
                self.config['model_directory'] = custom_path
        
        print(f" Model directory set to: {self.config['model_directory']}")
    
    def _setup_api_credentials(self):
        """Configure API keys and tokens"""
        print("\n API CREDENTIALS")
        print("-" * 20)
        
        # Google Gemini API Key
        print("\n1. Google Gemini API Key (for cloud-based analysis)")
        print("   Get your key from: https://aistudio.google.com/app/apikey")
        
        gemini_key = os.getenv('GOOGLE_API_KEY', '')
        if gemini_key:
            use_existing = input(f"Found existing GOOGLE_API_KEY environment variable. Use it? (Y/n): ").strip().lower()
            if use_existing in ['', 'y', 'yes']:
                self.config['gemini_api_key'] = 'use_env_var'
            else:
                new_key = input("Enter new Gemini API key (or press Enter to skip): ").strip()
                self.config['gemini_api_key'] = new_key if new_key else 'none'
        else:
            gemini_key = input("Enter Gemini API key (or press Enter to skip): ").strip()
            self.config['gemini_api_key'] = gemini_key if gemini_key else 'none'
        
        # Hugging Face Token
        print("\n2. Hugging Face Token (for downloading models)")
        print("   Get your token from: https://huggingface.co/settings/tokens")
        
        hf_token = os.getenv('HF_TOKEN', '')
        if hf_token:
            use_existing_hf = input(f"Found existing HF_TOKEN environment variable. Use it? (Y/n): ").strip().lower()
            if use_existing_hf in ['', 'y', 'yes']:
                self.config['hf_token'] = 'use_env_var'
            else:
                new_token = input("Enter new HF Token (or press Enter to skip): ").strip()
                self.config['hf_token'] = new_token if new_token else 'none'
        else:
            hf_token = input("Enter HF Token (or press Enter to skip): ").strip()
            self.config['hf_token'] = hf_token if hf_token else 'none'
    
    def _setup_model_downloads(self):
        """Configure automatic model downloads"""
        print("\n MODEL DOWNLOADS")
        print("-" * 20)
        
        if self.config.get('hf_token', 'none') == 'none':
            print("  No Hugging Face token configured - skipping automatic downloads")
            self.config['auto_download_models'] = False
            return
        
        print("\nRecommended models for image analysis:")
        
        models = [
            {
                'name': 'BakLLaVA (Mistral-based)',
                'repo': 'SkunkworksAI/BakLLaVA-1',
                'files': ['BakLLaVA-1-Q4_K_M.gguf', 'BakLLaVA-1-clip-model.gguf'],
                'size': '~4GB',
                'description': 'Fast, local vision model based on Mistral'
            },
            {
                'name': 'LLaVA 1.6 (Vicuna-based)',
                'repo': 'liuhaotian/llava-v1.6-vicuna-7b',
                'files': ['model files'],
                'size': '~13GB',
                'description': 'High-quality vision model'
            }
        ]
        
        print("\nAvailable models:")
        for i, model in enumerate(models, 1):
            print(f"  {i}. {model['name']} ({model['size']})")
            print(f"     {model['description']}")
        
        download_choice = input(f"\nDownload models now? (y/N): ").strip().lower()
        if download_choice in ['y', 'yes']:
            self.config['auto_download_models'] = True
            
            # Select models to download
            model_selections = input(f"Select models to download (1-{len(models)}, comma-separated, or 'all'): ").strip()
            if model_selections.lower() == 'all':
                self.config['models_to_download'] = list(range(len(models)))
            else:
                try:
                    selections = [int(x.strip()) - 1 for x in model_selections.split(',')]
                    self.config['models_to_download'] = [i for i in selections if 0 <= i < len(models)]
                except:
                    print("Invalid selection - skipping downloads")
                    self.config['auto_download_models'] = False
        else:
            self.config['auto_download_models'] = False
    
    def _setup_default_preferences(self):
        """Configure default processing preferences"""
        print("\n  DEFAULT PREFERENCES")
        print("-" * 25)
        
        # Default processing goal
        print("What will be your most common use case?")
        print("  1. Archive Culling (fast, identify keepers vs deletes)")
        print("  2. Gallery Selection (detailed analysis for exhibitions)")
        print("  3. Catalog Organization (comprehensive tagging)")
        
        while True:
            try:
                goal_choice = int(input("Default goal (1-3): "))
                if goal_choice == 1:
                    self.config['default_goal'] = 'archive_cull'
                    break
                elif goal_choice == 2:
                    self.config['default_goal'] = 'gallery_select'
                    break
                elif goal_choice == 3:
                    self.config['default_goal'] = 'organize_catalog'
                    break
                else:
                    print("Invalid selection!")
            except ValueError:
                print("Please enter a number!")
        
        # Output preferences
        print(f"\nOutput format preference:")
        print("  1. XMP sidecar files (recommended for Lightroom)")
        print("  2. EXIF metadata (embedded in image files)")
        print("  3. CSV files only (no metadata modification)")
        
        while True:
            try:
                output_choice = int(input("Output format (1-3): "))
                if output_choice == 1:
                    self.config['default_output'] = 'xmp'
                    break
                elif output_choice == 2:
                    self.config['default_output'] = 'exif'
                    break
                elif output_choice == 3:
                    self.config['default_output'] = 'csv_only'
                    break
                else:
                    print("Invalid selection!")
            except ValueError:
                print("Please enter a number!")
        
        # Performance preferences
        cpu_cores = os.cpu_count() or 4
        print(f"\nPerformance settings (detected {cpu_cores} CPU cores):")
        
        max_workers = input(f"Max concurrent workers (recommended: {max(1, cpu_cores // 2)}): ").strip()
        try:
            self.config['max_workers'] = int(max_workers) if max_workers else max(1, cpu_cores // 2)
        except ValueError:
            self.config['max_workers'] = max(1, cpu_cores // 2)
    
    def _save_configuration(self):
        """Save configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
            print(f"\n Configuration saved to: {self.config_file}")
        except Exception as e:
            print(f" Failed to save configuration: {e}")
    
    def _get_directory_size(self, directory: Path) -> str:
        """Get human-readable directory size"""
        try:
            total_size = sum(f.stat().st_size for f in directory.rglob('*') if f.is_file())
            
            # Convert to human readable
            for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
                if total_size < 1024.0:
                    return f"{total_size:.1f} {unit}"
                total_size /= 1024.0
            return f"{total_size:.1f} PB"
        except:
            return "unknown size"
    
    @staticmethod
    def load_user_config() -> Dict:
        """Load user configuration if it exists"""
        config_file = Path("config/user_config.json")
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {}
    
    @staticmethod
    def has_been_configured() -> bool:
        """Check if the wizard has been run before"""
        return Path("config/user_config.json").exists()

def main():
    """Run the setup wizard"""
    if SetupWizard.has_been_configured():
        print(" Configuration already exists!")
        reconfigure = input("Run setup wizard again? (y/N): ").strip().lower()
        if reconfigure not in ['y', 'yes']:
            print("Setup cancelled.")
            return
    
    wizard = SetupWizard()
    wizard.run_setup()

if __name__ == "__main__":
    main()
