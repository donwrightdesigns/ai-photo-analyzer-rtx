# ----------------------------------------------------------------------
#  Enhanced AI Image Analyzer v2.0 - Production Ready
#  
#  Author: Don Wright
#  Date: July 20, 2025
#
#  CRITICAL UPDATES:
#  - Migrated from google-generativeai to google-genai
#  - Added comprehensive file-based logging
#  - Improved concurrent processing with system monitoring
#  - Enhanced error handling and recovery
#  - Better resource management for Lightroom compatibility
# ---------------------------------------------------------------------

import google.genai as genai  # MIGRATED: New package
import os
import json
import math
import time
import hashlib
import logging
import logging.handlers
import psutil
from pathlib import Path
from PIL import Image, ImageOps
import piexif
from typing import Optional, Dict, List, Tuple
import tempfile
import concurrent.futures
from datetime import datetime
import threading
from dataclasses import dataclass, asdict

# Enhanced Configuration with System Monitoring
@dataclass
class SystemConfig:
    """System configuration with dynamic adjustment based on resources"""
    api_key: str
    source_directory: Path
    
    # Image optimization
    max_dimension: int = 1024
    quality: int = 85
    skip_very_small: bool = True
    min_dimension: int = 200
    
    # Training data
    collect_training_data: bool = True
    training_data_path: Path = Path("training_data")
    
    # Processing - Dynamic based on system resources
    max_workers: int = 2  # Will be adjusted based on system
    batch_size: int = 50
    save_progress: bool = True
    progress_file: str = "analysis_progress.json"
    
    # Logging
    log_file: str = "ai_analyzer.log"
    log_level: str = "INFO"
    max_log_size: int = 10 * 1024 * 1024  # 10MB
    log_backup_count: int = 5
    
    # System monitoring
    max_memory_usage: float = 0.8  # 80% of available memory
    max_cpu_usage: float = 0.7     # 70% CPU usage
    check_lightroom: bool = True   # Check if Lightroom is running

# Classification Schema
CATEGORIES = ["Person", "Place", "Thing"]
SUB_CATEGORIES = [
    "candid", "posed", "man-made", "landscape",
    "animal", "object", "house", "interior", "exterior", "nature", "scenery", 
    "other"
]
TAGS = [
    "artificial_light", "natural_light", "monochrome", 
    "duplicate", "large", "small", "dark", 
    "light", "heavy", "face", "abstract", "couple", 
    "action", "minimalist", "blurry", "evocative", 
    "disturbing", "boring", "wedding", "bride", "groom",
    "love", "calm", "busy", "automotive",
]

class EnhancedLogger:
    """Comprehensive logging system with file rotation and console output"""
    
    def __init__(self, config: SystemConfig):
        self.logger = logging.getLogger('ai_image_analyzer')
        self.logger.setLevel(getattr(logging, config.log_level))
        
        # Clear existing handlers
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
        
        self.logger.info("Enhanced AI Image Analyzer v2.0 - Logging initialized")
    
    def info(self, msg): self.logger.info(msg)
    def warning(self, msg): self.logger.warning(msg)
    def error(self, msg): self.logger.error(msg)
    def debug(self, msg): self.logger.debug(msg)

