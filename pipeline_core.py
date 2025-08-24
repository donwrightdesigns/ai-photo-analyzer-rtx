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
    print("  pyiqa not available - using fallback quality assessment")
import threading
import queue
import json
import base64
import requests
from PIL import Image
import google.generativeai as genai
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
            print(" Using fallback quality assessment (file size + basic image analysis)")
            self.iqa_metric = None
            return
            
        try:
            self.iqa_metric = pyiqa.create_metric(self.iqa_model_name, device=self.device)
            print(f" IQA model '{self.iqa_model_name}' loaded on {self.device}")
        except Exception as e:
            print(f" Failed to load IQA model '{self.iqa_model_name}': {e}")
            # Fallback to BRISQUE if the selected model fails
            if self.iqa_model_name != 'brisque':
                try:
                    self.iqa_metric = pyiqa.create_metric('brisque', device=self.device)
                    self.iqa_model_name = 'brisque'
                    print(f" Fallback to BRISQUE model successful")
                except Exception as fallback_e:
                    print(f" Fallback to BRISQUE also failed: {fallback_e}")
                    self.iqa_metric = None
                    print(" Using fallback quality assessment instead")
    
    def score_image(self, image_path: str) -> Optional[float]:
        """
        Score a single image using the IQA model or fallback assessment.
        
        Args:
            image_path (str): Path to the image file
            
        Returns:
            float: Quality score (lower is better for BRISQUE, higher for others)
        """
        # Skip PNG files due to alpha channel incompatibility
        if image_path.lower().endswith('.png'):
            print(f"Skipping PNG file (alpha channel not supported): {os.path.basename(image_path)}")
            return None
            
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
                                status_queue: Optional[queue.Queue] = None, recursive: bool = True) -> List[Tuple[str, float]]:
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
            status_queue.put(" Starting Image Quality Assessment (IQA)...")
            
        supported_extensions = ('.jpg', '.jpeg', '.png', '.tif', '.tiff')
        image_files = []
        
        # Discover all supported image files (recursive or not based on parameter)
        if recursive:
            # Recursive search through all subdirectories (default behavior)
            for ext in supported_extensions:
                image_files.extend(Path(image_directory).rglob(f'*{ext}'))
                image_files.extend(Path(image_directory).rglob(f'*{ext.upper()}'))
        else:
            # Non-recursive: only search in the immediate directory
            for ext in supported_extensions:
                image_files.extend(Path(image_directory).glob(f'*{ext}'))
                image_files.extend(Path(image_directory).glob(f'*{ext.upper()}'))
        
        if not image_files:
            if status_queue:
                status_queue.put(" No supported image files found in directory")
            return []
        
        total_images = len(image_files)
        if status_queue:
            status_queue.put(f" Found {total_images} images for quality assessment")
        
        scores = []
        for i, image_path in enumerate(image_files):
            if status_queue:
                status_queue.put(f" Scoring image {i+1}/{total_images}: {image_path.name}")
            
            score = self.score_image(str(image_path))
            if score is not None:
                scores.append((str(image_path), score))
        
        if not scores:
            if status_queue:
                status_queue.put(" No images could be scored successfully")
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
            status_queue.put(f" Selected top {len(top_images)} images ({top_percent*100:.1f}%) for AI analysis")
            status_queue.put(f" Quality score range: {top_images[-1][1]:.2f} to {top_images[0][1]:.2f}")
        
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
        self.llava_13b_model = None  # Local LLaVA 13B
        self.ollama_url = model_config.get('ollama_url', 'http://localhost:11434')
        self._init_models()
    
    def _init_models(self):
        """Initialize available models: LLaVA 13B and Gemini."""
        self._init_gemini()  # Cloud fallback
        self._init_llava_13b()  # Local LLaVA 13B

    def _init_gemini(self):
        """Initialize Gemini model as fallback option."""
        if self.config.get('google_api_key'):
            try:
                genai.configure(api_key=self.config['google_api_key'])
                self.gemini_model = genai.GenerativeModel(self.config.get('gemini_model', 'gemini-pro-vision'))
                print("✅ Gemini model initialized (fallback)")
            except Exception as e:
                print(f"❌ Failed to initialize Gemini model: {e}")

    def _init_llava_13b(self):
        """Initialize local LLaVA 13B model via Ollama."""
        try:
            # Test if LLaVA 13B is available locally
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get('models', [])
                llava_models = [m for m in models if 'llava' in m['name'].lower() and '13b' in m['name']]
                if llava_models:
                    self.llava_13b_model = llava_models[0]['name']  # Use first available LLaVA 13B
                    print(f"✅ LLaVA 13B model initialized: {self.llava_13b_model}")
                else:
                    print("❌ LLaVA 13B model not found locally")
            else:
                print("❌ Ollama service not available for local LLaVA 13B")
        except Exception as e:
            print(f"❌ Failed to initialize LLaVA 13B: {e}")

    def _init_gemma_12b(self):
        """Initialize local Gemma 12B model via Ollama."""
        try:
            # Test if Gemma 12B is available locally
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get('models', [])
                gemma_models = [m for m in models if 'gemma' in m['name'].lower() and ('12b' in m['name'] or '2b' in m['name'])]
                if gemma_models:
                    self.gemma_12b_model = gemma_models[0]['name']  # Use first available Gemma model
                    print(f"✅ Gemma model initialized: {self.gemma_12b_model}")
                else:
                    print("❌ Gemma model not found locally")
            else:
                print("❌ Ollama service not available for local Gemma")
        except Exception as e:
            print(f"❌ Failed to initialize Gemma: {e}")
    
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
            },
            'street_photographer': {
                'name': 'Street Photographer',
                'persona': 'You are a seasoned street photographer with a keen eye for capturing authentic, spontaneous moments in urban environments.',
                'criteria': [
                    'Authenticity: Genuine, unposed moments and natural expressions',
                    'Composition: Use of leading lines, framing, and urban geometry',
                    'Human Connection: Emotional connection with subjects and environment',
                    'Decisive Moment: Capturing fleeting, significant instants'
                ]
            },
            'commercial_photographer': {
                'name': 'Commercial Photographer', 
                'persona': 'You are a commercial photographer specializing in creating images that sell products, services, and build brand identity.',
                'criteria': [
                    'Brand Alignment: Does the image fit the intended brand aesthetic?',
                    'Product Showcase: How effectively is the subject presented?',
                    'Marketing Appeal: Does the image drive consumer interest?',
                    'Professional Quality: Technical excellence for commercial use'
                ]
            },
            'photojournalist': {
                'name': 'Photojournalist',
                'persona': 'You are an experienced photojournalist dedicated to documenting events and telling compelling stories through powerful imagery.',
                'criteria': [
                    'Newsworthiness: Does the image capture a significant moment or event?',
                    'Objectivity: Fair and accurate representation without bias',
                    'Emotional Impact: Strong emotional response that supports the story',
                    'Narrative Clarity: Does the image tell a clear, compelling story?'
                ]
            },
            'social_media_influencer': {
                'name': 'Social Media Influencer',
                'persona': 'You are a social media expert with expertise in creating viral content and understanding what engages modern digital audiences.',
                'criteria': [
                    'Scroll-Stopping Power: Immediately captivating and attention-grabbing',
                    'Shareability: Relatable content that encourages sharing',
                    'Trend Awareness: Taps into current visual trends and aesthetics',
                    'Engagement Potential: Likely to generate likes, comments, and interaction'
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
        
        # Enhanced Photography-Specific Taxonomy (from BakLLaVA analyzer)
        DEFAULT_CATEGORIES = ["People", "Place", "Thing"]
        DEFAULT_SUB_CATEGORIES = ["Portrait", "Group-Shot", "Couple", "Family", "Children", "Baby", "Senior-Citizen", 
                                 "Pet", "Wildlife", "Bird", "Automotive", "Architecture", "Interior", "Product", 
                                 "Food", "Flowers", "Macro", "Landscape", "Urban", "Beach", "Forest", "Event"]
        
        # Photography-specific structured tags
        SUBJECT_TAGS = ["Portrait", "Group-Shot", "Couple", "Family", "Children", "Baby", "Senior-Citizen", 
                       "Pet", "Wildlife", "Bird", "Automotive", "Architecture", "Interior", "Product", 
                       "Food", "Flowers", "Macro"]
        
        LIGHTING_TAGS = ["Golden-Hour", "Blue-Hour", "Overcast", "Direct-Sun", "Window-Light", 
                        "Studio-Strobe", "Speedlight", "Natural-Light", "Low-Light", "Backlit", 
                        "Side-Lit", "Dramatic-Lighting"]
        
        STYLE_TAGS = ["Black-White", "Color-Graded", "High-Contrast", "Soft-Focus", "Sharp-Detail", 
                     "Shallow-DOF", "Wide-Angle", "Telephoto", "Candid", "Posed", "Action-Shot", "Still-Life"]
        
        EVENT_LOCATION_TAGS = ["Wedding", "Engagement", "Corporate", "Real-Estate", "Landscape", 
                              "Urban", "Beach", "Forest", "Indoor", "Outdoor", "Studio", "Event", 
                              "Concert", "Sports"]
        
        MOOD_TAGS = ["Bright-Cheerful", "Moody-Dark", "Romantic", "Professional", "Casual", 
                    "Energetic", "Peaceful", "Dramatic"]
        
        # Combine all tags for selection
        DEFAULT_TAGS = SUBJECT_TAGS + LIGHTING_TAGS + STYLE_TAGS + EVENT_LOCATION_TAGS + MOOD_TAGS
        
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
    
    def _resize_image_for_analysis(self, image_path: str, max_size: int = 1024) -> Image.Image:
        """
        Resize image for AI analysis if it's too large.
        
        Args:
            image_path (str): Path to the image file
            max_size (int): Maximum dimension (default 1024px for faster processing)
            
        Returns:
            PIL.Image: Resized image
        """
        img = Image.open(image_path)
        
        # Check if image needs resizing
        max_dimension = max(img.width, img.height)
        if max_dimension <= max_size:
            return img  # No resizing needed
        
        # Calculate new dimensions maintaining aspect ratio
        if img.width > img.height:
            new_width = max_size
            new_height = int((img.height * max_size) / img.width)
        else:
            new_height = max_size
            new_width = int((img.width * max_size) / img.height)
        
        # Resize with high-quality resampling
        resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        print(f"  Resized {img.width}x{img.height} → {new_width}x{new_height} for analysis")
        
        return resized_img
    
    def analyze_image_with_gemini(self, image_path: str) -> Optional[Dict[str, Any]]:
        """Analyze image using Gemini model."""
        if not self.gemini_model:
            return None
            
        try:
            img = self._resize_image_for_analysis(image_path)
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
    
    def analyze_image_with_llava_13b(self, image_path: str) -> Optional[Dict[str, Any]]:
        """Analyze image using local LLaVA 13B model."""
        if not self.llava_13b_model:
            return None
            
        try:
            # Resize image for faster processing
            img = self._resize_image_for_analysis(image_path)
            
            # Convert resized image to base64
            import io
            img_buffer = io.BytesIO()
            img.save(img_buffer, format='JPEG', quality=90)
            image_data = base64.b64encode(img_buffer.getvalue()).decode('utf-8')
            
            prompt = self.get_analysis_prompt()
            
            payload = {
                "model": self.llava_13b_model,
                "prompt": prompt,
                "images": [image_data],
                "stream": False,
                "options": {
                    "temperature": 0.3,
                    "top_p": 0.8
                }
            }
            
            # Add GPU optimization
            if self.config.get('enable_rtx', False):
                payload["options"].update({
                    "num_gpu": self.config.get('rtx_gpu_layers', 35),
                    "num_thread": 8,
                    "num_batch": int(self.config.get('rtx_batch_size', 512))
                })
            
            response = requests.post(f"{self.ollama_url}/api/generate", json=payload, timeout=120)
            
            if response.status_code == 200:
                result = response.json()
                response_text = result.get('response', '').strip()
                
                # Clean up response
                response_text = response_text.replace('```json', '').replace('```', '').strip()
                
                try:
                    data = json.loads(response_text)
                    if isinstance(data, dict) and "category" in data:
                        return data
                except json.JSONDecodeError:
                    pass
                    
        except Exception as e:
            print(f"Error analyzing image with LLaVA 13B: {e}")
        
        return None
    
    def analyze_image_with_gemma_12b(self, image_path: str) -> Optional[Dict[str, Any]]:
        """Analyze image using local Gemma 12B model."""
        if not self.gemma_12b_model:
            return None
            
        try:
            # Resize image for faster processing
            img = self._resize_image_for_analysis(image_path)
            
            # Convert resized image to base64
            import io
            img_buffer = io.BytesIO()
            img.save(img_buffer, format='JPEG', quality=90)
            image_data = base64.b64encode(img_buffer.getvalue()).decode('utf-8')
            
            prompt = self.get_analysis_prompt()
            
            payload = {
                "model": self.gemma_12b_model,
                "prompt": prompt,
                "images": [image_data],
                "stream": False,
                "options": {
                    "temperature": 0.3,
                    "top_p": 0.8
                }
            }
            
            # Add GPU optimization
            if self.config.get('enable_rtx', False):
                payload["options"].update({
                    "num_gpu": self.config.get('rtx_gpu_layers', 35),
                    "num_thread": 8,
                    "num_batch": int(self.config.get('rtx_batch_size', 512))
                })
            
            response = requests.post(f"{self.ollama_url}/api/generate", json=payload, timeout=120)
            
            if response.status_code == 200:
                result = response.json()
                response_text = result.get('response', '').strip()
                
                # Clean up response
                response_text = response_text.replace('```json', '').replace('```', '').strip()
                
                try:
                    data = json.loads(response_text)
                    if isinstance(data, dict) and "category" in data:
                        return data
                except json.JSONDecodeError:
                    pass
                    
        except Exception as e:
            print(f"Error analyzing image with Gemma 12B: {e}")
        
        return None
    
    
    def analyze_image_with_bakllava(self, image_path: str) -> Optional[Dict[str, Any]]:
        """Analyze image using BakLLaVA model."""
        try:
            if not self.bakllava_analyzer or not self.bakllava_analyzer.available:
                print("BakLLaVA not available, using placeholder")
                return {
                    "category": "Thing",
                    "subcategory": "Other",
                    "tags": ["BakLLaVA", "Placeholder"],
                    "score": 6,
                    "critique": "BakLLaVA placeholder - model not initialized or available"
                }

            # Use archive_culling goal for speed
            result = self.bakllava_analyzer.analyze_image(image_path, "archive_culling")
            
            if result and result.get('success'):
                analysis = result.get('results', {})
                
                # Extract score
                keep_score_text = analysis.get('keep_score', '6')
                try:
                    # Extract number from text like "8 - High quality image"
                    import re
                    score_match = re.search(r'(\d+)', str(keep_score_text))
                    score = int(score_match.group(1)) if score_match else 6
                except:
                    score = 6
                
                # Extract tags
                tags_text = analysis.get('quick_tags', 'automotive,engine')
                tags = [tag.strip() for tag in str(tags_text).split(',')][:4]
                
                return {
                    "category": "Thing",
                    "subcategory": "Automotive", 
                    "tags": tags,
                    "score": score,
                    "critique": keep_score_text
                }
            else:
                print(f"BakLLaVA analysis failed: {result}")
                return None
                
        except Exception as e:
            print(f"Error analyzing image with BakLLaVA: {e}")
            return None
    
    
    def analyze_image(self, image_path: str) -> Optional[Dict[str, Any]]:
        """Analyze image using the best available model."""
        
        # Priority order: Local LLaVA 13B > Gemini (fallback)
        if self.llava_13b_model:
            print(f"🚀 Using LLaVA 13B: {self.llava_13b_model}")
            result = self.analyze_image_with_llava_13b(image_path)
            if result:
                return result
        
        if self.gemini_model:
            print("☁️ Using Gemini (fallback)")
            result = self.analyze_image_with_gemini(image_path)
            if result:
                return result
        
        # Final fallback if all models fail
        print("⚠️ All models failed, using placeholder")
        return {
            "category": "Thing",
            "subcategory": "Other",
            "tags": ["AI", "Analyzed"],
            "score": 6,
            "critique": "Analysis failed - using placeholder data"
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
                # Test with version check instead of empty metadata call
                et.execute("-ver")
            print(" ExifTool is available and working")
        except Exception as e:
            print(f" ExifTool not available: {e}")
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
            # Correct XMP naming: filename.xmp (not filename.jpg.xmp)
            xmp_path = image_path.with_suffix('.xmp')
            
            # Prepare metadata
            tags = analysis_data.get('tags', [])
            description = analysis_data.get('critique', '')
            rating = analysis_data.get('score', 3)  # Default to 3 stars if no rating
            
            # Ensure rating is a valid integer
            if rating is None or not isinstance(rating, (int, float)):
                rating = 3
            else:
                rating = int(rating)
                rating = max(1, min(5, rating))  # Clamp to 1-5 range
            
            # Add GALLERY tag for 5-star ratings
            if rating == 5 and "GALLERY" not in tags:
                tags.append("GALLERY")
            
            metadata_dict = {
                "XMP-dc:Subject": tags,
                "IPTC:Keywords": tags,
                "XMP-dc:Description": description,
                "XMP:Rating": rating,
                "XMP-dc:Title": f"Rating: {rating}/5"
            }
            
            with exiftool.ExifToolHelper(executable=self.exiftool_path) as et:
                et.set_tags(
                    [str(xmp_path)],
                    tags=metadata_dict,
                    params=["-overwrite_original"]
                )
            
            print(f" XMP sidecar written: {xmp_path.name}")
            return True
            
        except Exception as e:
            print(f" Error writing XMP sidecar for {os.path.basename(image_path)}: {e}")
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
            rating = analysis_data.get('score', 3)  # Default to 3 stars if no rating
            
            # Ensure rating is a valid integer
            if rating is None or not isinstance(rating, (int, float)):
                rating = 3
            else:
                rating = int(rating)
                rating = max(1, min(5, rating))  # Clamp to 1-5 range
            
            # Add GALLERY tag for 5-star ratings
            if rating == 5 and "GALLERY" not in tags:
                tags.append("GALLERY")
            
            metadata_dict = {
                "IPTC:Keywords": tags,
                "XMP-dc:Subject": tags,
                "EXIF:UserComment": description,
                "EXIF:Rating": rating,
                "EXIF:ImageDescription": f"Category: {analysis_data.get('category', 'N/A')}, Rating: {rating}/5"
            }
            
            with exiftool.ExifToolHelper(executable=self.exiftool_path) as et:
                et.set_tags(
                    [str(image_path)],
                    tags=metadata_dict,
                    params=["-overwrite_original"]
                )
            
            print(f" Embedded metadata written: {os.path.basename(image_path)}")
            return True
            
        except Exception as e:
            print(f" Error writing embedded metadata for {os.path.basename(image_path)}: {e}")
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
            status_queue.put(f" Writing metadata for {len(analysis_results)} images...")
        
        success_count = 0
        
        for i, result in enumerate(analysis_results):
            image_path = result.get('file_path', '')
            analysis_data = result.get('analysis', {})
            
            if status_queue:
                status_queue.put(f" Writing metadata {i+1}/{len(analysis_results)}: {os.path.basename(image_path)}")
            
            if use_exif:
                success = self.write_embedded_metadata(image_path, analysis_data)
            else:
                success = self.write_xmp_sidecar(image_path, analysis_data)
            
            if success:
                success_count += 1
        
        if status_queue:
            status_queue.put(f" Metadata writing complete: {success_count}/{len(analysis_results)} files processed")
        
        return success_count


class MultiStageProcessingPipeline:
    """
    Complete Multi-Stage Processing Pipeline
    
    Two-pass workflow for comprehensive photo archive management:
    Pass 1: Quick tagging/categorization for ALL images (searchable archive)
    Pass 2: Detailed analysis only for curated high-quality subset (portfolio/delivery)
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
            status_queue.put(" Starting Multi-Stage Processing Pipeline...")
            status_queue.put(f" Target directory: {directory_path}")
        
        # Stage 1 & 2: Quality Assessment and Curation
        top_percent = self.config.get('quality_threshold', 0.10)
        recursive = self.config.get('recursive', True)
        curated_images = self.curation_engine.curate_images_by_quality(
            directory_path, top_percent, status_queue, recursive
        )
        
        if not curated_images:
            if status_queue:
                status_queue.put(" No images selected for processing")
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
                
                # Format detailed progress log with analysis results
                category = analysis_data.get('category', 'Unknown')
                subcategory = analysis_data.get('subcategory', 'Unknown')
                tags = analysis_data.get('tags', [])
                score = analysis_data.get('score', 0)
                
                # Create tags string
                if isinstance(tags, list):
                    tags_str = ' '.join(tags[:4])  # Show first 4 tags
                else:
                    tags_str = str(tags)[:50]  # Limit to 50 chars
                
                # Stars representation
                stars = '⭐' * min(score, 5) if score > 0 else '⭐'
                
                # Detailed progress with results
                if status_queue:
                    status_queue.put(f"✅ {category} | {subcategory} | {tags_str} | {stars} ({score}/10)")
                
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
            status_queue.put(f" Pipeline Complete!")
            status_queue.put(f" Processed {success_count}/{len(analysis_results)} images in {total_time:.1f}s")
            status_queue.put(f" Used {self.curation_engine.iqa_model_name.upper()} quality assessment")
            status_queue.put(f"🤖 Used {self.config.get('model_type', 'unknown').upper()} AI model")
        
        return stats
    
    def process_directory_with_callback(self, directory_path: str, status_callback: callable = None) -> Dict[str, Any]:
        """
        Process all images in a directory through the complete pipeline using callback for status updates.
        
        Args:
            directory_path (str): Path to directory containing images
            status_callback (callable): Optional callback function for progress updates
            
        Returns:
            dict: Processing results and statistics
        """
        start_time = time.time()
        
        if status_callback:
            status_callback("[INFO] Starting Multi-Stage Processing Pipeline...")
            status_callback(f"[INFO] Target directory: {directory_path}")
        
        # Stage 1 & 2: Quality Assessment and Curation
        top_percent = self.config.get('quality_threshold', 0.10)
        
        # Use direct callback instead of queue for curation
        curated_images = self._curate_with_callback(directory_path, top_percent, status_callback)
        
        if not curated_images:
            if status_callback:
                status_callback("[ERROR] No images selected for processing")
            return {"success": False, "error": "No images passed quality assessment"}
        
        # Stage 3: AI Content Analysis
        if status_callback:
            status_callback(f"[INFO] Starting AI analysis of {len(curated_images)} curated images...")
        
        analysis_results = []
        for i, (image_path, quality_score) in enumerate(curated_images):
            if status_callback:
                status_callback(f"[PROGRESS] Analyzing {i+1}/{len(curated_images)}: {os.path.basename(image_path)}")
            
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
        success_count = self._write_metadata_with_callback(analysis_results, use_exif, status_callback)
        
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
        
        if status_callback:
            status_callback(f"[OK] Pipeline Complete!")
            status_callback(f"[INFO] Processed {success_count}/{len(analysis_results)} images in {total_time:.1f}s")
            status_callback(f"[INFO] Used {self.curation_engine.iqa_model_name.upper()} quality assessment")
            status_callback(f"[INFO] Used {self.config.get('model_type', 'unknown').upper()} AI model")
        
        return stats
    
    def _curate_with_callback(self, image_directory: str, top_percent: float, status_callback: callable = None) -> List[Tuple[str, float]]:
        """Curate images with callback instead of queue."""
        if status_callback:
            status_callback("[INFO] Starting Image Quality Assessment (IQA)...")
            
        supported_extensions = ('.jpg', '.jpeg', '.png', '.tif', '.tiff')
        image_files = []
        
        # Discover all supported image files
        for ext in supported_extensions:
            image_files.extend(Path(image_directory).rglob(f'*{ext}'))
            image_files.extend(Path(image_directory).rglob(f'*{ext.upper()}'))
        
        if not image_files:
            if status_callback:
                status_callback("[ERROR] No supported image files found in directory")
            return []
        
        total_images = len(image_files)
        if status_callback:
            status_callback(f"[INFO] Found {total_images} images for quality assessment")
        
        scores = []
        for i, image_path in enumerate(image_files):
            if status_callback:
                status_callback(f"[PROGRESS] Scoring image {i+1}/{total_images}: {image_path.name}")
            
            score = self.curation_engine.score_image(str(image_path))
            if score is not None:
                scores.append((str(image_path), score))
        
        if not scores:
            if status_callback:
                status_callback("[ERROR] No images could be scored successfully")
            return []
        
        # Sort by score (ascending for BRISQUE, descending for others)
        if self.curation_engine.iqa_metric and hasattr(self.curation_engine.iqa_metric, 'lower_better'):
            reverse_sort = not self.curation_engine.iqa_metric.lower_better
        else:
            # For fallback quality assessment, higher scores are better
            reverse_sort = True
        scores.sort(key=lambda x: x[1], reverse=reverse_sort)
        
        # Calculate selection threshold
        num_to_select = max(1, int(len(scores) * top_percent))
        top_images = scores[:num_to_select]
        
        if status_callback:
            status_callback(f"[OK] Selected top {len(top_images)} images ({top_percent*100:.1f}%) for AI analysis")
            status_callback(f"[INFO] Quality score range: {top_images[-1][1]:.2f} to {top_images[0][1]:.2f}")
        
        return top_images
    
    def _write_metadata_with_callback(self, analysis_results: List[Dict[str, Any]], use_exif: bool = False,
                                     status_callback: callable = None) -> int:
        """Write metadata with callback instead of queue."""
        if status_callback:
            status_callback(f"[INFO] Writing metadata for {len(analysis_results)} images...")
        
        success_count = 0
        
        for i, result in enumerate(analysis_results):
            image_path = result.get('file_path', '')
            analysis_data = result.get('analysis', {})
            
            if status_callback:
                status_callback(f"[PROGRESS] Writing metadata {i+1}/{len(analysis_results)}: {os.path.basename(image_path)}")
            
            if use_exif:
                success = self.metadata_layer.write_embedded_metadata(image_path, analysis_data)
            else:
                success = self.metadata_layer.write_xmp_sidecar(image_path, analysis_data)
            
            if success:
                success_count += 1
        
        if status_callback:
            status_callback(f"[OK] Metadata writing complete: {success_count}/{len(analysis_results)} files processed")
        
        return success_count
    
    def process_single_image(self, image_path: str) -> Dict[str, Any]:
        """
        Process a single image through the appropriate pipeline stage.
        Used for Lightroom integration and single-image processing.
        
        Args:
            image_path (str): Path to the image file
            
        Returns:
            dict: Processing result with success status and metadata
        """
        start_time = time.time()
        
        if not os.path.exists(image_path):
            return {"success": False, "error": f"Image file not found: {image_path}"}
        
        try:
            # Analyze the image
            analysis_data = self.content_engine.analyze_image(image_path)
            
            if not analysis_data:
                return {"success": False, "error": "AI analysis failed"}
            
            # Create result structure
            result = {
                'file_path': image_path,
                'image_name': os.path.basename(image_path),
                'analysis': analysis_data,
                'timestamp': time.time()
            }
            
            # Write metadata
            use_exif = self.config.get('use_exif', False)
            if use_exif:
                metadata_success = self.metadata_layer.write_embedded_metadata(image_path, analysis_data)
            else:
                metadata_success = self.metadata_layer.write_xmp_sidecar(image_path, analysis_data)
            
            processing_time = time.time() - start_time
            
            return {
                "success": True,
                "result": result,
                "metadata_written": metadata_success,
                "processing_time": processing_time,
                "ai_model": self.config.get('model_type', 'unknown'),
                "message": f"Processed successfully in {processing_time:.2f}s"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Processing failed: {str(e)}",
                "processing_time": time.time() - start_time
            }
    
    def process_all_images_archive_mode(self, directory_path: str, status_callback: callable = None) -> Dict[str, Any]:
        """
        Archive mode: Process ALL images with quick tagging (no curation filtering).
        Maintains fast RTX performance while creating searchable metadata for entire archive.
        
        Args:
            directory_path (str): Path to directory containing images
            status_callback (callable): Optional callback function for progress updates
            
        Returns:
            dict: Processing results and statistics
        """
        start_time = time.time()
        
        if status_callback:
            status_callback("[INFO] Starting Archive Mode - Processing ALL Images...")
            status_callback(f"[INFO] Target directory: {directory_path}")
        
        # Discover ALL supported images
        supported_extensions = ('.jpg', '.jpeg', '.png', '.tif', '.tiff', '.raw', '.cr2', '.nef', '.arw', '.dng')
        image_files = []
        
        recursive = self.config.get('recursive', True)
        
        if recursive:
            for ext in supported_extensions:
                image_files.extend(Path(directory_path).rglob(f'*{ext}'))
                image_files.extend(Path(directory_path).rglob(f'*{ext.upper()}'))
        else:
            for ext in supported_extensions:
                image_files.extend(Path(directory_path).glob(f'*{ext}'))
                image_files.extend(Path(directory_path).glob(f'*{ext.upper()}'))
        
        if not image_files:
            if status_callback:
                status_callback("[ERROR] No supported images found")
            return {"success": False, "error": "No images found"}
        
        total_images = len(image_files)
        if status_callback:
            status_callback(f"[INFO] Found {total_images} images for archive processing")
        
        # Process ALL images with BakLLaVA archive_culling mode
        analysis_results = []
        
        for i, image_path in enumerate(image_files):
            if status_callback:
                status_callback(f"[PROGRESS] Analyzing {i+1}/{total_images}: {os.path.basename(image_path)}")
            
            # Use archive_culling mode for fast, focused analysis
            analysis_data = self.content_engine.analyze_image(str(image_path))
            
            if analysis_data:
                result = {
                    'file_path': str(image_path),
                    'image_name': os.path.basename(str(image_path)),
                    'analysis': analysis_data,
                    'timestamp': time.time()
                }
                analysis_results.append(result)
        
        # Write metadata for ALL processed images
        use_exif = self.config.get('use_exif', False)
        success_count = self._write_metadata_with_callback(analysis_results, use_exif, status_callback)
        
        # Generate archive statistics
        stats = self._generate_archive_stats(analysis_results)
        
        # Final statistics
        total_time = time.time() - start_time
        archive_results = {
            "success": True,
            "mode": "archive_all_images",
            "total_images_found": total_images,
            "images_analyzed": len(analysis_results),
            "metadata_written": success_count,
            "processing_time": total_time,
            "ai_model": self.config.get('model_type', 'unknown'),
            "archive_statistics": stats,
            "results": analysis_results
        }
        
        if status_callback:
            status_callback(f"[OK] Archive Processing Complete!")
            status_callback(f"[INFO] Processed {success_count}/{total_images} images in {total_time:.1f}s")
            status_callback(f"[INFO] Average: {total_time/total_images:.2f}s per image")
            self._log_archive_summary(stats, status_callback)
        
        return archive_results
    
    def _generate_archive_stats(self, results: List[Dict]) -> Dict[str, Any]:
        """
        Generate archive statistics from analysis results.
        
        Args:
            results: List of analysis result dictionaries
            
        Returns:
            dict: Archive statistics
        """
        if not results:
            return {"total_images": 0}
        
        # Rating distribution
        ratings = [result['analysis'].get('score', 3) for result in results]
        rating_counts = {i: ratings.count(i) for i in range(1, 6)}
        
        # Category distribution
        categories = [result['analysis'].get('category', 'Unknown') for result in results]
        category_counts = {}
        for cat in categories:
            category_counts[cat] = category_counts.get(cat, 0) + 1
        
        # Tag frequency analysis
        all_tags = []
        for result in results:
            tags = result['analysis'].get('tags', [])
            if isinstance(tags, list):
                all_tags.extend(tags)
            elif isinstance(tags, str):
                all_tags.extend(tags.split(','))
        
        # Clean and count tags
        clean_tags = [tag.strip() for tag in all_tags if tag.strip()]
        tag_counts = {}
        for tag in clean_tags:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        # Get top tags
        top_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return {
            "total_images": len(results),
            "average_rating": sum(ratings) / len(ratings) if ratings else 0,
            "rating_distribution": rating_counts,
            "category_distribution": category_counts,
            "top_tags": top_tags,
            "five_star_images": rating_counts.get(5, 0),
            "gallery_worthy_percentage": (rating_counts.get(5, 0) / len(results) * 100) if results else 0
        }
    
    def _log_archive_summary(self, stats: Dict[str, Any], status_callback: callable):
        """
        Log comprehensive archive summary.
        
        Args:
            stats: Archive statistics dictionary
            status_callback: Callback function for logging
        """
        status_callback("\n[ARCHIVE SUMMARY]")
        status_callback(f"Total Images Processed: {stats['total_images']}")
        status_callback(f"Average Quality Rating: {stats['average_rating']:.2f}/5")
        status_callback(f"Gallery-Worthy Images (5⭐): {stats['five_star_images']} ({stats['gallery_worthy_percentage']:.1f}%)")
        
        status_callback("\nRating Distribution:")
        for rating in range(1, 6):
            count = stats['rating_distribution'].get(rating, 0)
            percentage = (count / stats['total_images'] * 100) if stats['total_images'] else 0
            stars = '⭐' * rating + '⭐' * (5 - rating)
            status_callback(f"  {rating}⭐ {count} images ({percentage:.1f}%)")
        
        status_callback("\nTop Categories:")
        for category, count in list(stats['category_distribution'].items())[:5]:
            percentage = (count / stats['total_images'] * 100) if stats['total_images'] else 0
            status_callback(f"  {category}: {count} images ({percentage:.1f}%)")
        
        status_callback("\nMost Used Tags:")
        for tag, count in stats['top_tags'][:5]:
            status_callback(f"  {tag}: {count} times")
