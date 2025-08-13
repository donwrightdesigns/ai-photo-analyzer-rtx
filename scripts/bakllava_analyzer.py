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
    
    def __init__(self, models_dir: str = "J:/models"):
        self.models_dir = Path(models_dir)
        self.model_path = None
        self.clip_path = None
        self.assistant = None
        self.available = False
        
        if not BAKLLAVA_AVAILABLE:
            logger.error("BakLLaVA not available: PyLLMCore not installed")
            return
            
        self._find_model_files()
        if self.model_path and self.clip_path:
            self._initialize_assistant()
    
    def _find_model_files(self):
        """Find BakLLaVA model files"""
        bakllava_dir = self.models_dir / "BakLLaVA"
        
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
            # Initialize OpenWeights model with loader_kwargs for GGUF models
            # Use CPU-only mode to avoid GPU conflicts with other processes
            loader_kwargs = {
                "model_path": self.model_path,
                "clip_model_path": self.clip_path,
                "n_ctx": 2048,
                "n_gpu_layers": 0,  # Force CPU-only to avoid GPU conflicts
                "n_threads": 4,     # Use 4 CPU threads for reasonable performance
                "verbose": False,
                "use_mlock": False,  # Don't lock memory to avoid conflicts
                "use_mmap": True,    # Use memory mapping for efficiency
            }
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
                # Convert to RGB if necessary
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Resize if too large (BakLLaVA works best with smaller images)
                max_size = 1024
                if max(img.size) > max_size:
                    img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                
                # Convert to base64
                buffer = BytesIO()
                img.save(buffer, format='JPEG', quality=85)
                img_base64 = base64.b64encode(buffer.getvalue()).decode()
                return img_base64
        except Exception as e:
            logger.error(f"Error preparing image {image_path}: {e}")
            return None
    
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
                response = self.model.ask(
                    prompt=prompt,
                    image_b64=img_base64,
                    temperature=0.1
                )
                results[analysis_type] = response.strip() if response else "No response"
                logger.info(f"✅ Completed {analysis_type} analysis")
            except Exception as e:
                logger.error(f"Error in {analysis_type} analysis: {e}")
                results[analysis_type] = f"Error: {str(e)}"
        
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
                Rate this image from 1-10 for archival value. Consider:
                - Technical quality (focus, exposure, composition)
                - Uniqueness (is this likely a duplicate or similar to others?)
                - Content importance (memorable moments, people, places)
                
                Return only a number 1-10 and brief reason.
                """,
                "quick_tags": """
                Provide 3-5 essential keywords for this image for organization.
                Focus on: main subjects, location type, activity, time period.
                Format as comma-separated list.
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
