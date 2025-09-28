#!/usr/bin/env python3
"""
AI Image Analyzer - Main Entry Point
Supports both standalone GUI and Lightroom plugin integration
"""

import argparse
import sys
import os
from pathlib import Path

def parse_arguments():
    """Parse command line arguments for Lightroom integration"""
    parser = argparse.ArgumentParser(description='AI Image Analyzer - Desktop Application')
    
    parser.add_argument('--images', type=str, 
                      help='Path to text file containing list of image paths (for Lightroom integration)')
    parser.add_argument('--mode', type=str, choices=['archive', 'curated'], 
                      help='Processing mode: archive (full analysis) or curated (quick quality filtering)')
    parser.add_argument('--gui', action='store_true', default=True,
                      help='Launch GUI interface (default)')
    parser.add_argument('--batch', action='store_true',
                      help='Run in batch mode without GUI')
    parser.add_argument('--config', type=str,
                      help='Path to configuration file')
    
    args = parser.parse_args()
    
    # If no arguments provided, default to GUI mode
    if len(sys.argv) == 1:
        args.gui = True
        args.batch = False
        
    return args

def load_image_list(images_file):
    """Load list of image paths from file"""
    try:
        with open(images_file, 'r') as f:
            images = []
            for line in f:
                line = line.strip()
                if line and os.path.exists(line):
                    images.append(line)
            return images
    except Exception as e:
        print(f"Error loading image list: {e}")
        return []

def run_batch_mode(images, processing_mode='archive', config_path=None):
    """Run processing in batch mode without GUI"""
    from pipeline_core import MultiStageProcessingPipeline
    import json
    
    # Load configuration
    config = {}
    if config_path and os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
        except Exception as e:
            print(f"Error loading config: {e}")
    
    # Create pipeline with appropriate settings for mode
    if processing_mode == 'curated':
        # Curated mode: fast processing, quality filtering only
        config.update({
            'quality_threshold': 0.15,  # Higher threshold for curated
            'generate_curator': True,
            'model_type': 'brisque',  # Fast quality assessment only
        })
        print(f"Running Curated Mode on {len(images)} images...")
    else:
        # Archive mode: comprehensive analysis
        config.update({
            'quality_threshold': 0.05,  # Lower threshold for archive
            'generate_curator': False,
        })
        print(f"Running Archive Mode on {len(images)} images...")
    
    try:
        pipeline = MultiStageProcessingPipeline(config)
        
        # Process each image
        for i, image_path in enumerate(images, 1):
            print(f"Processing {i}/{len(images)}: {os.path.basename(image_path)}")
            
            try:
                # Process single image
                result = pipeline.process_single_image(image_path)
                
                if result and result.get('success', False):
                    print(f"  ✓ Success: {result.get('message', 'Processed successfully')}")
                else:
                    print(f"  ✗ Failed: {result.get('error', 'Unknown error')}")
                    
            except Exception as e:
                print(f"  ✗ Error processing {image_path}: {e}")
        
        print(f"\nBatch processing complete!")
        return True
        
    except Exception as e:
        print(f"Error initializing pipeline: {e}")
        return False

def run_gui_mode(initial_images=None, processing_mode=None):
    """Launch GUI with optional preloaded images"""
    from ai_image_analyzer_gui_v2 import MainWindow
    
    # Create and run GUI
    app = MainWindow()
    
    # If images provided, preload them
    if initial_images:
        # Set the folder to the common directory of the images
        if initial_images:
            first_image_dir = os.path.dirname(initial_images[0])
            app.folder_var.set(first_image_dir)
            app.folder_label.config(text=f"Folder: {first_image_dir}")
            
            # Set processing mode if specified
            if processing_mode == 'archive':
                # Switch to archive mode settings
                app.config['quality_threshold'] = 0.05
                app.config['generate_curator'] = False
                app.folder_label.config(text=f"Archive Mode - Folder: {first_image_dir}")
            elif processing_mode == 'curated':
                # Switch to curated mode settings  
                app.config['quality_threshold'] = 0.15
                app.config['generate_curator'] = True
                app.folder_label.config(text=f"Curated Mode - Folder: {first_image_dir}")
    
    app.run()

def main():
    """Main entry point"""
    args = parse_arguments()
    
    # Handle image list loading
    images = []
    if args.images:
        if not os.path.exists(args.images):
            print(f"Error: Image list file not found: {args.images}")
            sys.exit(1)
        
        images = load_image_list(args.images)
        if not images:
            print("Error: No valid images found in the list")
            sys.exit(1)
            
        print(f"Loaded {len(images)} images from Lightroom")
    
    # Determine mode
    if args.batch or (args.images and not args.gui):
        # Run in batch mode
        success = run_batch_mode(images, args.mode or 'archive', args.config)
        sys.exit(0 if success else 1)
    else:
        # Run GUI mode (with optional preloaded images)
        try:
            run_gui_mode(images, args.mode)
        except KeyboardInterrupt:
            print("\nApplication terminated by user")
        except Exception as e:
            print(f"Error running GUI: {e}")
            sys.exit(1)

if __name__ == "__main__":
    main()
