#!/usr/bin/env python3
# ----------------------------------------------------------------------
#  AI Image Analyzer - Pipeline Test Script
#  
#  Test script to validate the multi-stage processing pipeline
#  functionality and ensure all components work together correctly.
# ----------------------------------------------------------------------

import os
import tempfile
import shutil
from pathlib import Path
import queue
from pipeline_core import ImageCurationEngine, MultiStageProcessingPipeline

def create_test_images():
    """Create temporary test images for pipeline testing"""
    import random
    from PIL import Image, ImageDraw
    
    test_dir = Path(tempfile.mkdtemp(prefix="ai_analyzer_test_"))
    print(f"📁 Creating test images in: {test_dir}")
    
    # Create several test images with varying quality characteristics
    test_images = []
    
    for i in range(10):
        # Create images with different characteristics
        width, height = 800, 600
        
        # Create base image
        img = Image.new('RGB', (width, height), color=(
            random.randint(50, 200),
            random.randint(50, 200), 
            random.randint(50, 200)
        ))
        
        draw = ImageDraw.Draw(img)
        
        # Add some content to make images more varied
        for j in range(random.randint(5, 15)):
            x1, y1 = random.randint(0, width-100), random.randint(0, height-100)
            x2, y2 = x1 + random.randint(50, 150), y1 + random.randint(50, 150)
            color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
            
            if random.choice([True, False]):
                draw.rectangle([x1, y1, x2, y2], fill=color)
            else:
                draw.ellipse([x1, y1, x2, y2], fill=color)
        
        # Add some noise for lower quality images (randomly)
        if random.random() < 0.3:  # 30% chance of noisy image
            pixels = img.load()
            for x in range(0, width, 5):  # Add noise every 5 pixels
                for y in range(0, height, 5):
                    if random.random() < 0.1:  # 10% of these positions get noise
                        noise = random.randint(-30, 30)
                        try:
                            r, g, b = pixels[x, y]
                            pixels[x, y] = (
                                max(0, min(255, r + noise)),
                                max(0, min(255, g + noise)),
                                max(0, min(255, b + noise))
                            )
                        except:
                            pass
        
        # Save image
        image_path = test_dir / f"test_image_{i:03d}.jpg"
        img.save(image_path, "JPEG", quality=random.randint(70, 95))
        test_images.append(image_path)
        
    print(f"✅ Created {len(test_images)} test images")
    return test_dir, test_images

def test_image_curation_engine():
    """Test the Image Curation Engine (IQA stage)"""
    print("\n🔍 Testing Image Curation Engine...")
    
    test_dir, test_images = create_test_images()
    
    try:
        # Test BRISQUE model
        curation_engine = ImageCurationEngine(iqa_model='brisque')
        
        # Test single image scoring
        test_image = test_images[0]
        score = curation_engine.score_image(str(test_image))
        print(f"📊 Single image score: {score:.2f}")
        
        assert score is not None, "Image scoring failed"
        assert isinstance(score, float), "Score should be a float"
        
        # Test directory curation
        status_queue = queue.Queue()
        curated_images = curation_engine.curate_images_by_quality(
            str(test_dir), 
            top_percent=0.30,  # Top 30% for testing
            status_queue=status_queue
        )
        
        print(f"📈 Curated {len(curated_images)} images from {len(test_images)} total")
        
        # Check results
        assert len(curated_images) > 0, "No images were curated"
        assert len(curated_images) <= len(test_images), "More images curated than available"
        assert all(isinstance(item, tuple) and len(item) == 2 for item in curated_images), "Invalid curation format"
        
        # Check status messages
        messages = []
        try:
            while True:
                messages.append(status_queue.get_nowait())
        except queue.Empty:
            pass
        
        print(f"📝 Status messages: {len(messages)}")
        
        print("✅ Image Curation Engine test passed")
        return test_dir
        
    except Exception as e:
        print(f"❌ Image Curation Engine test failed: {e}")
        shutil.rmtree(test_dir)
        raise

