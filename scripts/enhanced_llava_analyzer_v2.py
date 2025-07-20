# ----------------------------------------------------------------------
#  Enhanced LLaVA Image Analyzer v2.0 - Production Ready
#  
#  Based on your improvements with additional enhancements:
#  - Comprehensive file-based logging
#  - System resource monitoring (Lightroom detection)
#  - Enhanced concurrent processing with throttling
#  - Better error handling and recovery
#  - Image optimization for faster processing
#  - Progress tracking and statistics
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
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image, ImageOps
from typing import Optional, Dict, List, Tuple, Any
from dataclasses import dataclass
from datetime import datetime

# Enhanced Configuration
@dataclass
class LLaVAConfig:
    """Configuration for enhanced LLaVA processing"""
    # Ollama settings
    ollama_url: str = "http://localhost:11434/api/generate"
    model_name: str = "llava:13b"
    prompt: str = "Analyze this image in detail, focusing on composition, subject matter, lighting, and artistic merit."
    
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
    log_file: str = "llava_analyzer.log"
    log_level: str = "INFO"
    max_log_size: int = 10 * 1024 * 1024  # 10MB
    log_backup_count: int = 5
    
    # Output
    output_file: str = "llava_analysis_results.csv"
    save_progress: bool = True
    progress_file: str = "llava_progress.json"

class EnhancedLogger:
    """Comprehensive logging system"""
    
    def __init__(self, config: LLaVAConfig):
        self.logger = logging.getLogger('llava_analyzer')
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
        
        self.logger.info("Enhanced LLaVA Analyzer v2.0 - Logging initialized")
    
    def info(self, msg): self.logger.info(msg)
    def warning(self, msg): self.logger.warning(msg)
    def error(self, msg): self.logger.error(msg)
    def debug(self, msg): self.logger.debug(msg)

class SystemMonitor:
    """Monitor system resources and adjust processing"""
    
    def __init__(self, config: LLaVAConfig, logger: EnhancedLogger):
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
    """Optimize images for faster LLaVA processing"""
    
    def __init__(self, config: LLaVAConfig, logger: EnhancedLogger):
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
                temp_dir = Path(tempfile.gettempdir()) / "llava_analysis"
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
    
    @staticmethod
    def encode_image_to_base64(image_path: Path) -> str:
        """Encode image to base64 string"""
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode('utf-8')

class ProgressTracker:
    """Track processing progress with save/load capability"""
    
    def __init__(self, config: LLaVAConfig):
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
    image_path, config, optimizer, logger = args
    
    try:
        # Check if image should be skipped
        should_skip, reason = optimizer.should_skip_image(image_path)
        if should_skip:
            return image_path, None, f"Skipped: {reason}"
        
        # Optimize and encode image
        base64_image = optimizer.optimize_image(image_path)
        if not base64_image:
            return image_path, None, "Failed to encode image"
        
        # Prepare payload for Ollama
        payload = {
            "model": config.model_name,
            "prompt": config.prompt,
            "stream": False,
            "images": [base64_image]
        }
        
        headers = {'Content-Type': 'application/json'}
        
        # Make request to Ollama
        response = requests.post(
            config.ollama_url, 
            data=json.dumps(payload), 
            headers=headers, 
            timeout=config.timeout
        )
        
        response.raise_for_status()
        response_data = response.json()
        
        # Extract analysis text
        analysis_text = response_data.get('response', 'No response content found').strip()
        
        if analysis_text and analysis_text != 'No response content found':
            result = {
                'image_path': str(image_path),
                'image_name': image_path.name,
                'analysis': analysis_text,
                'timestamp': datetime.now().isoformat(),
                'model': config.model_name
            }
            return image_path, result, None
        else:
            return image_path, None, "Empty or invalid response from model"
            
    except requests.exceptions.Timeout:
        return image_path, None, f"Timeout after {config.timeout}s"
    except requests.exceptions.RequestException as e:
        return image_path, None, f"Network error: {e}"
    except json.JSONDecodeError:
        return image_path, None, "Could not decode JSON response"
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
            fieldnames = ['image_name', 'image_path', 'analysis', 'timestamp', 'model']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)
        logger.info("Results saved successfully")
    except Exception as e:
        logger.error(f"Failed to save results: {e}")

