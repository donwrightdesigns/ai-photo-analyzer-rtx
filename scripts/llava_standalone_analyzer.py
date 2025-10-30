#!/usr/bin/env python3
"""
LLaVA Standalone Analyzer for AI Image Analyzer
Uses PyLLMCore with LLaVA model for local vision analysis
"""
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import base64
from io import BytesIO
from PIL import Image

try:
    from llm_core.llm import OpenWeightsModel
    LLAVA_AVAILABLE = True
except ImportError:
    LLAVA_AVAILABLE = False
    logging.warning("PyLLMCore not available. Install with: pip install py-llm-core")

logger = logging.getLogger(__name__)

class LLaVAStandaloneAnalyzer:
    """Local LLaVA image analyzer"""
    
    def __init__(self, models_dir: str = "J:/models", gpu_config: Optional[Dict] = None):
        self.models_dir = Path(models_dir)
        self.model_path = None
        self.clip_path = None
        self.assistant = None
        self.available = False
        self.gpu_config = gpu_config or {}
        
        if not LLAVA_AVAILABLE:
            logger.error("LLaVA not available: PyLLMCore not installed")
            return
            
        self._find_model_files()
        if self.model_path and self.clip_path:
            self._initialize_assistant()
    
    def _find_model_files(self):
        """Find LLaVA model files"""
        llava_dir = self.models_dir / "llava-v1.5-7b-GGUF"
        
        if not llava_dir.exists():
            logger.error(f"LLaVA directory not found: {llava_dir}")
            return
        
        # Check for model files
        model_file = llava_dir / "ggml-model-q4_k.gguf"
        clip_file = llava_dir / "mmproj-model-f16.gguf"
        
        if not model_file.exists():
            logger.error(f"LLaVA model file not found: {model_file}")
            return
            
        if not clip_file.exists():
            logger.error(f"LLaVA CLIP file not found: {clip_file}")
            return
        
        self.model_path = str(model_file)
        self.clip_path = str(clip_file)
        logger.info(f"Found LLaVA model: {self.model_path}")
        logger.info(f"Found LLaVA CLIP: {self.clip_path}")
    
    def _initialize_assistant(self):
        """Initialize the OpenWeights model with LLaVA"""
        try:
            use_gpu = self.gpu_config.get('enable_rtx', False)
            gpu_layers = self.gpu_config.get('rtx_gpu_layers', 0) if use_gpu else 0
            batch_size = int(self.gpu_config.get('rtx_batch_size', '128')) if use_gpu else 128
            
            loader_kwargs = {
                "model_path": self.model_path,
                "clip_model_path": self.clip_path,
                "n_ctx": 2048,
                "n_gpu_layers": gpu_layers,
                "n_threads": 8,
                "verbose": False,
                "use_mlock": False,
                "use_mmap": True,
                "n_batch": batch_size,
                "f16_kv": use_gpu,
            }
            
            if use_gpu:
                logger.info(f"Initializing LLaVA with GPU support: {gpu_layers} layers, batch size {batch_size}")
            else:
                logger.info("Initializing LLaVA in CPU-only mode")

            # Use direct llama-cpp-python with vision support
            try:
                from llama_cpp import Llama
                
                # Initialize with vision model
                self.llama_model = Llama(
                    model_path=self.model_path,
                    chat_format="llava-1-5",  # Specify LLaVA chat format
                    clip_model_path=self.clip_path,  # Vision model
                    n_ctx=2048,
                    n_gpu_layers=gpu_layers,
                    n_threads=8,
                    verbose=False,
                    n_batch=batch_size,
                    f16_kv=use_gpu
                )
                
                logger.info(f"LLaVA 7B model loaded with vision support")
                logger.info(f"Model path: {self.model_path}")
                logger.info(f"CLIP path: {self.clip_path}")
                    
            except Exception as e:
                logger.error(f"Failed to initialize LLaVA: {e}")
                self.llama_model = None
                raise e
            self.available = True
            logger.info("LLaVA model initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize LLaVA: {e}")
            self.available = False
    
    def _prepare_image(self, image_path: str) -> Optional[str]:
        """Prepare image for analysis"""
        try:
            with Image.open(image_path) as img:
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                max_size = 1024
                if max(img.size) > max_size:
                    img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                
                buffer = BytesIO()
                img.save(buffer, format='JPEG', quality=85)
                img_base64 = base64.b64encode(buffer.getvalue()).decode()
                return img_base64
        except Exception as e:
            logger.error(f"Error preparing image {image_path}: {e}")
            return None

    def analyze_image(self, image_path: str, prompt: str) -> Optional[Dict]:
        """Analyze an image using LLaVA"""
        if not self.available:
            return {"error": "LLaVA not available"}
        
        img_base64 = self._prepare_image(image_path)
        if not img_base64:
            return {"error": "Failed to prepare image"}
            
        try:
            if not hasattr(self, 'llama_model') or self.llama_model is None:
                return {"error": "LLaVA model not properly initialized"}
                
            # Use direct llama-cpp vision capabilities
            import base64
            from io import BytesIO
            
            # Create the message with image
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{img_base64}"
                            }
                        }
                    ]
                }
            ]
            
            # Generate response using vision capabilities
            response = self.llama_model.create_chat_completion(
                messages=messages,
                temperature=0.2,
                max_tokens=500
            )
            
            if response and 'choices' in response and response['choices']:
                response_text = response['choices'][0]['message']['content']
                
                if response_text and response_text.strip():
                    # Clean up the response
                    cleaned_response = response_text.strip().replace('```json', '').replace('```', '')
                    try:
                        parsed_response = json.loads(cleaned_response)
                        return parsed_response
                    except json.JSONDecodeError:
                        # If JSON parsing fails, return the text as an error with context
                        return {"error": f"Invalid JSON response", "raw_response": cleaned_response[:200]}
                else:
                    return {"error": "Model returned empty response"}
            return None

        except Exception as e:
            logger.error(f"Error during LLaVA analysis: {e}")
            return {"error": f"Analysis failed: {str(e)}", "raw_response": ""}

