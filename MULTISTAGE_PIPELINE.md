# Multi-Stage Processing Pipeline Implementation

This document describes the implementation of the advanced multi-stage processing pipeline for the AI Image Analyzer, based on the technical report specifications.

## Overview

The multi-stage pipeline transforms the tool from a simple batch script into a sophisticated, economically viable system that processes only the highest quality images with expensive AI analysis.

## Architecture

### Pipeline Stages

1. **Image Curation Engine (IQA)** - Quality assessment and filtering
2. **Content Generation Engine** - AI analysis of curated images  
3. **Metadata Persistence Layer** - Robust metadata writing

### Key Benefits

- 🎯 **Cost Efficiency**: Only processes top-quality images (10-50% threshold)
- 🚀 **Performance**: Filter-then-process approach saves computational resources
- 🔧 **Modularity**: Each stage can be optimized, tested, and replaced independently
- 📊 **Professional Quality**: Uses industry-standard tools (PyExifTool, pyiqa)

## Components

### 1. Image Curation Engine (`ImageCurationEngine`)

**Purpose**: Assess and filter images by quality before expensive AI analysis.

**Features**:
- Multiple IQA models: BRISQUE, NIQE, MUSIQ, TOPIQ
- Configurable quality thresholds (5-50%)
- GPU acceleration when available
- Progress tracking via status queues

```python
from pipeline_core import ImageCurationEngine

# Create curation engine
engine = ImageCurationEngine(iqa_model='brisque')

# Score single image
score = engine.score_image('path/to/image.jpg')

# Curate directory (top 10%)
curated = engine.curate_images_by_quality('path/to/directory', top_percent=0.10)
```

### 2. Content Generation Engine (`ContentGenerationEngine`)

**Purpose**: Perform AI analysis on the curated high-quality image subset.

**Features**:
- Multi-model support: Gemini, Ollama LLaVA, BakLLaVA
- Dynamic prompt engineering based on user profiles
- Structured JSON output with categories, tags, scores
- Optional curatorial descriptions

```python
from pipeline_core import ContentGenerationEngine

# Configure for Gemini
config = {
    'model_type': 'gemini',
    'google_api_key': 'your_api_key',
    'enable_gallery_critique': True
}

engine = ContentGenerationEngine(config)
analysis = engine.analyze_image('path/to/image.jpg')
```

### 3. Metadata Persistence Layer (`MetadataPersistenceLayer`)

**Purpose**: Write analysis results to XMP sidecar files or embedded EXIF metadata.

**Features**:
- PyExifTool backend for maximum compatibility
- XMP sidecar files (non-destructive, default)
- Embedded EXIF/IPTC support
- Batch processing optimization
- Automatic star ratings and GALLERY tags

```python
from pipeline_core import MetadataPersistenceLayer

layer = MetadataPersistenceLayer()

# Write to XMP sidecar (default)
layer.write_xmp_sidecar('image.jpg', analysis_data)

# Write embedded metadata  
layer.write_embedded_metadata('image.jpg', analysis_data)
```

### 4. Complete Pipeline (`MultiStageProcessingPipeline`)

**Purpose**: Orchestrate the complete pipeline flow.

```python
from pipeline_core import MultiStageProcessingPipeline

config = {
    'model_type': 'gemini',
    'google_api_key': 'your_key',
    'quality_threshold': 0.10,
    'iqa_model': 'brisque',
    'use_exif': False  # Use XMP sidecars
}

pipeline = MultiStageProcessingPipeline(config)
results = pipeline.process_directory('/path/to/images')
```

## Installation & Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

The new dependencies include:
- `torch>=2.0.0` - PyTorch for ML models
- `torchvision>=0.15.0` - Computer vision utilities
- `pyiqa>=0.1.7` - Image Quality Assessment toolkit
- `PyExifTool>=0.5.6` - Professional metadata handling

### 2. Install ExifTool

Download ExifTool from https://exiftool.org/ and ensure it's in your system PATH.

**Windows**: Extract to a folder and add to PATH, or place in the project directory.

**Linux/Mac**: 
```bash
# Ubuntu/Debian
sudo apt-get install exiftool

# macOS  
brew install exiftool
```

### 3. Configure API Keys (Optional)

For Gemini API:
```bash
export GOOGLE_API_KEY="your_api_key_here"
```

## Usage

### Standalone GUI Application

Run the complete Tkinter GUI:

```bash
python ai_image_analyzer_gui.py
```

**Features**:
- Professional GUI with progress tracking
- IQA model selection (BRISQUE, NIQE, etc.)
- Quality threshold configuration (5-50%)
- Multiple AI model support
- Real-time status updates
- XMP sidecar and EXIF options

### Web Interface

The Flask web app now includes multi-stage pipeline support:

```bash
python web/app.py
```

Navigate to `http://localhost:5001` and use the new multi-stage processing option.

### Programmatic Usage

