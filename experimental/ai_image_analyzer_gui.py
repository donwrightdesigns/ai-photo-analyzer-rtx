#!/usr/bin/env python3
# ----------------------------------------------------------------------
#  AI Image Analyzer - Standalone GUI Application
#  
#  Complete Tkinter implementation of the multi-stage processing pipeline
#  as specified in the technical report. Features:
#  - Image Curation Engine (IQA) with quality assessment
#  - Content Generation Engine (AI analysis)
#  - Metadata Persistence Layer (PyExifTool)
#  - Professional GUI with progress tracking
# ----------------------------------------------------------------------

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import threading
import queue
import time
import json
from pathlib import Path
from pipeline_core import MultiStageProcessingPipeline
import google.genai as genai

class ImageAnalyzerApp:
    """
    Main GUI application window implementing the complete multi-stage pipeline
    from the technical report.
    """

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("AI Image Analyzer - Multi-Stage Processing Pipeline")
        self.root.geometry("800x700")
        self.root.resizable(True, True)
        
        # Application state
        self.directory = tk.StringVar()
        self.status_queue = queue.Queue()
        self.pipeline_thread = None
        self.is_processing = False
        
        # Configuration variables
        self.use_exif_var = tk.BooleanVar(value=False)
        self.generate_curator_var = tk.BooleanVar(value=False)
        self.recursive_var = tk.BooleanVar(value=True)  # Default to recursive
        self.model_type_var = tk.StringVar(value="gemini")
        self.api_key_var = tk.StringVar()
        self.quality_threshold_var = tk.DoubleVar(value=0.10)
        self.iqa_model_var = tk.StringVar(value="brisque")
        
        # RTX GPU optimization variables
        self.enable_rtx_var = tk.BooleanVar(value=True)
        self.rtx_gpu_layers_var = tk.IntVar(value=35)
        self.rtx_batch_size_var = tk.StringVar(value="512")
        self.rtx_max_vram_var = tk.DoubleVar(value=8.0)
        
        # Processing mode variable
        self.processing_mode_var = tk.StringVar(value="curated")
        
        self.setup_ui()
        # Load environment variables
        self._load_environment_config()
        self.schedule_queue_check()
        
    def setup_ui(self):
        """Create and layout all UI widgets"""
        # Main container
        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(main_frame, text="AI Image Analyzer", 
                               font=('Arial', 16, 'bold'))
        title_label.pack(pady=(0, 10))
        
        subtitle_label = ttk.Label(main_frame, 
                                  text="Multi-Stage Processing Pipeline with Image Quality Assessment",
                                  font=('Arial', 10))
        subtitle_label.pack(pady=(0, 20))
        
        # 1. Directory Selection
        dir_frame = ttk.LabelFrame(main_frame, text="1. Select Image Directory", padding="10")
        dir_frame.pack(fill=tk.X, pady=(0, 10))
        
        dir_entry_frame = ttk.Frame(dir_frame)
        dir_entry_frame.pack(fill=tk.X)
        
        ttk.Label(dir_entry_frame, textvariable=self.directory).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(dir_entry_frame, text="Browse...", command=self.select_directory).pack(side=tk.RIGHT, padx=(10, 0))
        self.directory.set("No directory selected")
        
        # 2. Processing Mode Selection
        mode_frame = ttk.LabelFrame(main_frame, text="2. Processing Mode", padding="10")
        mode_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Mode selection radio buttons
        mode_radio_frame = ttk.Frame(mode_frame)
        mode_radio_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Radiobutton(mode_radio_frame, text="📷 Curated Mode (Quality-based selection)", 
                       variable=self.processing_mode_var, value="curated",
                       command=self.on_mode_change).pack(anchor=tk.W, pady=2)
        ttk.Label(mode_radio_frame, text="   ↳ Process top-quality images for portfolio/delivery (faster)", 
                 font=('Arial', 9), foreground='gray').pack(anchor=tk.W, padx=(20, 0))
        
        ttk.Radiobutton(mode_radio_frame, text="🗂️ Archive Mode (All images)", 
                       variable=self.processing_mode_var, value="archive",
                       command=self.on_mode_change).pack(anchor=tk.W, pady=(10, 2))
        ttk.Label(mode_radio_frame, text="   ↳ Tag and catalog ALL images for searchable archive", 
                 font=('Arial', 9), foreground='gray').pack(anchor=tk.W, padx=(20, 0))
        
        # 3. Multi-Stage Pipeline Configuration
        pipeline_frame = ttk.LabelFrame(main_frame, text="3. Pipeline Configuration", padding="10")
        pipeline_frame.pack(fill=tk.X, pady=(0, 10))
        
        # IQA Configuration
        iqa_frame = ttk.Frame(pipeline_frame)
        iqa_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(iqa_frame, text="Quality Assessment Model:").pack(side=tk.LEFT)
        iqa_combo = ttk.Combobox(iqa_frame, textvariable=self.iqa_model_var,
                                values=['brisque', 'niqe', 'musiq', 'topiq'],
                                state='readonly', width=15)
        iqa_combo.pack(side=tk.LEFT, padx=(10, 20))
        
        ttk.Label(iqa_frame, text="Quality Threshold:").pack(side=tk.LEFT)
        threshold_spin = ttk.Spinbox(iqa_frame, from_=0.05, to=0.50, increment=0.05,
                                    textvariable=self.quality_threshold_var,
                                    width=10, format="%.2f")
        threshold_spin.pack(side=tk.LEFT, padx=(10, 0))
        
        ttk.Label(iqa_frame, text="(top % of images to process)").pack(side=tk.LEFT, padx=(5, 0))
        
        # 3. AI Model Selection
        model_frame = ttk.LabelFrame(main_frame, text="3. AI Model Configuration", padding="10")
        model_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Model Type Selection
        model_type_frame = ttk.Frame(model_frame)
        model_type_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(model_type_frame, text="AI Model:").pack(side=tk.LEFT)
        
        model_radio_frame = ttk.Frame(model_type_frame)
        model_radio_frame.pack(side=tk.LEFT, padx=(10, 0))
        
        ttk.Radiobutton(model_radio_frame, text="Google Gemini", variable=self.model_type_var, 
                       value="gemini").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Radiobutton(model_radio_frame, text="Ollama LLaVA", variable=self.model_type_var, 
                       value="ollama").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Radiobutton(model_radio_frame, text="BakLLaVA", variable=self.model_type_var, 
                       value="bakllava").pack(side=tk.LEFT)
        
        # API Key Entry
        api_frame = ttk.Frame(model_frame)
        api_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(api_frame, text="Google API Key:").pack(side=tk.LEFT)
        api_entry = ttk.Entry(api_frame, textvariable=self.api_key_var, show="*", width=40)
        api_entry.pack(side=tk.LEFT, padx=(10, 0), fill=tk.X, expand=True)
        
        # 4. Processing Options
        options_frame = ttk.LabelFrame(main_frame, text="4. Processing Options", padding="10")
        options_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Note: IPTC metadata is always embedded directly in image files for maximum website compatibility
        ttk.Label(options_frame, text="✓ IPTC Metadata (Embedded directly in image files)", 
                 font=('Arial', 10)).pack(anchor=tk.W, pady=2)
        ttk.Label(options_frame, text="   ↳ Industry standard for websites and stock photo platforms", 
                 font=('Arial', 9), foreground='gray').pack(anchor=tk.W)
        
        ttk.Checkbutton(options_frame, text="Generate Curatorial Descriptions", 
                       variable=self.generate_curator_var).pack(anchor=tk.W, pady=(10, 2))
        ttk.Label(options_frame, text="   ↳ Requires API key, adds detailed artistic analysis", 
                 font=('Arial', 9), foreground='gray').pack(anchor=tk.W)
        
        ttk.Checkbutton(options_frame, text="Include Subfolders (Recursive Search)", 
                       variable=self.recursive_var).pack(anchor=tk.W, pady=(10, 2))
        ttk.Label(options_frame, text="   ↳ Process images in subdirectories recursively", 
                 font=('Arial', 9), foreground='gray').pack(anchor=tk.W)
        
        # 5. Action Buttons
        action_frame = ttk.Frame(main_frame)
        action_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.start_button = ttk.Button(action_frame, text=" Start Multi-Stage Analysis", 
                                      command=self.start_analysis, style='Accent.TButton')
        self.start_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.stop_button = ttk.Button(action_frame, text="⏹ Stop Processing", 
                                     command=self.stop_processing, state='disabled')
        self.stop_button.pack(side=tk.LEFT)
        
        # Progress Section
        progress_frame = ttk.LabelFrame(main_frame, text="Processing Status", padding="10")
        progress_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, 
                                           mode='determinate')
        self.progress_bar.pack(fill=tk.X, pady=(0, 10))
        
        # Status text area with scrollbar
        text_frame = ttk.Frame(progress_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_text = tk.Text(text_frame, state='disabled', wrap='word', height=15,
                               font=('Consolas', 9))
        scrollbar = ttk.Scrollbar(text_frame, orient='vertical', command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Apply modern styling
        self.apply_styling()
        
    def apply_styling(self):
        """Apply modern styling to the application"""
        style = ttk.Style()
        
        # Try to use a modern theme
        try:
            style.theme_use('clam')
        except:
            pass
            
        # Configure custom accent button style
        style.configure('Accent.TButton', font=('Arial', 10, 'bold'))
        
    def _load_environment_config(self):
        """Load configuration from environment variables"""
        # Load Google API key from environment if available
        google_api_key = os.environ.get('GOOGLE_API_KEY', '')
        if google_api_key:
            self.api_key_var.set(google_api_key)
            self.log("[INFO] Loaded Google API key from environment variable")
    
    def on_model_change(self):
        """Handle model type change to show/hide RTX options"""
        # This will be implemented when we add the RTX UI components
        pass
    
    def on_rtx_toggle(self):
        """Handle RTX enable/disable toggle"""
        # This will be implemented when we add the RTX UI components
        pass
    
    def on_gpu_layers_change(self, value):
        """Update GPU layers label"""
        # This will be implemented when we add the RTX UI components
        pass
    
    def on_mode_change(self):
        """Handle processing mode change"""
        if self.processing_mode_var.get() == "archive":
            self.log("[INFO] Archive Mode selected - will process ALL images")
        else:
            self.log("[INFO] Curated Mode selected - will process top quality images only")
        
    def select_directory(self):
        """Open directory selection dialog"""
        directory = filedialog.askdirectory()
        if directory:
            self.directory.set(directory)
            self.log(f" Selected directory: {directory}")
            
    def log(self, message):
        """Add message to the status log"""
        self.log_text.config(state='normal')
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')
        self.root.update_idletasks()
    
    def start_analysis(self):
        """Start the multi-stage processing pipeline"""
        # Validate inputs
        if not os.path.isdir(self.directory.get()):
            messagebox.showerror("Error", "Please select a valid directory containing images.")
            return
        
        if self.model_type_var.get() == "gemini" and not self.api_key_var.get():
            messagebox.showerror("Error", "Please provide a Google API key for Gemini model.")
            return
            
        if self.is_processing:
            messagebox.showwarning("Warning", "Analysis is already in progress.")
            return
        
        # Clear previous log
        self.log_text.config(state='normal')
        self.log_text.delete('1.0', tk.END)
        self.log_text.config(state='disabled')
        
        # Update UI state
        self.is_processing = True
        self.start_button.config(state='disabled')
        self.stop_button.config(state='normal')
        self.progress_var.set(0)
        
        # Prepare pipeline configuration
        import os
        exiftool_path = os.path.join(os.path.dirname(__file__), 'exiftoolapp', 'exiftool.exe')
        
        pipeline_config = {
            'model_type': self.model_type_var.get(),
            'google_api_key': self.api_key_var.get(),
            'gemini_model': 'gemini-2.0-flash-exp',
            'ollama_url': 'http://localhost:11434',
            'model': 'llava:13b',
            'enable_gallery_critique': self.generate_curator_var.get(),
            'prompt_profile': 'professional_art_critic',
            'quality_threshold': self.quality_threshold_var.get(),
            'iqa_model': self.iqa_model_var.get(),
            'use_exif': self.use_exif_var.get(),
            'recursive': self.recursive_var.get(),
            'exiftool_path': exiftool_path if os.path.exists(exiftool_path) else None
        }
        
        self.log(" Starting Multi-Stage Processing Pipeline...")
        self.log(f" Configuration: {self.iqa_model_var.get().upper()} IQA, top {self.quality_threshold_var.get()*100:.0f}% quality threshold")
        self.log(f"[INFO] AI Model: {self.model_type_var.get().upper()}")
        self.log(f"💾 Metadata: IPTC embedded directly in image files")
        self.log(f" Search mode: {'Recursive (includes subfolders)' if self.recursive_var.get() else 'Current directory only'}")
        
        # Start processing in separate thread
        def run_pipeline():
            try:
                pipeline = MultiStageProcessingPipeline(pipeline_config)
                
                # Choose processing mode
                if self.processing_mode_var.get() == "archive":
                    # Archive Mode: Process ALL images
                    def status_callback(msg):
                        self.status_queue.put(msg)
                    
                    results = pipeline.process_all_images_archive_mode(
                        self.directory.get(),
                        status_callback=status_callback
                    )
                else:
                    # Curated Mode: Process top quality images only
                    results = pipeline.process_directory(
                        self.directory.get(),
                        status_queue=self.status_queue
                    )
                
                # Signal completion
                self.status_queue.put("PIPELINE_COMPLETE")
                self.status_queue.put(results)
                
            except Exception as e:
                self.status_queue.put(f"ERROR: {str(e)}")
                self.status_queue.put("PIPELINE_ERROR")
        
        self.pipeline_thread = threading.Thread(target=run_pipeline, daemon=True)
        self.pipeline_thread.start()
    
    def stop_processing(self):
        """Stop the current processing"""
        if self.is_processing:
            self.log("⏹ Stopping processing...")
            self.is_processing = False
            self.start_button.config(state='normal')
            self.stop_button.config(state='disabled')
            # Note: The actual pipeline stopping would need to be implemented
            # in the pipeline classes with a stop flag
    
    def schedule_queue_check(self):
        """Schedule periodic checking of the status queue"""
        self.process_queue()
        self.root.after(100, self.schedule_queue_check)
    
    def process_queue(self):
        """Process messages from the status queue"""
        try:
            while True:
                message = self.status_queue.get_nowait()
                
                if message == "PIPELINE_COMPLETE":
                    # Get the results
                    results = self.status_queue.get_nowait()
                    self.handle_completion(results)
                elif message == "PIPELINE_ERROR":
                    self.handle_error()
                elif isinstance(message, str) and message.startswith("ERROR:"):
                    self.log(f" {message}")
                else:
                    # Regular status message
                    self.log(message)
                    
        except queue.Empty:
            pass
    
    def handle_completion(self, results):
        """Handle successful pipeline completion"""
        self.is_processing = False
        self.start_button.config(state='normal')
        self.stop_button.config(state='disabled')
        self.progress_var.set(100)
        
        # Handle both curated and archive mode results
        mode = results.get('mode', 'curated')
        total_found = results.get('total_images_found', 0)
        analyzed = results.get('images_analyzed', 0)
        written = results.get('metadata_written', 0)
        processing_time = results.get('processing_time', 0)
        ai_model = results.get('ai_model', 'unknown')
        
        if mode == 'archive_all_images':
            # Archive mode summary
            stats = results.get('archive_statistics', {})
            avg_rating = stats.get('average_rating', 0)
            five_star = stats.get('five_star_images', 0)
            
            summary = f"""
🗂️ Archive Processing Complete!

 Processing Summary:
   • Total images found: {total_found}
   • Images analyzed and tagged: {analyzed}
   • Metadata files written: {written}
   • Processing time: {processing_time:.1f} seconds
   • Average rating: {avg_rating:.2f}/5 stars
   • Gallery-worthy (5⭐): {five_star} images
   • AI analysis model: {ai_model.upper()}

 All images in your archive are now searchable!
            """
            
            dialog_msg = f"Archive Processing Complete!\n\n" \
                        f"Tagged {analyzed} images for searchable archive\n" \
                        f"Processing time: {processing_time:.1f} seconds\n" \
                        f"Average quality: {avg_rating:.2f}/5 stars"
        else:
            # Curated mode summary  
            iqa_model = results.get('iqa_model', 'unknown')
            
            summary = f"""
📷 Curated Processing Complete!

 Processing Summary:
   • Total images found: {total_found}
   • High-quality images analyzed: {analyzed}
   • Metadata files written: {written}
   • Processing time: {processing_time:.1f} seconds
   • Quality assessment: {iqa_model.upper()}
   • AI analysis model: {ai_model.upper()}

 Top-quality images have been processed and tagged!
            """
            
            dialog_msg = f"Successfully processed {analyzed} high-quality images!\n\n" \
                        f"Processing time: {processing_time:.1f} seconds\n" \
                        f"Metadata written: {written} files"
        
        self.log(summary)
        messagebox.showinfo("Processing Complete", dialog_msg)
    
    def handle_error(self):
        """Handle pipeline error"""
        self.is_processing = False
        self.start_button.config(state='normal')
        self.stop_button.config(state='disabled')
        self.log(" Processing failed. Check the error messages above.")
        messagebox.showerror("Processing Error", 
                           "An error occurred during processing. Please check the log for details.")
    
    def run(self):
        """Start the GUI application"""
        self.root.mainloop()


def main():
    """Main entry point"""
    try:
        app = ImageAnalyzerApp()
        app.run()
    except Exception as e:
        import traceback
        error_msg = f"Application failed to start: {e}\n\nTraceback:\n{traceback.format_exc()}"
        print(error_msg)
        
        # Try to show error dialog
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("Startup Error", error_msg)
        except:
            pass


if __name__ == "__main__":
    main()
