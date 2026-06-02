import os
import logging
from PIL import Image
import threading
from .resize import resize_image
from .converter import convert_and_save

class BatchProcessor:
    def __init__(self, file_paths, output_dir, settings, progress_callback, completion_callback):
        self.file_paths = file_paths
        self.output_dir = output_dir
        self.settings = settings
        self.progress_callback = progress_callback
        self.completion_callback = completion_callback
        self.cancel_requested = False
        
    def start(self):
        threading.Thread(target=self._process, daemon=True).start()
        
    def cancel(self):
        self.cancel_requested = True
        
    def _process(self):
        total = len(self.file_paths)
        results = []
        
        for i, file_path in enumerate(self.file_paths):
            if self.cancel_requested:
                break
                
            try:
                # Open image
                with Image.open(file_path) as img:
                    # Resize
                    resized_img = resize_image(
                        img, 
                        custom_width=self.settings.get('width'),
                        custom_height=self.settings.get('height')
                    )
                    
                    # Convert & Save
                    filename = os.path.basename(file_path)
                    name, _ = os.path.splitext(filename)
                    target_format = self.settings.get('format', 'JPEG').upper()
                    if target_format == 'JPG':
                        target_format = 'JPEG'
                    
                    ext = target_format.lower()
                    if ext == 'jpeg': ext = 'jpg'
                    
                    base_out_path = os.path.join(self.output_dir, f"{name}_compressed.{ext}")
                    out_path = base_out_path
                    counter = 1
                    while os.path.exists(out_path):
                        out_path = os.path.join(self.output_dir, f"{name}_compressed_{counter}.{ext}")
                        counter += 1
                    
                    target_size_kb = self.settings.get('target_size_kb')
                    
                    res = convert_and_save(resized_img, out_path, target_format, target_size_kb)
                    
                    results.append({
                        'file': file_path,
                        'success': res.get('success', False),
                        'final_size': res.get('final_size', 0),
                        'quality': res.get('quality', 100),
                        'error': res.get('error', '')
                    })
            except Exception as e:
                 logging.error(f"Batch processing error on {file_path}: {e}")
                 results.append({
                        'file': file_path,
                        'success': False,
                        'error': str(e)
                 })
                 
            # Update progress
            if self.progress_callback:
                self.progress_callback(i + 1, total, file_path)
                
        if self.completion_callback:
            self.completion_callback(results, self.cancel_requested)

