# ----------------------------------------------------------------------
#  Unified AI Image Analyzer v3.0 - Complete Production Ready
#  
#  Features:
#  - LLaVA and Gemini model support with selection
#  - XMP sidecar file generation option
#  - Gallery critique feature with selective application
#  - System resource monitoring and optimization
#  - Progress tracking with resume capability
#  - Comprehensive logging with rotation
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

# Try to import Gemini (optional)
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("Warning: google-generativeai not available. Gemini model will not work.")

# Enhanced Configuration
@dataclass
class UnifiedConfig:
    """Configuration for unified analyzer"""
    # Model settings
    model_type: str = "llava"  # "llava" or "gemini"
    ollama_url: str = "http://localhost:11434/api/generate"
    llava_model_name: str = "llava:13b"
    gemini_model_name: str = "gemini-2.0-flash-exp"
    api_key: Optional[str] = None  # For Gemini
    
    # Prompt settings
    base_prompt: str = "Analyze this image in detail, focusing on composition, subject matter, lighting, and artistic merit."
    
    # Gallery critique settings
    enable_gallery_critique: bool = False
    critique_threshold: int = 5  # Only critique images scoring 5 or lower when disabled
    
    # Output settings
    generate_xmp: bool = True  # Generate XMP sidecar files instead of EXIF
    modify_exif: bool = False   # Modify EXIF data (when XMP is False)
    
    # Processing settings
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
    log_file: str = "unified_analyzer.log"
    log_level: str = "INFO"
    max_log_size: int = 10 * 1024 * 1024  # 10MB
    log_backup_count: int = 5
    
    # Output
    output_file: str = "unified_analysis_results.csv"
    save_progress: bool = True
    progress_file: str = "unified_progress.json"

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

class EnhancedLogger:
    """Comprehensive logging system"""
    
    def __init__(self, config: UnifiedConfig):
        self.logger = logging.getLogger('unified_analyzer')
        self.logger.setLevel(getattr(logging, config.log_level))
        self.logger.handlers.clear()
        
        # File handler with rotation
        file_handler = logging.handlers.RotatingFileHandler(
            config.log_file,
            maxBytes=config.max_log_size,
            backupCount=config.log_backup_count
        )
        
        # Console handler
        console_handler = logging.StreamHandler()
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        self.logger.info("Unified AI Image Analyzer v3.0 - Logging initialized")
    
    def info(self, msg): self.logger.info(msg)
    def warning(self, msg): self.logger.warning(msg)
    def error(self, msg): self.logger.error(msg)
    def debug(self, msg): self.logger.debug(msg)

