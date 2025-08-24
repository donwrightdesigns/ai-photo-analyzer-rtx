#!/usr/bin/env python3
# ----------------------------------------------------------------------
#  AI Image Analyzer - Streamlined GUI Application v2.0
#  
#  Clean, professional interface with separate settings dialog
#  Features:
#  - Streamlined main GUI focused on folder selection and processing
#  - Separate settings dialog for configuration
#  - Floating status overlay (NVIDIA-style)
#  - Persistent configuration
#  - GPU auto-detection and recommendations
# ----------------------------------------------------------------------

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import threading
import queue
import time
import json
import platform
from pathlib import Path
from pipeline_core import MultiStageProcessingPipeline

class ConfigManager:
    """Handles persistent configuration storage"""
    
    def __init__(self):
        self.config_dir = Path.home() / ".ai-image-analyzer"
        self.config_file = self.config_dir / "config.json"
        self.config_dir.mkdir(exist_ok=True)
        
        # Default configuration
        self.defaults = {
            "model_type": "gemini",
            "google_api_key": "",
            "quality_threshold": 0.10,
            "iqa_model": "brisque",
            "use_exif": False,
            "generate_curator": False,
            "persona_profile": "professional_art_critic",
            "enable_rtx": True,
            "rtx_gpu_layers": 35,
            "rtx_batch_size": "512",
            "rtx_max_vram": 8.0,
            "gemini_model": "gemini-2.0-flash-exp",
            "ollama_url": "http://localhost:11434",
            "ollama_model": "llava:13b"
        }
        
    def load_config(self):
        """Load configuration from file"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                # Merge with defaults to handle new settings
                merged = self.defaults.copy()
                merged.update(config)
                return merged
            return self.defaults.copy()
        except Exception as e:
            print(f"Error loading config: {e}")
            return self.defaults.copy()
    
    def save_config(self, config):
        """Save configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False

class GPUDetector:
    """Auto-detect GPU capabilities and provide recommendations"""
    
    @staticmethod
    def detect_gpu():
        """Detect available GPU and return recommendations"""
        try:
            import torch
            if torch.cuda.is_available():
                gpu_name = torch.cuda.get_device_name(0)
                gpu_memory = torch.cuda.get_device_properties(0).total_memory / (1024**3)  # GB
                
                # RTX recommendations based on GPU
                if "RTX 4090" in gpu_name or "RTX 4080" in gpu_name:
                    return {
                        "gpu_name": gpu_name,
                        "gpu_memory": gpu_memory,
                        "recommended_layers": 45,
                        "recommended_batch": "1024",
                        "recommended_vram": min(16.0, gpu_memory * 0.8)
                    }
                elif "RTX 40" in gpu_name or "RTX 30" in gpu_name:
                    return {
                        "gpu_name": gpu_name,
                        "gpu_memory": gpu_memory,
                        "recommended_layers": 35,
                        "recommended_batch": "512",
                        "recommended_vram": min(12.0, gpu_memory * 0.8)
                    }
                elif "RTX" in gpu_name or "GTX" in gpu_name:
                    return {
                        "gpu_name": gpu_name,
                        "gpu_memory": gpu_memory,
                        "recommended_layers": 25,
                        "recommended_batch": "256",
                        "recommended_vram": min(8.0, gpu_memory * 0.7)
                    }
                else:
                    return {
                        "gpu_name": gpu_name,
                        "gpu_memory": gpu_memory,
                        "recommended_layers": 20,
                        "recommended_batch": "256",
                        "recommended_vram": min(6.0, gpu_memory * 0.6)
                    }
        except:
            pass
        
        return {
            "gpu_name": "CPU Only",
            "gpu_memory": 0,
            "recommended_layers": 0,
            "recommended_batch": "128",
            "recommended_vram": 0
        }

