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
    'prompt_profile': 'professional_art_critic'  # Default prompt profile
}

# Global variables for processing state
processing_jobs = {}
active_sessions = set()

# Categories and tags configuration
DEFAULT_CATEGORIES = ["People", "Place", "Thing"]
DEFAULT_SUB_CATEGORIES = ["Candid", "Posed", "Automotive", "Real Estate", "Landscape", 
                         "Events", "Animal", "Product", "Food"]
DEFAULT_TAGS = ["Strobist", "Available Light", "Natural Light", "Beautiful", "Black & White", 
               "Timeless", "Low Quality", "Sentimental", "Action", "Minimalist", "Out of Focus", 
               "Other", "Evocative", "Disturbing", "Boring", "Wedding", "Bride", "Groom", 
               "Family", "Love", "Calm", "Busy"]

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
            "score": 7
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
        
        SCORING GUIDE (1-10 scale from {profile['name']} perspective):
        1-2: Poor (fails to meet basic standards for this evaluation type)
        3-4: Below Average (basic competence, limited value for intended purpose)
        5-6: Average (meets standard expectations for this type of image)
        7-8: Above Average (strong quality and purpose alignment)
        9-10: Exceptional (outstanding example that excels in all criteria)
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
        """Write analysis data to metadata (EXIF or XMP based on configuration)"""
        try:
            if CONFIG.get('generate_xmp', False):
                return self.write_xmp_sidecar(image_path, analysis_data)
            else:
                return self.write_exif_data(image_path, analysis_data)
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
            <rdf:li xml:lang="x-default">Score: {score}/10</rdf:li>
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
    
    def write_exif_data(self, image_path, analysis_data):
        """Write analysis data to EXIF metadata"""
        try:
            # Load existing EXIF data
            try:
                exif_dict = piexif.load(str(image_path))
            except piexif.InvalidImageDataError:
                exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}

            # Calculate star rating
            score = analysis_data.get('score', 0)
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
        socketio.emit('progress_update', initial_data)
        
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
            socketio.emit('progress_update', progress_data)
            
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
                })
            
            self.processed_count = i + 1
        
        self.is_running = False
        
        # Emit completion
        socketio.emit('processing_complete', {
            'session_id': self.session_id,
            'total_processed': self.processed_count,
            'results': self.results
        })

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
    write_exif = data.get('write_exif', True)
    model_type = data.get('model_type', 'local')
    api_key = data.get('api_key', '')
    
    # Update global config with user selection
    CONFIG['model_type'] = model_type
    if api_key:
        CONFIG['google_api_key'] = api_key
    
    if not directory_path or not os.path.exists(directory_path):
        return jsonify({'success': False, 'error': 'Invalid directory path'})
    
    session_id = session.get('session_id', str(uuid.uuid4()))
    session['session_id'] = session_id
    
    # Create analyzer instance
    analyzer = ImageAnalyzer(session_id)
    processing_jobs[session_id] = analyzer
    
    # Start processing in background thread
    thread = threading.Thread(target=analyzer.process_directory, args=(directory_path, write_exif))
    thread.daemon = True
    thread.start()
    
    return jsonify({'success': True, 'session_id': session_id})

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
    session_id = session.get('session_id', str(uuid.uuid4()))
    session['session_id'] = session_id
    active_sessions.add(session_id)
    emit('connected', {'session_id': session_id})

@socketio.on('disconnect')
def handle_disconnect():
    session_id = session.get('session_id')
    if session_id:
        active_sessions.discard(session_id)

if __name__ == '__main__':
    # Create templates directory
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static/css', exist_ok=True)
    os.makedirs('static/js', exist_ok=True)
    
    # Run the application
    socketio.run(app, host='0.0.0.0', port=5001, debug=True)
