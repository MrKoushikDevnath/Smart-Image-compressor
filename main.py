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

appdata = os.getenv("APPDATA")
app_dir = os.path.join(appdata, "SmartImageCompressorPro")
log_dir = os.path.join(app_dir, "logs")
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    filename=os.path.join(log_dir, "app.log"),
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
        self.format_dropdown = ctk.CTkOptionMenu(self.left_panel, values=["JPEG", "JPG", "PNG", "WEBP", "PDF"], variable=self.format_var, command=self.update_preview)
        self.format_dropdown.pack(pady=(5, 0), padx=20, fill="x")
        
        self.format_warning_lbl = ctk.CTkLabel(self.left_panel, text="", text_color="#ff5555", font=ctk.CTkFont(size=11))
        self.format_warning_lbl.pack(pady=(0, 10), padx=20, anchor="w")

        # Resize System
        ctk.CTkLabel(self.left_panel, text="Resize (Optional)", font=ctk.CTkFont(weight="bold")).pack(padx=20, anchor="w")
        
        resize_frame = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        resize_frame.pack(padx=20, pady=(5, 20), fill="x")
        
        self.width_entry = ctk.CTkEntry(resize_frame, placeholder_text="Width (px)", width=100)
        self.width_entry.pack(side="left", padx=(0, 10))
        self.width_entry.bind("<KeyRelease>", self.update_preview_delayed)
        self.width_entry.bind("<FocusOut>", self.update_preview)
        self.width_entry.bind("<Return>", self.update_preview)
        
        self.height_entry = ctk.CTkEntry(resize_frame, placeholder_text="Height (px)", width=100)
        self.height_entry.pack(side="left")
        self.height_entry.bind("<KeyRelease>", self.update_preview_delayed)
        self.height_entry.bind("<FocusOut>", self.update_preview)
        self.height_entry.bind("<Return>", self.update_preview)

        # Smart Compression
        ctk.CTkLabel(self.left_panel, text="Target File Size", font=ctk.CTkFont(weight="bold")).pack(padx=20, anchor="w")
        
        size_frame = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        size_frame.pack(padx=20, pady=(5, 0), fill="x")
        
        self.target_size_entry = ctk.CTkEntry(size_frame, width=140)
        self.target_size_entry.pack(side="left", padx=(0, 10))
        
        self.target_placeholder = "e.g. 500 KB"
        
        def on_focus_in(event):
            if self.target_size_entry.get() == self.target_placeholder:
                self.target_size_entry.delete(0, 'end')
                # Reset to default theme text color
                self.target_size_entry.configure(text_color=ctk.ThemeManager.theme["CTkEntry"]["text_color"])

        def on_focus_out(event):
            if not self.target_size_entry.get():
                self.target_size_entry.insert(0, self.target_placeholder)
                self.target_size_entry.configure(text_color="gray")
            self.update_preview()

        def validate_input(P):
            if P == "" or P == self.target_placeholder:
                return True
            # Allow digits and a single decimal point
            return P.replace('.', '', 1).isdigit()

        vcmd = (self.register(validate_input), '%P')
        self.target_size_entry.configure(validate='key', validatecommand=vcmd)
        
        self.target_size_entry.bind("<FocusIn>", on_focus_in)
        self.target_size_entry.bind("<FocusOut>", on_focus_out)
        self.target_size_entry.bind("<KeyRelease>", self.update_preview_delayed)
        self.target_size_entry.bind("<Return>", self.update_preview)
        
        # Set initial placeholder
        self.target_size_entry.insert(0, self.target_placeholder)
        self.target_size_entry.configure(text_color="gray")
        
        self.size_unit_var = ctk.StringVar(value="KB")
        self.size_unit_dropdown = ctk.CTkOptionMenu(size_frame, values=["KB", "MB"], variable=self.size_unit_var, command=self.update_size_placeholder, width=60)
        self.size_unit_dropdown.pack(side="left")
        
        self.size_hint_lbl = ctk.CTkLabel(self.left_panel, text="Target size must be smaller than original size", font=ctk.CTkFont(size=11), text_color="gray")
        self.size_hint_lbl.pack(padx=20, anchor="w", pady=(0, 20))

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
        
    def update_size_placeholder(self, *args):
        unit = self.size_unit_var.get()
        old_placeholder = getattr(self, 'target_placeholder', "e.g. 500 KB")
        if unit == "KB":
            self.target_placeholder = "e.g. 500 KB"
        else:
            self.target_placeholder = "e.g. 1 MB"
            
        if hasattr(self, 'target_size_entry'):
            if self.target_size_entry.get() == old_placeholder:
                self.target_size_entry.delete(0, 'end')
                self.target_size_entry.insert(0, self.target_placeholder)
                self.target_size_entry.configure(text_color="gray")
                
        self.update_preview()
        
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
        self.clear_files()
        
        for f in files:
            if f not in self.file_paths:
                self.file_paths.append(f)
        
        self.file_count_lbl.configure(text=f"{len(self.file_paths)} files selected")
        if self.file_paths:
            self.preview_image_path = self.file_paths[-1]
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
            
        if not hasattr(self, 'preview_request_id'):
            self.preview_request_id = 0
        self.preview_request_id += 1
            
        # Run everything in a thread so UI never freezes for large images
        threading.Thread(target=self._process_preview_thread, args=(self.preview_image_path, self.preview_request_id), daemon=True).start()

    def _process_preview_thread(self, path, request_id):
        try:
            # Display 'Loading' text if needed or just let it process
            orig_img = Image.open(path)
            orig_size = os.path.getsize(path)
            orig_w, orig_h = orig_img.size
            orig_format = orig_img.format
            
            # Create a copy for the after processing
            img_for_after = orig_img.copy()
            
            # Generate thumbnail for 'Before' image in background
            orig_img.thumbnail((400, 400), Image.Resampling.LANCZOS)
            
            def update_before_gui():
                ctk_img = ctk.CTkImage(light_image=orig_img, dark_image=orig_img, size=orig_img.size)
                self.before_img_lbl.configure(image=ctk_img, text="")
                self.before_img_lbl.image = ctk_img
                self.before_stats.configure(text=f"Size: {format_size(orig_size)}\nDimension: {orig_w}x{orig_h}\nFormat: {orig_format}")
            self.after(0, update_before_gui)
            
            # Process 'After' image
            target_format = self.format_var.get()
            
            w_str = self.width_entry.get()
            h_str = self.height_entry.get()
            custom_w = int(w_str) if w_str.isdigit() else None
            custom_h = int(h_str) if h_str.isdigit() else None
            
            ts_str = self.target_size_entry.get()
            target_kb = float(ts_str) if ts_str.replace('.','',1).isdigit() else None
            
            # Reset format warning label
            self.after(0, lambda: [
                self.format_warning_lbl.configure(text=""),
                self.size_hint_lbl.configure(text_color="gray")
            ])
            
            if self.preview_request_id != request_id: return
            
            allow_resolution_reduction = True
            if target_kb is None:
                target_kb = orig_size / 1024.0
                allow_resolution_reduction = False
            else:
                user_target_kb = target_kb
                if self.size_unit_var.get() == "MB":
                    user_target_kb *= 1024
                    
                if user_target_kb * 1024 >= orig_size:
                    self.after(0, lambda: self.size_hint_lbl.configure(text_color="#ff5555"))
                target_kb = user_target_kb
            
            if self.preview_request_id != request_id: return
            
            # Resize
            resized_img = resize_image(img_for_after, custom_w, custom_h)
            res_w, res_h = resized_img.size
            
            if self.preview_request_id != request_id: return
            
            # Compress (Mock save to memory to get stats)
            quality, img_bytes, info = compress_image(resized_img, target_format, target_kb, allow_resolution_reduction)
            
            if self.preview_request_id != request_id: return
            
            if img_bytes:
                final_size = len(img_bytes)
                import io
                preview_after_img = Image.open(io.BytesIO(img_bytes))
                preview_after_img.thumbnail((400, 400), Image.Resampling.LANCZOS)
                
                # Update GUI
                self.after(0, self._update_after_gui, preview_after_img, final_size, orig_size, res_w, res_h, quality, target_format, info)
                
            img_for_after.close()
            resized_img.close()
            
        except Exception as e:
            logging.error(f"Process preview error: {e}")

    def _update_after_gui(self, img, final_size, orig_size, w, h, quality, format, info=None):
        ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=img.size)
        self.after_img_lbl.configure(image=ctk_img, text="")
        self.after_img_lbl.image = ctk_img
        
        reduction = 0
        if orig_size > 0:
            reduction = ((orig_size - final_size) / orig_size) * 100
            
        stats_text = f"Size: {format_size(final_size)} (-{reduction:.1f}%)\n"
        stats_text += f"Dimension: {w}x{h}\n"
        stats_text += f"Format: {format}"
        if format in ['JPEG', 'WEBP']:
            stats_text += f" (Q: {quality})"
            
        if info:
            if info.get('target_unreachable'):
                stats_text += "\n[!] Target unreachable. Closest size achieved."
            elif info.get('resolution_reduced'):
                stats_text += "\n[*] Resolution reduced to meet target."
            
        self.after_stats.configure(text=stats_text)

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
            
            target_kb = float(ts_str) if ts_str.replace('.','',1).isdigit() else None
            if target_kb is not None:
                user_target_kb = target_kb
                if self.size_unit_var.get() == "MB":
                    user_target_kb *= 1024
                target_kb = user_target_kb
                
                # Target size is passed to the processor, which handles unreachable targets gracefully.
            
            settings = {
                'format': self.format_var.get(),
                'width': int(w_str) if w_str.isdigit() else None,
                'height': int(h_str) if h_str.isdigit() else None,
                'target_size_kb': target_kb,
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
                unreachable_count = sum(1 for r in success_results if r.get('info', {}).get('target_unreachable'))
                msg = f"Successfully processed {success_count} images."
                if unreachable_count > 0:
                    msg += f"\n\nNote: {unreachable_count} image(s) could not reach the exact target size while maintaining usability. Target size reached as close as possible."
                    messagebox.showwarning("Export Complete with Warnings", msg)
                else:
                    messagebox.showinfo("Export Complete", msg)
                
            # Optional: Clear after success?
            # self.clear_files()
        self.after(0, update)

def create_desktop_shortcut():
    import sys
    import subprocess
    try:
        if getattr(sys, 'frozen', False):
            exe_path = sys.executable
        else:
            return

        desktop_path = os.path.join(os.environ['USERPROFILE'], 'Desktop')
        shortcut_path = os.path.join(desktop_path, "Smart Image Compressor Pro.lnk")

        if not os.path.exists(shortcut_path):
            ps_script = f'''
            $WshShell = New-Object -comObject WScript.Shell
            $Shortcut = $WshShell.CreateShortcut("{shortcut_path}")
            $Shortcut.TargetPath = "{exe_path}"
            $Shortcut.WorkingDirectory = "{os.path.dirname(exe_path)}"
            $Shortcut.Save()
            '''
            subprocess.run(["powershell", "-Command", ps_script], creationflags=subprocess.CREATE_NO_WINDOW)
    except Exception as e:
        logging.error(f"Failed to create desktop shortcut: {e}")

if __name__ == "__main__":
    create_desktop_shortcut()
    app = App()
    app.mainloop()
