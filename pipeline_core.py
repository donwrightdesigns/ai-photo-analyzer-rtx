# ----------------------------------------------------------------------
#  AI Image Analyzer - Multi-Stage Processing Pipeline
#  
#  Implementation of the architectural blueprint from the technical report:
#  1. Image Curation Engine (IQA) - Quality assessment and filtering
#  2. Content Generation Engine - AI analysis of curated images
#  3. Metadata Persistence Layer - Robust metadata writing
# ----------------------------------------------------------------------

import os
import torch
from pathlib import Path

# Make pyiqa optional to allow testing without complex dependencies
try:
    import pyiqa
    PYIQA_AVAILABLE = True
except ImportError:
    PYIQA_AVAILABLE = False
    print("⚠️  pyiqa not available - using fallback quality assessment")
import threading
import queue
import json
import base64
import requests
from PIL import Image
import google.genai as genai
from google.generativeai import types
import exiftool
import time
import math
from typing import List, Dict, Optional, Tuple, Any


class ImageCurationEngine:
    """
    Stage 1: Image Quality Assessment and Curation
    
    Uses No-Reference Image Quality Assessment (NR-IQA) algorithms to score
    and filter images, selecting only the highest quality subset for expensive
    AI analysis.
    """
    
    def __init__(self, iqa_model='brisque', device=None):
        """
        Initialize the Image Curation Engine.
        
        Args:
            iqa_model (str): IQA model to use ('brisque', 'niqe', 'musiq', 'topiq')
            device: PyTorch device to use (auto-detected if None)
        """
        self.device = device or (torch.device("cuda") if torch.cuda.is_available() else torch.device("cpu"))
        self.iqa_model_name = iqa_model
        self.iqa_metric = None
        self._init_iqa_model()
        
    def _init_iqa_model(self):
        """Initialize the IQA model."""
        if not PYIQA_AVAILABLE:
            print("📊 Using fallback quality assessment (file size + basic image analysis)")
            self.iqa_metric = None
            return
            
        try:
            self.iqa_metric = pyiqa.create_metric(self.iqa_model_name, device=self.device)
            print(f"✅ IQA model '{self.iqa_model_name}' loaded on {self.device}")
        except Exception as e:
            print(f"❌ Failed to load IQA model '{self.iqa_model_name}': {e}")
            # Fallback to BRISQUE if the selected model fails
            if self.iqa_model_name != 'brisque':
                try:
                    self.iqa_metric = pyiqa.create_metric('brisque', device=self.device)
                    self.iqa_model_name = 'brisque'
                    print(f"✅ Fallback to BRISQUE model successful")
                except Exception as fallback_e:
                    print(f"❌ Fallback to BRISQUE also failed: {fallback_e}")
                    self.iqa_metric = None
                    print("📊 Using fallback quality assessment instead")
    
    def score_image(self, image_path: str) -> Optional[float]:
        """
        Score a single image using the IQA model or fallback assessment.
        
        Args:
            image_path (str): Path to the image file
            
        Returns:
            float: Quality score (lower is better for BRISQUE, higher for others)
        """
        if self.iqa_metric is None:
            # Use fallback quality assessment
            return self._fallback_quality_score(image_path)
            
        try:
            score_tensor = self.iqa_metric(image_path)
            return score_tensor.item()
        except Exception as e:
            print(f"Warning: Could not score {os.path.basename(image_path)}: {e}")
            return self._fallback_quality_score(image_path)
    
    def _fallback_quality_score(self, image_path: str) -> Optional[float]:
        """
        Simple fallback quality assessment based on file size and basic image metrics.
        
        Args:
            image_path (str): Path to the image file
            
        Returns:
            float: Quality score (higher is better for fallback)
        """
        try:
            # Get file size (larger files generally indicate higher quality)
            file_size = os.path.getsize(image_path)
            
            # Get image dimensions
            with Image.open(image_path) as img:
                width, height = img.size
                total_pixels = width * height
                
                # Simple quality heuristic:
                # - Higher resolution = better
                # - Larger file size relative to pixels = better (less compression)
                # - Reasonable aspect ratio = better
                
                # Calculate compression ratio (bytes per pixel)
                compression_ratio = file_size / total_pixels if total_pixels > 0 else 0
                
                # Calculate aspect ratio penalty (prefer standard ratios)
                aspect_ratio = width / height if height > 0 else 1
                aspect_penalty = min(aspect_ratio, 1/aspect_ratio)  # Closer to 1 is better
                
                # Combine metrics (scale to 0-100 range)
                resolution_score = min(100, total_pixels / 10000)  # 1MP = 100 points
                compression_score = min(100, compression_ratio * 100)  # Adjust scaling
                aspect_score = aspect_penalty * 100
                
                # Weighted combination
                final_score = (resolution_score * 0.4 + compression_score * 0.4 + aspect_score * 0.2)
                
                return final_score
                
        except Exception as e:
            print(f"Warning: Fallback scoring failed for {os.path.basename(image_path)}: {e}")
            return 50.0  # Default middle score
    
    def curate_images_by_quality(self, image_directory: str, top_percent: float = 0.10, 
                                status_queue: Optional[queue.Queue] = None) -> List[Tuple[str, float]]:
        """
        Analyze all images in a directory and return the top N percent by quality.
        
        Args:
            image_directory (str): Path to directory containing images
            top_percent (float): Percentage of top images to return (0.0 to 1.0)
            status_queue (Queue): Optional queue for progress updates
            
        Returns:
            List[Tuple[str, float]]: List of (image_path, score) tuples for top images
        """
        if status_queue:
            status_queue.put("🔍 Starting Image Quality Assessment (IQA)...")
            
        supported_extensions = ('.jpg', '.jpeg', '.png', '.tif', '.tiff')
        image_files = []
        
        # Discover all supported image files
        for ext in supported_extensions:
            image_files.extend(Path(image_directory).rglob(f'*{ext}'))
            image_files.extend(Path(image_directory).rglob(f'*{ext.upper()}'))
        
        if not image_files:
            if status_queue:
                status_queue.put("❌ No supported image files found in directory")
            return []
        
        total_images = len(image_files)
        if status_queue:
            status_queue.put(f"📊 Found {total_images} images for quality assessment")
        
        scores = []
        for i, image_path in enumerate(image_files):
            if status_queue:
                status_queue.put(f"📈 Scoring image {i+1}/{total_images}: {image_path.name}")
            
            score = self.score_image(str(image_path))
            if score is not None:
                scores.append((str(image_path), score))
        
        if not scores:
            if status_queue:
                status_queue.put("❌ No images could be scored successfully")
            return []
        
        # Sort by score (ascending for BRISQUE, descending for others)
        if self.iqa_metric and hasattr(self.iqa_metric, 'lower_better'):
            reverse_sort = not self.iqa_metric.lower_better
        else:
            # For fallback quality assessment, higher scores are better
            reverse_sort = True
        scores.sort(key=lambda x: x[1], reverse=reverse_sort)
        
        # Calculate selection threshold
        num_to_select = max(1, int(len(scores) * top_percent))
        top_images = scores[:num_to_select]
        
        if status_queue:
            status_queue.put(f"✅ Selected top {len(top_images)} images ({top_percent*100:.1f}%) for AI analysis")
            status_queue.put(f"📊 Quality score range: {top_images[-1][1]:.2f} to {top_images[0][1]:.2f}")
        
        return top_images