```python
from pipeline_core import MultiStageProcessingPipeline
import queue

# Configure pipeline
config = {
    'model_type': 'gemini',           # or 'ollama', 'bakllava'
    'google_api_key': 'your_key',
    'quality_threshold': 0.15,        # Top 15% of images
    'iqa_model': 'brisque',          # Quality assessment model
    'use_exif': False,               # Use XMP sidecars (recommended)
    'enable_gallery_critique': True  # Generate detailed descriptions
}

# Create pipeline
pipeline = MultiStageProcessingPipeline(config)

# Create status queue for progress updates
status_queue = queue.Queue()

# Process directory
results = pipeline.process_directory('/path/to/images', status_queue)

# Print results
print(f"Processed {results['images_analyzed']} high-quality images")
print(f"Total processing time: {results['processing_time']:.1f}s")
```

## Configuration Options

### IQA Models

| Model | Type | Best For | Score Interpretation |
|-------|------|----------|---------------------|
| BRISQUE | Conventional | General synthetic distortions | Lower is better |
| NIQE | Conventional | Natural image evaluation | Lower is better |
| MUSIQ | Deep Learning | Complex authentic distortions | Higher is better |
| TOPIQ | Deep Learning | Technical + aesthetic quality | Higher is better |

### Quality Thresholds

- **5%**: Ultra-selective, only exceptional images
- **10%**: Default, high-quality subset
- **15-25%**: Balanced selection
- **50%**: Liberal filtering, removes worst images

### AI Models

- **Gemini**: Best quality, requires API key, cloud-based
- **Ollama LLaVA**: Good quality, local processing, requires Ollama
- **BakLLaVA**: Local Mistral-based, GPU acceleration

## Testing

Run the comprehensive test suite:

```bash
python test_pipeline.py
```

This validates:
- Image Curation Engine functionality
- Complete multi-stage pipeline
- Different IQA model variations
- Metadata writing capabilities

## Performance Optimization

### Filter-then-Process Benefits

Traditional approach (100% processing):
```
1000 images × 30s/image = 8.3 hours + $50 API costs
```

Multi-stage approach (10% processing):
```
1000 images × 0.1s/image (IQA) + 100 images × 30s/image (AI) = 1 hour + $5 API costs
```

**Savings**: 85% time reduction, 90% cost reduction

### Hardware Recommendations

- **CPU**: Multi-core for parallel IQA processing
- **GPU**: CUDA-capable for accelerated quality assessment
- **Memory**: 8GB+ for large image batches
- **Storage**: SSD recommended for I/O intensive operations

## Professional Workflow Integration

### Adobe Lightroom

The pipeline generates XMP sidecar files compatible with Lightroom:

1. Process images with multi-stage pipeline
2. Import folder into Lightroom 
3. XMP metadata automatically appears
4. Use star ratings and GALLERY tags for organization

### Digital Asset Management

- **Non-destructive**: Original images never modified
- **Standards compliant**: XMP, EXIF, IPTC metadata
- **Batch operations**: Efficient for large collections
- **Version control**: Separate metadata files enable rollback

## Advanced Features

### Statistical Quality Filtering

Instead of fixed percentiles, use adaptive thresholds:

```python
# Future enhancement concept
def adaptive_threshold(scores):
    mean_score = np.mean(scores)
    std_score = np.std(scores)
    return mean_score - std_score  # Select above-average quality
```

### Custom IQA Models

The architecture supports custom quality assessment models:

```python
class CustomIQAModel:
    def score_image(self, image_path):
        # Custom scoring logic
        return score
        
    @property
    def lower_better(self):
        return True  # or False
```

## Troubleshooting

### Common Issues

1. **PyTorch Installation**: Ensure compatible versions for your system
2. **ExifTool Not Found**: Verify installation and PATH configuration  
3. **API Rate Limits**: Use appropriate delays and error handling
4. **Memory Issues**: Process smaller batches for large collections

### Error Messages

- `"IQA model failed to load"`: Check PyTorch and pyiqa installation
- `"ExifTool not available"`: Install ExifTool and check PATH
- `"No images passed quality assessment"`: Lower quality threshold or check image directory

## Future Enhancements

- **Asynchronous Processing**: Parallel API calls for large batches
- **Advanced NLP**: Extract keywords from curatorial descriptions  
- **Custom Prompts**: User-defined analysis criteria
- **Model Comparison**: A/B testing between different AI models
- **Cloud Integration**: S3, Google Cloud storage support

## Contributing

The modular architecture makes contributions straightforward:

1. **New IQA Models**: Extend `ImageCurationEngine`
2. **AI Models**: Add to `ContentGenerationEngine`  
3. **Metadata Formats**: Enhance `MetadataPersistenceLayer`
4. **UI Improvements**: Update Tkinter or Flask interfaces

## License

This implementation maintains the same MIT license as the main project.

---

**The multi-stage processing pipeline transforms the AI Image Analyzer into a professional-grade tool suitable for handling large photography collections efficiently and economically.**
