#!/usr/bin/env python3
"""
Direct Ollama HTTP Analyzer for AI Image Analyzer
Based on OBtagger's proven TypeScript implementation
Uses direct HTTP calls to Ollama API instead of PyLLMCore
"""

import json
import logging
import time
import base64
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from io import BytesIO
from PIL import Image
import requests

logger = logging.getLogger(__name__)

class OllamaDirectAnalyzer:
    """Direct HTTP-based Ollama analyzer using OBtagger's proven approach"""
    
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llava:latest", timeout: int = 30, gpu_load_profile: str = "⚡ Normal Demand (Balanced)"):
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.gpu_load_profile = gpu_load_profile
        
        # Adjust timeouts and delays based on GPU load profile
        self._configure_performance_settings(timeout, gpu_load_profile)
        
        self.available = False
        self.last_request_time = 0
        self.max_retries = 3
        
        # Test connection on initialization
        self._test_connection()
    
    def _configure_performance_settings(self, base_timeout: int, gpu_load_profile: str):
        """Configure timeout and delay settings based on GPU load profile"""
        if "🔥 Hurt My GPU" in gpu_load_profile:
            # Maximum speed - shortest timeouts and delays
            self.timeout = max(15, base_timeout // 2)  # Minimum 15s, half base timeout
            self.min_request_interval = 0.05  # 50ms between requests
            logger.info(f"GPU Load Profile: Maximum Speed - timeout={self.timeout}s, interval={self.min_request_interval}s")
        elif "🌿 Light Demand" in gpu_load_profile:
            # Background safe - longer timeouts and delays
            self.timeout = base_timeout * 2  # Double the timeout
            self.min_request_interval = 1.0  # 1 second between requests
            logger.info(f"GPU Load Profile: Background Safe - timeout={self.timeout}s, interval={self.min_request_interval}s")
        else:
            # Normal demand (balanced) - use base settings
            self.timeout = base_timeout
            self.min_request_interval = 0.1  # 100ms between requests
            logger.info(f"GPU Load Profile: Balanced - timeout={self.timeout}s, interval={self.min_request_interval}s")
    
    def _test_connection(self) -> bool:
        """Test connection to Ollama server and verify model availability"""
        try:
            logger.info(f"Testing Ollama connection at {self.base_url}")
            
            # Check if Ollama is running
            response = requests.get(f"{self.base_url}/api/tags", timeout=10)
            
            if response.status_code != 200:
                logger.error(f"Ollama server not accessible: HTTP {response.status_code}")
                return False
            
            tags = response.json()
            
            # Check if our model is available
            available_models = [model['name'] for model in tags.get('models', [])]
            model_exists = any(
                model_name == self.model or model_name.startswith(self.model.split(':')[0])
                for model_name in available_models
            )
            
            if not model_exists:
                logger.error(f"Model '{self.model}' not found. Available models: {available_models}")
                return False
            
            logger.info(f"Ollama connection successful - model '{self.model}' is available")
            self.available = True
            return True
            
        except Exception as e:
            logger.error(f"Ollama connection test failed: {e}")
            self.available = False
            return False
    
    def get_available_models(self) -> List[Dict[str, Any]]:
        """Get list of available models from Ollama"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=10)
            if response.status_code == 200:
                tags = response.json()
                return tags.get('models', [])
        except Exception as e:
            logger.error(f"Failed to get available models: {e}")
        return []
    
    def _rate_limit_delay(self):
        """Apply minimal delay for local Ollama processing"""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.min_request_interval:
            delay_time = self.min_request_interval - time_since_last_request
            logger.debug(f"Local processing delay: waiting {delay_time:.3f}s")
            time.sleep(delay_time)
        
        self.last_request_time = time.time()
    
    def _prepare_image(self, image_path: str, max_size: int = 1024) -> Optional[str]:
        """Prepare image for analysis by resizing and encoding to base64"""
        try:
            with Image.open(image_path) as img:
                # Convert to RGB if necessary
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Resize if too large
                if max(img.size) > max_size:
                    img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                    logger.debug(f"Resized image to {img.size} for analysis")
                
                # Convert to base64
                buffer = BytesIO()
                img.save(buffer, format='JPEG', quality=85)
                img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
                
                return img_base64
                
        except Exception as e:
            logger.error(f"Error preparing image {image_path}: {e}")
            return None
    
    def _parse_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """Parse Ollama response using OBtagger's robust parsing approach"""
        if not response_text or not response_text.strip():
            return None
        
        logger.debug(f"Parsing response (first 200 chars): {response_text[:200]}...")
        
        # First, try to extract JSON from markdown code blocks
        json_patterns = [
            r'```json\s*(.*?)\s*```',  # ```json ... ```
            r'```\s*(.*?)\s*```',      # ``` ... ```
            r'\{[^}]*\}',              # Simple JSON object
        ]
        
        for pattern in json_patterns:
            matches = re.findall(pattern, response_text, re.DOTALL)
            for match in matches:
                try:
                    # Clean up the extracted text
                    json_text = match.strip()
                    
                    # Try to parse as JSON
                    data = json.loads(json_text)
                    
                    # Validate required fields
                    if isinstance(data, dict) and 'category' in data:
                        logger.debug("Successfully parsed JSON response")
                        return data
                        
                except json.JSONDecodeError:
                    continue
        
        # If JSON parsing fails, fall back to text parsing
        logger.debug("JSON parsing failed, attempting text parsing")
        return self._parse_text_response(response_text)
    
    def _parse_text_response(self, response_text: str) -> Dict[str, Any]:
        """Parse natural language response as fallback"""
        lines = [line.strip() for line in response_text.split('\n') if line.strip()]
        
        result = {
            'category': 'Thing',
            'subcategory': 'Other',
            'tags': [],
            'score': 3,
            'critique': ''  # Add critique field for descriptions
        }
        
        # Look for structured patterns
        for line in lines:
            lower_line = line.lower()
            
            if 'category:' in lower_line:
                result['category'] = line.split(':', 1)[1].strip()
            elif 'subcategory:' in lower_line:
                result['subcategory'] = line.split(':', 1)[1].strip()
            elif any(word in lower_line for word in ['keywords:', 'tags:']):
                keyword_text = line.split(':', 1)[1].strip()
                result['tags'] = [tag.strip() for tag in keyword_text.split(',')]
            elif any(word in lower_line for word in ['score:', 'rating:']):
                try:
                    score_text = line.split(':', 1)[1].strip()
                    # Extract number from text like "4 out of 5" or "4/5"
                    score_match = re.search(r'(\d+)', score_text)
                    if score_match:
                        result['score'] = int(score_match.group(1))
                except (ValueError, IndexError):
                    pass
            elif any(word in lower_line for word in ['critique:', 'description:']):
                critique_text = line.split(':', 1)[1].strip()
                result['critique'] = critique_text
        
        # Generate basic tags if none found
        if not result['tags']:
            result['tags'] = self._extract_keywords_from_text(response_text)
        
        return result
    
    def _extract_keywords_from_text(self, text: str) -> List[str]:
        """Extract basic keywords from text"""
        # Simple keyword extraction
        words = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())
        
        # Filter out common words
        common_words = {
            'this', 'that', 'with', 'have', 'will', 'from', 'they', 'been', 
            'were', 'said', 'each', 'which', 'their', 'time', 'there', 'would',
            'could', 'should', 'about', 'after', 'before', 'image', 'photo'
        }
        
        keywords = [word for word in set(words) if word not in common_words]
        return keywords[:5]  # Return top 5 keywords
    
    def analyze_image(self, image_path: str, prompt: str) -> Optional[Dict[str, Any]]:
        """Analyze image using direct Ollama HTTP API"""
        if not self.available:
            return {"error": "Ollama not available"}
        
        # Prepare image
        base64_image = self._prepare_image(image_path)
        if not base64_image:
            return {"error": "Failed to prepare image"}
        
        # Retry loop with exponential backoff
        last_error = None
        
        for attempt in range(1, self.max_retries + 1):
            try:
                # Apply rate limiting
                self._rate_limit_delay()
                
                logger.info(f"Ollama API request attempt {attempt}/{self.max_retries}")
                
                # Create request payload
                payload = {
                    "model": self.model,
                    "prompt": prompt,
                    "images": [base64_image],
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "num_predict": 1000
                    }
                }
                
                # Make request to Ollama
                response = requests.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                    timeout=self.timeout
                )
                
                if response.status_code != 200:
                    raise Exception(f"HTTP {response.status_code}: {response.text}")
                
                result = response.json()
                
                if 'response' not in result:
                    raise Exception("No response field in Ollama result")
                
                # Parse the response
                parsed_result = self._parse_response(result['response'])
                
                if parsed_result:
                    logger.info(f"Ollama analysis successful on attempt {attempt}")
                    return parsed_result
                else:
                    raise Exception("Failed to parse Ollama response")
                
            except Exception as e:
                last_error = e
                logger.warning(f"Ollama request attempt {attempt} failed: {e}")
                
                if attempt < self.max_retries:
                    # Exponential backoff
                    delay = min(2 ** (attempt - 1), 10)  # Max 10 seconds
                    logger.info(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
        
        # All retries failed
        error_msg = f"Ollama analysis failed after {self.max_retries} attempts: {last_error}"
        logger.error(error_msg)
        return {"error": error_msg}

    def test_with_simple_prompt(self, image_path: str) -> bool:
        """Test the analyzer with a simple prompt to verify it's working"""
        simple_prompt = """Look at this image and respond with JSON:
{"category": "Thing", "subcategory": "Test", "tags": ["test", "working"], "score": 3}"""
        
        result = self.analyze_image(image_path, simple_prompt)
        return result is not None and 'error' not in result