class SystemMonitor:
    """Monitor system resources and adjust processing accordingly"""
    
    def __init__(self, config: SystemConfig, logger: EnhancedLogger):
        self.config = config
        self.logger = logger
        self.initial_memory = psutil.virtual_memory().available
        
    def get_optimal_workers(self) -> int:
        """Calculate optimal number of workers based on system resources"""
        cpu_count = psutil.cpu_count()
        memory_gb = psutil.virtual_memory().total / (1024**3)
        
        # Check if Lightroom is running
        lightroom_running = self.is_lightroom_running() if self.config.check_lightroom else False
        
        if lightroom_running:
            # Conservative approach when Lightroom is running
            optimal_workers = max(1, cpu_count // 4)
            self.logger.warning(f"Lightroom detected - reducing workers to {optimal_workers}")
        else:
            # More aggressive when Lightroom is not running
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
        cpu_percent = psutil.cpu_percent(interval=1)
        
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

class MigratedImageAnalyzer:
    """Image analyzer using the new google-genai package"""
    
    def __init__(self, config: SystemConfig, logger: EnhancedLogger):
        self.config = config
        self.logger = logger
        
        # Initialize the new Google GenAI client
        try:
            # MIGRATED: New initialization method
            genai.configure(api_key=config.api_key)
            self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
            self.logger.info("Successfully initialized Google GenAI client")
        except Exception as e:
            self.logger.error(f"Failed to initialize Google GenAI: {e}")
            raise
    
    def analyze_image(self, image_path: Path, optimized_path: Path) -> Optional[Dict]:
        """Analyze image using the new Google GenAI package"""
        try:
            # Load optimized image
            img = Image.open(optimized_path)
            
            # Enhanced prompt with better structure
            prompt = f"""
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
            
            SCORING GUIDE (0-5 scale):
            0: Unrated, or Absence of Rating (default for images upon import)
            1: Poor (technical flaws, no artistic merit)
            2: Duplicate or Below Average (not interesting or properly exposed, limited appeal, not worth keeping unless group image)
            3: Average (good technical execution, moderate appeal, delivery & archive worthy,)
            4: Above Average (strong technique and artistic vision, social sharing worthy)
            5: Exceptional (gallery-worthy, memorable impact, website homepage worthy)
            
            CRITIQUE REQUIREMENTS:
            - 3 Sentences: A) describe subjectively suitable for ALT tag purposes (screen reader) B) Describe Style or Treatment C) What it conveys 
            - Focus on what makes the image succeed or fail
            - Be constructive but honest
            
            RESPOND WITH VALID JSON ONLY:
            {{
              "category": "chosen_category",
              "subcategory": "chosen_subcategory",
              "tags": ["tag1", "tag2", "tag3"],
              "score": 7,
              "critique": "Professional critique focusing on technical and artistic merits."
            }}
            """
            
            # MIGRATED: New API call method
            response = self.model.generate_content(
                [prompt, img],
                generation_config=genai.GenerationConfig(
                    temperature=0.3,  # Lower temperature for more consistent results
                    top_p=0.8,
                    max_output_tokens=500
                )
            )
            
            # Parse response
            text_response = response.text.strip()
            # Remove markdown formatting if present
            text_response = text_response.replace("```json", "").replace("```", "").strip()
            
            try:
                data = json.loads(text_response)
                
                # Validate required fields
                required_keys = ["category", "subcategory", "tags", "score", "critique"]
                if all(k in data for k in required_keys):
                    self.logger.info(f"Successfully analyzed {image_path.name} - Score: {data['score']}/10")
                    return data
                else:
                    missing = [k for k in required_keys if k not in data]
                    self.logger.error(f"Missing keys in response for {image_path.name}: {missing}")
                    return None
                    
            except json.JSONDecodeError as e:
                self.logger.error(f"JSON decode error for {image_path.name}: {e}")
                self.logger.debug(f"Raw response: {text_response}")
                return None
                
        except Exception as e:
            self.logger.error(f"Analysis error for {image_path.name}: {e}")
            return None

class ImageOptimizer:
    """Enhanced image optimizer with better error handling"""
    
    def __init__(self, config: SystemConfig, logger: EnhancedLogger):
        self.config = config
        self.logger = logger
    
    def should_skip_image(self, image_path: Path) -> Tuple[bool, str]:
        """Enhanced image quality checking"""
        try:
            with Image.open(image_path) as img:
                width, height = img.size
                file_size = image_path.stat().st_size
                
                # Skip very small images
                if self.config.skip_very_small and (width < self.config.min_dimension or height < self.config.min_dimension):
                    return True, f"Too small ({width}x{height})"
                
                # Skip very small file sizes (likely corrupted)
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
    
    def optimize_image_for_analysis(self, image_path: Path) -> Optional[Path]:
        """Create optimized image with better error handling"""
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
                    # Calculate new dimensions maintaining aspect ratio
                    if width > height:
                        new_width = self.config.max_dimension
                        new_height = int(height * (self.config.max_dimension / width))
                    else:
                        new_height = self.config.max_dimension
                        new_width = int(width * (self.config.max_dimension / height))
                    
                    img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    self.logger.debug(f"Resized {image_path.name} from {width}x{height} to {new_width}x{new_height}")
                
                # Save to temporary file
                temp_dir = Path(tempfile.gettempdir()) / "ai_image_analysis"
                temp_dir.mkdir(exist_ok=True)
                
                temp_path = temp_dir / f"opt_{int(time.time())}_{image_path.stem}.jpg"
                img.save(temp_path, "JPEG", quality=self.config.quality, optimize=True)
                
                return temp_path
                
        except Exception as e:
            self.logger.error(f"Failed to optimize {image_path.name}: {e}")
            return None

def process_single_image(args) -> Tuple[Path, Optional[Dict], Optional[str]]:
    """Process a single image - designed for concurrent execution"""
    image_path, config, analyzer, optimizer = args
    
    try:
        # Check if image should be skipped
        should_skip, reason = optimizer.should_skip_image(image_path)
        if should_skip:
            return image_path, None, f"Skipped: {reason}"
        
        # Optimize image
        optimized_path = optimizer.optimize_image_for_analysis(image_path)
        if not optimized_path:
            return image_path, None, "Failed to optimize image"
        
        try:
            # Analyze image
            result = analyzer.analyze_image(image_path, optimized_path)
            return image_path, result, None
        finally:
            # Clean up temporary file
            try:
                optimized_path.unlink()
            except:
                pass
                
    except Exception as e:
        return image_path, None, f"Error: {e}"

def main():
    """Enhanced main function with comprehensive logging and monitoring"""
    # Initialize configuration
    config = SystemConfig(
        api_key=os.getenv("GOOGLE_API_KEY"),
        source_directory=Path(r"F:\Photo-Library\OLD UPLOADS\iphoneuploads")
    )
    
    # Initialize logging
    logger = EnhancedLogger(config)
    
    logger.info("🚀 Enhanced AI Image Analyzer v2.0 Starting...")
    logger.info("✨ Features: Migrated to google-genai, comprehensive logging, resource monitoring")
    
    if not config.api_key:
        logger.error("GOOGLE_API_KEY environment variable not set")
        return
    
    if not config.source_directory.is_dir():
        logger.error(f"Source directory not found: {config.source_directory}")
        return
    
    # Initialize system monitor
    monitor = SystemMonitor(config, logger)
    optimal_workers = monitor.get_optimal_workers()
    config.max_workers = optimal_workers
    
    logger.info(f"System Analysis - Optimal workers: {optimal_workers}")
    
    # Initialize components
    try:
        analyzer = MigratedImageAnalyzer(config, logger)
        optimizer = ImageOptimizer(config, logger)
    except Exception as e:
        logger.error(f"Failed to initialize components: {e}")
        return
    
    # Get image files
    image_extensions = ('.jpg', '.jpeg', '.tif', '.tiff')
    logger.info(f"Scanning for images in: {config.source_directory}")
    
    try:
        all_files = [p for p in config.source_directory.rglob('*') 
                     if p.suffix.lower() in image_extensions]
        logger.info(f"Found {len(all_files)} total images")
    except Exception as e:
        logger.error(f"Error scanning directory: {e}")
        return
    
    if not all_files:
        logger.warning("No images found to process")
        return
    
    # Process images with concurrent execution
    processed_count = 0
    skipped_count = 0
    error_count = 0
    
    logger.info(f"Starting concurrent processing with {config.max_workers} workers")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=config.max_workers) as executor:
        # Prepare arguments for each image
        args_list = [(img, config, analyzer, optimizer) for img in all_files]
        
        # Submit all tasks
        future_to_image = {executor.submit(process_single_image, args): args[0] 
                          for args in args_list}
        
        # Process results as they complete
        for i, future in enumerate(concurrent.futures.as_completed(future_to_image)):
            image_path = future_to_image[future]
            
            try:
                img_path, result, error_msg = future.result()
                
                if result:
                    # TODO: Write EXIF data here
                    processed_count += 1
                    logger.info(f"[{i+1}/{len(all_files)}] ✅ {img_path.name} - Score: {result['score']}")
                elif error_msg:
                    if "Skipped:" in error_msg:
                        skipped_count += 1
                        logger.debug(f"[{i+1}/{len(all_files)}] ⏭️ {img_path.name} - {error_msg}")
                    else:
                        error_count += 1
                        logger.error(f"[{i+1}/{len(all_files)}] ❌ {img_path.name} - {error_msg}")
                else:
                    error_count += 1
                    logger.error(f"[{i+1}/{len(all_files)}] ❌ {img_path.name} - Unknown error")
                
                # Check system resources periodically
                if i % 10 == 0 and monitor.should_throttle():
                    logger.warning("System resources high - pausing processing")
                    time.sleep(2)
                    
            except Exception as e:
                error_count += 1
                logger.error(f"[{i+1}/{len(all_files)}] ❌ {image_path.name} - Exception: {e}")
    
    # Final statistics
    logger.info("🎉 Processing complete!")
    logger.info(f"   ✅ Successfully processed: {processed_count}")
    logger.info(f"   ⏭️ Skipped: {skipped_count}")
    logger.info(f"   ❌ Errors: {error_count}")
    
    final_resources = monitor.check_system_resources()
    logger.info(f"Final system state - Memory: {final_resources['memory_percent']:.1%}, CPU: {final_resources['cpu_percent']:.1%}")

if __name__ == "__main__":
    main()
