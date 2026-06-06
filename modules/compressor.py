import io
import logging
from PIL import Image

def compress_image(img: Image.Image, target_format: str, target_size_kb: float = None, allow_resolution_reduction: bool = True) -> tuple:
    """
    Compresses an image to be under the target_size_kb if possible.
    Returns (quality_used: int|str, compressed_bytes: bytes, info: dict)
    """
    target_format = target_format.upper()
    if target_format == 'JPG':
        target_format = 'JPEG'
        
    info = {
        'resolution_reduced': False,
        'target_unreachable': False
    }

    def save_to_bytes(image, fmt, q=None):
        buf = io.BytesIO()
        kwargs = {'format': fmt}
        if fmt in ['JPEG', 'WEBP'] and q is not None:
            kwargs['quality'] = q
        if fmt == 'JPEG':
            kwargs['optimize'] = True
            kwargs['subsampling'] = 0
        if fmt == 'PNG':
            kwargs['optimize'] = True
            
        img_to_save = image
        if fmt == 'JPEG' and img_to_save.mode in ('RGBA', 'P'):
            img_to_save = image.convert('RGB')
        elif fmt == 'PDF' and img_to_save.mode == 'RGBA':
            img_to_save = image.convert('RGB')
            
        try:
            img_to_save.save(buf, **kwargs)
            res = buf.getvalue()
        except Exception as e:
            # Fallback if optimize=True fails on large JPEGs ("Suspension not allowed here")
            if kwargs.get('optimize'):
                kwargs['optimize'] = False
                try:
                    buf = io.BytesIO()
                    img_to_save.save(buf, **kwargs)
                    res = buf.getvalue()
                except Exception as e2:
                    logging.error(f"Save error (fallback): {e2}")
                    res = b''
            else:
                logging.error(f"Save error: {e}")
                res = b''
            
        if img_to_save is not image:
            img_to_save.close()
            
        return res

    # 1. No target size provided
    if not target_size_kb:
        q = 95 if target_format in ['JPEG', 'WEBP'] else 100
        return q, save_to_bytes(img, target_format, q), info

    target_bytes = int(target_size_kb * 1024)
    
    # Formats that don't support quality adjustments (PNG, PDF)
    if target_format not in ['JPEG', 'WEBP']:
        best_bytes = save_to_bytes(img, target_format)
        if len(best_bytes) <= target_bytes:
            return 100, best_bytes, info
        else:
            if not allow_resolution_reduction:
                info['target_unreachable'] = True
                return 100, best_bytes, info
            # Resolution reduction pipeline for formats without quality
            scale = 0.9
            current_img = img
            while scale >= 0.1:
                new_w = max(1, int(img.width * scale))
                new_h = max(1, int(img.height * scale))
                resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                b = save_to_bytes(resized, target_format)
                resized.close()
                if len(b) <= target_bytes:
                    info['resolution_reduced'] = True
                    return 100, b, info
                scale -= 0.1
                current_img = resized
                
            info['resolution_reduced'] = True
            info['target_unreachable'] = True
            # Return lowest resolution attempted
            new_w = max(1, int(img.width * 0.1))
            new_h = max(1, int(img.height * 0.1))
            resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            b = save_to_bytes(resized, target_format)
            resized.close()
            return 100, b, info

    # Stage 1: Optimize metadata and encoding at highest quality
    best_bytes = save_to_bytes(img, target_format, 100)
    if len(best_bytes) <= target_bytes:
        return 100, best_bytes, info
        
    best_bytes = save_to_bytes(img, target_format, 95)
    if len(best_bytes) <= target_bytes:
        return 95, best_bytes, info
        
    # Stage 2: Adaptive binary search
    low = 10
    high = 94
    best_quality = 10
    best_valid_bytes = None
    
    while low <= high:
        mid = (low + high) // 2
        b = save_to_bytes(img, target_format, mid)
        if not b:
            break
        
        size = len(b)
        if size <= target_bytes:
            best_quality = mid
            best_bytes = b
            low = mid + 1
        else:
            high = mid - 1

    # Adaptive Fine-tuning (Linear Search upward to find max possible quality)
    # Check if we can push the quality a bit higher due to non-linear compression
    if len(best_bytes) <= target_bytes:
        current_q = best_quality + 1
        while current_q <= 94:
            b = save_to_bytes(img, target_format, current_q)
            if b and len(b) <= target_bytes:
                # Still under target, keep it!
                best_quality = current_q
                best_bytes = b
                current_q += 1
            else:
                # We hit the ceiling
                break

    # Check if even quality 10 is too big
    if len(best_bytes) > target_bytes:
        if not allow_resolution_reduction:
            info['target_unreachable'] = True
            return 10, best_bytes, info
            
        # Step 3: Resolution reduction
        info['resolution_reduced'] = True
        scale = 0.95
        while scale >= 0.05:
            new_w = max(1, int(img.width * scale))
            new_h = max(1, int(img.height * scale))
            resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            b = save_to_bytes(resized, target_format, 10)
            resized.close()
            if len(b) <= target_bytes:
                return 10, b, info
            scale -= 0.05
            
        info['target_unreachable'] = True
        new_w = max(1, int(img.width * 0.05))
        new_h = max(1, int(img.height * 0.05))
        resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        b = save_to_bytes(resized, target_format, 10)
        resized.close()
        return 10, b, info
        
    return best_quality, best_bytes, info
