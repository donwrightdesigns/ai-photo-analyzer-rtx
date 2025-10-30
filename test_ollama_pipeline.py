#!/usr/bin/env python3
"""
Comprehensive test for the new Ollama-based AI Image Analyzer pipeline
Tests: IQA -> Ollama Direct Analysis -> Metadata Writing
"""

import sys
import os
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_ollama_direct_analyzer():
    """Test the direct Ollama analyzer"""
    print("\n" + "="*60)
    print("🔧 TESTING: Ollama Direct Analyzer")
    print("="*60)
    
    try:
        from scripts.ollama_direct_analyzer import OllamaDirectAnalyzer
        
        # Test connection first
        analyzer = OllamaDirectAnalyzer(
            base_url="http://localhost:11434",
            model="llava:latest"
        )
        
        if not analyzer.available:
            print("❌ Ollama not available - is Ollama running with LLaVA model?")
            return False
        
        print("✅ Ollama connection successful")
        
        # Get available models
        models = analyzer.get_available_models()
        print(f"📋 Available models: {[m['name'] for m in models]}")
        
        # Test with simple image if available
        test_images = list(Path('.').glob('*.jpg')) + list(Path('.').glob('*.jpeg'))
        if not test_images:
            print("⚠️  No test images found in current directory")
            return True
        
        test_image = str(test_images[0])
        print(f"🖼️  Testing with: {test_image}")
        
        # Test simple analysis
        success = analyzer.test_with_simple_prompt(test_image)
        if success:
            print("✅ Simple prompt test successful")
        else:
            print("❌ Simple prompt test failed")
            
        return success
        
    except Exception as e:
        print(f"❌ Error testing Ollama Direct Analyzer: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_photography_taxonomy():
    """Test the updated photography taxonomy"""
    print("\n" + "="*60)
    print("📝 TESTING: Photography Taxonomy with Hierarchical Keywords")
    print("="*60)
    
    try:
        from photography_taxonomy import get_analysis_prompt
        
        prompt = get_analysis_prompt('professional_art_critic')
        print("✅ Generated photography taxonomy prompt")
        print(f"📄 Prompt length: {len(prompt)} characters")
        
        # Check for hierarchical keyword format
        if '" > "' in prompt:
            print("✅ Hierarchical keyword format detected")
        else:
            print("⚠️  Hierarchical keyword format not found in prompt")
            
        # Show sample of prompt
        print(f"📖 Prompt sample: {prompt[:200]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing photography taxonomy: {e}")
        return False

def test_pipeline_integration():
    """Test the complete pipeline integration"""
    print("\n" + "="*60)
    print("🔗 TESTING: Complete Pipeline Integration")
    print("="*60)
    
    try:
        from pipeline_core import ContentGenerationEngine
        
        # Test configuration for Ollama
        test_config = {
            'model_type': 'ollama',
            'ollama_url': 'http://localhost:11434',
            'ollama_model': 'llava:latest',
            'persona_profile': 'professional_art_critic',
            'google_api_key': ''  # Disable Gemini for this test
        }
        
        print("🔧 Initializing ContentGenerationEngine...")
        engine = ContentGenerationEngine(test_config)
        
        if engine.ollama_analyzer and engine.ollama_analyzer.available:
            print("✅ Ollama analyzer initialized successfully")
            
            # Test with image if available
            test_images = list(Path('.').glob('*.jpg')) + list(Path('.').glob('*.jpeg'))
            if test_images:
                test_image = str(test_images[0])
                print(f"🖼️  Testing analysis with: {test_image}")
                
                result = engine.analyze_image_with_ollama_direct(test_image)
                
                if result and 'error' not in result:
                    print("✅ Image analysis successful!")
                    print(f"   Category: {result.get('category')}")
                    print(f"   Subcategory: {result.get('subcategory')}")
                    print(f"   Tags: {result.get('tags')}")
                    print(f"   Score: {result.get('score')}/5")
                    
                    # Check for hierarchical tags
                    tags = result.get('tags', [])
                    hierarchical_found = any(' > ' in str(tag) for tag in tags) if isinstance(tags, list) else ' > ' in str(tags)
                    if hierarchical_found:
                        print("✅ Hierarchical keywords detected in result")
                    else:
                        print("⚠️  No hierarchical keywords found")
                    
                    return True
                else:
                    print(f"❌ Image analysis failed: {result}")
                    return False
            else:
                print("⚠️  No test images available - skipping image analysis test")
                return True
        else:
            print("❌ Ollama analyzer not available")
            return False
            
    except Exception as e:
        print(f"❌ Error testing pipeline integration: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_gui_configuration():
    """Test GUI configuration compatibility"""
    print("\n" + "="*60)
    print("🖥️  TESTING: GUI Configuration")
    print("="*60)
    
    try:
        from ai_image_analyzer_gui import ConfigManager
        
        config_manager = ConfigManager()
        config = config_manager.load_config()
        
        print("✅ ConfigManager initialized")
        print(f"📋 Default model type: {config.get('model_type')}")
        print(f"🌐 Ollama URL: {config.get('ollama_url')}")
        print(f"🤖 Ollama model: {config.get('ollama_model')}")
        
        # Test saving config
        test_config = config.copy()
        test_config['model_type'] = 'ollama'
        test_config['ollama_model'] = 'llava:7b'
        
        success = config_manager.save_config(test_config)
        if success:
            print("✅ Configuration save/load test successful")
            return True
        else:
            print("❌ Configuration save test failed")
            return False
            
    except Exception as e:
        print(f"❌ Error testing GUI configuration: {e}")
        return False

def run_comprehensive_test():
    """Run all tests and provide summary"""
    print("🚀 AI Image Analyzer - Ollama Integration Test Suite")
    print("=" * 70)
    
    test_results = []
    
    # Run all tests
    tests = [
        ("Ollama Direct Analyzer", test_ollama_direct_analyzer),
        ("Photography Taxonomy", test_photography_taxonomy), 
        ("Pipeline Integration", test_pipeline_integration),
        ("GUI Configuration", test_gui_configuration)
    ]
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            test_results.append((test_name, result))
        except KeyboardInterrupt:
            print(f"\n⏹️  Test interrupted by user")
            break
        except Exception as e:
            print(f"\n❌ Unexpected error in {test_name}: {e}")
            test_results.append((test_name, False))
    
    # Print summary
    print("\n" + "="*70)
    print("📊 TEST SUMMARY")
    print("="*70)
    
    passed = 0
    for test_name, result in test_results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 Results: {passed}/{len(test_results)} tests passed")
    
    if passed == len(test_results):
        print("\n🎉 ALL TESTS PASSED! The Ollama integration is working correctly.")
        print("You can now run the GUI with: python ai_image_analyzer_gui.py")
    else:
        print(f"\n⚠️  {len(test_results) - passed} tests failed. Please check the errors above.")
        if passed > 0:
            print("Some components are working - you may still be able to use the application with limitations.")

if __name__ == "__main__":
    run_comprehensive_test()