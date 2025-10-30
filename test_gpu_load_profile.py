#!/usr/bin/env python3
"""
Test GPU Load Profile Functionality
Tests the different GPU load profiles and their effect on timeouts and delays.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent / "scripts"))

from ollama_direct_analyzer import OllamaDirectAnalyzer

def test_gpu_load_profiles():
    """Test different GPU load profiles and their configuration"""
    
    profiles = [
        "🔥 Hurt My GPU (Maximum Speed)",
        "⚡ Normal Demand (Balanced)", 
        "🌿 Light Demand (Background Safe)"
    ]
    
    base_timeout = 30
    
    print("Testing GPU Load Profiles:\n" + "="*50)
    
    for profile in profiles:
        print(f"\nTesting Profile: {profile}")
        print("-" * 30)
        
        # Create analyzer with this profile
        analyzer = OllamaDirectAnalyzer(
            base_url="http://localhost:11434",
            model="llava:13b",
            timeout=base_timeout,
            gpu_load_profile=profile
        )
        
        print(f"  Timeout: {analyzer.timeout}s")
        print(f"  Request Interval: {analyzer.min_request_interval}s")
        
        # Calculate expected values for verification
        if "🔥 Hurt My GPU" in profile:
            expected_timeout = max(15, base_timeout // 2)
            expected_interval = 0.05
        elif "🌿 Light Demand" in profile:
            expected_timeout = base_timeout * 2
            expected_interval = 1.0
        else:
            expected_timeout = base_timeout
            expected_interval = 0.1
            
        # Verify settings
        assert analyzer.timeout == expected_timeout, f"Expected timeout {expected_timeout}, got {analyzer.timeout}"
        assert analyzer.min_request_interval == expected_interval, f"Expected interval {expected_interval}, got {analyzer.min_request_interval}"
        
        print(f"  ✅ Configuration verified")
        
    print(f"\n" + "="*50)
    print("All GPU Load Profile tests passed! ✅")

if __name__ == "__main__":
    test_gpu_load_profiles()