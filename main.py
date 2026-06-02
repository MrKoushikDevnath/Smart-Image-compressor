import os
import threading
import math
import logging
import customtkinter as ctk
from tkinterdnd2 import TkinterDnD, DND_FILES
from tkinter import filedialog, messagebox
from PIL import Image

from modules.batch import BatchProcessor
from modules.compressor import compress_image
from modules.resize import resize_image
from modules.settings import SettingsManager

os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    filename=os.path.join("logs", "app.log"),
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Apply basic styling
ctk.set_default_color_theme("blue")

class CustomTkinterDnD(ctk.CTk, TkinterDnD.DnDWrapper):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.TkdndVersion = TkinterDnD._require(self)

def format_size(size_bytes):
    if size_bytes == 0:
        return "0 B"
    size_name = ("B", "KB", "MB", "GB", "TB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"

class App(CustomTkinterDnD):
    def __init__(self):
        super().__init__()

        self.settings = SettingsManager()
        
        current_theme = self.settings.get("theme", "Dark")
        ctk.set_appearance_mode(current_theme)

        self.title("Smart Image Compressor Pro")
        self.geometry("1150x800")
        self.minsize(1000, 700)
        
        # Force maximize reliably (after the window loop initializes)
        self.after(200, lambda: self.state("zoomed"))
        
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.file_paths = []
        self.preview_image_path = None
        self.is_processing = False

        # Configure Grid
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.build_left_panel()
        self.build_right_panel()
        self.build_bottom_panel()

    def build_left_panel(self):
        self.left_panel = ctk.CTkFrame(self, width=320, corner_radius=0)
        self.left_panel.grid(row=0, column=0, rowspan=2, sticky="nsew")
        self.left_panel.grid_propagate(False)

        # Title
        title_lbl = ctk.CTkLabel(self.left_panel, text="Settings", font=ctk.CTkFont(size=24, weight="bold"))
        title_lbl.pack(pady=(20, 20), padx=20, anchor="w")

        # Format Converter
        ctk.CTkLabel(self.left_panel, text="Output Format", font=ctk.CTkFont(weight="bold")).pack(padx=20, anchor="w")
        saved_format = self.settings.get("format", "JPEG")
        self.format_var = ctk.StringVar(value=saved_format)
        self.format_dropdown = ctk.CTkComboBox(self.left_panel, values=["JPEG", "JPG", "PNG", "WEBP", "PDF"], variable=self.format_var, command=self.update_preview)
        self.format_dropdown.pack(pady=(5, 20), padx=20, fill="x")

        # Resize System
        ctk.CTkLabel(self.left_panel, text="Resize (Optional)", font=ctk.CTkFont(weight="bold")).pack(padx=20, anchor="w")
        
        resize_frame = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        resize_frame.pack(padx=20, pady=(5, 20), fill="x")
        
        self.width_entry = ctk.CTkEntry(resize_frame, placeholder_text="Width (px)", width=100)
        self.width_entry.pack(side="left", padx=(0, 10))
        self.width_entry.bind("<KeyRelease>", self.update_preview_delayed)
        
        self.height_entry = ctk.CTkEntry(resize_frame, placeholder_text="Height (px)", width=100)
        self.height_entry.pack(side="left")
        self.height_entry.bind("<KeyRelease>", self.update_preview_delayed)

        # Smart Compression
        ctk.CTkLabel(self.left_panel, text="Target File Size", font=ctk.CTkFont(weight="bold")).pack(padx=20, anchor="w")
        self.target_size_entry = ctk.CTkEntry(self.left_panel, placeholder_text="e.g. 500 (in KB)")
        self.target_size_entry.pack(pady=(5, 20), padx=20, fill="x")
        self.target_size_entry.bind("<KeyRelease>", self.update_preview_delayed)

        # Theme Toggle
        theme_frame = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        theme_frame.pack(side="bottom", pady=20, padx=20, fill="x")
        self.theme_var = ctk.StringVar(value=self.settings.get("theme", "Dark"))
        self.theme_switch = ctk.CTkSwitch(theme_frame, text="Dark Mode", variable=self.theme_var, onvalue="Dark", offvalue="Light", command=self.toggle_theme)
        self.theme_switch.pack(side="left")

    def build_right_panel(self):
        self.right_panel = ctk.CTkFrame(self)
        self.right_panel.grid(row=0, column=1, padx=20, pady=(20, 10), sticky="nsew")
        self.right_panel.grid_columnconfigure(0, weight=1)
        self.right_panel.grid_columnconfigure(1, weight=1)
        self.right_panel.grid_rowconfigure(1, weight=1)

        # Drop Area & Import buttons
        top_frame = ctk.CTkFrame(self.right_panel, fg_color="transparent")
        top_frame.grid(row=0, column=0, columnspan=2, pady=10, padx=10, sticky="ew")
        
        self.import_btn = ctk.CTkButton(top_frame, text="Select Images", command=self.select_files)
        self.import_btn.pack(side="left", padx=10)
        
        self.clear_btn = ctk.CTkButton(top_frame, text="Clear List", fg_color="#C62828", hover_color="#B71C1C", command=self.clear_files)
        self.clear_btn.pack(side="left", padx=10)
        
        self.file_count_lbl = ctk.CTkLabel(top_frame, text="0 files selected")
        self.file_count_lbl.pack(side="right", padx=10)

        # Preview Labels
        self.before_frame = ctk.CTkFrame(self.right_panel)
        self.before_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        ctk.CTkLabel(self.before_frame, text="Original Image", font=ctk.CTkFont(weight="bold")).pack(pady=10)
        self.before_img_lbl = ctk.CTkLabel(self.before_frame, text="Drag & Drop Images Here")
        self.before_img_lbl.pack(expand=True, fill="both", padx=10, pady=10)
        self.before_stats = ctk.CTkLabel(self.before_frame, text="", justify="left")
        self.before_stats.pack(pady=10)

        self.after_frame = ctk.CTkFrame(self.right_panel)
        self.after_frame.grid(row=1, column=1, padx=10, pady=10, sticky="nsew")
        ctk.CTkLabel(self.after_frame, text="Compressed Preview", font=ctk.CTkFont(weight="bold")).pack(pady=10)
        self.after_img_lbl = ctk.CTkLabel(self.after_frame, text="")
        self.after_img_lbl.pack(expand=True, fill="both", padx=10, pady=10)
        self.after_stats = ctk.CTkLabel(self.after_frame, text="", justify="left")
        self.after_stats.pack(pady=10)

        # Register Drag & Drop
        self.right_panel.drop_target_register(DND_FILES)
        self.right_panel.dnd_bind('<<Drop>>', self.handle_drop)
        self.before_frame.drop_target_register(DND_FILES)
        self.before_frame.dnd_bind('<<Drop>>', self.handle_drop)
        self.after_frame.drop_target_register(DND_FILES)
        self.after_frame.dnd_bind('<<Drop>>', self.handle_drop)

    def build_bottom_panel(self):
        self.bottom_panel = ctk.CTkFrame(self, height=80)
        self.bottom_panel.grid(row=1, column=1, padx=20, pady=(0, 20), sticky="nsew")
        self.bottom_panel.grid_columnconfigure(0, weight=1)

        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(self.bottom_panel)
        self.progress_bar.grid(row=0, column=0, padx=20, pady=(20, 5), sticky="ew")
        self.progress_bar.set(0)

        # Status text
        self.status_lbl = ctk.CTkLabel(self.bottom_panel, text="Ready")
        self.status_lbl.grid(row=1, column=0, padx=20, pady=(0, 10), sticky="w")

        # Export button
        self.export_btn = ctk.CTkButton(self.bottom_panel, text="Export Images", command=self.export_images, height=40, font=ctk.CTkFont(weight="bold"))
        self.export_btn.grid(row=0, column=1, rowspan=2, padx=20, pady=20)

    def toggle_theme(self):
        ctk.set_appearance_mode(self.theme_var.get())
        
    def on_closing(self):
        self.settings.set("theme", self.theme_var.get())
        self.settings.set("format", self.format_var.get())
        self.settings.save_settings()
        self.destroy()

    def select_files(self):
        try:
            files = filedialog.askopenfilenames(title="Select Images", filetypes=[("Image Files", "*.png *.jpg *.jpeg *.webp *.bmp")])
            if files:
                self.add_files(files)
        except Exception as e:
            logging.error(f"Error selecting files: {e}")
            messagebox.showerror("Error", "An error occurred while selecting files.")

    def handle_drop(self, event):
        try:
            # event.data contains paths separated by space or curly braces (if spaces in path)
            raw_data = event.data
            if "{" in raw_data:
                import re
                files = re.findall(r'\{([^}]+)\}', raw_data)
            else:
                files = raw_data.split()
                
            valid_files = [f for f in files if os.path.isfile(f) and f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.bmp'))]
            if valid_files:
                self.add_files(valid_files)
        except Exception as e:
            logging.error(f"Error handling dropped files: {e}")
            messagebox.showerror("Error", "An error occurred while processing dropped files.")

    def add_files(self, files):
        for f in files:
            if f not in self.file_paths:
                self.file_paths.append(f)
        
        self.file_count_lbl.configure(text=f"{len(self.file_paths)} files selected")
        if self.file_paths:
            self.preview_image_path = self.file_paths[0]
            self.update_preview()

    def clear_files(self):
        self.file_paths.clear()
        self.preview_image_path = None
        self.file_count_lbl.configure(text="0 files selected")
        self.before_img_lbl.configure(image="", text="Drag & Drop Images Here")
        self.after_img_lbl.configure(image="", text="")
        self.before_stats.configure(text="")
        self.after_stats.configure(text="")

    def update_preview_delayed(self, event=None):
        if hasattr(self, '_preview_timer'):
            self.after_cancel(self._preview_timer)
        self._preview_timer = self.after(500, self.update_preview)

    def update_preview(self, *args):
        if not self.preview_image_path:
            return
            
        try:
            # Show Before
            orig_img = Image.open(self.preview_image_path)
            orig_size = os.path.getsize(self.preview_image_path)
            orig_w, orig_h = orig_img.size
            orig_format = orig_img.format
            
            # Display Original Image
            self.display_image(orig_img, self.before_img_lbl)
            self.before_stats.configure(text=f"Size: {format_size(orig_size)}\nResolution: {orig_w}x{orig_h}\nFormat: {orig_format}")
            
            # Run "After" preview in thread to keep GUI responsive
            threading.Thread(target=self._process_preview, args=(self.preview_image_path, orig_img.copy(), orig_size), daemon=True).start()
            
        except Exception as e:
            logging.error(f"Preview error: {e}")

    def _process_preview(self, path, img, orig_size):
        try:
            # Settings
            target_format = self.format_var.get()
            
            w_str = self.width_entry.get()
            h_str = self.height_entry.get()
            custom_w = int(w_str) if w_str.isdigit() else None
            custom_h = int(h_str) if h_str.isdigit() else None
            
            ts_str = self.target_size_entry.get()
            target_kb = float(ts_str) if ts_str.replace('.','',1).isdigit() else None
            
            # Resize
            resized_img = resize_image(img, custom_w, custom_h)
            res_w, res_h = resized_img.size
            
            # Compress (Mock save to memory to get stats)
            quality, img_bytes = compress_image(resized_img, target_format, target_kb)
            
            if img_bytes:
                final_size = len(img_bytes)
                import io
                preview_after_img = Image.open(io.BytesIO(img_bytes))
                
                # Update GUI
                self.after(0, self._update_after_gui, preview_after_img, final_size, orig_size, res_w, res_h, quality, target_format)
                
            img.close()
            resized_img.close()
            
        except Exception as e:
            logging.error(f"Process preview error: {e}")

    def _update_after_gui(self, img, final_size, orig_size, w, h, quality, format):
        self.display_image(img, self.after_img_lbl)
        
        reduction = 0
        if orig_size > 0:
            reduction = ((orig_size - final_size) / orig_size) * 100
            
        stats_text = f"Size: {format_size(final_size)} (-{reduction:.1f}%)\n"
        stats_text += f"Resolution: {w}x{h}\n"
        stats_text += f"Format: {format}"
        if format in ['JPEG', 'WEBP']:
            stats_text += f" (Q: {quality})"
            
        self.after_stats.configure(text=stats_text)

    def display_image(self, img, label):
        # Resize for display only
        img.thumbnail((400, 400), Image.Resampling.LANCZOS)
        ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=img.size)
        label.configure(image=ctk_img, text="")
        label.image = ctk_img

    def export_images(self):
        try:
            if not self.file_paths:
                messagebox.showwarning("No Images", "Please select or drop images first.")
                return
                
            if self.is_processing:
                return
                
            output_dir = filedialog.askdirectory(title="Select Output Folder")
            if not output_dir:
                return
                
            self.is_processing = True
            self.export_btn.configure(state="disabled", text="Processing...")
            self.progress_bar.set(0)
            self.status_lbl.configure(text="Compressing images...")
            
            # Prepare settings
            w_str = self.width_entry.get()
            h_str = self.height_entry.get()
            ts_str = self.target_size_entry.get()
            
            settings = {
                'format': self.format_var.get(),
                'width': int(w_str) if w_str.isdigit() else None,
                'height': int(h_str) if h_str.isdigit() else None,
                'target_size_kb': float(ts_str) if ts_str.replace('.','',1).isdigit() else None,
            }
            
            self.processor = BatchProcessor(
                self.file_paths,
                output_dir,
                settings,
                self.on_progress,
                self.on_complete
            )
            self.processor.start()
        except Exception as e:
            logging.error(f"Error starting export: {e}")
            messagebox.showerror("Error", "An unexpected error occurred while starting export.")
            self.is_processing = False
            self.export_btn.configure(state="normal", text="Export Images")

    def on_progress(self, current, total, current_file):
        # Thread safe update
        def update():
            percent = current / total
            self.progress_bar.set(percent)
            fname = os.path.basename(current_file)
            self.status_lbl.configure(text=f"Compressing: {fname} ({current}/{total} - {int(percent*100)}%)")
        self.after(0, update)

    def on_complete(self, results, cancelled):
        def update():
            self.is_processing = False
            self.export_btn.configure(state="normal", text="Export Images")
            self.progress_bar.set(1)
            
            success_results = [r for r in results if r['success']]
            fail_results = [r for r in results if not r['success']]
            success_count = len(success_results)
            fail_count = len(fail_results)
            
            self.status_lbl.configure(text=f"Done! Successfully processed {success_count} images. Failed: {fail_count}")
            
            if fail_count > 0:
                failed_msg = "\n".join([f"- {os.path.basename(r['file'])}: {r.get('error', 'Unknown error')}" for r in fail_results[:5]])
                if fail_count > 5:
                    failed_msg += f"\n...and {fail_count - 5} more."
                messagebox.showwarning("Export Completed with Errors", f"Successfully processed {success_count} images.\nFailed to process {fail_count} images:\n\n{failed_msg}")
            else:
                messagebox.showinfo("Export Complete", f"Successfully processed {success_count} images.")
                
            # Optional: Clear after success?
            # self.clear_files()
        self.after(0, update)

if __name__ == "__main__":
    app = App()
    app.mainloop()