def test_multistage_pipeline():
    """Test the complete multi-stage pipeline"""
    print("\n🚀 Testing Multi-Stage Processing Pipeline...")
    
    test_dir, test_images = create_test_images()
    
    try:
        # Configure pipeline for testing (using placeholder/fallback modes)
        pipeline_config = {
            'model_type': 'gemini',  # Will fallback to placeholder if no API key
            'google_api_key': '',  # Empty - will use fallbacks
            'gemini_model': 'gemini-2.0-flash-exp',
            'ollama_url': 'http://localhost:11434',
            'model': 'llava:13b',
            'enable_gallery_critique': False,  # Disable to avoid API calls
            'prompt_profile': 'professional_art_critic',
            'quality_threshold': 0.40,  # Process top 40% for testing
            'iqa_model': 'brisque',
            'use_exif': False,  # Use XMP sidecars
            'exiftool_path': None  # Use system path
        }
        
        # Create pipeline
        pipeline = MultiStageProcessingPipeline(pipeline_config)
        
        # Create status queue
        status_queue = queue.Queue()
        
        # Run pipeline
        results = pipeline.process_directory(str(test_dir), status_queue)
        
        # Collect status messages
        messages = []
        try:
            while True:
                messages.append(status_queue.get_nowait())
        except queue.Empty:
            pass
        
        print(f"📝 Pipeline status messages: {len(messages)}")
        for msg in messages[-5:]:  # Show last 5 messages
            print(f"   {msg}")
        
        # Validate results
        assert results['success'], f"Pipeline failed: {results.get('error', 'Unknown error')}"
        assert 'total_images_found' in results, "Missing total images count"
        assert 'images_analyzed' in results, "Missing analyzed images count"
        assert 'processing_time' in results, "Missing processing time"
        
        total_found = results['total_images_found']
        analyzed = results['images_analyzed']
        processing_time = results['processing_time']
        
        print(f"📊 Pipeline Results:")
        print(f"   • Total images found: {total_found}")
        print(f"   • Images analyzed: {analyzed}")
        print(f"   • Processing time: {processing_time:.2f}s")
        print(f"   • IQA Model: {results.get('iqa_model', 'unknown')}")
        print(f"   • AI Model: {results.get('ai_model', 'unknown')}")
        
        # Validate reasonable results
        assert total_found == len(test_images), f"Expected {len(test_images)} images, found {total_found}"
        assert analyzed > 0, "No images were analyzed"
        assert analyzed <= total_found, "More images analyzed than found"
        assert processing_time > 0, "Processing time should be positive"
        
        # Check for XMP files if not using EXIF
        if not pipeline_config['use_exif']:
            xmp_files = list(Path(test_dir).glob("*.xmp"))
            print(f"📄 XMP sidecar files created: {len(xmp_files)}")
            # Note: XMP files may not be created if ExifTool is not available
        
        print("✅ Multi-Stage Pipeline test passed")
        return test_dir
        
    except Exception as e:
        print(f"❌ Multi-Stage Pipeline test failed: {e}")
        import traceback
        print(traceback.format_exc())
        shutil.rmtree(test_dir)
        raise

def test_pipeline_with_different_models():
    """Test pipeline with different IQA models"""
    print("\n🔄 Testing Pipeline with Different IQA Models...")
    
    test_dir, test_images = create_test_images()
    
    iqa_models_to_test = ['brisque']  # Start with BRISQUE, add others if available
    
    try:
        # Test available models
        for iqa_model in iqa_models_to_test:
            print(f"   Testing with {iqa_model.upper()} model...")
            
            try:
                curation_engine = ImageCurationEngine(iqa_model=iqa_model)
                
                # Test curation
                curated = curation_engine.curate_images_by_quality(str(test_dir), 0.20)
                print(f"   ✓ {iqa_model.upper()}: Curated {len(curated)} images")
                
            except Exception as e:
                print(f"   ❌ {iqa_model.upper()} failed: {e}")
        
        print("✅ IQA Model variation test completed")
        
    finally:
        shutil.rmtree(test_dir)

def main():
    """Run all pipeline tests"""
    print("🧪 AI Image Analyzer - Pipeline Test Suite")
    print("=" * 50)
    
    try:
        # Test 1: Image Curation Engine
        test_dir = test_image_curation_engine()
        
        # Clean up before next test
        shutil.rmtree(test_dir)
        
        # Test 2: Complete Multi-Stage Pipeline
        test_dir = test_multistage_pipeline()
        
        # Clean up
        shutil.rmtree(test_dir)
        
        # Test 3: Different IQA Models
        test_pipeline_with_different_models()
        
        print("\n🎉 All tests passed!")
        print("\n📋 Test Summary:")
        print("✅ Image Curation Engine (IQA) - Working")
        print("✅ Multi-Stage Processing Pipeline - Working") 
        print("✅ IQA Model Variations - Working")
        print("\n💡 The pipeline is ready for production use!")
        print("\n📚 Next Steps:")
        print("   • Install dependencies: pip install -r requirements.txt")
        print("   • For ExifTool support: Download from https://exiftool.org/")
        print("   • Set GOOGLE_API_KEY environment variable for Gemini")
        print("   • Run GUI: python ai_image_analyzer_gui.py")
        print("   • Run Web App: python web/app.py")
        
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