def main():
    """Enhanced main function with comprehensive features"""
    parser = argparse.ArgumentParser(
        description="Enhanced LLaVA Image Analyzer v2.0 with system monitoring and optimization"
    )
    parser.add_argument("source_dir", type=str, help="Source directory containing images")
    parser.add_argument("--url", type=str, default="http://localhost:11434/api/generate", 
                       help="Ollama API URL")
    parser.add_argument("--model", type=str, default="llava:13b", 
                       help="LLaVA model name")
    parser.add_argument("--prompt", type=str, 
                       default="Analyze this image in detail, focusing on composition, subject matter, lighting, and artistic merit.",
                       help="Analysis prompt")
    parser.add_argument("--workers", type=int, default=4, 
                       help="Maximum number of concurrent workers")
    parser.add_argument("--output", type=str, default="llava_analysis_results.csv", 
                       help="Output CSV file path")
    parser.add_argument("--optimize", action="store_true", default=True,
                       help="Enable image optimization (default: True)")
    parser.add_argument("--no-optimize", action="store_false", dest="optimize",
                       help="Disable image optimization")
    parser.add_argument("--log-level", type=str, default="INFO", 
                       choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                       help="Logging level")
    
    args = parser.parse_args()
    
    # Initialize configuration
    config = LLaVAConfig(
        ollama_url=args.url,
        model_name=args.model,
        prompt=args.prompt,
        max_workers=args.workers,
        output_file=args.output,
        optimize_images=args.optimize,
        log_level=args.log_level
    )
    
    # Initialize logger
    logger = EnhancedLogger(config)
    
    logger.info("🚀 Enhanced LLaVA Image Analyzer v2.0 Starting...")
    logger.info("✨ Features: Image optimization, system monitoring, progress tracking")
    
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
    optimizer = ImageOptimizer(config, logger)
    progress_tracker = ProgressTracker(config)
    
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
        args_list = [(img, config, optimizer, logger) for img in unprocessed_files]
        
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
                    logger.info(f"[{i+1}/{len(unprocessed_files)}] ✅ {img_path.name}")
                elif error_msg:
                    if "Skipped:" in error_msg:
                        skipped_count += 1
                        logger.debug(f"[{i+1}/{len(unprocessed_files)}] ⏭️ {img_path.name} - {error_msg}")
                    else:
                        error_count += 1
                        logger.error(f"[{i+1}/{len(unprocessed_files)}] ❌ {img_path.name} - {error_msg}")
                    progress_tracker.mark_processed(img_path)
                else:
                    error_count += 1
                    logger.error(f"[{i+1}/{len(unprocessed_files)}] ❌ {img_path.name} - Unknown error")
                    progress_tracker.mark_processed(img_path)
                
                # Save progress periodically and check resources
                if i % 10 == 0:
                    progress_tracker.save_progress()
                    if monitor.should_throttle():
                        logger.warning("High system usage - pausing briefly")
                        time.sleep(2)
                        
            except Exception as e:
                error_count += 1
                logger.error(f"[{i+1}/{len(unprocessed_files)}] ❌ {image_path.name} - Exception: {e}")
    
    # Final save and statistics
    progress_tracker.save_progress()
    save_results_to_csv(progress_tracker.results, config.output_file, logger)
    
    logger.info("🎉 Processing complete!")
    logger.info(f"   ✅ Successfully processed: {processed_count}")
    logger.info(f"   ⏭️ Skipped: {skipped_count}")
    logger.info(f"   ❌ Errors: {error_count}")
    logger.info(f"   📁 Results saved to: {config.output_file}")
    
    final_resources = monitor.check_system_resources()
    logger.info(f"Final system state - Memory: {final_resources['memory_percent']:.1%}, CPU: {final_resources['cpu_percent']:.1%}")

if __name__ == "__main__":
    main()