class StatusDisplay:
    """Header status display widget"""
    
    def __init__(self, parent_frame):
        self.parent_frame = parent_frame
        self.status_frame = None
        
    def create_status_display(self):
        """Create the status display in header"""
        self.status_frame = tk.Frame(self.parent_frame, bg='#f0f0f0', relief='sunken', bd=1)
        
        # Create status labels in a horizontal layout
        self.model_label = tk.Label(self.status_frame, bg='#f0f0f0', fg='#006600', font=('Arial', 9, 'bold'))
        self.model_label.pack(side=tk.LEFT, padx=(5, 15))
        
        self.gpu_label = tk.Label(self.status_frame, bg='#f0f0f0', fg='#0066cc', font=('Arial', 9, 'bold'))
        self.gpu_label.pack(side=tk.LEFT, padx=(0, 15))
        
        self.quality_label = tk.Label(self.status_frame, bg='#f0f0f0', fg='#cc6600', font=('Arial', 9, 'bold'))
        self.quality_label.pack(side=tk.LEFT, padx=(0, 15))
        
        self.metadata_label = tk.Label(self.status_frame, bg='#f0f0f0', fg='#660066', font=('Arial', 9, 'bold'))
        self.metadata_label.pack(side=tk.LEFT, padx=(0, 5))
        
        return self.status_frame
        
    def update_status(self, config):
        """Update the status display"""
        if not self.status_frame:
            return
            
        model_text = f"Model: {config.get('model_type', 'Unknown').upper()}"
        
        gpu_enabled = config.get('enable_rtx', False) and config.get('model_type') in ['bakllava', 'llava_standalone', 'llava_13b']
        gpu_text = f"GPU: {'RTX Enabled' if gpu_enabled else 'CPU Only'}"
        
        quality_text = f"Quality: {config.get('quality_threshold', 0.1)*100:.0f}%"
        
        metadata_text = f"Metadata: {'EXIF' if config.get('use_exif', False) else 'XMP'}"
        
        self.model_label.config(text=model_text)
        self.gpu_label.config(text=gpu_text)
        self.quality_label.config(text=quality_text)
        self.metadata_label.config(text=metadata_text)