class SystemMonitor:
    """Monitor system resources and adjust processing"""
    
    def __init__(self, config: UnifiedConfig, logger: EnhancedLogger):
        self.config = config
        self.logger = logger
    
    def get_optimal_workers(self) -> int:
        """Calculate optimal worker count based on system resources"""
        cpu_count = psutil.cpu_count()
        memory_gb = psutil.virtual_memory().total / (1024**3)
        
        # Check if Lightroom is running
        lightroom_running = self.is_lightroom_running() if self.config.check_lightroom else False
        
        if lightroom_running:
            optimal_workers = max(1, cpu_count // 4)
            self.logger.warning(f"Lightroom detected - reducing workers to {optimal_workers}")
        else:
            optimal_workers = max(1, min(cpu_count // 2, int(memory_gb // 2)))
        
        return min(optimal_workers, self.config.max_workers)
    
    def is_lightroom_running(self) -> bool:
        """Check if Adobe Lightroom is running"""
        lightroom_processes = ['Lightroom.exe', 'Adobe Lightroom Classic.exe', 'Adobe Lightroom.exe']
        
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if proc.info['name'] in lightroom_processes:
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return False
    
    def check_system_resources(self) -> Dict[str, float]:
        """Check current system resource usage"""
        memory = psutil.virtual_memory()
        cpu_percent = psutil.cpu_percent(interval=0.1)
        
        return {
            'memory_percent': memory.percent / 100,
            'memory_available_gb': memory.available / (1024**3),
            'cpu_percent': cpu_percent / 100
        }
    
    def should_throttle(self) -> bool:
        """Determine if processing should be throttled"""
        resources = self.check_system_resources()
        
        if resources['memory_percent'] > self.config.max_memory_usage:
            self.logger.warning(f"High memory usage: {resources['memory_percent']:.1%}")
            return True
        
        if resources['cpu_percent'] > self.config.max_cpu_usage:
            self.logger.warning(f"High CPU usage: {resources['cpu_percent']:.1%}")
            return True
            
        return False

class ImageOptimizer:
    """Optimize images for faster processing"""
    
    def __init__(self, config: UnifiedConfig, logger: EnhancedLogger):
        self.config = config
        self.logger = logger
    
    def should_skip_image(self, image_path: Path) -> Tuple[bool, str]:
        """Check if image should be skipped"""
        try:
            with Image.open(image_path) as img:
                width, height = img.size
                file_size = image_path.stat().st_size
                
                # Skip very small images
                if width < self.config.min_dimension or height < self.config.min_dimension:
                    return True, f"Too small ({width}x{height})"
                
                # Skip very small files
                if file_size < 1024:  # Less than 1KB
                    return True, "File too small (likely corrupted)"
                
                # Test image integrity
                try:
                    img.verify()
                except Exception:
                    return True, "Corrupted or invalid image format"
                    
                return False, ""
                
        except Exception as e:
            return True, f"Error reading image: {e}"
    
    def optimize_image(self, image_path: Path) -> Optional[str]:
        """Optimize image and return base64 encoded string"""
        if not self.config.optimize_images:
            # Return original image as base64
            return self.encode_image_to_base64(image_path)
        
        try:
            with Image.open(image_path) as img:
                # Convert to RGB if necessary
                if img.mode not in ['RGB', 'L']:
                    img = img.convert('RGB')
                
                # Apply EXIF orientation
                img = ImageOps.exif_transpose(img)
                
                # Resize if too large
                width, height = img.size
                if max(width, height) > self.config.max_dimension:
                    if width > height:
                        new_width = self.config.max_dimension
                        new_height = int(height * (self.config.max_dimension / width))
                    else:
                        new_height = self.config.max_dimension
                        new_width = int(width * (self.config.max_dimension / height))
                    
                    img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    self.logger.debug(f"Resized {image_path.name} from {width}x{height} to {new_width}x{new_height}")
                
                # Save to temporary file and encode
                temp_dir = Path(tempfile.gettempdir()) / "unified_analysis"
                temp_dir.mkdir(exist_ok=True)
                
                temp_path = temp_dir / f"opt_{int(time.time())}_{image_path.stem}.jpg"
                img.save(temp_path, "JPEG", quality=self.config.quality, optimize=True)
                
                try:
                    base64_data = self.encode_image_to_base64(temp_path)
                    return base64_data
                finally:
                    # Clean up temp file
                    try:
                        temp_path.unlink()
                    except:
                        pass
                        
        except Exception as e:
            self.logger.error(f"Failed to optimize {image_path.name}: {e}")
            # Fallback to original image
            return self.encode_image_to_base64(image_path)
    
    def optimize_for_gemini(self, image_path: Path) -> Optional[Path]:
        """Create optimized image for Gemini analysis"""
        try:
            with Image.open(image_path) as img:
                # Convert to RGB if necessary
                if img.mode not in ['RGB', 'L']:
                    img = img.convert('RGB')
                
                # Apply EXIF orientation
                img = ImageOps.exif_transpose(img)
                
                # Resize if too large
                width, height = img.size
                if max(width, height) > self.config.max_dimension:
                    if width > height:
                        new_width = self.config.max_dimension
                        new_height = int(height * (self.config.max_dimension / width))
                    else:
                        new_height = self.config.max_dimension
                        new_width = int(width * (self.config.max_dimension / height))
                    
                    img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                # Save to temporary file
                temp_dir = Path(tempfile.gettempdir()) / "unified_analysis"
                temp_dir.mkdir(exist_ok=True)
                
                temp_path = temp_dir / f"gemini_{int(time.time())}_{image_path.stem}.jpg"
                img.save(temp_path, "JPEG", quality=self.config.quality, optimize=True)
                
                return temp_path
                
        except Exception as e:
            self.logger.error(f"Failed to optimize for Gemini {image_path.name}: {e}")
            return None
    
    @staticmethod
    def encode_image_to_base64(image_path: Path) -> str:
        """Encode image to base64 string"""
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode('utf-8')

class ProgressTracker:
    """Track processing progress with save/load capability"""
    
    def __init__(self, config: UnifiedConfig):
        self.config = config
        self.processed_files = set()
        self.results = []
        self.load_progress()
    
    def load_progress(self):
        """Load previously processed files and results"""
        if self.config.save_progress and Path(self.config.progress_file).exists():
            try:
                with open(self.config.progress_file, 'r') as f:
                    data = json.load(f)
                    self.processed_files = set(data.get("processed_files", []))
                    self.results = data.get("results", [])
                print(f"   📋 Loaded progress: {len(self.processed_files)} files already processed")
            except Exception as e:
                print(f"   ⚠️ Could not load progress: {e}")
    
    def save_progress(self):
        """Save current progress"""
        if self.config.save_progress:
            try:
                data = {
                    "processed_files": list(self.processed_files),
                    "results": self.results,
                    "last_updated": datetime.now().isoformat()
                }
                with open(self.config.progress_file, 'w') as f:
                    json.dump(data, f, indent=2)
            except Exception as e:
                print(f"   ⚠️ Could not save progress: {e}")
    
    def mark_processed(self, file_path: Path):
        """Mark file as processed"""
        self.processed_files.add(str(file_path))
    
    def is_processed(self, file_path: Path) -> bool:
        """Check if file was already processed"""
        return str(file_path) in self.processed_files
    
    def add_result(self, result: Dict):
        """Add analysis result"""
        self.results.append(result)

class UnifiedAnalyzer:
    """Unified analyzer supporting both LLaVA and Gemini"""
    
    def __init__(self, config: UnifiedConfig, logger: EnhancedLogger):
        self.config = config
        self.logger = logger
        self.model = None
        
        if config.model_type == "gemini":
            self.init_gemini()
        else:
            self.init_llava()
    
    def init_gemini(self):
        """Initialize Gemini model"""
        if not GEMINI_AVAILABLE:
            raise ValueError("google-genai package not available for Gemini model")
        
        if not self.config.api_key:
            raise ValueError("API key required for Gemini model")
        
        try:
            genai.configure(api_key=self.config.api_key)
            self.model = genai.GenerativeModel(self.config.gemini_model_name)
            self.logger.info(f"Initialized Gemini model: {self.config.gemini_model_name}")
        except Exception as e:
            self.logger.error(f"Failed to initialize Gemini: {e}")
            raise
    
    def init_llava(self):
        """Initialize LLaVA model (via Ollama)"""
        try:
            # Test connection to Ollama
            response = requests.get(f"{self.config.ollama_url.replace('/api/generate', '/api/tags')}", timeout=5)
            if response.status_code == 200:
                self.logger.info(f"Connected to Ollama, using model: {self.config.llava_model_name}")
            else:
                raise ConnectionError("Could not connect to Ollama")
        except Exception as e:
            self.logger.error(f"Failed to initialize LLaVA: {e}")
            raise
    
    def create_analysis_prompt(self, enable_critique: bool = True) -> str:
        """Create analysis prompt with optional critique"""
        
        critique_section = ""
        if enable_critique:
            critique_section = f"""
            
            CRITIQUE REQUIREMENTS:
            - 2-3 sentences maximum
            - Focus on what makes the image succeed or fail
            - Mention specific technical or artistic elements
            - Be constructive but honest
            """
        
        return f"""
        You are a professional art critic and gallery curator with 25 years of experience,
        evaluating photographs for potential inclusion in a fine art exhibition.
        
        ANALYSIS CRITERIA:
        1. Technical Excellence: Focus, exposure, composition, color/lighting
        2. Artistic Merit: Creativity, emotional impact, visual storytelling
        3. Commercial Appeal: Marketability, broad audience appeal
        4. Uniqueness: What sets this image apart from typical photography
        
        CLASSIFICATION (select ONE from each category):
        CATEGORIES: {", ".join(CATEGORIES)}
        SUB_CATEGORIES: {", ".join(SUB_CATEGORIES)}
        TAGS: {", ".join(TAGS)} (select 2-4 most relevant)
        
        SCORING GUIDE (1-10 scale):
        1-2: Poor (technical flaws, no artistic merit)
        3-4: Below Average (basic competence, limited appeal)
        5-6: Average (good technical execution, moderate appeal)
        7-8: Above Average (strong technique and artistic vision)
        9-10: Exceptional (gallery-worthy, memorable impact)
        {critique_section}
        
        RESPOND WITH VALID JSON ONLY:
        {{
          "category": "chosen_category",
          "subcategory": "chosen_subcategory",
          "tags": ["tag1", "tag2", "tag3"],
          "score": 7{', "critique": "Professional critique focusing on technical and artistic merits."' if enable_critique else ''}
        }}
        """
    
    def analyze_image(self, image_path: Path, optimizer: ImageOptimizer) -> Optional[Dict]:
        """Analyze image using selected model"""
        
        # Determine if critique should be included
        enable_critique = self.config.enable_gallery_critique
        
        if self.config.model_type == "gemini":
            return self.analyze_with_gemini(image_path, optimizer, enable_critique)
        else:
            return self.analyze_with_llava(image_path, optimizer, enable_critique)
    
    def analyze_with_llava(self, image_path: Path, optimizer: ImageOptimizer, enable_critique: bool) -> Optional[Dict]:
        """Analyze image using LLaVA via Ollama"""
        try:
            # Optimize and encode image
            base64_image = optimizer.optimize_image(image_path)
            if not base64_image:
                return None
            
            # Create prompt
            prompt = self.create_analysis_prompt(enable_critique)
            
            # Prepare payload
            payload = {
                "model": self.config.llava_model_name,
                "prompt": prompt,
                "stream": False,
                "images": [base64_image]
            }
            
            headers = {'Content-Type': 'application/json'}
            
            # Make request
            response = requests.post(
                self.config.ollama_url, 
                data=json.dumps(payload), 
                headers=headers, 
                timeout=self.config.timeout
            )
            
            response.raise_for_status()
            response_data = response.json()
            
            # Extract analysis text
            analysis_text = response_data.get('response', '').strip()
            
            if analysis_text:
                return self.parse_response(analysis_text, enable_critique)
            
        except Exception as e:
            self.logger.error(f"LLaVA analysis failed for {image_path.name}: {e}")
            return None
    
    def analyze_with_gemini(self, image_path: Path, optimizer: ImageOptimizer, enable_critique: bool) -> Optional[Dict]:
        """Analyze image using Gemini"""
        try:
            # Optimize image for Gemini
            optimized_path = optimizer.optimize_for_gemini(image_path)
            if not optimized_path:
                return None
            
            try:
                # Load image
                img = Image.open(optimized_path)
                
                # Create prompt
                prompt = self.create_analysis_prompt(enable_critique)
                
                # Generate content
                response = self.model.generate_content(
                    [prompt, img],
                    generation_config=genai.GenerationConfig(
                        temperature=0.3,
                        top_p=0.8,
                        max_output_tokens=500
                    )
                )
                
                # Parse response
                text_response = response.text.strip()
                return self.parse_response(text_response, enable_critique)
                
            finally:
                # Clean up temp file
                try:
                    optimized_path.unlink()
                except:
                    pass
                
        except Exception as e:
            self.logger.error(f"Gemini analysis failed for {image_path.name}: {e}")
            return None
    
    def parse_response(self, response_text: str, has_critique: bool) -> Optional[Dict]:
        """Parse analysis response from model"""
        try:
            # Clean up response text
            response_text = response_text.replace("```json", "").replace("```", "").strip()
            
            data = json.loads(response_text)
            
            # Validate required fields
            required_keys = ["category", "subcategory", "tags", "score"]
            if has_critique:
                required_keys.append("critique")
                
            if all(k in data for k in required_keys):
                # Post-process critique based on configuration
                if not self.config.enable_gallery_critique and has_critique:
                    score = data.get('score', 0)
                    critique_threshold = self.config.critique_threshold if self.config.critique_threshold is not None else 5
                    if score > critique_threshold:
                        # Remove critique for high-scoring images when gallery critique is disabled
                        data.pop('critique', None)
                
                return data
            else:
                missing = [k for k in required_keys if k not in data]
                self.logger.error(f"Missing keys in response: {missing}")
                return None
                
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON decode error: {e}")
            self.logger.debug(f"Raw response: {response_text}")
            return None

class MetadataWriter:
    """Handle writing metadata to EXIF or XMP files"""
    
    def __init__(self, config: UnifiedConfig, logger: EnhancedLogger):
        self.config = config
        self.logger = logger
    
    def write_metadata(self, image_path: Path, analysis_data: Dict) -> bool:
        """Write analysis data to EXIF or XMP based on configuration"""
        if self.config.generate_xmp:
            return self.write_xmp_sidecar(image_path, analysis_data)
        elif self.config.modify_exif:
            return self.write_exif_data(image_path, analysis_data)
        else:
            return True  # Skip writing metadata
    
    def write_exif_data(self, image_path: Path, analysis_data: Dict) -> bool:
        """Write analysis data to EXIF metadata"""
        try:
            # Load existing EXIF data
            try:
                exif_dict = piexif.load(str(image_path))
            except piexif.InvalidImageDataError:
                exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}
            
            # Calculate star rating
            score = analysis_data.get('score', 0)
            if score is None:
                score = 0
            star_rating = math.ceil(score / 2) if score >= 1 else 1
            
            # Check for existing high rating
            existing_rating = exif_dict.get("0th", {}).get(piexif.ImageIFD.Rating)
            if existing_rating in [4, 5]:
                final_rating = existing_rating
            else:
                final_rating = star_rating
            
            # Add GALLERY tag for 5-star ratings
            tags_list = analysis_data.get('tags', [])
            if final_rating == 5 and "GALLERY" not in tags_list:
                tags_list.append("GALLERY")
                analysis_data['tags'] = tags_list
            
            # Set EXIF data
            exif_dict["0th"][piexif.ImageIFD.Rating] = final_rating
            
            # Description
            description = f"Category: {analysis_data['category']}, Subcategory: {analysis_data['subcategory']}"
            exif_dict["0th"][piexif.ImageIFD.ImageDescription] = description.encode('utf-8')
            
            # User comment with full analysis
            critique = analysis_data.get('critique', 'N/A')
            tags = ", ".join(tags_list)
            full_comment = f"Critique: {critique} | Score: {score}/10 | Tags: {tags}"
            exif_dict["Exif"][piexif.ExifIFD.UserComment] = full_comment.encode('utf-8')
            
            # Save EXIF data
            exif_bytes = piexif.dump(exif_dict)
            piexif.insert(exif_bytes, str(image_path))
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error writing EXIF data to {image_path.name}: {e}")
            return False
    
    def write_xmp_sidecar(self, image_path: Path, analysis_data: Dict) -> bool:
        """Write analysis data to XMP sidecar file"""
        try:
            xmp_path = image_path.with_suffix(image_path.suffix + '.xmp')
            
            # Calculate star rating
            score = analysis_data.get('score', 0)
            if score is None:
                score = 0
            star_rating = math.ceil(score / 2) if score >= 1 else 1
            
            # Add GALLERY tag for 5-star ratings
            tags_list = analysis_data.get('tags', [])
            if star_rating == 5 and "GALLERY" not in tags_list:
                tags_list.append("GALLERY")
                analysis_data['tags'] = tags_list
            
            # Create XMP content
            xmp_content = self.create_xmp_content(analysis_data, star_rating)
            
            # Write XMP file
            with open(xmp_path, 'w', encoding='utf-8') as f:
                f.write(xmp_content)
            
            self.logger.debug(f"Created XMP sidecar: {xmp_path.name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error writing XMP sidecar for {image_path.name}: {e}")
            return False
    
    def create_xmp_content(self, analysis_data: Dict, star_rating: int) -> str:
        """Create XMP file content"""
        tags = analysis_data.get('tags', [])
        tags_xml = '\n'.join([f'      <rdf:li>{tag}</rdf:li>' for tag in tags])
        
        critique = analysis_data.get('critique', 'N/A')
        
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/">
  <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
    <rdf:Description rdf:about=""
        xmlns:xmp="http://ns.adobe.com/xap/1.0/"
        xmlns:dc="http://purl.org/dc/elements/1.1/"
        xmlns:lr="http://ns.adobe.com/lightroom/1.0/"
        xmlns:ai="http://ai-image-analyzer/1.0/">
      
      <!-- AI Analysis Results -->
      <xmp:Rating>{star_rating}</xmp:Rating>
      <dc:description>{critique}</dc:description>
      <dc:subject>
        <rdf:Bag>
{tags_xml}
        </rdf:Bag>
      </dc:subject>
      
      <!-- AI Analysis Metadata -->
      <ai:category>{analysis_data['category']}</ai:category>
      <ai:subcategory>{analysis_data['subcategory']}</ai:subcategory>
      <ai:score>{analysis_data['score']}</ai:score>
      <ai:analysisDate>{datetime.now().isoformat()}</ai:analysisDate>
      <ai:modelType>{self.config.model_type}</ai:modelType>
      
    </rdf:Description>
  </rdf:RDF>
</x:xmpmeta>"""

def get_image_files(directory: Path, logger: EnhancedLogger) -> List[Path]:
    """Enhanced image file scanning with logging"""
    image_extensions = ('.jpg', '.jpeg', '.png', '.tif', '.tiff', '.webp')
    logger.info(f"Scanning for images in: {directory}")
    
    try:
        files = [p for p in directory.rglob('*') if p.suffix.lower() in image_extensions]
        if not files:
            logger.warning(f"No images found in {directory}")
            return []
        logger.info(f"Found {len(files)} processable images")
        return files
    except FileNotFoundError:
        logger.error(f"Directory not found: {directory}")
        return []
    except Exception as e:
        logger.error(f"Error scanning directory: {e}")
        return []

def analyze_single_image(args) -> Tuple[Path, Optional[Dict], Optional[str]]:
    """Analyze a single image - designed for concurrent execution"""
    image_path, config, analyzer, optimizer, metadata_writer = args
    
    try:
        # Check if image should be skipped
        should_skip, reason = optimizer.should_skip_image(image_path)
        if should_skip:
            return image_path, None, f"Skipped: {reason}"
        
        # Analyze image
        analysis_result = analyzer.analyze_image(image_path, optimizer)
        if not analysis_result:
            return image_path, None, "Analysis failed"
        
        # Write metadata
        metadata_success = metadata_writer.write_metadata(image_path, analysis_result)
        
        # Prepare result
        result = {
            'image_path': str(image_path),
            'image_name': image_path.name,
            'analysis': analysis_result,
            'metadata_written': metadata_success,
            'timestamp': datetime.now().isoformat(),
            'model': config.model_type
        }
        
        return image_path, result, None
        
    except Exception as e:
        return image_path, None, f"Unexpected error: {e}"

def save_results_to_csv(results: List[Dict], output_file: str, logger: EnhancedLogger):
    """Save results to CSV file"""
    if not results:
        logger.warning("No results to save")
        return
    
    try:
        logger.info(f"Saving {len(results)} results to {output_file}")
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['image_name', 'image_path', 'category', 'subcategory', 'tags', 
                         'score', 'critique', 'metadata_written', 'timestamp', 'model']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for result in results:
                analysis = result['analysis']
                writer.writerow({
                    'image_name': result['image_name'],
                    'image_path': result['image_path'],
                    'category': analysis['category'],
                    'subcategory': analysis['subcategory'],
                    'tags': ', '.join(analysis['tags']),
                    'score': analysis['score'],
                    'critique': analysis.get('critique', 'N/A'),
                    'metadata_written': result['metadata_written'],
                    'timestamp': result['timestamp'],
                    'model': result['model']
                })
        logger.info("Results saved successfully")
    except Exception as e:
        logger.error(f"Failed to save results: {e}")

def main():
    """Enhanced main function with comprehensive features"""
    parser = argparse.ArgumentParser(
        description="Unified AI Image Analyzer v3.0 with LLaVA and Gemini support"
    )
    parser.add_argument("source_dir", type=str, help="Source directory containing images")
    parser.add_argument("--model", type=str, choices=["llava", "gemini"], default="llava",
                       help="AI model to use (llava or gemini)")
    parser.add_argument("--api-key", type=str, help="API key for Gemini model")
    parser.add_argument("--ollama-url", type=str, default="http://localhost:11434/api/generate",
                       help="Ollama API URL for LLaVA")
    parser.add_argument("--llava-model", type=str, default="llava:13b",
                       help="LLaVA model name")
    parser.add_argument("--gemini-model", type=str, default="gemini-2.0-flash-exp",
                       help="Gemini model name")
    parser.add_argument("--workers", type=int, default=4,
                       help="Maximum number of concurrent workers")
    parser.add_argument("--output", type=str, default="unified_analysis_results.csv",
                       help="Output CSV file path")
    parser.add_argument("--generate-xmp", action="store_true",
                       help="Generate XMP sidecar files instead of modifying EXIF")
    parser.add_argument("--no-exif", action="store_true",
                       help="Skip writing EXIF metadata (only applies when not generating XMP)")
    parser.add_argument("--enable-gallery-critique", action="store_true",
                       help="Enable gallery critique for all images")
    parser.add_argument("--critique-threshold", type=int, default=5,
                       help="Score threshold for critique when gallery critique is disabled (default: 5)")
    parser.add_argument("--optimize", action="store_true", default=True,
                       help="Enable image optimization (default: True)")
    parser.add_argument("--no-optimize", action="store_false", dest="optimize",
                       help="Disable image optimization")
    parser.add_argument("--log-level", type=str, default="INFO",
                       choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                       help="Logging level")
    
    args = parser.parse_args()
    
    # Initialize configuration
    config = UnifiedConfig(
        model_type=args.model,
        api_key=args.api_key,
        ollama_url=args.ollama_url,
        llava_model_name=args.llava_model,
        gemini_model_name=args.gemini_model,
        max_workers=args.workers,
        output_file=args.output,
        generate_xmp=args.generate_xmp,
        modify_exif=not args.no_exif and not args.generate_xmp,
        enable_gallery_critique=args.enable_gallery_critique,
        critique_threshold=args.critique_threshold,
        optimize_images=args.optimize,
        log_level=args.log_level
    )
    
    # Initialize logger
    logger = EnhancedLogger(config)
    
    logger.info("[*] Unified AI Image Analyzer v3.0 Starting...")
    logger.info(f"[*] Model: {config.model_type.upper()}")
    logger.info(f"[*] Features: {'XMP sidecar' if config.generate_xmp else 'EXIF metadata'}, {'Gallery critique enabled' if config.enable_gallery_critique else f'Selective critique (<={config.critique_threshold})'}")
    
    # Validate source directory
    source_directory = Path(args.source_dir)
    if not source_directory.is_dir():
        logger.error(f"Source directory not found: {source_directory}")
        return
    
    # Initialize system monitor and adjust workers
    monitor = SystemMonitor(config, logger)
    optimal_workers = monitor.get_optimal_workers()
    config.max_workers = optimal_workers
    logger.info(f"System analysis - Using {optimal_workers} workers")
    
    # Initialize components
    try:
        analyzer = UnifiedAnalyzer(config, logger)
        optimizer = ImageOptimizer(config, logger)
        metadata_writer = MetadataWriter(config, logger)
        progress_tracker = ProgressTracker(config)
    except Exception as e:
        logger.error(f"Failed to initialize components: {e}")
        return
    
    # Get image files
    image_files = get_image_files(source_directory, logger)
    if not image_files:
        return
    
    # Filter out already processed files
    unprocessed_files = [f for f in image_files if not progress_tracker.is_processed(f)]
    logger.info(f"Processing {len(unprocessed_files)} new images (total: {len(image_files)})")
    
    if not unprocessed_files:
        logger.info("All images have been processed!")
        return
    
    # Process images concurrently
    processed_count = 0
    skipped_count = 0
    error_count = 0
    
    logger.info(f"Starting concurrent processing with {config.max_workers} workers")
    
    with ThreadPoolExecutor(max_workers=config.max_workers) as executor:
        # Prepare arguments for each image
        args_list = [(img, config, analyzer, optimizer, metadata_writer) for img in unprocessed_files]
        
        # Submit all tasks
        future_to_image = {executor.submit(analyze_single_image, arg): arg[0] 
                          for arg in args_list}
        
        # Process results as they complete
        for i, future in enumerate(as_completed(future_to_image)):
            image_path = future_to_image[future]
            
            try:
                img_path, result, error_msg = future.result()
                
                if result:
                    processed_count += 1
                    progress_tracker.add_result(result)
                    progress_tracker.mark_processed(img_path)
                    score = result['analysis']['score']
                    logger.info(f"[{i+1}/{len(unprocessed_files)}] [+] {img_path.name} - Score: {score}/10")
                elif error_msg:
                    if "Skipped:" in error_msg:
                        skipped_count += 1
                        logger.debug(f"[{i+1}/{len(unprocessed_files)}] [>] {img_path.name} - {error_msg}")
                    else:
                        error_count += 1
                        logger.error(f"[{i+1}/{len(unprocessed_files)}] [!] {img_path.name} - {error_msg}")
                    progress_tracker.mark_processed(img_path)
                else:
                    error_count += 1
                    logger.error(f"[{i+1}/{len(unprocessed_files)}] [!] {img_path.name} - Unknown error")
                    progress_tracker.mark_processed(img_path)
                
                # Save progress periodically and check resources
                if i % 10 == 0:
                    progress_tracker.save_progress()
                    if monitor.should_throttle():
                        logger.warning("High system usage - pausing briefly")
                        time.sleep(2)
                        
            except Exception as e:
                error_count += 1
                logger.error(f"[{i+1}/{len(unprocessed_files)}] [!] {image_path.name} - Exception: {e}")
    
    # Final save and statistics
    progress_tracker.save_progress()
    save_results_to_csv(progress_tracker.results, config.output_file, logger)
    
    logger.info("[*] Processing complete!")
    logger.info(f"   [+] Successfully processed: {processed_count}")
    logger.info(f"   [>] Skipped: {skipped_count}")
    logger.info(f"   [!] Errors: {error_count}")
    logger.info(f"   [F] Results saved to: {config.output_file}")
    
    final_resources = monitor.check_system_resources()
    logger.info(f"Final system state - Memory: {final_resources['memory_percent']:.1%}, CPU: {final_resources['cpu_percent']:.1%}")

if __name__ == "__main__":
    main()
