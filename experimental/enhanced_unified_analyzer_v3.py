# ----------------------------------------------------------------------
#  Enhanced AI Image Analyzer v3.1 - Model Comparison & BakLLaVA Support
#  
#  New Features:
#  - Interactive model selection menu
#  - Test mode (first 20 images)
#  - Model comparison feature
#  - BakLLaVA integration via llama.cpp
#  - Goal-oriented processing modes
# ----------------------------------------------------------------------

import os
import base64
import requests
import json
import argparse
import csv
import logging
import logging.handlers
import psutil
import time
import tempfile
import math
import xml.etree.ElementTree as ET
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image, ImageOps
import piexif
from typing import Optional, Dict, List, Tuple, Any
from dataclasses import dataclass
from datetime import datetime

# Try to import optional dependencies
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

try:
    from llama_cpp import Llama
    from llama_cpp.llama_chat_format import Llava15ChatHandler
    LLAMACPP_AVAILABLE = True
except ImportError:
    LLAMACPP_AVAILABLE = False

try:
    import sys
    from pathlib import Path
    scripts_dir = Path(__file__).parent
    sys.path.insert(0, str(scripts_dir))
    from bakllava_simple import SimpleBakLLaVAAnalyzer
    BAKLLAVA_AVAILABLE = True
except ImportError:
    BAKLLAVA_AVAILABLE = False

# Processing Goals - determines prompts, speed, and output focus
@dataclass
class ProcessingGoal:
    name: str
    description: str
    prompt_type: str
    enable_critique: bool
    max_workers_multiplier: float
    timeout_seconds: int
    include_tags: bool
    include_categories: bool
    focus_on_quality: bool

PROCESSING_GOALS = {
    "archive_cull": ProcessingGoal(
        name="Archive Culling",
        description="Fast processing to identify keepers vs. delete candidates (20-year archive friendly)",
        prompt_type="cull",
        enable_critique=False,
        max_workers_multiplier=1.5,  # More aggressive threading
        timeout_seconds=60,  # Faster timeout
        include_tags=False,  # Skip detailed tagging
        include_categories=False,
        focus_on_quality=True
    ),
    "gallery_select": ProcessingGoal(
        name="Gallery Selection",
        description="Detailed analysis for portfolio/exhibition selection",
        prompt_type="gallery",
        enable_critique=True,
        max_workers_multiplier=0.8,  # More conservative for quality
        timeout_seconds=120,
        include_tags=True,
        include_categories=True,
        focus_on_quality=True
    ),
    "organize_catalog": ProcessingGoal(
        name="Catalog Organization", 
        description="Comprehensive tagging and categorization for searchability",
        prompt_type="catalog",
        enable_critique=False,
        max_workers_multiplier=1.0,
        timeout_seconds=90,
        include_tags=True,
        include_categories=True,
        focus_on_quality=False
    ),
    "model_compare": ProcessingGoal(
        name="Model Comparison",
        description="Test different AI models on same images for evaluation",
        prompt_type="compare",
        enable_critique=True,
        max_workers_multiplier=0.5,  # Conservative for accuracy
        timeout_seconds=120,
        include_tags=True,
        include_categories=True,
        focus_on_quality=True
    )
}

