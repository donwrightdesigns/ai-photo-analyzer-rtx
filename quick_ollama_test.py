#!/usr/bin/env python3
"""
Quick Ollama connectivity test
"""
import requests
import json
import time

def test_ollama_connection():
    print("🔧 Testing Ollama connection...")
    
    try:
        # Test basic connectivity
        response = requests.get("http://localhost:11434/api/tags", timeout=10)
        if response.status_code == 200:
            models = response.json()
            print(f"✅ Ollama is responding")
            print(f"📋 Available models: {[m['name'] for m in models.get('models', [])]}")
            
            # Check if our target model is available
            model_names = [m['name'] for m in models.get('models', [])]
            if 'llava:13b' in model_names:
                print("✅ llava:13b model is available")
                return True
            else:
                print("❌ llava:13b model not found")
                return False
        else:
            print(f"❌ Ollama responded with status {response.status_code}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ Connection timed out")
        return False
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to Ollama")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = test_ollama_connection()
    if success:
        print("\n🎉 Ollama is ready! You can now run the full GUI.")
    else:
        print("\n⚠️  Please check Ollama configuration.")