class SettingsDialog:
    """Separate settings dialog window"""
    
    def __init__(self, parent, config_manager, on_config_change):
        self.parent = parent
        self.config_manager = config_manager
        self.on_config_change = on_config_change
        self.config = config_manager.load_config()
        self.gpu_info = GPUDetector.detect_gpu()
        self.dialog = None
        
        # Create tkinter variables
        self.setup_variables()
        
    def setup_variables(self):
        """Setup tkinter variables from config"""
        self.model_type_var = tk.StringVar(value=self.config.get("model_type", "gemini"))
        self.api_key_var = tk.StringVar(value=self.config.get("google_api_key", ""))
        self.quality_threshold_var = tk.DoubleVar(value=self.config.get("quality_threshold", 0.10))
        self.iqa_model_var = tk.StringVar(value=self.config.get("iqa_model", "brisque"))
        self.use_exif_var = tk.BooleanVar(value=self.config.get("use_exif", False))
        self.generate_curator_var = tk.BooleanVar(value=self.config.get("generate_curator", False))
        self.persona_profile_var = tk.StringVar(value=self.config.get("persona_profile", "professional_art_critic"))
        self.enable_rtx_var = tk.BooleanVar(value=self.config.get("enable_rtx", True))
        self.rtx_gpu_layers_var = tk.IntVar(value=self.config.get("rtx_gpu_layers", 35))
        self.rtx_batch_size_var = tk.StringVar(value=self.config.get("rtx_batch_size", "512"))
        self.rtx_max_vram_var = tk.DoubleVar(value=self.config.get("rtx_max_vram", 8.0))
    
    def show_dialog(self):
        """Show the settings dialog"""
        if self.dialog:
            self.dialog.lift()
            return
            
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Settings - AI Image Analyzer")
        self.dialog.geometry("600x700")
        self.dialog.resizable(False, False)
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # Handle dialog closing
        self.dialog.protocol("WM_DELETE_WINDOW", self.on_cancel)
        
        self.setup_dialog_ui()
        
        # Center on parent
        self.dialog.update_idletasks()
        x = self.parent.winfo_x() + (self.parent.winfo_width() // 2) - (self.dialog.winfo_width() // 2)
        y = self.parent.winfo_y() + (self.parent.winfo_height() // 2) - (self.dialog.winfo_height() // 2)
        self.dialog.geometry(f"+{x}+{y}")
        
    def setup_dialog_ui(self):
        """Setup the settings dialog UI"""
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create scrollable frame
        canvas = tk.Canvas(main_frame)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # 1. API Configuration Section
        api_frame = ttk.LabelFrame(scrollable_frame, text="API Configuration", padding="10")
        api_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(api_frame, text="Google API Key:").pack(anchor=tk.W)
        api_entry = ttk.Entry(api_frame, textvariable=self.api_key_var, show="*", width=60)
        api_entry.pack(fill=tk.X, pady=(5, 5))
        
        env_key = os.environ.get('GOOGLE_API_KEY', '')
        if env_key:
            ttk.Label(api_frame, text="✅ API key loaded from environment variable", 
                     foreground='green', font=('Arial', 9)).pack(anchor=tk.W)
        
        ttk.Label(api_frame, text="Get your API key from Google AI Studio", 
                 foreground='blue', font=('Arial', 9)).pack(anchor=tk.W)
        
        # 2. Model Selection Section
        model_frame = ttk.LabelFrame(scrollable_frame, text="AI Model Selection", padding="10")
        model_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Radiobutton(model_frame, text="🖥️ LLaVA 13B (Local, GPU-Optimized, Recommended)", 
                       variable=self.model_type_var, value="llava_13b",
                       command=self.on_model_change).pack(anchor=tk.W, pady=5)
        
        ttk.Radiobutton(model_frame, text="🌐 Google Gemini (Cloud-based, Fast Fallback)", 
                       variable=self.model_type_var, value="gemini",
                       command=self.on_model_change).pack(anchor=tk.W, pady=5)
        
        # Model info
        info_frame = ttk.Frame(model_frame)
        info_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Label(info_frame, text="💡 LLaVA 13B is recommended for best performance and privacy. Gemini provides cloud backup.",
                 font=('Arial', 9), foreground='blue').pack(anchor=tk.W)
        
        # Download Models Section
        download_frame = ttk.Frame(model_frame)
        download_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(download_frame, text="📥 Download Local Models", 
                  command=self.show_model_download).pack(side=tk.LEFT)
        
        ttk.Label(download_frame, text="Download compatible local models", 
                 font=('Arial', 9), foreground='gray').pack(side=tk.LEFT, padx=(10, 0))
        
        # 3. GPU Optimization Section
        self.gpu_frame = ttk.LabelFrame(scrollable_frame, text="🚀 GPU Optimization", padding="10")
        self.gpu_frame.pack(fill=tk.X, pady=(0, 10))
        
        # GPU Detection Info
        gpu_info_frame = ttk.Frame(self.gpu_frame)
        gpu_info_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(gpu_info_frame, text=f"Detected GPU: {self.gpu_info['gpu_name']}", 
                 font=('Arial', 10, 'bold')).pack(anchor=tk.W)
        
        if self.gpu_info['gpu_memory'] > 0:
            ttk.Label(gpu_info_frame, text=f"VRAM: {self.gpu_info['gpu_memory']:.1f} GB", 
                     font=('Arial', 9)).pack(anchor=tk.W)
        
        # RTX Enable Checkbox
        rtx_check = ttk.Checkbutton(self.gpu_frame, text="Enable RTX GPU Acceleration", 
                                   variable=self.enable_rtx_var, command=self.on_rtx_toggle)
        rtx_check.pack(anchor=tk.W, pady=(0, 10))
        
        # RTX Settings
        self.rtx_settings_frame = ttk.Frame(self.gpu_frame)
        self.rtx_settings_frame.pack(fill=tk.X, padx=(20, 0))
        
        # GPU Layers
        layers_frame = ttk.Frame(self.rtx_settings_frame)
        layers_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(layers_frame, text="GPU Layers:").pack(side=tk.LEFT)
        self.layers_scale = ttk.Scale(layers_frame, from_=0, to=50, 
                                     variable=self.rtx_gpu_layers_var, 
                                     orient='horizontal', length=200,
                                     command=self.on_gpu_layers_change)
        self.layers_scale.pack(side=tk.LEFT, padx=(10, 10))
        self.layers_label = ttk.Label(layers_frame, text=f"{self.rtx_gpu_layers_var.get()}/50")
        self.layers_label.pack(side=tk.LEFT)
        
        # Batch Size
        batch_frame = ttk.Frame(self.rtx_settings_frame)
        batch_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(batch_frame, text="Batch Size:").pack(side=tk.LEFT)
        batch_combo = ttk.Combobox(batch_frame, textvariable=self.rtx_batch_size_var,
                                  values=['128', '256', '512', '1024'], state='readonly', width=10)
        batch_combo.pack(side=tk.LEFT, padx=(10, 0))
        
        # VRAM Limit
        vram_frame = ttk.Frame(self.rtx_settings_frame)
        vram_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(vram_frame, text="Max VRAM (GB):").pack(side=tk.LEFT)
        vram_spin = ttk.Spinbox(vram_frame, from_=4.0, to=24.0, increment=1.0,
                               textvariable=self.rtx_max_vram_var, width=8, format="%.1f")
        vram_spin.pack(side=tk.LEFT, padx=(10, 0))
        
        # Recommendations
        if self.gpu_info['gpu_memory'] > 0:
            rec_frame = ttk.Frame(self.rtx_settings_frame)
            rec_frame.pack(fill=tk.X, pady=(10, 0))
            
            ttk.Button(rec_frame, text="📋 Apply Recommended Settings", 
                      command=self.apply_gpu_recommendations).pack(side=tk.LEFT)
            
            rec_text = f"Recommended: {self.gpu_info['recommended_layers']} layers, {self.gpu_info['recommended_batch']} batch, {self.gpu_info['recommended_vram']:.1f}GB"
            ttk.Label(rec_frame, text=rec_text, font=('Arial', 8), 
                     foreground='blue').pack(side=tk.LEFT, padx=(10, 0))
        
        # 4. Quality Assessment Section
        quality_frame = ttk.LabelFrame(scrollable_frame, text="Quality Assessment", padding="10")
        quality_frame.pack(fill=tk.X, pady=(0, 10))
        
        iqa_frame = ttk.Frame(quality_frame)
        iqa_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(iqa_frame, text="IQA Model:").pack(side=tk.LEFT)
        iqa_combo = ttk.Combobox(iqa_frame, textvariable=self.iqa_model_var,
                                values=['brisque', 'niqe', 'musiq', 'topiq'],
                                state='readonly', width=15)
        iqa_combo.pack(side=tk.LEFT, padx=(10, 20))
        
        threshold_frame = ttk.Frame(quality_frame)
        threshold_frame.pack(fill=tk.X)
        
        ttk.Label(threshold_frame, text="Quality Threshold:").pack(side=tk.LEFT)
        threshold_spin = ttk.Spinbox(threshold_frame, from_=0.05, to=0.50, increment=0.05,
                                    textvariable=self.quality_threshold_var,
                                    width=10, format="%.2f")
        threshold_spin.pack(side=tk.LEFT, padx=(10, 10))
        
        ttk.Label(threshold_frame, text="(top % of images to process)", 
                 font=('Arial', 9), foreground='gray').pack(side=tk.LEFT)
        
        # 5. Processing Options Section
        processing_frame = ttk.LabelFrame(scrollable_frame, text="Processing Options", padding="10")
        processing_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Checkbutton(processing_frame, text="Write metadata to EXIF (embeds in image files)", 
                       variable=self.use_exif_var).pack(anchor=tk.W, pady=2)
        ttk.Label(processing_frame, text="   ↳ Default: XMP sidecar files (non-destructive)", 
                 font=('Arial', 9), foreground='gray').pack(anchor=tk.W)
        
        ttk.Checkbutton(processing_frame, text="Generate curatorial descriptions (requires API key)", 
                       variable=self.generate_curator_var).pack(anchor=tk.W, pady=(10, 2))
        ttk.Label(processing_frame, text="   ↳ Adds detailed artistic analysis and critique", 
                 font=('Arial', 9), foreground='gray').pack(anchor=tk.W)
        
        # 6. Analysis Persona Selection
        persona_frame = ttk.LabelFrame(scrollable_frame, text="🎭 Analysis Persona", padding="10")
        persona_frame.pack(fill=tk.X, pady=(0, 10))
        
        persona_selection_frame = ttk.Frame(persona_frame)
        persona_selection_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(persona_selection_frame, text="Evaluation Perspective:").pack(side=tk.LEFT)
        
        # Define persona options with display names
        persona_options = [
            ("professional_art_critic", "🎨 Professional Art Critic"),
            ("street_photographer", "📷 Street Photographer"),
            ("commercial_photographer", "💼 Commercial Photographer"),
            ("photojournalist", "📰 Photojournalist"),
            ("social_media_influencer", "📱 Social Media Influencer")
        ]
        
        persona_combo = ttk.Combobox(persona_selection_frame, textvariable=self.persona_profile_var,
                                    values=[display for _, display in persona_options],
                                    state='readonly', width=30)
        persona_combo.pack(side=tk.LEFT, padx=(10, 0))
        
        # Set current selection based on stored value
        current_persona = self.config.get('persona_profile', 'professional_art_critic')
        for key, display in persona_options:
            if key == current_persona:
                persona_combo.set(display)
                break
        
        # Store mapping for later retrieval
        self.persona_mapping = {display: key for key, display in persona_options}
        
        ttk.Label(persona_frame, text="🔍 Choose the evaluation perspective for image analysis and descriptions.", 
                 font=('Arial', 9), foreground='blue').pack(anchor=tk.W, pady=(10, 0))
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Button frame
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(fill=tk.X, padx=20, pady=(10, 20))
        
        ttk.Button(button_frame, text="Cancel", command=self.on_cancel).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="Apply", command=self.on_apply).pack(side=tk.RIGHT)
        ttk.Button(button_frame, text="OK", command=self.on_ok).pack(side=tk.RIGHT, padx=(0, 5))
        
        # Initialize UI state
        self.on_model_change()
        self.on_rtx_toggle()
        
    def on_model_change(self):
        """Handle model selection change"""
        model = self.model_type_var.get()
        if model in ['bakllava', 'llava_standalone', 'llava_13b']:
            self.gpu_frame.pack(fill=tk.X, pady=(0, 10))
        else:
            self.gpu_frame.pack_forget()
    
    def on_rtx_toggle(self):
        """Handle RTX toggle"""
        if hasattr(self, 'rtx_settings_frame'):
            if self.enable_rtx_var.get():
                for widget in self.rtx_settings_frame.winfo_children():
                    widget.pack()
            else:
                for widget in self.rtx_settings_frame.winfo_children():
                    widget.pack_forget()
    
    def on_gpu_layers_change(self, value):
        """Update GPU layers label"""
        layers = int(float(value))
        self.rtx_gpu_layers_var.set(layers)
        if hasattr(self, 'layers_label'):
            self.layers_label.config(text=f"{layers}/50")
    
    def apply_gpu_recommendations(self):
        """Apply recommended GPU settings"""
        self.rtx_gpu_layers_var.set(self.gpu_info['recommended_layers'])
        self.rtx_batch_size_var.set(self.gpu_info['recommended_batch'])
        self.rtx_max_vram_var.set(self.gpu_info['recommended_vram'])
        self.on_gpu_layers_change(self.gpu_info['recommended_layers'])
    
    def show_model_download(self):
        """Show model download options"""
        download_dialog = tk.Toplevel(self.dialog)
        download_dialog.title("Download Local Models")
        download_dialog.geometry("500x400")
        download_dialog.transient(self.dialog)
        download_dialog.grab_set()
        
        main_frame = ttk.Frame(download_dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main_frame, text="Available Local Models", 
                 font=('Arial', 14, 'bold')).pack(pady=(0, 20))
        
        # BakLLaVA Models
        bakllava_frame = ttk.LabelFrame(main_frame, text="BakLLaVA Models", padding="10")
        bakllava_frame.pack(fill=tk.X, pady=(0, 10))
        
        models = [
            ("BakLLaVA-1-Q4_K_M.gguf", "4-bit quantized", "~4GB", "Balanced speed/quality"),
            ("BakLLaVA-1-Q8_0.gguf", "8-bit quantized", "~7GB", "Higher quality"),
            ("BakLLaVA-1-F16.gguf", "Full precision", "~13GB", "Maximum quality")
        ]
        
        for model_name, quant, size, desc in models:
            model_frame = ttk.Frame(bakllava_frame)
            model_frame.pack(fill=tk.X, pady=2)
            
            ttk.Label(model_frame, text=f"• {model_name}", font=('Arial', 9, 'bold')).pack(anchor=tk.W)
            ttk.Label(model_frame, text=f"  {quant} | {size} | {desc}", 
                     font=('Arial', 8), foreground='gray').pack(anchor=tk.W)
            
            ttk.Button(model_frame, text="Download", 
                      command=lambda m=model_name: self.download_model(m)).pack(anchor=tk.E)
        
        ttk.Button(main_frame, text="Close", 
                  command=download_dialog.destroy).pack(pady=(20, 0))
    
    def download_model(self, model_name):
        """Download a specific model"""
        messagebox.showinfo("Download", f"Model download for {model_name} would be implemented here.\n\nThis will integrate with the existing download scripts.")
    
    def get_config(self):
        """Get current configuration from UI"""
        # Convert persona display name back to key
        persona_display = self.persona_profile_var.get()
        persona_key = getattr(self, 'persona_mapping', {}).get(persona_display, 'professional_art_critic')
        
        return {
            "model_type": self.model_type_var.get(),
            "google_api_key": self.api_key_var.get(),
            "quality_threshold": self.quality_threshold_var.get(),
            "iqa_model": self.iqa_model_var.get(),
            "use_exif": self.use_exif_var.get(),
            "generate_curator": self.generate_curator_var.get(),
            "persona_profile": persona_key,
            "enable_rtx": self.enable_rtx_var.get(),
            "rtx_gpu_layers": self.rtx_gpu_layers_var.get(),
            "rtx_batch_size": self.rtx_batch_size_var.get(),
            "rtx_max_vram": self.rtx_max_vram_var.get(),
            "gemini_model": "gemini-2.0-flash-exp",
            "ollama_url": "http://localhost:11434",
            "ollama_model": "llava:13b"
        }
    
    def on_ok(self):
        """Handle OK button"""
        self.on_apply()
        self.dialog.destroy()
        self.dialog = None
    
    def on_apply(self):
        """Handle Apply button"""
        config = self.get_config()
        if self.config_manager.save_config(config):
            self.config = config
            self.on_config_change(config)
            messagebox.showinfo("Settings", "Configuration saved successfully!")
        else:
            messagebox.showerror("Error", "Failed to save configuration.")
    
    def on_cancel(self):
        """Handle Cancel button"""
        self.dialog.destroy()
        self.dialog = None

class MainWindow:
    """Streamlined main application window"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("AI Image Analyzer v2.0")
        self.root.geometry("700x500")
        self.root.resizable(True, True)
        
        # Application state
        self.directory = tk.StringVar()
        self.recursive_var = tk.BooleanVar(value=True)
        self.status_queue = queue.Queue()
        self.pipeline_thread = None
        self.is_processing = False
        
        # Configuration management
        self.config_manager = ConfigManager()
        self.config = self.config_manager.load_config()
        
        # Settings dialog
        self.settings_dialog = SettingsDialog(self.root, self.config_manager, self.on_config_change)
        
        self.setup_ui()
        self.schedule_queue_check()
        
        # Initialize status display
        self.status_display.update_status(self.config)
        
    def setup_ui(self):
        """Create streamlined main UI"""
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title and Status Header
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Title row
        title_frame = ttk.Frame(header_frame)
        title_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(title_frame, text="AI Image Analyzer", 
                 font=('Arial', 18, 'bold')).pack(side=tk.LEFT)
        
        ttk.Button(title_frame, text="⚙️ Settings", 
                  command=self.show_settings).pack(side=tk.RIGHT)
        
        # Status display row
        self.status_display = StatusDisplay(header_frame)
        status_frame = self.status_display.create_status_display()
        status_frame.pack(fill=tk.X, pady=(5, 10))
        
        # Directory selection
        dir_frame = ttk.LabelFrame(main_frame, text="Select Images", padding="15")
        dir_frame.pack(fill=tk.X, pady=(10, 20))
        
        dir_entry_frame = ttk.Frame(dir_frame)
        dir_entry_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(dir_entry_frame, textvariable=self.directory).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(dir_entry_frame, text="📁 Browse", 
                  command=self.select_directory).pack(side=tk.RIGHT, padx=(10, 0))
        
        self.directory.set("No directory selected")
        
        # Options
        options_frame = ttk.Frame(dir_frame)
        options_frame.pack(fill=tk.X)
        
        ttk.Checkbutton(options_frame, text="Include subfolders", 
                       variable=self.recursive_var).pack(side=tk.LEFT)
        
        # Action buttons
        action_frame = ttk.Frame(main_frame)
        action_frame.pack(fill=tk.X, pady=(0, 20))
        
        self.start_button = ttk.Button(action_frame, text="🚀 Start Analysis", 
                                      command=self.start_analysis)
        self.start_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.stop_button = ttk.Button(action_frame, text="⏹ Stop", 
                                     command=self.stop_processing, state='disabled')
        self.stop_button.pack(side=tk.LEFT)
        
        # Progress section
        progress_frame = ttk.LabelFrame(main_frame, text="Progress", padding="15")
        progress_frame.pack(fill=tk.BOTH, expand=True)
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, 
                                           mode='determinate')
        self.progress_bar.pack(fill=tk.X, pady=(0, 10))
        
        # Status text area
        text_frame = ttk.Frame(progress_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_text = tk.Text(text_frame, state='disabled', wrap='word', height=12,
                               font=('Consolas', 9))
        scrollbar = ttk.Scrollbar(text_frame, orient='vertical', command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
    def show_settings(self):
        """Show settings dialog"""
        self.settings_dialog.show_dialog()
    
    def select_directory(self):
        """Open directory selection dialog"""
        directory = filedialog.askdirectory()
        if directory:
            self.directory.set(directory)
            self.log(f"📁 Selected directory: {directory}")
    
    def on_config_change(self, config):
        """Handle configuration changes"""
        self.config = config
        self.status_display.update_status(config)
        self.log("⚙️ Configuration updated")
    
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
        
        if self.config.get('model_type') == 'gemini' and not self.config.get('google_api_key'):
            messagebox.showerror("Error", "Please configure Google API key in Settings for Gemini model.")
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
        exiftool_path = os.path.join(os.path.dirname(__file__), 'exiftoolapp', 'exiftool.exe')
        
        pipeline_config = {
            'model_type': self.config.get('model_type'),
            'google_api_key': self.config.get('google_api_key'),
            'gemini_model': self.config.get('gemini_model'),
            'ollama_url': self.config.get('ollama_url'),
            'model': self.config.get('ollama_model'),
            'enable_gallery_critique': self.config.get('generate_curator'),
            'prompt_profile': self.config.get('persona_profile', 'professional_art_critic'),
            'quality_threshold': self.config.get('quality_threshold'),
            'iqa_model': self.config.get('iqa_model'),
            'use_exif': self.config.get('use_exif'),
            'recursive': self.recursive_var.get(),
            'exiftool_path': exiftool_path if os.path.exists(exiftool_path) else None,
            # RTX GPU settings
            'enable_rtx_optimization': self.config.get('enable_rtx'),
            'rtx_gpu_layers': self.config.get('rtx_gpu_layers'),
            'rtx_batch_size': int(self.config.get('rtx_batch_size', '512')),
            'rtx_max_vram_gb': self.config.get('rtx_max_vram')
        }
        
        self.log("🚀 Starting Multi-Stage Processing Pipeline...")
        self.log(f"📊 Configuration: {self.config.get('iqa_model', 'unknown').upper()} IQA, top {self.config.get('quality_threshold', 0.1)*100:.0f}%")
        self.log(f"🤖 AI Model: {self.config.get('model_type', 'unknown').upper()}")
        
        if self.config.get('enable_rtx') and self.config.get('model_type') in ['bakllava', 'ollama', 'gemma3', 'llava_13b']:
            self.log(f"🚀 GPU: RTX enabled ({self.config.get('rtx_gpu_layers')} layers, batch {self.config.get('rtx_batch_size')}, {self.config.get('rtx_max_vram'):.1f}GB)")
        
        self.log(f"📁 Search: {'Recursive' if self.recursive_var.get() else 'Current directory only'}")
        
        # Start processing in separate thread
        def run_pipeline():
            try:
                pipeline = MultiStageProcessingPipeline(pipeline_config)
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
                    results = self.status_queue.get_nowait()
                    self.handle_completion(results)
                elif message == "PIPELINE_ERROR":
                    self.handle_error()
                elif isinstance(message, str) and message.startswith("ERROR:"):
                    self.log(f"❌ {message}")
                else:
                    self.log(message)
                    
        except queue.Empty:
            pass
    
    def handle_completion(self, results):
        """Handle successful pipeline completion"""
        self.is_processing = False
        self.start_button.config(state='normal')
        self.stop_button.config(state='disabled')
        self.progress_var.set(100)
        
        # Display completion summary
        total_found = results.get('total_images_found', 0)
        analyzed = results.get('images_analyzed', 0)
        written = results.get('metadata_written', 0)
        processing_time = results.get('processing_time', 0)
        
        summary = f"""
🎉 Multi-Stage Pipeline Complete!

📊 Processing Summary:
   • Total images found: {total_found}
   • High-quality images analyzed: {analyzed}
   • Metadata files written: {written}
   • Processing time: {processing_time:.1f} seconds

✅ All selected images have been processed and tagged!
        """
        
        self.log(summary)
        messagebox.showinfo("Processing Complete", 
                           f"Successfully processed {analyzed} high-quality images!\n\n"
                           f"Processing time: {processing_time:.1f} seconds\n"
                           f"Metadata written: {written} files")
    
    def handle_error(self):
        """Handle pipeline error"""
        self.is_processing = False
        self.start_button.config(state='normal')
        self.stop_button.config(state='disabled')
        self.log("❌ Processing failed. Check the error messages above.")
        messagebox.showerror("Processing Error", 
                           "An error occurred during processing. Please check the log for details.")
    
    def run(self):
        """Start the GUI application"""
        self.root.mainloop()

def main():
    """Main entry point"""
    try:
        app = MainWindow()
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