class ContentGenerationEngine:
    """
    Stage 2: AI-Powered Content Analysis
    
    Performs sophisticated AI analysis on the curated high-quality image subset,
    generating categories, tags, scores, and optional curatorial descriptions.
    """
    
    def __init__(self, model_config: Dict[str, Any]):
        """
        Initialize the Content Generation Engine.
        
        Args:
            model_config (dict): Configuration for AI models including type, API keys, etc.
        """
        self.config = model_config
        self.gemini_model = None
        self.ollama_url = model_config.get('ollama_url', 'http://localhost:11434')
        self._init_models()
    
    def _init_models(self):
        """Initialize AI models based on configuration."""
        if self.config.get('model_type') == 'gemini' and self.config.get('google_api_key'):
            try:
                genai.configure(api_key=self.config['google_api_key'])
                self.gemini_model = genai.GenerativeModel(self.config.get('gemini_model', 'gemini-2.0-flash-exp'))
                print("✅ Gemini model initialized")
            except Exception as e:
                print(f"❌ Failed to initialize Gemini model: {e}")
    
    def get_analysis_prompt(self, profile_key: str = 'professional_art_critic') -> str:
        """Generate analysis prompt based on selected profile."""
        # Use the same PROMPT_PROFILES from your existing app.py
        PROMPT_PROFILES = {
            'professional_art_critic': {
                'name': 'Professional Art Critic',
                'persona': 'You are a professional art critic and gallery curator with 25 years of experience, evaluating photographs for potential inclusion in a fine art exhibition.',
                'criteria': [
                    'Technical Excellence: Focus, exposure, composition, color/lighting',
                    'Artistic Merit: Creativity, emotional impact, visual storytelling', 
                    'Commercial Appeal: Marketability, broad audience appeal',
                    'Uniqueness: What sets this image apart from typical photography'
                ]
            }
        }
        
        profile = PROMPT_PROFILES.get(profile_key, PROMPT_PROFILES['professional_art_critic'])
        
        # Build criteria text
        criteria_text = "\\n".join([f"{i+1}. {criterion}" for i, criterion in enumerate(profile['criteria'])])
        
        # Build JSON template
        json_template = {
            "category": "chosen_category",
            "subcategory": "chosen_subcategory", 
            "tags": ["tag1", "tag2", "tag3"],
            "score": 7
        }
        
        if self.config.get('enable_gallery_critique', False):
            json_template["critique"] = f"Professional critique from {profile['name']} perspective."
        
        json_str = json.dumps(json_template, indent=2)
        
        DEFAULT_CATEGORIES = ["People", "Place", "Thing"]
        DEFAULT_SUB_CATEGORIES = ["Candid", "Posed", "Automotive", "Real Estate", "Landscape", 
                                 "Events", "Animal", "Product", "Food"]
        DEFAULT_TAGS = ["Strobist", "Available Light", "Natural Light", "Beautiful", "Black & White", 
                       "Timeless", "Low Quality", "Sentimental", "Action", "Minimalist", "Out of Focus", 
                       "Other", "Evocative", "Disturbing", "Boring", "Wedding", "Bride", "Groom", 
                       "Family", "Love", "Calm", "Busy"]
        
        prompt = f"""
        {profile['persona']}
        
        ANALYSIS CRITERIA:
        {criteria_text}
        
        CLASSIFICATION (select ONE from each category):
        CATEGORIES: {', '.join(DEFAULT_CATEGORIES)}
        SUB_CATEGORIES: {', '.join(DEFAULT_SUB_CATEGORIES)}
        TAGS: {', '.join(DEFAULT_TAGS)} (select 2-4 most relevant)
        
        SCORING GUIDE (1-10 scale from {profile['name']} perspective):
        1-2: Poor (fails to meet basic standards for this evaluation type)
        3-4: Below Average (basic competence, limited value for intended purpose)
        5-6: Average (meets standard expectations for this type of image)
        7-8: Above Average (strong quality and purpose alignment)
        9-10: Exceptional (outstanding example that excels in all criteria)
        
        RESPOND WITH VALID JSON ONLY:
        {json_str}
        """
        
        return prompt
    
    def analyze_image_with_gemini(self, image_path: str) -> Optional[Dict[str, Any]]:
        """Analyze image using Gemini model."""
        if not self.gemini_model:
            return None
            
        try:
            img = Image.open(image_path)
            prompt = self.get_analysis_prompt()
            
            response = self.gemini_model.generate_content(
                [prompt, img],
                generation_config=genai.GenerationConfig(
                    temperature=0.3,
                    top_p=0.8,
                    max_output_tokens=500
                )
            )
            
            # Clean and parse response
            response_text = response.text.replace('```json', '').replace('```', '').strip()
            
            try:
                data = json.loads(response_text)
                required_keys = ["category", "subcategory", "tags", "score"]
                if self.config.get('enable_gallery_critique', False):
                    required_keys.append("critique")
                    
                if all(k in data for k in required_keys):
                    return data
            except json.JSONDecodeError:
                pass
                
        except Exception as e:
            print(f"Error analyzing image with Gemini: {e}")
        
        return None
    
    def analyze_image_with_ollama(self, image_path: str) -> Optional[Dict[str, Any]]:
        """Analyze image using Ollama LLaVA model."""
        try:
            with open(image_path, 'rb') as img_file:
                image_data = base64.b64encode(img_file.read()).decode('utf-8')
            
            prompt = self.get_analysis_prompt()
            
            payload = {
                "model": self.config.get('model', 'llava:13b'),
                "prompt": prompt,
                "images": [image_data],
                "stream": False
            }
            
            response = requests.post(f"{self.ollama_url}/api/generate", json=payload, timeout=120)
            
            if response.status_code == 200:
                result = response.json()
                response_text = result.get('response', '').strip()
                
                # Clean up response
                response_text = response_text.replace('```json', '').replace('```', '').strip()
                
                try:
                    data = json.loads(response_text)
                    if all(k in data for k in ["category", "subcategory", "tags", "score"]):
                        return data
                except json.JSONDecodeError:
                    pass
                    
        except Exception as e:
            print(f"Error analyzing image with Ollama: {e}")
        
        return None
    
    def analyze_image(self, image_path: str) -> Optional[Dict[str, Any]]:
        """Analyze image using the configured model."""
        if self.config.get('model_type') == 'gemini':
            return self.analyze_image_with_gemini(image_path)
        elif self.config.get('model_type') == 'ollama':
            return self.analyze_image_with_ollama(image_path)
        else:
            # Fallback placeholder
            return {
                "category": "Thing",
                "subcategory": "Other",
                "tags": ["AI", "Analyzed"],
                "score": 6
            }