# Enhanced Configuration
@dataclass
class EnhancedConfig:
    """Enhanced configuration with goal-oriented processing"""
    # Processing goal
    processing_goal: str = "archive_cull"
    
    # Model settings
    model_type: str = "llava"  # "llava", "gemini", "bakllava"
    ollama_url: str = "http://localhost:11434/api/generate"
    llava_model_name: str = "llava:13b"
    gemini_model_name: str = "gemini-2.0-flash-exp"
    bakllava_model_path: str = ""
    bakllava_clip_path: str = ""
    api_key: Optional[str] = None
    
    # Test mode settings
    test_mode: bool = False
    test_image_count: int = 20
    enable_comparison: bool = False
    comparison_model: Optional[str] = None
    
    # Output settings (XMP focus for Lightroom)
    generate_xmp: bool = True  # Default to XMP for Lightroom collections
    modify_exif: bool = False
    xmp_collection_prefix: str = "AI_Analysis"  # For Lightroom collections
    
    # Processing settings (will be modified by goal)
    max_workers: int = 4
    timeout: int = 120
    
    # Image optimization
    optimize_images: bool = True
    max_dimension: int = 1024
    quality: int = 85
    min_dimension: int = 200
    
    # System monitoring
    check_lightroom: bool = True
    max_memory_usage: float = 0.8
    max_cpu_usage: float = 0.7
    
    # Logging
    log_file: str = "enhanced_analyzer.log"
    log_level: str = "INFO"
    max_log_size: int = 10 * 1024 * 1024
    log_backup_count: int = 5
    
    # Output
    output_file: str = "enhanced_analysis_results.csv"
    comparison_file: str = "model_comparison_results.csv"
    save_progress: bool = True
    progress_file: str = "enhanced_progress.json"

# Classification Schema
CATEGORIES = ["People", "Place", "Thing"]
SUB_CATEGORIES = [
    "Candid", "Posed", "Automotive", "Real Estate", "Landscape",
    "Events", "Animal", "Product", "Food"
]
TAGS = [
    "Strobist", "Available Light", "Natural Light", "Beautiful", 
    "Black & White", "Timeless", "Low Quality", "Sentimental", 
    "Action", "Minimalist", "Out of Focus", "Other", "Evocative", 
    "Disturbing", "Boring", "Wedding", "Bride", "Groom", "Family", 
    "Love", "Calm", "Busy"
]

class PromptManager:
    """Generate prompts based on processing goals"""
    
    @staticmethod
    def create_prompt(goal: ProcessingGoal) -> str:
        """Create goal-specific prompts"""
        
        if goal.prompt_type == "cull":
            return PromptManager._create_cull_prompt()
        elif goal.prompt_type == "gallery":
            return PromptManager._create_gallery_prompt()
        elif goal.prompt_type == "catalog":
            return PromptManager._create_catalog_prompt()
        elif goal.prompt_type == "compare":
            return PromptManager._create_comparison_prompt()
        else:
            return PromptManager._create_default_prompt()
    
    @staticmethod
    def _create_cull_prompt() -> str:
        """Fast culling prompt - focus on keep/delete decision"""
        return """
        You are a professional photographer reviewing a 20-year photo archive for culling.
        Your goal is to quickly identify photos worth keeping vs. those that should be deleted.
        
        FOCUS ON:
        - Technical quality (focus, exposure, composition basics)
        - Obvious keepers vs. clear rejects
        - Speed over detailed analysis
        
        SCORING (1-10, optimized for culling):
        1-3: DELETE (blurry, bad exposure, no value)
        4-6: MAYBE (average quality, consider context)
        7-10: KEEP (good to excellent, definitely preserve)
        
        RESPOND WITH VALID JSON ONLY:
        {
          "score": 7,
          "cull_decision": "KEEP",
          "reason": "Sharp focus, good exposure, interesting subject"
        }
        """
    
    @staticmethod  
    def _create_gallery_prompt() -> str:
        """Detailed gallery selection prompt"""
        return f"""
        You are a gallery curator selecting photographs for a fine art exhibition.
        Evaluate for artistic merit, technical excellence, and emotional impact.
        
        ANALYSIS CRITERIA:
        1. Technical Excellence: Focus, exposure, composition, lighting
        2. Artistic Merit: Creativity, emotional impact, storytelling
        3. Exhibition Potential: Uniqueness, broad appeal, memorable impact
        
        CLASSIFICATION:
        CATEGORIES: {", ".join(CATEGORIES)}
        SUB_CATEGORIES: {", ".join(SUB_CATEGORIES)}  
        TAGS: {", ".join(TAGS)} (select 2-4 most relevant)
        
        SCORING (1-10):
        1-2: Poor quality, no artistic merit
        3-4: Below average, technical issues
        5-6: Average, competent but unremarkable
        7-8: Above average, strong potential
        9-10: Exceptional, exhibition worthy
        
        RESPOND WITH VALID JSON ONLY:
        {{
          "category": "chosen_category",
          "subcategory": "chosen_subcategory", 
          "tags": ["tag1", "tag2", "tag3"],
          "score": 7,
          "critique": "Professional assessment focusing on what makes this image succeed or fail as fine art."
        }}
        """
    
    @staticmethod
    def _create_catalog_prompt() -> str:
        """Comprehensive cataloging prompt"""
        return f"""
        You are organizing a photo library for maximum searchability and organization.
        Focus on accurate categorization and comprehensive tagging.
        
        CLASSIFICATION (select most accurate):
        CATEGORIES: {", ".join(CATEGORIES)}
        SUB_CATEGORIES: {", ".join(SUB_CATEGORIES)}
        TAGS: {", ".join(TAGS)} (select 3-5 relevant tags)
        
        SCORING (1-10, for organization priority):
        1-3: Low priority (duplicates, test shots, poor quality)
        4-6: Medium priority (average family photos, decent shots)
        7-10: High priority (important events, excellent quality, unique moments)
        
        RESPOND WITH VALID JSON ONLY:
        {{
          "category": "chosen_category",
          "subcategory": "chosen_subcategory",
          "tags": ["tag1", "tag2", "tag3", "tag4"], 
          "score": 7,
          "priority": "HIGH"
        }}
        """
    
    @staticmethod
    def _create_comparison_prompt() -> str:
        """Model comparison prompt"""
        return PromptManager._create_gallery_prompt()  # Use detailed analysis for comparison
    
    @staticmethod
    def _create_default_prompt() -> str:
        """Default balanced prompt"""
        return PromptManager._create_gallery_prompt()

