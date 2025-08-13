#!/usr/bin/env python3
"""
Direct BakLLaVA Test using llama-cpp-python
Bypasses PyLLMCore to test model files directly
"""
import base64
import logging
from pathlib import Path
from PIL import Image
from io import BytesIO

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def prepare_image_base64(image_path: str) -> str:
    """Convert image to base64 for model input"""
    try:
        with Image.open(image_path) as img:
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Resize to reasonable size
            max_size = 512
            if max(img.size) > max_size:
                img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            
            buffer = BytesIO()
            img.save(buffer, format='JPEG', quality=85)
            img_base64 = base64.b64encode(buffer.getvalue()).decode()
            return img_base64
    except Exception as e:
        logger.error(f"Error preparing image: {e}")
        return None

def test_bakllava_direct(image_path: str):
    """Test BakLLaVA model directly with llama-cpp-python"""
    
    # Model paths
    models_dir = Path("J:/models/BakLLaVA")
    model_path = models_dir / "BakLLaVA-1-Q4_K_M.gguf"
    clip_path = models_dir / "BakLLaVA-1-clip-model.gguf"
    
    if not model_path.exists():
        logger.error(f"Model file not found: {model_path}")
        return False
        
    if not clip_path.exists():
        logger.error(f"CLIP file not found: {clip_path}")
        return False
    
    try:
        from llama_cpp import Llama
        
        logger.info("🚀 Initializing BakLLaVA model (CPU-only)...")
        
        # Initialize with CPU-only, basic settings
        llama = Llama(
            model_path=str(model_path),
            clip_model_path=str(clip_path),
            n_ctx=2048,
            n_gpu_layers=0,  # CPU only
            verbose=False,
            n_threads=4
        )
        
        logger.info("✅ Model loaded successfully!")
        
        # Prepare image
        img_b64 = prepare_image_base64(image_path)
        if not img_b64:
            return False
            
        logger.info(f"🔍 Analyzing {image_path}...")
        
        # Use proper BakLLaVA prompt format (similar to LLaVA)
        prompt = "USER: <image>\nDescribe this image briefly.\nASSISTANT:"
        
        # Use direct completion instead of chat completion
        response = llama(
            prompt=prompt,
            temperature=0.1,
            max_tokens=200,
            images=[img_b64]  # Pass image as base64
        )
        
        result = response['choices'][0]['text'] if 'choices' in response else str(response)
        logger.info(f"📊 Result: {result}")
        
        return True
        
    except ImportError:
        logger.error("❌ llama-cpp-python not available")
        return False
    except Exception as e:
        logger.error(f"❌ Error during direct test: {e}")
        return False

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Test BakLLaVA directly')
    parser.add_argument('image_path', help='Path to test image')
    args = parser.parse_args()
    
    success = test_bakllava_direct(args.image_path)
    if success:
        print("✅ BakLLaVA direct test successful!")
    else:
        print("❌ BakLLaVA direct test failed")

if __name__ == "__main__":
    main()
