# ----------------------------------------------------------------------
#  AI Image Analyzer Web GUI
#  
#  A Flask web application for analyzing images with LLaVA AI model
#  Designed for easy sharing and deployment
# ----------------------------------------------------------------------

from flask import Flask, render_template, request, jsonify, send_from_directory, session
from flask_socketio import SocketIO, emit
import os
import json
import base64
import requests
import threading
import time
from pathlib import Path
from PIL import Image
import piexif
import math
from werkzeug.utils import secure_filename
import uuid

# Import the new multi-stage pipeline
import sys
from pathlib import Path

# Add parent directory to Python path
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

try:
    from pipeline_core import MultiStageProcessingPipeline, ImageCurationEngine
    MULTISTAGE_AVAILABLE = True
    print("✅ Multi-stage pipeline imported successfully")
except ImportError as e:
    MULTISTAGE_AVAILABLE = False
    print(f"⚠️  Multi-stage pipeline not available: {e}")

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
socketio = SocketIO(app, cors_allowed_origins="*")

# Configuration
CONFIG = {
    'ollama_url': 'http://localhost:11434',  # Standard Ollama port
    'model': 'llava:13b',
    'models_path': 'J:\\models',  # Updated to match your model location
    'max_workers': 2,
    'supported_formats': ['.jpg', '.jpeg', '.tif', '.tiff', '.png', '.webp'],
    'model_type': 'gemini',  # 'ollama', 'gemini', or 'bakllava'
    'google_api_key': '',  # Your Google API key for cloud usage
    'available_local_models': ['llava:13b', 'llava:7b', 'llava:34b'],  # Ollama models
    'available_bakllava_models': ['BakLLaVA-1-Q4_K_M.gguf'],  # BakLLaVA models
    'gemini_model': 'gemini-2.0-flash-exp',
    'generate_xmp': True,  # Generate XMP sidecar files instead of EXIF
    'enable_gallery_critique': False,  # Enable gallery critique for all images
    'critique_threshold': 5,  # Score threshold for critique when gallery critique is disabled
    'goal_type': 'archive_culling',  # Default goal: archive_culling, gallery_selection, catalog_organization
    'test_mode': False,  # Process only first 20 images for testing
    'prompt_profile': 'professional_art_critic',  # Default prompt profile
    # Multi-stage pipeline settings
    'use_multistage_pipeline': False,  # Enable the multi-stage IQA pipeline
    'quality_threshold': 0.10,  # Top percentage of images to process (0.10 = top 10%)
    'iqa_model': 'brisque',  # IQA model: 'brisque', 'niqe', 'musiq', 'topiq'
    'use_exif': False  # Write to EXIF or XMP sidecar
}

# Global variables for processing state
processing_jobs = {}
active_sessions = set()

# Categories and tags configuration - Original Professional Schema
DEFAULT_CATEGORIES = ["Person", "Place", "Thing"]
DEFAULT_SUB_CATEGORIES = ["candid", "posed", "man-made", "landscape", "animal", "object", 
                         "house", "interior", "exterior", "nature", "scenery", "other"]
DEFAULT_TAGS = ["artificial_light", "natural_light", "monochrome", "duplicate", "large", 
               "small", "dark", "light", "heavy", "face", "abstract", "couple", "action", 
               "minimalist", "blurry", "evocative", "disturbing", "boring", "wedding", 
               "bride", "groom", "love", "calm", "busy", "automotive"]