class ModelSelector:
    """Interactive model and goal selection"""
    
    @staticmethod
    def detect_available_models() -> Dict[str, bool]:
        """Detect which models are available"""
        available = {
            'gemini': GEMINI_AVAILABLE,
            'ollama': ModelSelector._check_ollama(),
            'bakllava': LLAMACPP_AVAILABLE and ModelSelector._check_bakllava_files()
        }
        return available
    
    @staticmethod
    def _check_ollama() -> bool:
        """Check if Ollama is running with LLaVA"""
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get('models', [])
                return any('llava' in model.get('name', '').lower() for model in models)
        except:
            pass
        return False
    
    @staticmethod
    def _check_bakllava_files() -> bool:
        """Check if BakLLaVA files exist"""
        return ModelSelector._find_bakllava_files() is not None
    
    @staticmethod
    def _find_bakllava_files() -> Optional[Tuple[Path, Path]]:
        """Find BakLLaVA model files"""
        search_paths = [
            Path("J:/models"),  # Your specific models directory
            Path.cwd(),
            Path.cwd() / "models", 
            Path.home() / "models",
            Path.home() / "Downloads"
        ]
        
        model_file = None
        clip_file = None
        
        for base_path in search_paths:
            if not base_path.exists():
                continue
            for file_path in base_path.rglob("*.gguf"):
                # Skip cache directories and only look for actual .gguf files
                if '.cache' in str(file_path) or file_path.suffix != '.gguf':
                    continue
                if file_path.is_file():
                    if "BakLLaVA-1-Q4_K_M.gguf" in file_path.name:
                        model_file = file_path
                    elif "BakLLaVA-1-clip-model.gguf" in file_path.name:
                        clip_file = file_path
        
        if model_file and clip_file:
            return model_file, clip_file
        return None
    
    @staticmethod
    def show_setup_menu() -> Tuple[str, EnhancedConfig]:
        """Show comprehensive setup menu"""
        print("\n" + "="*70)
        print("🤖 ENHANCED AI IMAGE ANALYZER v3.1 - GOAL-ORIENTED PROCESSING")
        print("="*70)
        
        # Step 1: Select processing goal
        goal = ModelSelector._select_processing_goal()
        
        # Step 2: Select model
        model_type = ModelSelector._select_model()
        
        # Step 3: Configure based on selections
        config = ModelSelector._create_config(goal, model_type)
        
        return model_type, config
    
    @staticmethod
    def _select_processing_goal() -> ProcessingGoal:
        """Select processing goal"""
        print("\n🎯 SELECT YOUR PROCESSING GOAL:")
        print("   Your goal determines speed, detail level, and output focus")
        print()
        
        goals = list(PROCESSING_GOALS.values())
        for i, goal in enumerate(goals, 1):
            print(f"  {i}. {goal.name}")
            print(f"     {goal.description}")
            print()
        
        while True:
            try:
                choice = int(input(f"Select goal (1-{len(goals)}): ")) - 1
                if 0 <= choice < len(goals):
                    selected = goals[choice]
                    print(f"\n✅ Selected: {selected.name}")
                    return selected
                else:
                    print("Invalid selection!")
            except ValueError:
                print("Please enter a number!")
    
    @staticmethod
    def _select_model() -> str:
        """Select AI model"""
        print("\n🤖 SELECT AI MODEL:")
        
        available = ModelSelector.detect_available_models()
        models = []
        
        if available['gemini']:
            models.append(('gemini', 'Google Gemini (Cloud-based, highest quality)'))
            print(f"  1. Google Gemini ✅")
        else:
            print(f"  1. Google Gemini ❌ (google-genai not installed)")
        
        if available['ollama']:
            models.append(('llava', 'LLaVA via Ollama (Local, good quality)'))
            print(f"  2. LLaVA (Ollama) ✅")
        else:
            print(f"  2. LLaVA (Ollama) ❌ (Not running or no LLaVA model)")
        
        if available['bakllava']:
            models.append(('bakllava', 'BakLLaVA (Mistral-based, local, fast)'))
            print(f"  3. BakLLaVA (Mistral) ✅")
        else:
            print(f"  3. BakLLaVA (Mistral) ❌ (Missing dependencies or model files)")
        
        if not models:
            print("\n❌ No models available! Please install at least one.")
            exit(1)
        
        while True:
            try:
                choice = int(input(f"\nSelect model (1-{len(models)}): ")) - 1
                if 0 <= choice < len(models):
                    selected = models[choice][0]
                    print(f"✅ Selected: {models[choice][1]}")
                    return selected
                else:
                    print("Invalid selection!")
            except ValueError:
                print("Please enter a number!")
    
    @staticmethod
    def _create_config(goal: ProcessingGoal, model_type: str) -> EnhancedConfig:
        """Create optimized configuration"""
        config = EnhancedConfig()
        config.processing_goal = goal.name
        config.model_type = model_type
        
        # Apply goal-based optimizations
        config.timeout = goal.timeout_seconds
        config.generate_xmp = True  # Always use XMP for Lightroom collections
        config.xmp_collection_prefix = f"AI_{goal.name.replace(' ', '_')}"
        
        # Configure model-specific settings
        if model_type == 'gemini':
            api_key = input("\nEnter Gemini API key (or press Enter for GOOGLE_API_KEY env var): ").strip()
            config.api_key = api_key if api_key else os.getenv('GOOGLE_API_KEY')
            if not config.api_key:
                print("❌ Gemini API key required!")
                exit(1)
        
        elif model_type == 'bakllava':
            model_files = ModelSelector._find_bakllava_files()
            if model_files:
                config.bakllava_model_path = str(model_files[0])
                config.bakllava_clip_path = str(model_files[1])
                print(f"✅ Found BakLLaVA files")
            else:
                print("❌ BakLLaVA files not found!")
                exit(1)
        
        # Test mode option
        test_choice = input(f"\nTest mode (process only first 20 images)? (y/N): ").strip().lower()
        if test_choice in ['y', 'yes']:
            config.test_mode = True
            print("🧪 Test mode enabled")
        
        return config