class MetadataPersistenceLayer:
    """
    Stage 3: Robust Metadata Writing
    
    Handles writing analysis results to XMP sidecar files or embedded EXIF/IPTC
    metadata using PyExifTool for maximum compatibility and reliability.
    """
    
    def __init__(self, exiftool_path: Optional[str] = None):
        """
        Initialize the Metadata Persistence Layer.
        
        Args:
            exiftool_path (str, optional): Path to exiftool executable if not in PATH
        """
        self.exiftool_path = exiftool_path
        self._test_exiftool()
    
    def _test_exiftool(self):
        """Test if ExifTool is available."""
        try:
            with exiftool.ExifToolHelper(executable=self.exiftool_path) as et:
                et.get_metadata([])  # Test call
            print("✅ ExifTool is available and working")
        except Exception as e:
            print(f"❌ ExifTool not available: {e}")
            print("Please install ExifTool: https://exiftool.org/")
    
    def write_xmp_sidecar(self, image_path: str, analysis_data: Dict[str, Any]) -> bool:
        """
        Write analysis data to XMP sidecar file.
        
        Args:
            image_path (str): Path to the original image file
            analysis_data (dict): Analysis results to write
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            image_path = Path(image_path)
            xmp_path = image_path.with_suffix(image_path.suffix + '.xmp')
            
            # Prepare metadata
            tags = analysis_data.get('tags', [])
            description = analysis_data.get('critique', '')
            score = analysis_data.get('score', 0)
            star_rating = max(1, math.ceil(score / 2))
            
            # Add GALLERY tag for 5-star ratings
            if star_rating == 5 and "GALLERY" not in tags:
                tags.append("GALLERY")
            
            metadata_dict = {
                "XMP-dc:Subject": tags,
                "IPTC:Keywords": tags,
                "XMP-dc:Description": description,
                "XMP:Rating": star_rating,
                "XMP-dc:Title": f"Score: {score}/10"
            }
            
            with exiftool.ExifToolHelper(executable=self.exiftool_path) as et:
                et.set_tags(
                    [str(xmp_path)],
                    tags=metadata_dict,
                    params=["-overwrite_original"]
                )
            
            print(f"✅ XMP sidecar written: {xmp_path.name}")
            return True
            
        except Exception as e:
            print(f"❌ Error writing XMP sidecar for {os.path.basename(image_path)}: {e}")
            return False
    
    def write_embedded_metadata(self, image_path: str, analysis_data: Dict[str, Any]) -> bool:
        """
        Write analysis data directly to image file EXIF/IPTC metadata.
        
        Args:
            image_path (str): Path to the image file
            analysis_data (dict): Analysis results to write
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            tags = analysis_data.get('tags', [])
            description = analysis_data.get('critique', '')
            score = analysis_data.get('score', 0)
            star_rating = max(1, math.ceil(score / 2))
            
            # Add GALLERY tag for 5-star ratings
            if star_rating == 5 and "GALLERY" not in tags:
                tags.append("GALLERY")
            
            metadata_dict = {
                "IPTC:Keywords": tags,
                "XMP-dc:Subject": tags,
                "EXIF:UserComment": description,
                "EXIF:Rating": star_rating,
                "EXIF:ImageDescription": f"Category: {analysis_data.get('category', 'N/A')}, Score: {score}/10"
            }
            
            with exiftool.ExifToolHelper(executable=self.exiftool_path) as et:
                et.set_tags(
                    [str(image_path)],
                    tags=metadata_dict,
                    params=["-overwrite_original"]
                )
            
            print(f"✅ Embedded metadata written: {os.path.basename(image_path)}")
            return True
            
        except Exception as e:
            print(f"❌ Error writing embedded metadata for {os.path.basename(image_path)}: {e}")
            return False
    
    def write_metadata_batch(self, analysis_results: List[Dict[str, Any]], use_exif: bool = False,
                            status_queue: Optional[queue.Queue] = None) -> int:
        """
        Write metadata for a batch of analysis results.
        
        Args:
            analysis_results (list): List of analysis result dictionaries
            use_exif (bool): If True, write to image files; otherwise, XMP sidecars
            status_queue (Queue): Optional queue for progress updates
            
        Returns:
            int: Number of files successfully processed
        """
        if status_queue:
            status_queue.put(f"💾 Writing metadata for {len(analysis_results)} images...")
        
        success_count = 0
        
        for i, result in enumerate(analysis_results):
            image_path = result.get('file_path', '')
            analysis_data = result.get('analysis', {})
            
            if status_queue:
                status_queue.put(f"💾 Writing metadata {i+1}/{len(analysis_results)}: {os.path.basename(image_path)}")
            
            if use_exif:
                success = self.write_embedded_metadata(image_path, analysis_data)
            else:
                success = self.write_xmp_sidecar(image_path, analysis_data)
            
            if success:
                success_count += 1
        
        if status_queue:
            status_queue.put(f"✅ Metadata writing complete: {success_count}/{len(analysis_results)} files processed")
        
        return success_count


