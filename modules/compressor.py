import io
import logging
from PIL import Image

def compress_image(img: Image.Image, target_format: str, target_size_kb: float = None) -> tuple:
    """
    Compresses an image to be under the target_size_kb if possible.
    Returns (quality_used: int, compressed_bytes: bytes)
    """
    target_format = target_format.upper()
    if target_format == 'JPG':
        target_format = 'JPEG'

    # If no target size is provided, or format doesn't support quality adjustments (PNG, PDF)
    if not target_size_kb or target_format not in ['JPEG', 'WEBP']:
        # Just use high quality or default settings
        buffer = io.BytesIO()
        save_kwargs = {'format': target_format}
        if target_format in ['JPEG', 'WEBP']:
            save_kwargs['quality'] = 95
        if target_format == 'PNG':
            save_kwargs['optimize'] = True
        
        try:
            img_to_save = img
            if target_format == 'JPEG' and img_to_save.mode in ('RGBA', 'P'):
                # Convert RGBA/P to RGB for JPEG
                img_to_save = img.convert('RGB')
            elif target_format == 'PDF' and img_to_save.mode == 'RGBA':
                # Convert RGBA to RGB for PDF usually
                img_to_save = img.convert('RGB')
                
            img_to_save.save(buffer, **save_kwargs)
            return 95 if target_format in ['JPEG', 'WEBP'] else 100, buffer.getvalue()
        except Exception as e:
            logging.error(f"Save error: {e}")
            return 100, b''
        finally:
            if img_to_save is not img:
                img_to_save.close()

    target_bytes = int(target_size_kb * 1024)
    
    # Binary search for the best quality
    low = 1
    high = 100
    best_quality = 1
    best_bytes = b''
    
    img_to_save = img
    if target_format == 'JPEG' and img_to_save.mode in ('RGBA', 'P'):
        img_to_save = img_to_save.convert('RGB')

    while low <= high:
        mid = (low + high) // 2
        buffer = io.BytesIO()
        save_kwargs = {'format': target_format, 'quality': mid}
            
        try:
            img_to_save.save(buffer, **save_kwargs)
            size = buffer.tell()
            
            if size <= target_bytes:
                best_quality = mid
                best_bytes = buffer.getvalue()
                low = mid + 1 # Try to get higher quality
            else:
                high = mid - 1 # Reduce quality
        except Exception as e:
            logging.error(f"Error during compression: {e}")
            break
            
    # If even quality 1 is larger than target, just return quality 1
    if not best_bytes:
        buffer = io.BytesIO()
        save_kwargs = {'format': target_format, 'quality': 1}
        try:
            img_to_save.save(buffer, **save_kwargs)
            best_bytes = buffer.getvalue()
        except:
            pass
        best_quality = 1

    if img_to_save is not img:
        img_to_save.close()

    return best_quality, best_bytes