# Simplified logger for space
class EnhancedLogger:
    def __init__(self, config: EnhancedConfig):
        self.logger = logging.getLogger('enhanced_analyzer')
        self.logger.setLevel(getattr(logging, config.log_level))
        self.logger.handlers.clear()
        
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
    
    def info(self, msg): self.logger.info(msg)
    def warning(self, msg): self.logger.warning(msg)
    def error(self, msg): self.logger.error(msg)
    def debug(self, msg): self.logger.debug(msg)

class EnhancedImageProcessor:
    """Enhanced image processor with model comparison support"""
    
    def __init__(self, config: EnhancedConfig, logger: EnhancedLogger):
        self.config = config
        self.logger = logger
        self.bakllava_analyzer = None
        
        # Initialize BakLLaVA if selected
        if config.model_type == 'bakllava' and BAKLLAVA_AVAILABLE:
            try:
                self.bakllava_analyzer = SimpleBakLLaVAAnalyzer()
                if self.bakllava_analyzer.is_available():
                    self.logger.info("✅ BakLLaVA analyzer initialized")
                else:
                    self.logger.warning("⚠️ BakLLaVA files found but analyzer not ready")
            except Exception as e:
                self.logger.error(f"Failed to initialize BakLLaVA: {e}")
                self.bakllava_analyzer = None
    
    def process_images(self, images: List[Path], goal: ProcessingGoal) -> List[Dict]:
        """Process images with selected model and goal"""
        results = []
        
        for i, image_path in enumerate(images, 1):
            self.logger.info(f"Processing {i}/{len(images)}: {image_path.name}")
            
            try:
                # Process based on selected model
                if self.config.model_type == 'bakllava':
                    result = self._process_with_bakllava(image_path, goal)
                elif self.config.model_type == 'gemini':
                    result = self._process_with_gemini(image_path, goal)
                elif self.config.model_type == 'ollama':
                    result = self._process_with_ollama(image_path, goal)
                else:
                    result = {"error": f"Unknown model type: {self.config.model_type}"}
                
                # Add metadata
                result['image_path'] = str(image_path)
                result['processing_goal'] = goal.name
                result['model_type'] = self.config.model_type
                result['timestamp'] = datetime.now().isoformat()
                
                # Generate XMP if enabled
                if self.config.generate_xmp and 'error' not in result:
                    self._generate_xmp(image_path, result, goal)
                
                results.append(result)
                
            except Exception as e:
                self.logger.error(f"Error processing {image_path}: {e}")
                results.append({
                    'image_path': str(image_path),
                    'error': str(e),
                    'model_type': self.config.model_type
                })
        
        return results
    
    def _process_with_bakllava(self, image_path: Path, goal: ProcessingGoal) -> Dict:
        """Process image with BakLLaVA"""
        if not self.bakllava_analyzer:
            return {"error": "BakLLaVA analyzer not available"}
        
        # Map processing goal to BakLLaVA goal
        goal_mapping = {
            "Archive Culling": "archive_culling",
            "Gallery Selection": "gallery_selection", 
            "Catalog Organization": "catalog_organization",
            "Model Comparison": "catalog_organization"  # Use detailed for comparison
        }
        
        bakllava_goal = goal_mapping.get(goal.name, "archive_culling")
        
        try:
            result = self.bakllava_analyzer.analyze_image(str(image_path), bakllava_goal)
            
            # Transform BakLLaVA result to match expected format
            if result.get('success'):
                return {
                    'model': 'BakLLaVA-1',
                    'success': True,
                    'analysis': result.get('results', {}),
                    'note': result.get('note', '')
                }
            else:
                return {'error': result.get('error', 'BakLLaVA analysis failed')}
                
        except Exception as e:
            self.logger.error(f"BakLLaVA processing error: {e}")
            return {'error': f'BakLLaVA error: {str(e)}'}
    
    def _process_with_gemini(self, image_path: Path, goal: ProcessingGoal) -> Dict:
        """Process image with Gemini (placeholder)"""
        # This would contain actual Gemini processing logic
        return {
            'model': 'Gemini',
            'success': False,
            'error': 'Gemini processing not implemented in this version'
        }
    
    def _process_with_ollama(self, image_path: Path, goal: ProcessingGoal) -> Dict:
        """Process image with Ollama (placeholder)"""
        # This would contain actual Ollama processing logic
        return {
            'model': 'LLaVA-Ollama',
            'success': False,
            'error': 'Ollama processing not implemented in this version'
        }
    
    def _generate_xmp(self, image_path: Path, result: Dict, goal: ProcessingGoal):
        """Generate XMP sidecar file for Lightroom collections"""
        try:
            xmp_path = image_path.with_suffix(image_path.suffix + '.xmp')
            
            # Create XMP content
            collection_name = f"{self.config.xmp_collection_prefix}_{goal.name.replace(' ', '_')}"
            
            # Extract analysis data
            analysis = result.get('analysis', {})
            score = self._extract_score(analysis)
            tags = self._extract_tags(analysis)
            
            xmp_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/">
  <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
    <rdf:Description rdf:about=""
        xmlns:lr="http://ns.adobe.com/lightroom/1.0/"
        xmlns:dc="http://purl.org/dc/elements/1.1/">
      <lr:hierarchicalSubject>
        <rdf:Bag>
          <rdf:li>{collection_name}</rdf:li>
          <rdf:li>AI_Score_{score}</rdf:li>
        </rdf:Bag>
      </lr:hierarchicalSubject>
      <dc:subject>
        <rdf:Bag>
          <rdf:li>AI_Analysis</rdf:li>
          <rdf:li>{goal.name}</rdf:li>'''
            
            # Add extracted tags
            for tag in tags:
                xmp_content += f'\n          <rdf:li>{tag}</rdf:li>'
            
            xmp_content += '''
        </rdf:Bag>
      </dc:subject>
    </rdf:Description>
  </rdf:RDF>