# Prompt Profiles for different analysis styles
PROMPT_PROFILES = {
    'professional_art_critic': {
        'name': 'Professional Art Critic',
        'description': 'Gallery curator perspective focusing on artistic merit and technical excellence',
        'persona': 'You are a professional art critic and gallery curator with 25 years of experience, evaluating photographs for potential inclusion in a fine art exhibition.',
        'criteria': [
            'Technical Excellence: Focus, exposure, composition, color/lighting',
            'Artistic Merit: Creativity, emotional impact, visual storytelling', 
            'Commercial Appeal: Marketability, broad audience appeal',
            'Uniqueness: What sets this image apart from typical photography'
        ]
    },
    'family_archivist': {
        'name': 'Family Memory Keeper',
        'description': 'Personal photo organizer focused on emotional value and family memories',
        'persona': 'You are a professional family photo organizer and memory keeper, helping families preserve their most meaningful moments.',
        'criteria': [
            'Emotional Value: Sentimental importance and family connections',
            'Clarity & Quality: Technical aspects that preserve memories well',
            'Historical Significance: Moments that tell the family story',
            'Archival Worth: Long-term value for family heritage'
        ]
    },
    'commercial_photographer': {
        'name': 'Commercial Photographer',
        'description': 'Industry professional evaluating marketability and client appeal',
        'persona': 'You are an experienced commercial photographer and photo editor evaluating images for client delivery and portfolio inclusion.',
        'criteria': [
            'Client Deliverability: Professional quality and usability',
            'Technical Standards: Meeting industry quality benchmarks',
            'Market Appeal: Commercial viability and audience attraction',
            'Portfolio Worthy: Represents high professional standards'
        ]
    },
    'social_media_curator': {
        'name': 'Social Media Expert',
        'description': 'Digital content creator focused on engagement and shareability',
        'persona': 'You are a social media content strategist and digital marketing expert, evaluating images for online engagement and viral potential.',
        'criteria': [
            'Visual Impact: Immediate attention-grabbing qualities',
            'Engagement Potential: Likely to generate likes, shares, comments',
            'Platform Suitability: Works well across social platforms',
            'Storytelling Power: Conveys clear message or emotion quickly'
        ]
    },
    'documentary_journalist': {
        'name': 'Documentary Journalist',
        'description': 'Photojournalist perspective emphasizing story and authenticity',
        'persona': 'You are an award-winning photojournalist and documentary photographer, evaluating images for their storytelling power and journalistic value.',
        'criteria': [
            'Storytelling Strength: Narrative power and emotional truth',
            'Authenticity: Genuine moments without artificial staging',
            'Historical Value: Documents important events or conditions',
            'Journalistic Merit: Newsworthy or socially significant content'
        ]
    },
    'travel_blogger': {
        'name': 'Travel Content Creator',
        'description': 'Travel photographer focused on destination appeal and wanderlust',
        'persona': 'You are a successful travel blogger and destination photographer, evaluating images for their ability to inspire wanderlust and showcase locations.',
        'criteria': [
            'Destination Appeal: Makes viewers want to visit the location',
            'Cultural Authenticity: Represents place and people genuinely',
            'Visual Wanderlust: Evokes desire to travel and explore',
            'Content Versatility: Useful across multiple travel platforms'
        ]
    }
}

