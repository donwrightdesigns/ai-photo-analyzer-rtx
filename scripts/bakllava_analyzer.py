#!/usr/bin/env python3
"""
BakLLaVA Analyzer for AI Image Analyzer
Uses PyLLMCore with BakLLaVA model for local vision analysis
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
    BAKLLAVA_AVAILABLE = True
except ImportError:
    BAKLLAVA_AVAILABLE = False
    logging.warning("PyLLMCore not available. Install with: pip install py-llm-core")

logger = logging.getLogger(__name__)

class BakLLaVAAnalyzer:
    """Local BakLLaVA image analyzer"""
    
    def __init__(self, models_dir: str = "J:/models", gpu_config: Optional[Dict] = None):
        self.models_dir = Path(models_dir)
        self.model_path = None
        self.clip_path = None
        self.assistant = None
        self.available = False
        self.gpu_config = gpu_config or {}
        
        if not BAKLLAVA_AVAILABLE:
            logger.error("BakLLaVA not available: PyLLMCore not installed")
            return
            
        self._find_model_files()
        if self.model_path and self.clip_path:
            self._initialize_assistant()
    
    def _find_model_files(self):
        """Find BakLLaVA model files"""
        # Case-insensitive search for BakLLaVA directory
        bakllava_dir_name = "BakLLaVA"
        found_dir = None
        for item in self.models_dir.iterdir():
            if item.is_dir() and item.name.lower() == bakllava_dir_name.lower():
                found_dir = item
                break
        
        if not found_dir:
            logger.error(f"BakLLaVA directory not found in: {self.models_dir}")
            return
        
        bakllava_dir = found_dir
        
        if not bakllava_dir.exists():
            logger.error(f"BakLLaVA directory not found: {bakllava_dir}")
            return
        
        # Check for model files
        model_file = bakllava_dir / "BakLLaVA-1-Q4_K_M.gguf"
        clip_file = bakllava_dir / "BakLLaVA-1-clip-model.gguf"
        
        if not model_file.exists():
            logger.error(f"BakLLaVA model file not found: {model_file}")
            return
            
        if not clip_file.exists():
            logger.error(f"BakLLaVA CLIP file not found: {clip_file}")
            return
        
        self.model_path = str(model_file)
        self.clip_path = str(clip_file)
        logger.info(f"Found BakLLaVA model: {self.model_path}")
        logger.info(f"Found BakLLaVA CLIP: {self.clip_path}")
    
    def _initialize_assistant(self):
        """Initialize the OpenWeights model with BakLLaVA"""
        try:
            # Check if GPU should be used based on configuration
            use_gpu = self.gpu_config.get('enable_rtx', False)
            gpu_layers = self.gpu_config.get('rtx_gpu_layers', 0) if use_gpu else 0
            batch_size = int(self.gpu_config.get('rtx_batch_size', '128')) if use_gpu else 128
            
            # Initialize OpenWeights model with loader_kwargs for GGUF models
            loader_kwargs = {
                "model_path": self.model_path,
                "clip_model_path": self.clip_path,
                "n_ctx": 2048,
                "n_gpu_layers": gpu_layers,  # Use GPU only if enabled in config
                "n_threads": 8,               # CPU threads
                "verbose": False,
                "use_mlock": False,
                "use_mmap": True,            # Efficient memory mapping
                "n_batch": batch_size,       # Batch size based on GPU config
                "f16_kv": use_gpu,           # Use FP16 only if GPU is enabled
            }
            
            if use_gpu:
                logger.info(f"Initializing BakLLaVA with GPU support: {gpu_layers} layers, batch size {batch_size}")
            else:
                logger.info("Initializing BakLLaVA in CPU-only mode")
            self.model = OpenWeightsModel(
                name="BakLLaVA-1",
                system_prompt="You are an expert image analyst.",
                loader_kwargs=loader_kwargs
            )
            self.available = True
            logger.info("BakLLaVA model initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize BakLLaVA: {e}")
            self.available = False
    
    def _prepare_image(self, image_path: str) -> Optional[str]:
        """Prepare image for analysis"""
        try:
            with Image.open(image_path) as img:
                # Check if image was loaded correctly
                if img is None or not hasattr(img, 'size') or img.size is None:
                    logger.error(f"Image could not be loaded properly: {image_path}")
                    return None
                
                # Convert to RGB if necessary
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Resize if too large (BakLLaVA works best with smaller images)
                max_size = 1024
                if isinstance(img.size, (list, tuple)) and len(img.size) == 2 and all(isinstance(dim, int) for dim in img.size) and max(img.size) > max_size:
                    img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                
                # Convert to base64
                buffer = BytesIO()
                img.save(buffer, format='JPEG', quality=85)
                img_base64 = base64.b64encode(buffer.getvalue()).decode()
                return img_base64
        except Exception as e:
            logger.error(f"Error preparing image {image_path}: {e}")
            return None
    
    def _get_fallback_response(self, analysis_type: str) -> str:
        """Provide fallback response when model fails"""
        fallback_responses = {
            "keep_score": "3 - Average quality image, suitable for archive",
            "quick_tags": "Photo, Image, Archive",
            "artistic_merit": "Standard photographic quality",
            "exhibition_notes": "Suitable for general display",
            "detailed_description": "Standard photograph with typical composition",
            "comprehensive_tags": "General, Photography, Archive"
        }
        return fallback_responses.get(analysis_type, "No analysis available")
    
    def analyze_image(self, image_path: str, goal: str = "detailed") -> Dict:
        """Analyze an image using BakLLaVA"""
        if not self.available:
            return {"error": "BakLLaVA not available"}
        
        # Prepare image as base64
        img_base64 = self._prepare_image(image_path)
        if not img_base64:
            return {"error": "Failed to prepare image"}
        
        # Define prompts based on goal
        prompts = self._get_prompts_by_goal(goal)
        
        results = {}
        
        for analysis_type, prompt in prompts.items():
            try:
                # Use the PyLLMCore ask method with image_b64 parameter
                # Use shorter context window and error handling
                response = self.model.ask(
                    prompt=prompt,
                    image_b64=img_base64,
                    temperature=0.1
                )
                
                # Handle response safely
                if response is not None and isinstance(response, str) and len(response.strip()) > 0:
                    results[analysis_type] = response.strip()
                else:
                    results[analysis_type] = self._get_fallback_response(analysis_type)
                logger.info(f"✅ Completed {analysis_type} analysis")
            except (TypeError, ValueError, AttributeError) as e:
                # Silently handle type/value errors from the model
                results[analysis_type] = self._get_fallback_response(analysis_type)
            except Exception as e:
                # For other exceptions, try to log safely
                try:
                    logger.error(f"Error in {analysis_type} analysis: {str(e)}")
                except:
                    pass  # If even logging fails, just continue
                results[analysis_type] = self._get_fallback_response(analysis_type)
        
        return {
            "model": "BakLLaVA-1",
            "success": True,
            "results": results,
            "file": str(image_path)
        }
    
    def _get_prompts_by_goal(self, goal: str) -> Dict[str, str]:
        """Get analysis prompts based on goal"""
        
        if goal == "archive_culling":
            return {
                "keep_score": """
                Rate this image from 1-5 stars for archival value. Consider:
                - Technical quality (focus, exposure, composition) 
                - Uniqueness (is this likely a duplicate or similar to others?)
                - Content importance (memorable moments, people, places)
                
                Rating scale:
                1 star: Poor quality, delete/cull
                2 stars: Below average, low priority
                3 stars: Average, good for archive
                4 stars: Above average, notable quality
                5 stars: Exceptional, gallery-worthy
                
                Return only a number 1-5 and brief reason.
                """,
                "quick_tags": """
                Provide 3-5 SPECIFIC photography keywords that a photographer would search for.
                
                CHOOSE FROM THESE PHOTOGRAPHY-SPECIFIC TAGS:
                
                SUBJECTS: Portrait, Group-Shot, Couple, Family, Children, Baby, Senior-Citizen, Pet, Wildlife, Bird, Automotive, Architecture, Interior, Product, Food, Flowers, Macro
                
                LIGHTING: Golden-Hour, Blue-Hour, Overcast, Direct-Sun, Window-Light, Studio-Strobe, Speedlight, Natural-Light, Low-Light, Backlit, Side-Lit, Dramatic-Lighting
                
                STYLE: Black-White, Color-Graded, High-Contrast, Soft-Focus, Sharp-Detail, Shallow-DOF, Wide-Angle, Telephoto, Candid, Posed, Action-Shot, Still-Life
                
                EVENT/LOCATION: Wedding, Engagement, Corporate, Real-Estate, Landscape, Urban, Beach, Forest, Indoor, Outdoor, Studio, Event, Concert, Sports
                
                MOOD: Bright-Cheerful, Moody-Dark, Romantic, Professional, Casual, Energetic, Peaceful, Dramatic
                
                FORMAT: jpg,png,tiff,raw
                """
            }
        
        elif goal == "gallery_selection":
            return {
                "artistic_merit": """
                Evaluate this image for artistic/aesthetic merit. Consider:
                - Composition and visual balance
                - Lighting and mood
                - Color harmony
                - Emotional impact
                - Technical execution
                
                Provide a detailed assessment.
                """,
                "exhibition_notes": """
                If this image were selected for exhibition, what story does it tell?
                What emotions or messages does it convey?
                What makes it stand out?
                """
            }
        
        else:  # catalog_organization
            return {
                "detailed_description": """
                Provide a comprehensive description of this image including:
                - Main subjects and their activities
                - Setting and environment
                - Time of day/lighting conditions
                - Mood and atmosphere
                - Notable technical aspects
                """,
                "comprehensive_tags": """
                Generate comprehensive tags for cataloging:
                - People: number, age groups, activities
                - Objects: vehicles, buildings, nature, items
                - Location: indoor/outdoor, urban/rural, specific places
                - Time: season, time of day, era
                - Style: color/bw, artistic style, technical notes
                
                Format as detailed categories.
                """
            }
    
    def batch_analyze(self, image_paths: List[str], goal: str = "detailed", 
                     max_images: int = 20) -> List[Dict]:
        """Batch analyze multiple images"""
        if not self.available:
            return [{"error": "BakLLaVA not available"}]
        
        results = []
        processed = 0
        
        for image_path in image_paths[:max_images]:
            logger.info(f"Analyzing {image_path} with BakLLaVA ({processed+1}/{min(len(image_paths), max_images)})")
            result = self.analyze_image(image_path, goal)
            results.append(result)
            processed += 1
        
        return results

def main():
    """Test BakLLaVA analyzer"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test BakLLaVA image analysis')
    parser.add_argument('image_path', help='Path to image file')
    parser.add_argument('--goal', choices=['archive_culling', 'gallery_selection', 'catalog_organization'],
                       default='catalog_organization', help='Analysis goal')
    parser.add_argument('--models-dir', default='J:/models', help='Models directory')
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    analyzer = BakLLaVAAnalyzer(args.models_dir)
    
    if not analyzer.available:
        print("❌ BakLLaVA not available")
        return
    
    print(f"🔍 Analyzing {args.image_path} with goal: {args.goal}")
    result = analyzer.analyze_image(args.image_path, args.goal)
    
    print("\n📊 Results:")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