</x:xmpmeta>'''
            
            # Write XMP file
            with open(xmp_path, 'w', encoding='utf-8') as f:
                f.write(xmp_content)
                
            self.logger.debug(f"Generated XMP: {xmp_path}")
            
        except Exception as e:
            self.logger.error(f"XMP generation failed for {image_path}: {e}")
    
    def _extract_score(self, analysis: Dict) -> int:
        """Extract numeric score from analysis"""
        # Try different score fields
        for field in ['score', 'keep_score', 'rating']:
            if field in analysis:
                value = analysis[field]
                if isinstance(value, (int, float)):
                    return int(value)
                elif isinstance(value, str):
                    # Extract number from string like "8 - High quality..."
                    import re
                    match = re.search(r'(\d+)', value)
                    if match:
                        return int(match.group(1))
        return 5  # Default score
    
    def _extract_tags(self, analysis: Dict) -> List[str]:
        """Extract tags from analysis"""
        tags = []
        
        # Try different tag fields
        for field in ['tags', 'quick_tags', 'comprehensive_tags']:
            if field in analysis:
                value = analysis[field]
                if isinstance(value, list):
                    tags.extend(value)
                elif isinstance(value, str):
                    # Split comma-separated tags
                    tags.extend([tag.strip() for tag in value.split(',')])
        
        return tags[:5]  # Limit to 5 tags

def main():
    """Enhanced main function"""
    
    # Interactive setup
    model_type, config = ModelSelector.show_setup_menu()
    
    # Get source directory
    import sys
    if len(sys.argv) > 1:
        source_dir = sys.argv[1]
    else:
        source_dir = input("\n📁 Enter image directory path: ").strip().strip('"')
    
    source_directory = Path(source_dir)
    if not source_directory.is_dir():
        print(f"❌ Directory not found: {source_directory}")
        return
    
    # Initialize
    logger = EnhancedLogger(config)
    # Fix goal key mapping
    goal_key_mapping = {
        'archive culling': 'archive_cull',
        'gallery selection': 'gallery_select', 
        'catalog organization': 'organize_catalog',
        'model comparison': 'model_compare'
    }
    
    goal_key = goal_key_mapping.get(config.processing_goal.lower(), 'archive_cull')
    goal = PROCESSING_GOALS[goal_key]
    
    print(f"\n🚀 STARTING ANALYSIS")
    print(f"📁 Directory: {source_directory}")
    print(f"🎯 Goal: {goal.name}")
    print(f"🤖 Model: {model_type.upper()}")
    print(f"💾 Output: XMP sidecar files (Lightroom collections: {config.xmp_collection_prefix}_*)")
    
    # Get images
    image_extensions = ('.jpg', '.jpeg', '.png', '.tif', '.tiff', '.webp')
    all_images = [p for p in source_directory.rglob('*') if p.suffix.lower() in image_extensions]
    
    if not all_images:
        print("❌ No images found!")
        return
    
    # Apply test mode limit
    if config.test_mode:
        images_to_process = all_images[:config.test_image_count]
        print(f"🧪 Test mode: Processing first {len(images_to_process)} of {len(all_images)} images")
    else:
        images_to_process = all_images
        print(f"🔄 Processing {len(images_to_process)} images")
    
    # Initialize processor
    processor = EnhancedImageProcessor(config, logger)
    
    print(f"\n⚡ Processing optimized for: {goal.description}")
    print(f"   Timeout: {goal.timeout_seconds}s per image")
    print(f"   Critique: {'Enabled' if goal.enable_critique else 'Disabled'}")
    print(f"   Tags/Categories: {'Enabled' if goal.include_tags else 'Quick mode'}")
    
    # Confirm before starting
    if config.test_mode:
        confirm = input(f"\n🧪 Test {len(images_to_process)} images? (y/N): ").strip().lower()
    else:
        confirm = input(f"\n🚀 Process {len(images_to_process)} images? (y/N): ").strip().lower()
    
    if confirm not in ['y', 'yes']:
        print("❌ Processing cancelled")
        return
    
    # Start processing
    print(f"\n🔄 Starting image analysis...")
    start_time = time.time()
    
    try:
        results = processor.process_images(images_to_process, goal)
        
        # Save results
        output_file = Path(config.output_file)
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            if results:
                fieldnames = results[0].keys()
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(results)
        
        # Summary
        elapsed = time.time() - start_time
        successful = sum(1 for r in results if r.get('success', False))
        failed = len(results) - successful
        
        print(f"\n🎉 PROCESSING COMPLETE!")
        print(f"   ✅ Successful: {successful}")
        print(f"   ❌ Failed: {failed}")
        print(f"   🕰️ Time: {elapsed:.1f}s ({elapsed/len(results):.1f}s per image)")
        print(f"   📄 Results saved to: {output_file}")
        
        if config.generate_xmp:
            print(f"   🏷️ XMP files generated for Lightroom collections")
            print(f"   📁 Collection name: {config.xmp_collection_prefix}_{goal.name.replace(' ', '_')}")
        
        # Offer model comparison
        if config.test_mode and not config.enable_comparison:
            print(f"\n🔍 MODEL COMPARISON OPPORTUNITY")
            print(f"   You just processed {len(images_to_process)} test images with {model_type.upper()}")
            compare_choice = input(f"   Run same images with different model for comparison? (y/N): ").strip().lower()
            
            if compare_choice in ['y', 'yes']:
                print("\n🔄 Setting up model comparison...")
                # Here you could implement automatic comparison setup
                print("📝 To compare models:")
                print(f"   1. Run this script again")
                print(f"   2. Select different model")
                print(f"   3. Use same {len(images_to_process)} images")
                print(f"   4. Compare results in separate CSV files")
        
        logger.info(f"Processing completed: {successful} successful, {failed} failed")
        
    except KeyboardInterrupt:
        print("\n❌ Processing interrupted by user")
        logger.info("Processing interrupted")
    except Exception as e:
        print(f"\n❌ Processing failed: {e}")
        logger.error(f"Processing failed: {e}")

if __name__ == "__main__":
    main()