class ImageAnalyzer:
    def __init__(self, session_id):
        self.session_id = session_id
        self.is_running = False
        self.current_image = None
        self.total_images = 0
        self.processed_count = 0
        self.results = []
        
    def get_analysis_prompt(self, profile_key=None):
        """Generate analysis prompt based on selected profile"""
        if not profile_key:
            profile_key = CONFIG.get('prompt_profile', 'professional_art_critic')
            
        profile = PROMPT_PROFILES.get(profile_key, PROMPT_PROFILES['professional_art_critic'])
        
        # Create critique section based on configuration
        enable_critique = CONFIG['enable_gallery_critique']
        critique_section = ""
        if enable_critique:
            critique_section = f"""
            
            CRITIQUE REQUIREMENTS:
            - 2-3 sentences maximum from the {profile['name']} perspective
            - Focus on what makes the image succeed or fail according to your criteria
            - Mention specific technical or artistic elements relevant to your expertise
            - Be constructive but honest
            """
        
        # Build criteria list
        criteria_text = "\n".join([f"{i+1}. {criterion}" for i, criterion in enumerate(profile['criteria'])])
        
        # Build the JSON template
        json_template = {
            "category": "chosen_category",
            "subcategory": "chosen_subcategory", 
            "tags": ["tag1", "tag2", "tag3"],
            "score": 4
        }
        
        if enable_critique:
            json_template["critique"] = f"Professional critique from {profile['name']} perspective focusing on your specific criteria."
        
        json_str = json.dumps(json_template, indent=2)
        
        prompt = f"""
        {profile['persona']}
        
        ANALYSIS CRITERIA:
        {criteria_text}
        
        CLASSIFICATION (select ONE from each category):
        CATEGORIES: {', '.join(DEFAULT_CATEGORIES)}
        SUB_CATEGORIES: {', '.join(DEFAULT_SUB_CATEGORIES)}
        TAGS: {', '.join(DEFAULT_TAGS)} (select 2-4 most relevant)
        
        SCORING GUIDE (1-5 star rating from {profile['name']} perspective):
        1 star: Poor (fails to meet basic standards for this evaluation type)
        2 stars: Below Average (basic competence, limited value for intended purpose)
        3 stars: Average (meets standard expectations for this type of image)
        4 stars: Above Average (strong quality and purpose alignment)
        5 stars: Exceptional (outstanding example that excels in all criteria)
        {critique_section}
        
        RESPOND WITH VALID JSON ONLY:
        {json_str}
        """
        
        return prompt

    def analyze_image(self, image_path):
        """Analyze image using the selected model"""
        try:
            if CONFIG['model_type'] == 'ollama':
                return self.analyze_with_ollama_model(image_path)
            elif CONFIG['model_type'] == 'gemini':
                return self.analyze_with_gemini_model(image_path)
            elif CONFIG['model_type'] == 'bakllava':
                return self.analyze_with_bakllava_model(image_path)
        except Exception as e:
            print(f"Error analyzing image: {e}")
            return None

    def analyze_with_ollama_model(self, image_path):
        """Analyze image using Ollama LLaVA model"""
        try:
            # Convert image to base64
            with open(image_path, 'rb') as img_file:
                image_data = base64.b64encode(img_file.read()).decode('utf-8')
            
            prompt = self.get_analysis_prompt()
            
            payload = {
                "model": CONFIG['model'],
                "prompt": prompt,
                "images": [image_data],
                "stream": False
            }
            
            response = requests.post(f"{CONFIG['ollama_url']}/api/generate", json=payload, timeout=120)
            
            if response.status_code == 200:
                result = response.json()
                response_text = result.get('response', '').strip()
                
                # Clean up response text
                response_text = response_text.replace('```json', '').replace('```', '').strip()
                
                try:
                    data = json.loads(response_text)
                    if all(k in data for k in ["category", "subcategory", "tags", "score"]):
                        return data
                    else:
                        return None
                except json.JSONDecodeError:
                    return None
            else:
                return None
                
        except Exception as e:
            print(f"Error analyzing image with Ollama: {e}")
            return None

    def analyze_with_bakllava_model(self, image_path):
        """Analyze image using BakLLaVA model"""
        try:
            # Import necessary modules for BakLLaVA
            import sys
            import os
            scripts_path = os.path.join(os.path.dirname(__file__), '..', 'scripts')
            if scripts_path not in sys.path:
                sys.path.insert(0, scripts_path)
            
            print(f"🔍 Attempting BakLLaVA import from: {scripts_path}")
            
            # Try to import BakLLaVA analyzer
            try:
                from bakllava_simple import SimpleBakLLaVAAnalyzer
                print("✅ BakLLaVA import successful")
                
                analyzer = SimpleBakLLaVAAnalyzer()
                print(f"🔍 BakLLaVA analyzer created, model available: {analyzer.model_available}")
                
                # Get the raw BakLLaVA result
                bakllava_result = analyzer.analyze_image(str(image_path))
                print(f"📊 BakLLaVA raw result: {bakllava_result}")
                
                if bakllava_result and bakllava_result.get('success'):
                    # Convert BakLLaVA format to our expected format
                    results = bakllava_result.get('results', {})
                    
                    # Map BakLLaVA results to our format
                    if 'keep_score' in results:
                        # Extract score from keep_score text
                        score_text = results['keep_score']
                        try:
                            score = int(score_text.split()[0]) if score_text else 6
                        except:
                            score = 6
                    else:
                        score = 6
                    
                    # Extract tags from quick_tags
                    tags = []
                    if 'quick_tags' in results:
                        tags = [tag.strip() for tag in results['quick_tags'].split(',')][:4]
                    
                    converted_result = {
                        "category": "Thing",  # Default category
                        "subcategory": "Other",  # Default subcategory
                        "tags": tags or ["BakLLaVA", "Analyzed"],
                        "score": score,
                        "critique": results.get('keep_score', 'BakLLaVA analysis complete')
                    }
                    print(f"✅ BakLLaVA converted result: {converted_result}")
                    return converted_result
                else:
                    print(f"❌ BakLLaVA analysis failed: {bakllava_result.get('error', 'Unknown error')}")
                    
            except ImportError as e:
                print(f"❌ BakLLaVA analyzer import failed: {e}")
            except Exception as e:
                print(f"❌ BakLLaVA analyzer exception: {e}")
                
            # Fallback placeholder response
            placeholder = {
                "category": "Thing",
                "subcategory": "Other", 
                "tags": ["BakLLaVA", "Placeholder"],
                "score": 6,
                "critique": "BakLLaVA placeholder result - actual model ready for GPU processing"
            }
            print(f"🔄 Using BakLLaVA placeholder: {placeholder}")
            return placeholder
                
        except Exception as e:
            print(f"💥 Error analyzing image with BakLLaVA: {e}")
            return None
            
    def analyze_with_gemini_model(self, image_path):
        """Analyze image using Gemini model"""
        try:
            import google.genai as genai
            
            if not CONFIG['google_api_key']:
                print("Google API key not provided")
                return None
                
            genai.configure(api_key=CONFIG['google_api_key'])
            model = genai.GenerativeModel(CONFIG['gemini_model'])
            
            # Load and prepare image
            img = Image.open(image_path)
            
            # Use dynamic prompt based on selected profile
            prompt = self.get_analysis_prompt()
            
            response = model.generate_content(
                [prompt, img],
                generation_config=genai.GenerationConfig(
                    temperature=0.3,
                    top_p=0.8,
                    max_output_tokens=500
                )
            )
            
            # Clean up response text
            response_text = response.text.replace('```json', '').replace('```', '').strip()
            
            try:
                data = json.loads(response_text)
                
                # Validate required fields
                required_keys = ["category", "subcategory", "tags", "score"]
                if CONFIG['enable_gallery_critique']:
                    required_keys.append("critique")
                    
                if all(k in data for k in required_keys):
                    return data
                else:
                    return None
            except json.JSONDecodeError:
                return None
                
        except Exception as e:
            print(f"Error with Gemini model: {e}")
            return None
    
    def write_metadata(self, image_path, analysis_data):
        """Write analysis data to metadata based on user-selected mode"""
        try:
            metadata_options = CONFIG.get('metadata_options', {'mode': 'xmp', 'handling': 'append'})
            mode = metadata_options['mode']
            
            success = True
            if mode == 'xmp':
                success = self.write_xmp_sidecar(image_path, analysis_data)
            elif mode == 'exif':
                success = self.write_exif_data(image_path, analysis_data, metadata_options)
            elif mode == 'both':
                xmp_success = self.write_xmp_sidecar(image_path, analysis_data)
                exif_success = self.write_exif_data(image_path, analysis_data, metadata_options)
                success = xmp_success and exif_success
            
            return success
        except Exception as e:
            print(f"Error writing metadata: {e}")
            return False
    
    def write_xmp_sidecar(self, image_path, analysis_data):
        """Write analysis data to XMP sidecar file"""
        try:
            image_path = Path(image_path)
            xmp_path = image_path.with_suffix(image_path.suffix + '.xmp')
            
            # Calculate star rating
            score = analysis_data.get('score', 0)
            star_rating = math.ceil(score / 2) if score >= 1 else 1
            
            # Add GALLERY tag for 5-star ratings
            tags_list = analysis_data.get('tags', [])
            if star_rating == 5 and "GALLERY" not in tags_list:
                tags_list.append("GALLERY")
            
            # Prepare XMP content
            critique = analysis_data.get('critique', 'N/A')
            tags_str = ", ".join(tags_list)
            category_desc = f"Category: {analysis_data['category']}, Subcategory: {analysis_data['subcategory']}"
            
            # Create XMP content
            xmp_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/" x:xmptk="AI Image Analyzer">
