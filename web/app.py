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
    'models_path': 'J:/models',
    'max_workers': 2,
    'supported_formats': ['.jpg', '.jpeg', '.tif', '.tiff', '.png', '.webp'],
    'model_type': 'llava',  # 'llava' or 'gemini'
    'google_api_key': '',  # Your Google API key for cloud usage
    'available_local_models': ['llava:13b', 'llava:7b', 'llava:34b'],  # List available local models
    'gemini_model': 'gemini-2.0-flash-exp',
    'generate_xmp': False,  # Generate XMP sidecar files instead of EXIF
    'enable_gallery_critique': False,  # Enable gallery critique for all images
    'critique_threshold': 5  # Score threshold for critique when gallery critique is disabled
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

class ImageAnalyzer:
    def __init__(self, session_id):
        self.session_id = session_id
        self.is_running = False
        self.current_image = None
        self.total_images = 0
        self.processed_count = 0
        self.results = []
        
    def analyze_image(self, image_path):
        """Analyze image using the selected model"""
        try:
            if CONFIG['model_type'] == 'local':
                return self.analyze_with_local_model(image_path)
            elif CONFIG['model_type'] == 'cloud':
                return self.analyze_with_cloud_model(image_path)
        except Exception as e:
            print(f"Error analyzing image: {e}")
            return None

    def analyze_with_local_model(self, image_path):
        """Analyze image using local model"""
        try:
            # Convert image to base64
            with open(image_path, 'rb') as img_file:
                image_data = base64.b64encode(img_file.read()).decode('utf-8')
            
            prompt = f"""
            You are an art connoisseur and graduate with a Master's in Fine Art, viewing a photograph 
            as if in a gallery showing for the first time.

            Analyze this image and provide:
            1. Category (choose ONE): {', '.join(DEFAULT_CATEGORIES)}
            2. Subcategory (choose ONE): {', '.join(DEFAULT_SUB_CATEGORIES)}
            3. Tags (choose up to 4): {', '.join(DEFAULT_TAGS)}
            4. A brief, insightful critique (2-3 sentences) on composition, lighting, and emotional impact
            5. Overall score from 1 (poor) to 10 (masterpiece)

            Respond ONLY with valid JSON:
            {{
                "category": "chosen_category",
                "subcategory": "chosen_subcategory", 
                "tags": ["tag1", "tag2"],
                "score": 8,
                "critique": "Your critique here"
            }}
            """
            
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
                    if all(k in data for k in ["category", "subcategory", "tags", "score", "critique"]):
                        return data
                    else:
                        return None
                except json.JSONDecodeError:
                    return None
            else:
                return None
                
        except Exception as e:
            print(f"Error analyzing image: {e}")
            return None
            
    def analyze_with_cloud_model(self, image_path):
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
            
            # Create analysis prompt with optional critique
            enable_critique = CONFIG['enable_gallery_critique']
            critique_section = ""
            if enable_critique:
                critique_section = f"""
                
                CRITIQUE REQUIREMENTS:
                - 2-3 sentences maximum
                - Focus on what makes the image succeed or fail
                - Mention specific technical or artistic elements
                - Be constructive but honest
                """
            
            prompt = f"""
            You are a professional art critic and gallery curator with 25 years of experience,
            evaluating photographs for potential inclusion in a fine art exhibition.
            
            ANALYSIS CRITERIA:
            1. Technical Excellence: Focus, exposure, composition, color/lighting
            2. Artistic Merit: Creativity, emotional impact, visual storytelling
            3. Commercial Appeal: Marketability, broad audience appeal
            4. Uniqueness: What sets this image apart from typical photography
            
            CLASSIFICATION (select ONE from each category):
            CATEGORIES: {', '.join(DEFAULT_CATEGORIES)}
            SUB_CATEGORIES: {', '.join(DEFAULT_SUB_CATEGORIES)}
            TAGS: {', '.join(DEFAULT_TAGS)} (select 2-4 most relevant)
            
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
                if enable_critique:
                    required_keys.append("critique")
                    
                if all(k in data for k in required_keys):
                    # Post-process critique based on configuration
                    if not CONFIG['enable_gallery_critique'] and enable_critique:
                        score = data.get('score', 0)
                        if score > CONFIG['critique_threshold']:
                            # Remove critique for high-scoring images when gallery critique is disabled
                            data.pop('critique', None)
                    
                    return data
                else:
                    return None
            except json.JSONDecodeError:
                return None
                
        except Exception as e:
            print(f"Error with Gemini model: {e}")
            return None
    
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
        socketio.emit('progress_update', {
            'session_id': self.session_id,
            'total': self.total_images,
            'processed': 0,
            'current_image': '',
            'status': 'Starting...'
        })
        
        for i, image_path in enumerate(image_files):
            if not self.is_running:
                break
                
            self.current_image = image_path.name
            
            # Emit progress update
            socketio.emit('progress_update', {
                'session_id': self.session_id,
                'total': self.total_images,
                'processed': i,
                'current_image': self.current_image,
                'status': f'Analyzing {self.current_image}...'
            })
            
            # Analyze image
            analysis_data = self.analyze_image(image_path)
            
            if analysis_data:
                # Write EXIF if requested
                if write_exif:
                    exif_success = self.write_exif_data(image_path, analysis_data)
                else:
                    exif_success = True
                
                # Store result
                result = {
                    'image_path': str(image_path),
                    'image_name': image_path.name,
                    'analysis': analysis_data,
                    'exif_written': exif_success,
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
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