class MultiStageProcessingPipeline:
    """
    Complete Multi-Stage Processing Pipeline
    
    Orchestrates the entire pipeline: IQA curation → AI analysis → Metadata writing
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the complete processing pipeline.
        
        Args:
            config (dict): Configuration dictionary with all pipeline settings
        """
        self.config = config
        self.curation_engine = ImageCurationEngine(
            iqa_model=config.get('iqa_model', 'brisque'),
            device=config.get('device')
        )
        self.content_engine = ContentGenerationEngine(config)
        self.metadata_layer = MetadataPersistenceLayer(
            exiftool_path=config.get('exiftool_path')
        )
    
    def process_directory(self, directory_path: str, status_queue: Optional[queue.Queue] = None) -> Dict[str, Any]:
        """
        Process all images in a directory through the complete pipeline.
        
        Args:
            directory_path (str): Path to directory containing images
            status_queue (Queue): Optional queue for progress updates
            
        Returns:
            dict: Processing results and statistics
        """
        start_time = time.time()
        
        if status_queue:
            status_queue.put("🚀 Starting Multi-Stage Processing Pipeline...")
            status_queue.put(f"📁 Target directory: {directory_path}")
        
        # Stage 1 & 2: Quality Assessment and Curation
        top_percent = self.config.get('quality_threshold', 0.10)
        curated_images = self.curation_engine.curate_images_by_quality(
            directory_path, top_percent, status_queue
        )
        
        if not curated_images:
            if status_queue:
                status_queue.put("❌ No images selected for processing")
            return {"success": False, "error": "No images passed quality assessment"}
        
        # Stage 3: AI Content Analysis
        if status_queue:
            status_queue.put(f"🧠 Starting AI analysis of {len(curated_images)} curated images...")
        
        analysis_results = []
        for i, (image_path, quality_score) in enumerate(curated_images):
            if status_queue:
                status_queue.put(f"🧠 Analyzing {i+1}/{len(curated_images)}: {os.path.basename(image_path)}")
            
            analysis_data = self.content_engine.analyze_image(image_path)
            
            if analysis_data:
                # Add quality score to analysis
                analysis_data['quality_score'] = quality_score
                
                result = {
                    'file_path': image_path,
                    'image_name': os.path.basename(image_path),
                    'analysis': analysis_data,
                    'timestamp': time.time()
                }
                analysis_results.append(result)
        
        # Stage 4: Metadata Writing
        use_exif = self.config.get('use_exif', False)
        success_count = self.metadata_layer.write_metadata_batch(
            analysis_results, use_exif, status_queue
        )
        
        # Final statistics
        total_time = time.time() - start_time
        stats = {
            "success": True,
            "total_images_found": len(curated_images),
            "images_analyzed": len(analysis_results),
            "metadata_written": success_count,
            "processing_time": total_time,
            "quality_threshold": top_percent,
            "iqa_model": self.curation_engine.iqa_model_name,
            "ai_model": self.config.get('model_type', 'unknown'),
            "results": analysis_results
        }
        
        if status_queue:
            status_queue.put(f"🎉 Pipeline Complete!")
            status_queue.put(f"📊 Processed {success_count}/{len(analysis_results)} images in {total_time:.1f}s")
            status_queue.put(f"🎯 Used {self.curation_engine.iqa_model_name.upper()} quality assessment")
            status_queue.put(f"🤖 Used {self.config.get('model_type', 'unknown').upper()} AI model")
        
        return stats
