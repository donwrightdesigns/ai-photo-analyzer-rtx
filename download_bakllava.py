#!/usr/bin/env python3
"""
Download BakLLaVA model files from HuggingFace
"""

import os
import json
from pathlib import Path
from huggingface_hub import hf_hub_download
from setup_wizard import SetupWizard

def download_bakllava():
    """Download BakLLaVA model files"""
    
    # Load user config
    config = SetupWizard.load_user_config()
    
    if not config:
        print("❌ No configuration found. Run setup_wizard.py first.")
        return
    
    model_dir = Path(config.get('model_directory', 'models'))
    hf_token = config.get('hf_token', 'none')
    
    if hf_token == 'none':
        print("❌ No HuggingFace token configured.")
        return
    elif hf_token == 'use_env_var':
        hf_token = os.getenv('HF_TOKEN')
        if not hf_token:
            print("❌ HF_TOKEN environment variable not found.")
            return
    
    # Create BakLLaVA subdirectory
    bakllava_dir = model_dir / "BakLLaVA"
    bakllava_dir.mkdir(exist_ok=True)
    
    print(f"📥 Downloading BakLLaVA to: {bakllava_dir}")
    print(f"🔑 Using HuggingFace token: {hf_token[:10]}...")
    
    # Files to download
    files_to_download = [
        {
            'filename': 'BakLLaVA-1-Q4_K_M.gguf',
            'size_estimate': '~4.0GB'
        },
        {
            'filename': 'BakLLaVA-1-clip-model.gguf', 
            'size_estimate': '~1.7GB'
        }
    ]
    
    repo_id = "SkunkworksAI/BakLLaVA-1"
    
    for file_info in files_to_download:
        filename = file_info['filename']
        target_path = bakllava_dir / filename
        
        if target_path.exists():
            print(f"✅ {filename} already exists, skipping...")
            continue
            
        print(f"\n📥 Downloading {filename} ({file_info['size_estimate']})...")
        print(f"   This may take several minutes depending on your connection...")
        
        try:
            downloaded_path = hf_hub_download(
                repo_id=repo_id,
                filename=filename,
                cache_dir=str(model_dir),
                token=hf_token
            )
            
            # Move from cache to our directory structure
            if Path(downloaded_path).exists():
                if not target_path.exists():
                    import shutil
                    shutil.copy2(downloaded_path, target_path)
                
                print(f"✅ Downloaded: {filename}")
                print(f"   Saved to: {target_path}")
            
        except Exception as e:
            print(f"❌ Failed to download {filename}: {e}")
            continue
    
    # Verify downloads
    print(f"\n🔍 Verifying downloads...")
    all_files_present = True
    
    for file_info in files_to_download:
        filename = file_info['filename']
        target_path = bakllava_dir / filename
        
        if target_path.exists():
            size_mb = target_path.stat().st_size / (1024*1024)
            print(f"✅ {filename} ({size_mb:.1f} MB)")
        else:
            print(f"❌ {filename} - missing")
            all_files_present = False
    
    if all_files_present:
        print(f"\n🎉 BakLLaVA download complete!")
        print(f"📁 Models saved to: {bakllava_dir}")
        print(f"\nYou can now use BakLLaVA in the enhanced analyzer:")
        print(f"python scripts/enhanced_unified_analyzer_v3.py")
    else:
        print(f"\n⚠️  Some files failed to download. Check your internet connection and try again.")

if __name__ == "__main__":
    try:
        download_bakllava()
    except ImportError as e:
        print("❌ Missing dependency. Install with:")
        print("pip install huggingface_hub")
    except Exception as e:
        print(f"❌ Download failed: {e}")