<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
<rdf:Description rdf:about=""
    xmlns:xmp="http://ns.adobe.com/xap/1.0/"
    xmlns:dc="http://purl.org/dc/elements/1.1/"
    xmlns:lr="http://ns.adobe.com/lightroom/1.0/"
    xmp:Rating="{star_rating}"
    dc:description="{category_desc}"
    dc:subject="{tags_str}"
    lr:hierarchicalSubject="{tags_str}">
    <dc:title>
        <rdf:Alt>
            <rdf:li xml:lang="x-default">AI Image Analysis - {star_rating} Stars</rdf:li>
        </rdf:Alt>
    </dc:title>
    <dc:creator>
        <rdf:Seq>
            <rdf:li>AI Image Analyzer</rdf:li>
        </rdf:Seq>
    </dc:creator>
    <dc:rights>
        <rdf:Alt>
            <rdf:li xml:lang="x-default">Critique: {critique}</rdf:li>
        </rdf:Alt>
    </dc:rights>
</rdf:Description>
</rdf:RDF>
</x:xmpmeta>"""
            
            # Write XMP file
            with open(xmp_path, 'w', encoding='utf-8') as f:
                f.write(xmp_content)
            
            print(f"✅ XMP sidecar written: {xmp_path.name}")
            return True
            
        except Exception as e:
            print(f"Error writing XMP sidecar: {e}")
            return False
    
    def write_exif_data(self, image_path, analysis_data, metadata_options=None):
        """Write analysis data to EXIF metadata with smart field mapping"""
        try:
            if not metadata_options:
                metadata_options = CONFIG.get('metadata_options', {'mode': 'exif', 'handling': 'append'})
            
            # Load existing EXIF data
            try:
                exif_dict = piexif.load(str(image_path))
            except piexif.InvalidImageDataError:
                exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}

            # Calculate star rating from 1-10 scale to 1-5 stars  
            score = analysis_data.get('score', 0)
            if score <= 10:  # If score is 1-10 scale, convert to 1-5 stars
                star_rating = max(1, min(5, math.ceil(score / 2)))
            else:  # If score is already 1-5, use directly
                star_rating = max(1, min(5, score))
            
            # Handle existing rating based on metadata handling mode
            handling_mode = metadata_options.get('handling', 'append')
            existing_rating = exif_dict.get("0th", {}).get(piexif.ImageIFD.Rating)
            
            if handling_mode == 'append' and existing_rating in [4, 5]:
                final_rating = existing_rating  # Preserve high ratings
            else:
                final_rating = star_rating
                
            # Handle tags with append/replace logic
            tags_list = analysis_data.get('tags', [])
            if final_rating == 5 and "GALLERY" not in tags_list:
                tags_list.append("GALLERY")
                analysis_data['tags'] = tags_list

            # Set EXIF data
            exif_dict["0th"][piexif.ImageIFD.Rating] = final_rating
            
            # Smart field mapping for web/SEO optimization
            web_opt = metadata_options.get('webOptimization', {})
            
            # Map AI description to Alt Text (ImageDescription) for SEO
            if web_opt.get('mapAltText', True):
                if handling_mode == 'append':
                    existing_desc = exif_dict.get("0th", {}).get(piexif.ImageIFD.ImageDescription, b'').decode('utf-8', errors='ignore')
                    if existing_desc:
                        description = f"{existing_desc} | AI: Category {analysis_data['category']}, {analysis_data['subcategory']}"
                    else:
                        description = f"Category: {analysis_data['category']}, Subcategory: {analysis_data['subcategory']}"
                else:
                    description = f"Category: {analysis_data['category']}, Subcategory: {analysis_data['subcategory']}"
                    
                exif_dict["0th"][piexif.ImageIFD.ImageDescription] = description.encode('utf-8')
            
            # Map AI tags to Keywords (via UserComment - EXIF doesn't have native keywords field)
            if web_opt.get('mapKeywords', True):
                tags_str = ", ".join(tags_list)
                
                if handling_mode == 'append':
                    existing_comment = exif_dict.get("Exif", {}).get(piexif.ExifIFD.UserComment, b'').decode('utf-8', errors='ignore')
                    if existing_comment and not existing_comment.startswith('Critique:'):
                        base_comment = existing_comment
                    else:
                        base_comment = ""
                else:
                    base_comment = ""
                
                # Build comment with critique and tags
                critique = analysis_data.get('critique', 'N/A')
                if web_opt.get('mapCaption', True):
                    full_comment = f"Critique: {critique} | Rating: {final_rating}/5 stars | Tags: {tags_str}"
                else:
                    full_comment = f"Rating: {final_rating}/5 stars | Tags: {tags_str}"
                
                if base_comment:
                    full_comment = f"{base_comment} | AI: {full_comment}"
                    
                exif_dict["Exif"][piexif.ExifIFD.UserComment] = full_comment.encode('utf-8')
            
            # Save EXIF data
            exif_bytes = piexif.dump(exif_dict)
            piexif.insert(exif_bytes, str(image_path))
            
            print(f"✅ EXIF metadata written: {image_path}")
            return True
            
        except Exception as e:
            print(f"Error writing EXIF data: {e}")
            return False
    
    def process_directory(self, directory_path, write_exif=True):
        """Process all images in directory"""
        self.is_running = True
        directory = Path(directory_path)
        
        # Get all image files
        image_files = []
        for ext in CONFIG['supported_formats']:
            image_files.extend(directory.rglob(f'*{ext}'))
            image_files.extend(directory.rglob(f'*{ext.upper()}'))
        
        self.total_images = len(image_files)
        self.processed_count = 0
        self.results = []
        
        # Emit initial status
        initial_data = {
            'total': self.total_images,
            'processed': 0,
            'current_image': '',
            'status': 'Starting...'
        }
        print(f"🔔 Emitting progress_update: {initial_data}")
        socketio.emit('progress_update', initial_data, room=self.session_id)
        
        for i, image_path in enumerate(image_files):
            if not self.is_running:
                break
                
            self.current_image = image_path.name
            
            # Emit progress update
            progress_data = {
                'total': self.total_images,
                'processed': i,
                'current_image': self.current_image,
                'status': f'Analyzing {self.current_image}...'
            }
            print(f"📈 Emitting progress [{i+1}/{self.total_images}]: {self.current_image}")
            socketio.emit('progress_update', progress_data, room=self.session_id)
            
            # Analyze image
            analysis_data = self.analyze_image(image_path)
            
            if analysis_data:
                # Write metadata if requested
                if write_exif:
                    metadata_success = self.write_metadata(image_path, analysis_data)
                else:
                    metadata_success = True
                
                # Store result
                result = {
                    'image_path': str(image_path),
                    'image_name': image_path.name,
                    'analysis': analysis_data,
                    'metadata_written': metadata_success,
                    'timestamp': time.time()
                }
                self.results.append(result)
                
                # Emit result
                socketio.emit('image_processed', {
                    'session_id': self.session_id,
                    'result': result
                }, room=self.session_id)
            
            self.processed_count = i + 1
        
        self.is_running = False
        
        # Emit completion
        socketio.emit('processing_complete', {
            'session_id': self.session_id,
            'total_processed': self.processed_count,
            'results': self.results
        }, room=self.session_id)

@app.route('/')
def index():
    """Main page"""
    session_id = session.get('session_id', str(uuid.uuid4()))
    session['session_id'] = session_id
    return render_template('index.html', session_id=session_id)

@app.route('/api/start_processing', methods=['POST'])
def start_processing():
    """Start processing images in directory"""
    data = request.get_json()
    directory_path = data.get('directory_path')
    model_type = data.get('model_type', 'gemini')
    api_key = data.get('api_key', '')
    metadata_options = data.get('metadata_options', {'mode': 'xmp', 'handling': 'append'})
    
    # Update global config with user selection
    CONFIG['model_type'] = model_type
    CONFIG['metadata_options'] = metadata_options
    if api_key:
        CONFIG['google_api_key'] = api_key
    
    if not directory_path or not os.path.exists(directory_path):
        return jsonify({'success': False, 'error': 'Invalid directory path'})
    
    session_id = session.get('session_id', str(uuid.uuid4()))
    session['session_id'] = session_id
    
    # Create analyzer instance
    analyzer = ImageAnalyzer(session_id)
    processing_jobs[session_id] = analyzer
    
    # Determine write metadata based on mode
    write_metadata = metadata_options['mode'] != 'none'
    
    # Start processing in background thread
    thread = threading.Thread(target=analyzer.process_directory, args=(directory_path, write_metadata))
    thread.daemon = True
    thread.start()
    
    return jsonify({'success': True, 'session_id': session_id})

@app.route('/api/start_multistage_processing', methods=['POST'])
def start_multistage_processing():
    """Start multi-stage pipeline processing with IQA curation"""
    if not MULTISTAGE_AVAILABLE:
        return jsonify({'success': False, 'error': 'Multi-stage pipeline not available. Please check dependencies.'})
        
    data = request.get_json()
    directory_path = data.get('directory_path')
    model_type = data.get('model_type', 'gemini')
    api_key = data.get('api_key', '')
    quality_threshold = data.get('quality_threshold', 0.10)
    iqa_model = data.get('iqa_model', 'brisque')
    use_exif = data.get('use_exif', False)
    
    if not directory_path or not os.path.exists(directory_path):
        return jsonify({'success': False, 'error': 'Invalid directory path'})
    
    session_id = session.get('session_id', str(uuid.uuid4()))
    session['session_id'] = session_id
    
    # Prepare configuration for multi-stage pipeline
    pipeline_config = {
        'model_type': model_type,
        'google_api_key': api_key,
        'gemini_model': CONFIG.get('gemini_model', 'gemini-2.0-flash-exp'),
        'ollama_url': CONFIG.get('ollama_url'),
        'model': CONFIG.get('model', 'llava:13b'),
        'enable_gallery_critique': CONFIG.get('enable_gallery_critique', False),
        'prompt_profile': CONFIG.get('prompt_profile', 'professional_art_critic'),
        'quality_threshold': quality_threshold,
        'iqa_model': iqa_model,
        'use_exif': use_exif
    }
    
    def run_multistage_pipeline():
        """Run the multi-stage processing pipeline in background"""
        try:
            # Create status queue for WebSocket updates
            import queue
            status_queue = queue.Queue()
            
            # Create and run pipeline
            pipeline = MultiStageProcessingPipeline(pipeline_config)
            
            # Process directory with status updates
            def emit_status_updates():
                while True:
                    try:
                        message = status_queue.get(timeout=1)
                        if message == "DONE":
                            break
                        socketio.emit('progress_update', {
                            'status': message,
                            'session_id': session_id
                        })
                    except:
                        continue
            
            # Start status update thread
            status_thread = threading.Thread(target=emit_status_updates, daemon=True)
            status_thread.start()
            
            # Run the pipeline
            results = pipeline.process_directory(directory_path, status_queue)
            status_queue.put("DONE")
            
            # Store results for session
            processing_jobs[session_id] = type('Results', (), {
                'results': results.get('results', []),
                'is_running': False,
                'processed_count': results.get('images_analyzed', 0),
                'total_images': results.get('total_images_found', 0)
            })()
            
            # Emit completion
            socketio.emit('processing_complete', {
                'session_id': session_id,
                'results': results,
                'message': f"Multi-stage pipeline complete! Processed {results.get('images_analyzed', 0)} images."
            })
            
        except Exception as e:
            print(f"Multi-stage pipeline error: {e}")
            socketio.emit('processing_error', {
                'session_id': session_id,
                'error': str(e)
            })
    
    # Start processing in background thread
    thread = threading.Thread(target=run_multistage_pipeline, daemon=True)
    thread.start()
    
    return jsonify({
        'success': True, 
        'session_id': session_id,
        'message': 'Multi-stage processing started with IQA curation'
    })

@app.route('/api/stop_processing', methods=['POST'])
def stop_processing():
    """Stop current processing job"""
    session_id = session.get('session_id')
    
    if session_id in processing_jobs:
        processing_jobs[session_id].is_running = False
        return jsonify({'success': True})
    
    return jsonify({'success': False, 'error': 'No active processing job'})

@app.route('/api/model_status')
def model_status():
    """Check if Ollama model is available"""
    try:
        response = requests.get(f"{CONFIG['ollama_url']}/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get('models', [])
            llava_available = any(CONFIG['model'] in model.get('name', '') for model in models)
            return jsonify({
                'success': True,
                'ollama_running': True,
                'llava_available': llava_available,
                'models': [model.get('name') for model in models]
            })
    except requests.exceptions.RequestException:
        pass
    
    return jsonify({
        'success': False,
        'ollama_running': False,
        'llava_available': False,
        'models': []
    })

@app.route('/api/download_model', methods=['POST'])
def download_model():
    """Download and setup a local model"""
    data = request.get_json()
    model_name = data.get('model_name', 'llava:13b')
    
    try:
        # Use Ollama API to pull the model
        response = requests.post(f"{CONFIG['ollama_url']}/api/pull", 
                               json={"name": model_name}, 
                               timeout=300)
        
        if response.status_code == 200:
            return jsonify({'success': True, 'message': f'Model {model_name} downloaded successfully'})
        else:
            return jsonify({'success': False, 'error': 'Failed to download model'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/prompt_profiles')
def get_prompt_profiles():
    """Get available prompt profiles"""
    profiles = {}
    for key, profile in PROMPT_PROFILES.items():
        profiles[key] = {
            'name': profile['name'],
            'description': profile['description']
        }
    return jsonify({
        'profiles': profiles,
        'current': CONFIG.get('prompt_profile', 'professional_art_critic')
    })

@app.route('/api/set_prompt_profile', methods=['POST'])
def set_prompt_profile():
    """Set the active prompt profile"""
    data = request.get_json()
    profile_key = data.get('profile_key')
    
    if profile_key in PROMPT_PROFILES:
        CONFIG['prompt_profile'] = profile_key
        return jsonify({'success': True, 'profile': profile_key})
    else:
        return jsonify({'success': False, 'error': 'Invalid profile key'})

@app.route('/api/pipeline_config')
def get_pipeline_config():
    """Get pipeline configuration options"""
    return jsonify({
        'iqa_models': ['brisque', 'niqe', 'musiq', 'topiq'],
        'current_iqa_model': CONFIG.get('iqa_model', 'brisque'),
        'quality_threshold': CONFIG.get('quality_threshold', 0.10),
        'use_multistage': CONFIG.get('use_multistage_pipeline', False),
        'supported_thresholds': [0.05, 0.10, 0.15, 0.20, 0.25, 0.50]
    })

@app.route('/api/set_pipeline_config', methods=['POST'])
def set_pipeline_config():
    """Update pipeline configuration"""
    data = request.get_json()
    
    if 'iqa_model' in data:
        CONFIG['iqa_model'] = data['iqa_model']
    if 'quality_threshold' in data:
        CONFIG['quality_threshold'] = float(data['quality_threshold'])
    if 'use_multistage' in data:
        CONFIG['use_multistage_pipeline'] = bool(data['use_multistage'])
    
    return jsonify({
        'success': True,
        'config': {
            'iqa_model': CONFIG.get('iqa_model'),
            'quality_threshold': CONFIG.get('quality_threshold'),
            'use_multistage': CONFIG.get('use_multistage_pipeline')
        }
    })

@app.route('/api/export_results/<format>')
def export_results(format):
    """Export processing results"""
    session_id = session.get('session_id')
    
    if session_id not in processing_jobs:
        return jsonify({'error': 'No results to export'}), 404
    
    results = processing_jobs[session_id].results
    
    if format == 'json':
        return jsonify(results)
    elif format == 'csv':
        # Convert to CSV format
        import csv
        import io
        output = io.StringIO()
        
        if results:
            writer = csv.DictWriter(output, fieldnames=[
                'image_name', 'image_path', 'category', 'subcategory', 
                'tags', 'score', 'critique', 'exif_written'
            ])
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
                    'critique': analysis['critique'],
                    'exif_written': result['exif_written']
                })
        
        from flask import Response
        return Response(output.getvalue(), mimetype='text/csv',
                       headers={'Content-Disposition': 'attachment; filename=analysis_results.csv'})

@socketio.on('connect')
def handle_connect():
    from flask_socketio import join_room
    session_id = session.get('session_id', str(uuid.uuid4()))
    session['session_id'] = session_id
    active_sessions.add(session_id)
    join_room(session_id)
    print(f"🔌 Client connected to session: {session_id}")
    emit('connected', {'session_id': session_id})

@socketio.on('disconnect')
def handle_disconnect():
    from flask_socketio import leave_room
    session_id = session.get('session_id')
    if session_id:
        active_sessions.discard(session_id)
        leave_room(session_id)
        print(f"🔌 Client disconnected from session: {session_id}")

if __name__ == '__main__':
    # Create templates directory
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static/css', exist_ok=True)
    os.makedirs('static/js', exist_ok=True)
    
    # Run the application
    socketio.run(app, host='0.0.0.0', port=5001, debug=True)
