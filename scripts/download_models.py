#!/usr/bin/env python3
"""
Model Downloader for AI Image Analyzer
Downloads BakLLaVA and other vision models from HuggingFace
"""
import os
import json
import argparse
from pathlib import Path
from huggingface_hub import hf_hub_download, HfApi
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ModelDownloader:
    def __init__(self, models_dir="J:/models"):
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(exist_ok=True, parents=True)
        self.hf_token = os.getenv('HF_TOKEN')
        
        # Load user config if exists
        config_path = Path("config/user_config.json")
        if config_path.exists():
            with open(config_path, 'r') as f:
                config = json.load(f)
                self.models_dir = Path(config.get('model_directory', models_dir))
                self.hf_token = config.get('hf_token', self.hf_token)
    
    def download_bakllava(self):
        """Download BakLLaVA model files"""
        logger.info("🚀 Downloading BakLLaVA model...")
        
        # Using the advanced-stack conversion (from the article author)
        model_name = "advanced-stack/bakllava-mistral-v1-gguf"
        files_to_download = [
            "BakLLaVA-1-Q4_K_M.gguf",
            "BakLLaVA-1-clip-model.gguf"  # CLIP/vision projector
        ]
        
        bakllava_dir = self.models_dir / "BakLLaVA"
        bakllava_dir.mkdir(exist_ok=True)
        
        for filename in files_to_download:
            try:
                logger.info(f"📥 Downloading {filename}...")
                file_path = hf_hub_download(
                    repo_id=model_name,
                    filename=filename,
                    local_dir=bakllava_dir,
                    token=self.hf_token
                )
                logger.info(f"✅ Downloaded: {file_path}")
            except Exception as e:
                logger.error(f"❌ Failed to download {filename}: {e}")
                return False
        
        # Create model info file
        model_info = {
            "name": "BakLLaVA-1",
            "type": "vision_language",
            "base_model": "Mistral-7B",
            "size_gb": 4.2,
            "quantization": "Q4_K_M",
            "files": {
                "main_model": str(bakllava_dir / "BakLLaVA-1-Q4_K_M.gguf"),
                "clip_model": str(bakllava_dir / "BakLLaVA-1-clip-model.gguf")
            },
            "source": model_name,
            "downloaded": True
        }
        
        with open(bakllava_dir / "model_info.json", 'w') as f:
            json.dump(model_info, f, indent=2)
        
        logger.info("🎉 BakLLaVA download complete!")
        return True
    
    def download_llava_16(self):
        """Download LLaVA 1.6 model files"""
        logger.info("🚀 Downloading LLaVA 1.6 model...")
        
        # This is a placeholder - would need actual LLaVA 1.6 GGUF model
        logger.warning("⚠️ LLaVA 1.6 GGUF download not yet implemented")
        logger.info("💡 Recommendation: Use BakLLaVA for now, it's better optimized")
        return False
    
    def list_available_models(self):
        """List all available models in the models directory"""
        logger.info("📋 Available models in {}:".format(self.models_dir))
        
        for model_dir in self.models_dir.iterdir():
            if model_dir.is_dir():
                info_file = model_dir / "model_info.json"
                if info_file.exists():
                    with open(info_file, 'r') as f:
                        info = json.load(f)
                    logger.info(f"  ✅ {info['name']} ({info['size_gb']}GB) - {info['type']}")
                else:
                    logger.info(f"  📁 {model_dir.name} (unknown)")
    
    def check_model_exists(self, model_name):
        """Check if a model already exists"""
        model_dir = self.models_dir / model_name
        info_file = model_dir / "model_info.json"
        return info_file.exists()

def main():
    parser = argparse.ArgumentParser(description='Download AI models for image analysis')
    parser.add_argument('--model', choices=['bakllava', 'llava16', 'all'], 
                       default='bakllava', help='Model to download')
    parser.add_argument('--models-dir', default=None, 
                       help='Directory to store models (default: from config)')
    parser.add_argument('--list', action='store_true', 
                       help='List available models')
    
    args = parser.parse_args()
    
    downloader = ModelDownloader(args.models_dir) if args.models_dir else ModelDownloader()
    
    if args.list:
        downloader.list_available_models()
        return
    
    if args.model in ['bakllava', 'all']:
        if downloader.check_model_exists('BakLLaVA'):
            logger.info("✅ BakLLaVA already exists. Skipping download.")
        else:
            downloader.download_bakllava()
    
    if args.model in ['llava16', 'all']:
        downloader.download_llava_16()

if __name__ == "__main__":
    main()
